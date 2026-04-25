from abc import ABC, abstractmethod
from typing import Any, Dict
import threading
from src.shared.schemas import CommandPayload, CommandResult
from src.shared.enums import CommandStatus

class CommandExecutor(ABC):
    """Abstract base class for all command executors."""


    def is_available(self) -> bool:
        """
        Returns True if this executor can run on the current platform/environment.
        Override in subclasses for OS-specific executors.
        """
        return True

    @abstractmethod
    def execute(self, payload: CommandPayload) -> CommandResult:
        """
        Execute the command with the given payload.
        Returns a CommandResult.
        """
        pass

    def run_async(self, payload: CommandPayload, callback):
        """
        Runs execute in a separate thread and calls callback with result.
        """
        def wrapper():
            try:
                result = self.execute(payload)
            except Exception as e:
                result = CommandResult(
                    status=CommandStatus.FAILED,
                    error_trace=str(e),
                    output="Execution Exception"
                )
            callback(result)
        
        t = threading.Thread(target=wrapper)
        t.daemon = True
        t.start()
