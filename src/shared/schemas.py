from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from .enums import CommandType, CommandStatus
import uuid

class CommandPayload(BaseModel):
    url: Optional[str] = None
    seconds: Optional[int] = None
    level: Optional[int] = None
    mute: Optional[bool] = None
    action: Optional[str] = None
    command_str: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

class Command(BaseModel):
    pk_command_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None # Optional as client might not know its DB PK immediately or not needed for exec
    command_type: CommandType
    payload: CommandPayload = Field(default_factory=CommandPayload)
    status: CommandStatus
    created_at: datetime
    executed_at: Optional[datetime] = None

class CommandResult(BaseModel):
    status: CommandStatus
    output: str = ""
    error_trace: str = ""
