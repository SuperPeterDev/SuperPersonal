import pytest
from unittest.mock import patch, MagicMock
import io
import sys
from PIL import Image

from src.shared.schemas import CommandPayload
from src.shared.enums import CommandStatus


class TestScreenshotExecutor:
    def _make_fake_screenshot(self):
        img = Image.new('RGB', (100, 100), color=(73, 109, 137))
        return img

    def test_returns_data_url(self):
        # Pre-load mock pyautogui to avoid X11 import errors on Linux
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = self._make_fake_screenshot()

        with patch.dict('sys.modules', {'pyautogui': mock_pyautogui}):
            from src.client.executors.screenshot_executor import ScreenshotExecutor
            executor = ScreenshotExecutor()
            result = executor.execute(CommandPayload())

        assert result.status == CommandStatus.SUCCESS
        assert result.output.startswith('data:image/jpeg;base64,')

    def test_output_is_valid_jpeg(self):
        mock_pyautogui = MagicMock()
        mock_pyautogui.screenshot.return_value = self._make_fake_screenshot()

        with patch.dict('sys.modules', {'pyautogui': mock_pyautogui}):
            from src.client.executors.screenshot_executor import ScreenshotExecutor
            executor = ScreenshotExecutor()
            result = executor.execute(CommandPayload())

        import base64
        b64_data = result.output.split(',', 1)[1]
        raw = base64.b64decode(b64_data)
        loaded = Image.open(io.BytesIO(raw))
        assert loaded.format == 'JPEG'


class TestShellExecExecutor:
    def test_returns_stdout(self):
        from src.client.executors.shell_executor import ShellExecExecutor
        executor = ShellExecExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='hello\n', stderr='', returncode=0)
            result = executor.execute(CommandPayload(command_str='echo hello'))

        assert result.status == CommandStatus.SUCCESS
        assert 'hello' in result.output

    def test_empty_command_fails(self):
        from src.client.executors.shell_executor import ShellExecExecutor
        executor = ShellExecExecutor()
        result = executor.execute(CommandPayload(command_str=None))
        assert result.status == CommandStatus.FAILED

    def test_stderr_included_in_output(self):
        from src.client.executors.shell_executor import ShellExecExecutor
        executor = ShellExecExecutor()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='', stderr='error msg\n', returncode=1)
            result = executor.execute(CommandPayload(command_str='bad_cmd'))

        assert 'error msg' in result.output
