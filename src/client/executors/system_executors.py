import psutil
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

@ExecutorRegistry.register(CommandType.CMD_PING)
class PingExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        return CommandResult(status=CommandStatus.SUCCESS, output="Pong")

@ExecutorRegistry.register(CommandType.CMD_SYSTEM_INFO)
class SystemInfoExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        return CommandResult(
            status=CommandStatus.SUCCESS, 
            output=f"CPU: {cpu}% | RAM: {ram}%"
        )
