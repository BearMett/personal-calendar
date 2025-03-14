import logging
import asyncio
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .nlp import NLPService
from .calendar_api import CalendarService
from .ollama_service import OllamaService
from config import settings
from ..models.event import Event
from ..models.task import Task

logger = logging.getLogger("agent_service")


class AgentService:
    """
    Main agent service that processes user requests and commands
    in natural language and interacts with calendar API.
    """

    def __init__(self, db: Session):
        """Initialize the agent service."""
        self.db = db
        self.nlp_service = NLPService()
        self.calendar_service = CalendarService(db)
        self.ollama_enabled = settings.OLLAMA_ENABLED
        if self.ollama_enabled:
            self.ollama_service = OllamaService()

    def process_command(self, user_id: int, text: str) -> Dict[str, Any]:
        """
        Process a natural language command from the user.

        Example commands:
        - "Schedule a meeting with John tomorrow at 2pm"
        - "Add a task to submit report by Friday"
        - "Show my events for next week"
        - "Mark task 123 as done"

        Returns a dict with the result of the command.
        """
        # Try LLM-based command classification first if enabled
        command_type = "unknown"
        if self.ollama_enabled:
            try:
                command_type = asyncio.run(self._classify_command_with_llm(text))
            except Exception as e:
                logger.warning(
                    f"Failed to classify command with LLM: {str(e)}. Falling back to rule-based classification."
                )
                command_type = self._classify_command(text)
        else:
            command_type = self._classify_command(text)

        if command_type == "create_event":
            return self._handle_create_event(user_id, text)
        elif command_type == "create_task":
            return self._handle_create_task(user_id, text)
        elif command_type == "show_events":
            return self._handle_show_events(user_id, text)
        elif command_type == "show_tasks":
            return self._handle_show_tasks(user_id, text)
        elif command_type == "update_task_status":
            return self._handle_update_task_status(user_id, text)
        elif self.ollama_enabled and command_type == "complex_query":
            # Handle complex queries with LLM assistance
            return asyncio.run(self._handle_complex_query(user_id, text))
        else:
            return {
                "success": False,
                "message": "I couldn't understand your command. Please try again.",
                "command_type": "unknown",
            }

    def _classify_command(self, text: str) -> str:
        """
        Classify the user's command into one of several categories.

        Uses simple keyword matching, but in a real app would use more sophisticated NLP.
        """
        text_lower = text.lower()

        # Create event patterns
        if any(
            keyword in text_lower
            for keyword in ["schedule", "create event", "add event", "new event"]
        ):
            return "create_event"

        # Create task patterns
        if any(
            keyword in text_lower
            for keyword in ["task", "todo", "to do", "to-do", "add task"]
        ):
            return "create_task"

        # Show events patterns
        if any(
            keyword in text_lower
            for keyword in [
                "show events",
                "list events",
                "display events",
                "what events",
                "my events",
            ]
        ):
            return "show_events"

        # Show tasks patterns
        if any(
            keyword in text_lower
            for keyword in [
                "show tasks",
                "list tasks",
                "display tasks",
                "what tasks",
                "my tasks",
            ]
        ):
            return "show_tasks"

        # Update task status patterns
        if (
            any(
                keyword in text_lower
                for keyword in ["mark", "complete", "finish", "done with"]
            )
            and "task" in text_lower
        ):
            return "update_task_status"

        # Default to creating an event if it contains time expressions
        time_indicators = [
            "today",
            "tomorrow",
            "next week",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            " at ",
            "pm",
            "am",
        ]
        if any(indicator in text_lower for indicator in time_indicators):
            return "create_event"

        # Default
        return "unknown"

    async def _classify_command_with_llm(self, text: str) -> str:
        """
        Classify the user's command using LLM.

        This provides more accurate classification for complex or ambiguous commands.
        """
        # Define possible command types
        command_schema = {
            "command_type": "string (create_event, create_task, show_events, show_tasks, update_task_status, complex_query)",
            "confidence": "number (0-1)",
        }

        system_prompt = """
        You are a calendar assistant that classifies user commands into specific action types.
        Classify the command into one of these categories:
        - create_event: Creating or scheduling a new calendar event
        - create_task: Adding a new task to a to-do list
        - show_events: Displaying or listing calendar events
        - show_tasks: Displaying or listing tasks
        - update_task_status: Changing the status of a task (e.g., marking as complete)
        - complex_query: Any command that doesn't fit the above categories or combines multiple actions
        
        Respond with the command_type and your confidence level (0-1).
        """

        # Get classification from LLM
        result = await self.ollama_service.generate_structured_output(
            text, command_schema, system_prompt
        )

        if "command_type" in result:
            command_type = result["command_type"].lower()
            confidence = float(result.get("confidence", 0))

            # Only accept classification if confidence is high enough
            if confidence >= 0.7:
                return command_type
            elif command_type != "unknown":
                # For lower confidence but valid classification, still accept it
                return command_type

        # Default to unknown if LLM classification failed
        return "unknown"

    async def _handle_complex_query(self, user_id: int, text: str) -> Dict[str, Any]:
        """
        Handle complex queries that require deeper understanding and context.
        Uses LLM to generate a more comprehensive response.
        """
        try:
            # First, gather relevant context
            # Get recent events (limit to 5)
            recent_events = self.calendar_service.get_events(
                user_id=user_id,
                start_date=datetime.now() - timedelta(days=7),
                end_date=datetime.now() + timedelta(days=14),
            )[:5]

            # Get active tasks (limit to 5)
            active_tasks = self.calendar_service.get_tasks(
                user_id=user_id, status="todo"
            )[:5]

            # Format context for the LLM
            context = "Current calendar context:\n"

            if recent_events:
                context += "\nUpcoming events:\n"
                for event in recent_events:
                    context += f"- {event.title} on {event.start_time.strftime('%Y-%m-%d %H:%M')} at {event.location or 'No location'}\n"
            else:
                context += "\nNo upcoming events.\n"

            if active_tasks:
                context += "\nActive tasks:\n"
                for task in active_tasks:
                    due_date = (
                        task.due_date.strftime("%Y-%m-%d")
                        if task.due_date
                        else "No due date"
                    )
                    context += f"- {task.title} (Priority: {task.priority.value}, Due: {due_date})\n"
            else:
                context += "\nNo active tasks.\n"

            # Create system prompt for the LLM to process the complex query
            system_prompt = """
            You are a helpful calendar assistant that can answer questions about events and tasks.
            Based on the calendar context provided and the user's question, provide a helpful response.
            If the query involves creating or modifying calendar items, explain what would need to be done.
            """

            # Combine context and user query
            prompt = (
                f"{context}\n\nUser query: {text}\n\nPlease provide a helpful response:"
            )

            # Get response from LLM
            response = await self.ollama_service.generate_completion(
                prompt, system_prompt
            )

            return {
                "success": True,
                "message": "Processed your complex query",
                "command_type": "complex_query",
                "response": response,
                "context_provided": {
                    "events_count": len(recent_events),
                    "tasks_count": len(active_tasks),
                },
            }

        except Exception as e:
            logger.error(f"Error handling complex query: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to process your complex query: {str(e)}",
                "command_type": "complex_query",
            }

    def _handle_create_event(self, user_id: int, text: str) -> Dict[str, Any]:
        """Handle creating an event from natural language."""
        try:
            # Parse the event data
            event_data = self.nlp_service.parse_event(text)

            # Create the event
            event = self.calendar_service.create_event(user_id, event_data)

            return {
                "success": True,
                "message": f"Event created: {event.title}",
                "command_type": "create_event",
                "event_id": event.id,
                "event": {
                    "title": event.title,
                    "start_time": event.start_time.strftime("%Y-%m-%d %H:%M"),
                    "end_time": event.end_time.strftime("%Y-%m-%d %H:%M"),
                    "location": event.location,
                },
            }
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {
                "success": False,
                "message": "Failed to create event. Please try again.",
                "command_type": "create_event",
                "error": str(e),
            }

    def _handle_create_task(self, user_id: int, text: str) -> Dict[str, Any]:
        """Handle creating a task from natural language."""
        try:
            # Parse the task data
            task_data = self.nlp_service.parse_task(text)

            # Create the task
            task = self.calendar_service.create_task(user_id, task_data)

            response = {
                "success": True,
                "message": f"Task created: {task.title}",
                "command_type": "create_task",
                "task_id": task.id,
                "task": {
                    "title": task.title,
                    "priority": task.priority.value,
                    "status": task.status.value,
                },
            }

            # Add due date if available
            if task.due_date:
                response["task"]["due_date"] = task.due_date.strftime("%Y-%m-%d")

            return response
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {
                "success": False,
                "message": "Failed to create task. Please try again.",
                "command_type": "create_task",
                "error": str(e),
            }

    def _handle_show_events(self, user_id: int, text: str) -> Dict[str, Any]:
        """Handle showing events from natural language query."""
        try:
            # Parse date range from text
            date_range = self._extract_date_range(text)

            # Get events in the range
            events = self.calendar_service.get_events(
                user_id=user_id, start_date=date_range[0], end_date=date_range[1]
            )

            # Format events for response
            event_list = [
                {
                    "id": event.id,
                    "title": event.title,
                    "start_time": event.start_time.strftime("%Y-%m-%d %H:%M"),
                    "end_time": event.end_time.strftime("%Y-%m-%d %H:%M"),
                    "location": event.location,
                }
                for event in events
            ]

            return {
                "success": True,
                "message": f"Found {len(events)} events",
                "command_type": "show_events",
                "events": event_list,
                "date_range": {
                    "start": (
                        date_range[0].strftime("%Y-%m-%d")
                        if date_range[0]
                        else "all past events"
                    ),
                    "end": (
                        date_range[1].strftime("%Y-%m-%d")
                        if date_range[1]
                        else "all future events"
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error showing events: {e}")
            return {
                "success": False,
                "message": "Failed to retrieve events. Please try again.",
                "command_type": "show_events",
                "error": str(e),
            }

    def _handle_show_tasks(self, user_id: int, text: str) -> Dict[str, Any]:
        """Handle showing tasks from natural language query."""
        try:
            # Parse filters from text
            status = None
            priority = None

            text_lower = text.lower()

            # Extract status filter
            if "done" in text_lower or "completed" in text_lower:
                status = "done"
            elif "in progress" in text_lower:
                status = "in_progress"
            elif "todo" in text_lower or "to do" in text_lower or "to-do" in text_lower:
                status = "todo"

            # Extract priority filter
            if "high priority" in text_lower:
                priority = "high"
            elif "low priority" in text_lower:
                priority = "low"
            elif "medium priority" in text_lower:
                priority = "medium"

            # Get tasks with filters
            tasks = self.calendar_service.get_tasks(
                user_id=user_id, status=status, priority=priority
            )

            # Format tasks for response
            task_list = [
                {
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "due_date": (
                        task.due_date.strftime("%Y-%m-%d") if task.due_date else None
                    ),
                }
                for task in tasks
            ]

            # Create a readable message
            filters_desc = []
            if status:
                filters_desc.append(f"status='{status}'")
            if priority:
                filters_desc.append(f"priority='{priority}'")

            filter_str = (
                f" with filters {', '.join(filters_desc)}" if filters_desc else ""
            )

            return {
                "success": True,
                "message": f"Found {len(tasks)} tasks{filter_str}",
                "command_type": "show_tasks",
                "tasks": task_list,
            }
        except Exception as e:
            logger.error(f"Error showing tasks: {e}")
            return {
                "success": False,
                "message": "Failed to retrieve tasks. Please try again.",
                "command_type": "show_tasks",
                "error": str(e),
            }

    def _handle_update_task_status(self, user_id: int, text: str) -> Dict[str, Any]:
        """Handle updating a task status from natural language."""
        try:
            # Try to extract task ID
            task_id = self._extract_task_id(text)
            if not task_id:
                return {
                    "success": False,
                    "message": "Couldn't identify which task to update. Please include the task ID.",
                    "command_type": "update_task_status",
                }

            # Determine the target status
            target_status = "done"  # Default to marking as done
            text_lower = text.lower()
            if "in progress" in text_lower:
                target_status = "in_progress"
            elif "todo" in text_lower or "to do" in text_lower or "to-do" in text_lower:
                target_status = "todo"

            # Update the task
            updated_task = self.calendar_service.update_task(
                task_id=task_id, user_id=user_id, task_data={"status": target_status}
            )

            if not updated_task:
                return {
                    "success": False,
                    "message": f"Couldn't find task {task_id} or you don't have permission to update it.",
                    "command_type": "update_task_status",
                }

            return {
                "success": True,
                "message": f"Task {task_id} marked as {target_status}",
                "command_type": "update_task_status",
                "task_id": updated_task.id,
                "task": {
                    "title": updated_task.title,
                    "status": updated_task.status.value,
                },
            }
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return {
                "success": False,
                "message": "Failed to update task status. Please try again.",
                "command_type": "update_task_status",
                "error": str(e),
            }

    def _extract_date_range(
        self, text: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract date range from text for event/task queries."""
        text_lower = text.lower()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Default to no start/end restriction
        start_date = None
        end_date = None

        # Today
        if "today" in text_lower:
            start_date = today
            end_date = today.replace(hour=23, minute=59, second=59)

        # Tomorrow
        elif "tomorrow" in text_lower:
            tomorrow = today + timedelta(days=1)
            start_date = tomorrow
            end_date = tomorrow.replace(hour=23, minute=59, second=59)

        # This week
        elif "this week" in text_lower:
            # Start of week (Monday)
            days_to_monday = today.weekday()
            start_date = today - timedelta(days=days_to_monday)
            # End of week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Next week
        elif "next week" in text_lower:
            # Start of next week (Monday)
            days_to_monday = today.weekday()
            start_of_this_week = today - timedelta(days=days_to_monday)
            start_date = start_of_this_week + timedelta(days=7)
            # End of next week (Sunday)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # This month
        elif "this month" in text_lower:
            start_date = today.replace(day=1)
            # Last day of month
            if today.month == 12:
                end_date = today.replace(
                    year=today.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(
                    days=1
                )
            end_date = end_date.replace(hour=23, minute=59, second=59)

        return (start_date, end_date)

    def _extract_task_id(self, text: str) -> Optional[int]:
        """Extract task ID from text."""
        import re

        # Look for patterns like "task 123", "task #123", "#123"
        patterns = [
            r"task\s+#?(\d+)",
            r"task\s+id\s+#?(\d+)",
            r"#(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return int(match.group(1))

        return None
