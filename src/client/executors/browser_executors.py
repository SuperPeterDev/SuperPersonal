import webbrowser
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

@ExecutorRegistry.register(CommandType.CMD_OPEN_BROWSER)
class OpenBrowserExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.url:
            webbrowser.open(payload.url)
            return CommandResult(status=CommandStatus.SUCCESS, output=f"Opened {payload.url}")
        return CommandResult(status=CommandStatus.FAILED, output="No URL provided")

@ExecutorRegistry.register(CommandType.CMD_OPEN_PRESET)
class OpenPresetExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.url:
            webbrowser.open(payload.url)
            return CommandResult(status=CommandStatus.SUCCESS, output=f"Opened preset {payload.url}")
        return CommandResult(status=CommandStatus.FAILED, output="No URL provided")
