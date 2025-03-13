import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..models.event import Event
from ..models.task import Task, TaskStatus, PriorityLevel
from ..models.user import User
from .notification import get_notification_service, NotificationService

logger = logging.getLogger("calendar_api")


class CalendarService:
    """Service for managing calendar events and tasks."""

    def __init__(self, db: Session):
        """Initialize the calendar service with database session."""
        self.db = db
        self.notification_service = get_notification_service()

    # Event operations
    def create_event(self, user_id: int, event_data: Dict[str, Any]) -> Event:
        """Create a new event for the user."""
        event = Event(
            user_id=user_id,
            title=event_data.get("title"),
            description=event_data.get("description"),
            location=event_data.get("location"),
            start_time=event_data.get("start_time"),
            end_time=event_data.get("end_time"),
            is_all_day=event_data.get("is_all_day", False),
            color=event_data.get("color"),
            recurring_rule=event_data.get("recurring_rule"),
            reminder_minutes=event_data.get("reminder_minutes"),
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        # Schedule a reminder if specified
        if event.reminder_minutes:
            # In a real application, this would be scheduled with a task queue
            # For now, just log it
            logger.info(
                f"Reminder scheduled for event {event.id} {event.reminder_minutes} minutes before the event"
            )

        return event

    def get_event(
        self, event_id: int, user_id: Optional[int] = None
    ) -> Optional[Event]:
        """Get an event by ID, optionally filtering by user."""
        query = self.db.query(Event).filter(Event.id == event_id)
        if user_id:
            query = query.filter(Event.user_id == user_id)
        return query.first()

    def get_events(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Event]:
        """Get events for a user in a specific date range."""
        query = self.db.query(Event).filter(Event.user_id == user_id)

        if start_date:
            query = query.filter(Event.start_time >= start_date)
        if end_date:
            query = query.filter(Event.start_time <= end_date)

        return query.order_by(Event.start_time).all()

    def update_event(
        self, event_id: int, user_id: int, event_data: Dict[str, Any]
    ) -> Optional[Event]:
        """Update an existing event."""
        event = self.get_event(event_id, user_id)
        if not event:
            return None

        # Update fields
        for key, value in event_data.items():
            if hasattr(event, key) and value is not None:
                setattr(event, key, value)

        self.db.commit()
        self.db.refresh(event)
        return event

    def delete_event(self, event_id: int, user_id: int) -> bool:
        """Delete an event."""
        event = self.get_event(event_id, user_id)
        if not event:
            return False

        self.db.delete(event)
        self.db.commit()
        return True

    # Task operations
    def create_task(self, user_id: int, task_data: Dict[str, Any]) -> Task:
        """Create a new task for the user."""
        # Convert string priority to enum if needed
        priority = task_data.get("priority")
        if isinstance(priority, str):
            priority = PriorityLevel(priority)

        # Convert string status to enum if needed
        status = task_data.get("status", "todo")
        if isinstance(status, str):
            status = TaskStatus(status)

        task = Task(
            user_id=user_id,
            title=task_data.get("title"),
            description=task_data.get("description"),
            due_date=task_data.get("due_date"),
            priority=priority,
            status=status,
            reminder_date=task_data.get("reminder_date"),
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        # Schedule a reminder if specified
        if task.reminder_date:
            # In a real application, this would be scheduled with a task queue
            # For now, just log it
            logger.info(
                f"Reminder scheduled for task {task.id} at {task.reminder_date}"
            )

        return task

    def get_task(self, task_id: int, user_id: Optional[int] = None) -> Optional[Task]:
        """Get a task by ID, optionally filtering by user."""
        query = self.db.query(Task).filter(Task.id == task_id)
        if user_id:
            query = query.filter(Task.user_id == user_id)
        return query.first()

    def get_tasks(
        self,
        user_id: int,
        status: Optional[Union[TaskStatus, str]] = None,
        due_date_start: Optional[datetime] = None,
        due_date_end: Optional[datetime] = None,
        priority: Optional[Union[PriorityLevel, str]] = None,
    ) -> List[Task]:
        """Get tasks for a user with various filters."""
        query = self.db.query(Task).filter(Task.user_id == user_id)

        # Apply filters
        if status:
            if isinstance(status, str):
                status = TaskStatus(status)
            query = query.filter(Task.status == status)

        if due_date_start:
            query = query.filter(Task.due_date >= due_date_start)
        if due_date_end:
            query = query.filter(Task.due_date <= due_date_end)

        if priority:
            if isinstance(priority, str):
                priority = PriorityLevel(priority)
            query = query.filter(Task.priority == priority)

        return query.order_by(Task.due_date, Task.priority).all()

    def update_task(
        self, task_id: int, user_id: int, task_data: Dict[str, Any]
    ) -> Optional[Task]:
        """Update an existing task."""
        task = self.get_task(task_id, user_id)
        if not task:
            return None

        # Handle special case for completing a task
        if task_data.get("status") == TaskStatus.DONE:
            task_data["completed_at"] = datetime.utcnow()

        # Convert string values to enums if needed
        if "priority" in task_data and isinstance(task_data["priority"], str):
            task_data["priority"] = PriorityLevel(task_data["priority"])

        if "status" in task_data and isinstance(task_data["status"], str):
            task_data["status"] = TaskStatus(task_data["status"])

        # Update fields
        for key, value in task_data.items():
            if hasattr(task, key) and value is not None:
                setattr(task, key, value)

        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: int, user_id: int) -> bool:
        """Delete a task."""
        task = self.get_task(task_id, user_id)
        if not task:
            return False

        self.db.delete(task)
        self.db.commit()
        return True

    # Reminder operations
    def process_due_reminders(self) -> int:
        """
        Process all reminders that are due.

        In a real application, this would be called by a scheduled job.
        Returns the number of reminders sent.
        """
        now = datetime.utcnow()
        count = 0

        # Process event reminders
        event_reminders = self._get_due_event_reminders(now)
        for event in event_reminders:
            self.notification_service.send_reminder(
                user_id=event.user_id, event_id=event.id
            )
            count += 1

        # Process task reminders
        task_reminders = self._get_due_task_reminders(now)
        for task in task_reminders:
            self.notification_service.send_reminder(
                user_id=task.user_id, task_id=task.id
            )
            count += 1

        return count

    def _get_due_event_reminders(self, now: datetime) -> List[Event]:
        """Get all events with reminders that need to be sent."""
        result = []

        # Get events that start soon and have reminder_minutes set
        upcoming_events = (
            self.db.query(Event)
            .filter(Event.start_time > now, Event.reminder_minutes.isnot(None))
            .all()
        )

        for event in upcoming_events:
            # Calculate reminder time
            reminder_time = event.start_time - timedelta(minutes=event.reminder_minutes)
            # If the reminder time is now or in the past, it's due
            if reminder_time <= now:
                result.append(event)

        return result

    def _get_due_task_reminders(self, now: datetime) -> List[Task]:
        """Get all tasks with reminders that need to be sent."""
        return (
            self.db.query(Task)
            .filter(
                Task.reminder_date <= now,
                Task.status != TaskStatus.DONE,
                Task.status != TaskStatus.ARCHIVED,
            )
            .all()
        )
