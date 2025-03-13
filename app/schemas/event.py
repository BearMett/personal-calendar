from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base schema for Event."""

    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    color: Optional[str] = None
    recurring_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None


class EventCreate(EventBase):
    """Schema for creating a new event."""

    pass


class EventUpdate(BaseModel):
    """Schema for updating an existing event."""

    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    color: Optional[str] = None
    recurring_rule: Optional[str] = None
    reminder_minutes: Optional[int] = None


class EventInDB(EventBase):
    """Event schema as stored in database."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Event(EventInDB):
    """Schema for event response."""

    pass


class NaturalLanguageEventRequest(BaseModel):
    """Schema for creating an event using natural language."""

    text: str = Field(
        ..., min_length=3, description="Natural language description of the event"
    )
