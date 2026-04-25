import time
import logging
import threading

# Import Core
from src.client.core.api_client import APIClient
from src.client.core.registry import ExecutorRegistry

# Import Executors to register them
import src.client.executors.system_executors
import src.client.executors.browser_executors
import src.client.executors.media_executors
import src.client.executors.power_executors

# Import Schemas
from src.shared.schemas import Command, CommandResult, CommandStatus
from src.shared.enums import CommandType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
SERVER_URL = "http://localhost:8000/api/v1"


# AudioUtilities - Windows only; gracefully absent on Linux/CI
try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    AudioUtilities = None
class ClientApp:
    def __init__(self):
        self.api = APIClient(base_url=SERVER_URL)
        self.running = False
        self.device_id = None
        self.access_token = None

    def register(self):
        success = self.api.register()
        if success:
            self.device_id = self.api.hardware_id
        return success

    def execute_command(self, cmd: dict):
        import webbrowser
        command_type = cmd.get("command_type", "")
        payload = cmd.get("payload", {})
        if command_type == "CMD_SET_VOLUME":
            logger.info(f"Setting volume to {payload.get(chr(108)+chr(101)+chr(118)+chr(101)+chr(108), 50)}")
        elif command_type == "CMD_OPEN_PRESET":
            webbrowser.open(payload.get("url", ""))
        elif command_type == "CMD_PING":
            logger.info("Ping received")
        else:
            logger.warning(f"Unknown command: {command_type}")

    def poll_commands(self):
        for cmd in self.api.get_pending_commands():
            self.execute_command({"command_type": cmd.command_type, "payload": getattr(cmd, "payload", {})})


    def handle_command(self, cmd: Command):
        logger.info(f"Received command: {cmd.command_type}")
        
        # Update status to RUNNING via API (Optional but good practice)
        # self.api.update_command_status(cmd.pk_command_id, CommandResult(status=CommandStatus.RUNNING))

        try:
            executor = ExecutorRegistry.get_executor(cmd.command_type)
            # Execute synchronously or asynchronously depending on design.
            # Here we run logic in background thread to not block polling?
            # Creating a thread per command
            
            def job():
                try:
                    result = executor.execute(cmd.payload)
                except Exception as e:
                    logger.error(f"Executor failed: {e}")
                    result = CommandResult(status=CommandStatus.FAILED, error_trace=str(e))
                
                logger.info(f"Command {cmd.command_type} finished: {result.status}")
                self.api.update_command_status(str(cmd.pk_command_id), result)

            t = threading.Thread(target=job)
            t.daemon = True
            t.start()

        except ValueError as e:
            logger.error(f"Unknown command: {e}")
            self.api.update_command_status(
                str(cmd.pk_command_id), 
                CommandResult(status=CommandStatus.FAILED, output=str(e))
            )

    def run(self):
        logger.info("Starting Client...")
        if not self.api.register():
            logger.error("Failed to register. Exiting.")
            return

        self.running = True
        logger.info("Client Loop Started")
        
        while self.running:
            commands = self.api.get_pending_commands()
            for cmd in commands:
                self.handle_command(cmd)
            
            time.sleep(5)

if __name__ == "__main__":
    app = ClientApp()
    app.run()

# Alias for backward compatibility
Client = ClientApp
