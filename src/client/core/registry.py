from typing import Dict, Type
from src.shared.enums import CommandType
from .executor import CommandExecutor

class ExecutorRegistry:
    _executors: Dict[CommandType, Type[CommandExecutor]] = {}

    @classmethod
    def register(cls, command_type: CommandType):
        def decorator(executor_cls: Type[CommandExecutor]):
            cls._executors[command_type] = executor_cls
            return executor_cls
        return decorator

    @classmethod
    def get_executor(cls, command_type: CommandType) -> CommandExecutor:
        executor_cls = cls._executors.get(command_type)
        if not executor_cls:
            raise ValueError(f"No executor registered for {command_type}")
        return executor_cls()
