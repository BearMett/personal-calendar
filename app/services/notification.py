import abc
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.NOTIFICATION_LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("calendar_notification")


class NotificationService(abc.ABC):
    """Abstract base class for notification services."""

    @abc.abstractmethod
    def send_notification(
        self, user_id: int, title: str, message: str, **kwargs
    ) -> bool:
        """Send a notification to a user."""
        pass

    @abc.abstractmethod
    def send_reminder(
        self,
        user_id: int,
        event_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ) -> bool:
        """Send a reminder for an event or task."""
        pass


class LogNotificationService(NotificationService):
    """Notification service that logs messages instead of sending real notifications."""

    def send_notification(
        self, user_id: int, title: str, message: str, **kwargs
    ) -> bool:
        """Log a notification message."""
        logger.info(f"NOTIFICATION to user {user_id} - {title}: {message}")
        logger.debug(f"Additional data: {kwargs}")
        return True

    def send_reminder(
        self,
        user_id: int,
        event_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ) -> bool:
        """Log a reminder message."""
        if event_id:
            logger.info(f"EVENT REMINDER to user {user_id} for event_id {event_id}")
            return True
        elif task_id:
            logger.info(f"TASK REMINDER to user {user_id} for task_id {task_id}")
            return True
        else:
            logger.error("Either event_id or task_id must be provided")
            return False


class EmailNotificationService(NotificationService):
    """Notification service that sends emails."""

    def __init__(self):
        self.enabled = settings.EMAIL_ENABLED
        if not self.enabled:
            logger.warning("Email notifications are disabled")

    def send_notification(
        self, user_id: int, title: str, message: str, **kwargs
    ) -> bool:
        """Send an email notification."""
        if not self.enabled:
            logger.info(f"Email would be sent to user {user_id} - {title}")
            return False

        # In a real implementation, this would use SMTP to send an email
        # For now, just log the attempt
        logger.info(f"Sending email to user {user_id}: {title}")
        logger.debug(f"Email content: {message}")
        return True

    def send_reminder(
        self,
        user_id: int,
        event_id: Optional[int] = None,
        task_id: Optional[int] = None,
    ) -> bool:
        """Send a reminder email."""
        if not self.enabled:
            logger.info(f"Email reminder would be sent to user {user_id}")
            return False

        if event_id:
            title = f"Reminder for Event #{event_id}"
            message = f"You have an upcoming event (ID: {event_id})"
        elif task_id:
            title = f"Reminder for Task #{task_id}"
            message = f"You have a task due soon (ID: {task_id})"
        else:
            logger.error("Either event_id or task_id must be provided")
            return False

        return self.send_notification(user_id, title, message)


# Factory to get the appropriate notification service
def get_notification_service() -> NotificationService:
    """Factory function to get the appropriate notification service."""
    if settings.EMAIL_ENABLED:
        return EmailNotificationService()
    else:
        return LogNotificationService()
