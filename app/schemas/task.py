from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ARCHIVED = "archived"


class TaskBase(BaseModel):
    """Base schema for Task."""

    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    reminder_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    pass


class TaskUpdate(BaseModel):
    """Schema for updating an existing task."""

    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[PriorityLevel] = None
    status: Optional[TaskStatus] = None
    reminder_date: Optional[datetime] = None


class TaskInDB(TaskBase):
    """Task schema as stored in database."""

    id: int
    user_id: int
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Task(TaskInDB):
    """Schema for task response."""

    pass


class NaturalLanguageTaskRequest(BaseModel):
    """Schema for creating a task using natural language."""

    text: str = Field(
        ..., min_length=3, description="Natural language description of the task"
    )
