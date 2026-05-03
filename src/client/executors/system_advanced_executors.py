import json
import psutil
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_LIST_PROCESSES)
class ListProcessesExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                processes.append(proc.info)
        except psutil.Error as e:
            return CommandResult(status=CommandStatus.FAILED, output=f"Process scan failed: {e}")
        processes.sort(key=lambda p: p.get('memory_percent', 0), reverse=True)
        return CommandResult(status=CommandStatus.SUCCESS, output=json.dumps(processes[:50]))


@ExecutorRegistry.register(CommandType.CMD_KILL_PROCESS)
class KillProcessExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.pid is None:
            return CommandResult(status=CommandStatus.FAILED, output="No PID provided")
        try:
            psutil.Process(payload.pid).kill()
            return CommandResult(status=CommandStatus.SUCCESS, output=f"Killed PID {payload.pid}")
        except psutil.NoSuchProcess:
            return CommandResult(status=CommandStatus.FAILED, output=f"No process with PID {payload.pid}")
        except psutil.AccessDenied:
            return CommandResult(status=CommandStatus.FAILED, output=f"Access denied killing PID {payload.pid}")


@ExecutorRegistry.register(CommandType.CMD_CLIPBOARD_GET)
class ClipboardGetExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        import pyperclip
        try:
            text = pyperclip.paste()
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, output=f"Clipboard read failed: {e}")
        return CommandResult(status=CommandStatus.SUCCESS, output=text)


@ExecutorRegistry.register(CommandType.CMD_CLIPBOARD_SET)
class ClipboardSetExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if payload.text is None:
            return CommandResult(status=CommandStatus.FAILED, output="No text provided")
        import pyperclip
        try:
            pyperclip.copy(payload.text)
        except Exception as e:
            return CommandResult(status=CommandStatus.FAILED, output=f"Clipboard write failed: {e}")
        return CommandResult(status=CommandStatus.SUCCESS, output=f"Clipboard set ({len(payload.text)} chars)")
