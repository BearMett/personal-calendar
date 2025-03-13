from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..models import get_db
from ..models.user import User
from ..models.event import Event
from ..schemas.event import (
    Event as EventSchema,
    EventCreate,
    EventUpdate,
    NaturalLanguageEventRequest,
)
from ..services.google_calendar_service import GoogleCalendarService
from ..services.apple_calendar_service import AppleCalendarService
from ..services.calendar_interface import CalendarInterface
from ..services.nlp import NLPService
from ..utils.auth import get_current_active_user
from config import settings

router = APIRouter(tags=["events"], prefix="/events")


def get_calendar_service(current_user: User) -> CalendarInterface:
    if current_user.calendar_preference == "google":
        credentials = (
            current_user.google_credentials
        )  # Retrieve from database or session
        return GoogleCalendarService(credentials=credentials)
    elif current_user.calendar_preference == "apple":
        return AppleCalendarService(credentials="apple_credentials")
    else:
        raise ValueError("Unsupported calendar service provider")


@router.post("", response_model=EventSchema, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new event."""
    calendar_service = get_calendar_service(current_user)
    event = calendar_service.create_event(event_data.dict())
    return event


@router.post("/parse", response_model=EventSchema, status_code=status.HTTP_201_CREATED)
async def create_event_from_text(
    request: NaturalLanguageEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new event from natural language text."""
    nlp_service = NLPService()
    calendar_service = get_calendar_service(current_user)
    # Parse event data from text
    event_data = nlp_service.parse_event(request.text)
    # Create event
    event = calendar_service.create_event(event_data)
    return event


@router.get("", response_model=List[EventSchema])
async def get_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all events for current user with optional date filters."""
    calendar_service = get_calendar_service(current_user)
    events = calendar_service.get_events()
    return events


@router.get("/{event_id}", response_model=EventSchema)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific event by ID."""
    calendar_service = get_calendar_service(current_user)
    event = calendar_service.get_events()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found",
        )
    return event


@router.put("/{event_id}", response_model=EventSchema)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update an event."""
    calendar_service = get_calendar_service(current_user)
    updated_event = calendar_service.update_event(
        event_id=event_id,
        event=event_data.dict(exclude_unset=True),
    )
    if not updated_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found or you don't have permission to update it",
        )
    return updated_event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete an event."""
    calendar_service = get_calendar_service(current_user)
    result = calendar_service.delete_event(event_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found or you don't have permission to delete it",
        )
    return None
