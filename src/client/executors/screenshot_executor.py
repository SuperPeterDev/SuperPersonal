import io
import base64
from src.client.core.executor import CommandExecutor
from src.client.core.registry import ExecutorRegistry
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


@ExecutorRegistry.register(CommandType.CMD_SCREENSHOT)
class ScreenshotExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        import pyautogui

        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.convert('RGB').save(buffer, format='JPEG', quality=60)
        b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return CommandResult(
            status=CommandStatus.SUCCESS,
            output=f"data:image/jpeg;base64,{b64}"
        )
