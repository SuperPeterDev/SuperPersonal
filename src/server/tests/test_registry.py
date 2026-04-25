import pytest
import platform
from src.client.core.registry import ExecutorRegistry
from src.client.core.executor import CommandExecutor
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandType, CommandStatus


class AlwaysAvailableExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        return CommandResult(status=CommandStatus.SUCCESS, output="ok")
    def is_available(self) -> bool:
        return True


class NeverAvailableExecutor(CommandExecutor):
    def execute(self, payload: CommandPayload) -> CommandResult:
        return CommandResult(status=CommandStatus.SUCCESS, output="ok")
    def is_available(self) -> bool:
        return False


class TestExecutorRegistry:

    def test_get_executor_returns_instance_when_available(self):
        ExecutorRegistry._executors[CommandType.CMD_PING] = AlwaysAvailableExecutor
        executor = ExecutorRegistry.get_executor(CommandType.CMD_PING)
        assert isinstance(executor, AlwaysAvailableExecutor)

    def test_get_executor_raises_when_unavailable(self):
        ExecutorRegistry._executors[CommandType.CMD_MEDIA] = NeverAvailableExecutor
        with pytest.raises(EnvironmentError, match="not available on this platform"):
            ExecutorRegistry.get_executor(CommandType.CMD_MEDIA)

    def test_default_is_available_returns_true(self):
        executor = AlwaysAvailableExecutor()
        assert executor.is_available() is True

    def test_media_executor_unavailable_on_linux(self):
        if platform.system() == "Windows":
            pytest.skip("Only runs on Linux CI")
        from src.client.executors.media_executors import MediaExecutor
        assert MediaExecutor().is_available() is False

    def test_volume_executor_unavailable_on_linux(self):
        if platform.system() == "Windows":
            pytest.skip("Only runs on Linux CI")
        from src.client.executors.media_executors import VolumeExecutor
        assert VolumeExecutor().is_available() is False
