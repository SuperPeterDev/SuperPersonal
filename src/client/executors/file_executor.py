import json
from pathlib import Path
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus

_READ_LIMIT_BYTES = 100 * 1024  # 100 KB


@ExecutorRegistry.register(CommandType.CMD_FILE_LIST)
class FileListExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.path:
            return CommandResult(status=CommandStatus.FAILED, output="No path provided")

        p = Path(payload.path)
        if not p.exists():
            return CommandResult(status=CommandStatus.FAILED, output=f"Path not found: {payload.path}")

        if p.is_file():
            items = [{"name": p.name, "type": "file", "size": p.stat().st_size}]
        else:
            items = []
            for child in sorted(p.iterdir()):
                try:
                    items.append({
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else None,
                        "path": str(child)
                    })
                except PermissionError:
                    pass

        return CommandResult(status=CommandStatus.SUCCESS, output=json.dumps(items))


@ExecutorRegistry.register(CommandType.CMD_FILE_READ)
class FileReadExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        if not payload.path:
            return CommandResult(status=CommandStatus.FAILED, output="No path provided")

        p = Path(payload.path)
        if not p.is_file():
            return CommandResult(status=CommandStatus.FAILED, output=f"Not a file: {payload.path}")

        try:
            raw = p.read_bytes()[:_READ_LIMIT_BYTES]
            try:
                text = raw.decode('utf-8', errors='replace')
            except Exception:
                text = f"[binary file, {p.stat().st_size} bytes]"
            return CommandResult(status=CommandStatus.SUCCESS, output=text)
        except PermissionError:
            return CommandResult(status=CommandStatus.FAILED, output=f"Permission denied: {payload.path}")
