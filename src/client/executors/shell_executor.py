import subprocess
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_SHELL_EXEC)
class ShellExecExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.command_str:
            return CommandResult(status=CommandStatus.FAILED, output="No command provided")

        try:
            proc = subprocess.run(
                payload.command_str,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            combined = proc.stdout + proc.stderr
            return CommandResult(status=CommandStatus.SUCCESS, output=combined.strip())
        except subprocess.TimeoutExpired:
            return CommandResult(status=CommandStatus.FAILED, output="Command timed out (30s limit)")
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, output=str(e))
