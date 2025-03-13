from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentCommandRequest(BaseModel):
    """Schema for sending a natural language command to the agent."""

    command: str = Field(
        ..., min_length=3, description="Natural language command for the agent"
    )


class CommandResponse(BaseModel):
    """Base schema for agent command responses."""

    success: bool
    message: str
    command_type: str


class EventCommandResponse(CommandResponse):
    """Schema for event-related command responses."""

    event_id: Optional[int] = None
    event: Optional[Dict[str, Any]] = None
    events: Optional[List[Dict[str, Any]]] = None
    date_range: Optional[Dict[str, str]] = None


class TaskCommandResponse(CommandResponse):
    """Schema for task-related command responses."""

    task_id: Optional[int] = None
    task: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None


class AgentCommandResponse(BaseModel):
    """Schema for general agent command responses."""

    response: Dict[str, Any]
