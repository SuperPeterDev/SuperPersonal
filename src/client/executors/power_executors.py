import os
import platform
import subprocess
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

@ExecutorRegistry.register(CommandType.CMD_SCHEDULED_SHUTDOWN)
class ScheduledShutdownExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        seconds = payload.seconds if payload.seconds is not None else 60
        
        if platform.system() == "Windows":
            os.system(f"shutdown /s /t {int(seconds)}")
        else:
            # Linux/Mac usually use -h +minutes or similar. 
            # safe fallback: shutdown -h +{min}
            minutes = max(1, int(seconds/60))
            os.system(f"shutdown -h +{minutes}")
            
        return CommandResult(status=CommandStatus.SUCCESS, output=f"Shutdown scheduled in {seconds}s")

# Implement others if needed (CMD_SHUTDOWN, CMD_RESTART, CMD_LOCK_PC)
# For now, following what was in client.py plus the enum hints

@ExecutorRegistry.register(CommandType.CMD_SHUTDOWN)
class ShutdownExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if platform.system() == "Windows":
            os.system("shutdown /s /t 0")
        else:
            os.system("shutdown -h now")
        return CommandResult(status=CommandStatus.SUCCESS, output="Shutting down immediately")

@ExecutorRegistry.register(CommandType.CMD_RESTART)
class RestartExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if platform.system() == "Windows":
            os.system("shutdown /r /t 0")
        else:
            os.system("shutdown -r now")
        return CommandResult(status=CommandStatus.SUCCESS, output="Restarting immediately")

@ExecutorRegistry.register(CommandType.CMD_LOCK_PC)
class LockExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return CommandResult(status=CommandStatus.SUCCESS, output="PC Locked")
        else:
            return CommandResult(status=CommandStatus.FAILED, output="Lock not supported on non-Windows yet")
