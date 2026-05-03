import pytest
from unittest.mock import patch, MagicMock
import io
import sys
import psutil
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


import json
from src.client.executors.system_advanced_executors import (
    ListProcessesExecutor, KillProcessExecutor,
    ClipboardGetExecutor, ClipboardSetExecutor,
)


class TestProcessExecutors:
    def test_list_processes_returns_json_list(self):
        executor = ListProcessesExecutor()
        with patch('psutil.process_iter') as mock_iter:
            mock_proc = MagicMock()
            mock_proc.info = {'pid': 1, 'name': 'test.exe', 'cpu_percent': 0.5, 'memory_percent': 1.2}
            mock_iter.return_value = [mock_proc]
            result = executor.execute(CommandPayload())

        assert result.status == CommandStatus.SUCCESS
        processes = json.loads(result.output)
        assert processes[0]['pid'] == 1
        assert processes[0]['name'] == 'test.exe'

    def test_kill_process_calls_kill(self):
        executor = KillProcessExecutor()
        with patch('psutil.Process') as MockProc:
            result = executor.execute(CommandPayload(pid=9999))
            MockProc.return_value.kill.assert_called_once()

        assert result.status == CommandStatus.SUCCESS

    def test_kill_process_missing_pid_fails(self):
        executor = KillProcessExecutor()
        result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED

    def test_list_processes_handles_psutil_error(self):
        executor = ListProcessesExecutor()
        with patch('psutil.process_iter', side_effect=psutil.AccessDenied()):
            result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED


class TestClipboardExecutors:
    def test_clipboard_get_returns_text(self):
        executor = ClipboardGetExecutor()
        with patch('pyperclip.paste', return_value='copied text'):
            result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.SUCCESS
        assert result.output == 'copied text'

    def test_clipboard_set_writes_text(self):
        executor = ClipboardSetExecutor()
        with patch('pyperclip.copy') as mock_copy:
            result = executor.execute(CommandPayload(text='new text'))
            mock_copy.assert_called_once_with('new text')
        assert result.status == CommandStatus.SUCCESS

    def test_clipboard_set_missing_text_fails(self):
        executor = ClipboardSetExecutor()
        result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED

    def test_clipboard_get_handles_pyperclip_error(self):
        executor = ClipboardGetExecutor()
        with patch('pyperclip.paste', side_effect=Exception("no clipboard")):
            result = executor.execute(CommandPayload())
        assert result.status == CommandStatus.FAILED

    def test_clipboard_set_handles_pyperclip_error(self):
        executor = ClipboardSetExecutor()
        with patch('pyperclip.copy', side_effect=Exception("no clipboard")):
            result = executor.execute(CommandPayload(text='test'))
        assert result.status == CommandStatus.FAILED


from src.client.executors.file_executor import FileListExecutor, FileReadExecutor


class TestFileExecutors:
    def test_file_list_returns_json(self, tmp_path):
        (tmp_path / "foo.txt").write_text("hello")
        (tmp_path / "bar.py").write_text("world")
        executor = FileListExecutor()
        result = executor.execute(CommandPayload(path=str(tmp_path)))

        assert result.status == CommandStatus.SUCCESS
        items = json.loads(result.output)
        names = [i['name'] for i in items]
        assert 'foo.txt' in names
        assert 'bar.py' in names

    def test_file_list_nonexistent_path_fails(self):
        executor = FileListExecutor()
        result = executor.execute(CommandPayload(path="/nonexistent/path"))
        assert result.status == CommandStatus.FAILED

    def test_file_read_returns_text(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("file contents here")
        executor = FileReadExecutor()
        result = executor.execute(CommandPayload(path=str(f)))
        assert result.status == CommandStatus.SUCCESS
        assert result.output == "file contents here"

    def test_file_read_limits_size(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("x" * 200_000)
        executor = FileReadExecutor()
        result = executor.execute(CommandPayload(path=str(f)))
        assert result.status == CommandStatus.SUCCESS
        assert len(result.output) <= 102_500  # 100KB limit (102400 bytes) + small overhead
