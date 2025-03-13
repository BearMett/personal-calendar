import re
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
import asyncio

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except:
    # If the model is not installed, provide instructions
    logging.warning("Spacy model 'en_core_web_sm' is not installed. Installing...")
    import subprocess

    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

from config import settings
from .ollama_service import OllamaService

logger = logging.getLogger("nlp_service")


class NLPService:
    """Service for processing natural language inputs related to calendar events and tasks."""

    def __init__(self):
        """Initialize the NLP service."""
        self.nlp = nlp
        self.ollama_enabled = settings.OLLAMA_ENABLED
        if self.ollama_enabled:
            self.ollama_service = OllamaService()

    def parse_event(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract event information.

        Example:
        "Meeting with John at 2pm tomorrow for 1 hour at coffee shop"
        -> {
            "title": "Meeting with John",
            "start_time": datetime object for tomorrow at 2pm,
            "end_time": datetime object for tomorrow at 3pm,
            "location": "coffee shop"
        }
        """
        # First try using Ollama if enabled
        if self.ollama_enabled:
            try:
                event_data = asyncio.run(self._parse_event_with_llm(text))
                if event_data and "title" in event_data:
                    return event_data
            except Exception as e:
                logger.warning(
                    f"Failed to parse event with LLM: {e}. Falling back to rule-based parsing."
                )

        # Fall back to rule-based parsing if LLM fails or is disabled
        doc = self.nlp(text)

        # Default values
        event_data = {
            "title": text[:50],  # Default title is truncated text
            "start_time": None,
            "end_time": None,
            "location": None,
            "description": None,
        }

        # Extract time information
        time_info = self._extract_time_info(text)
        if time_info:
            event_data.update(time_info)

        # Extract location using prepositions
        location = self._extract_location(doc)
        if location:
            event_data["location"] = location

        # If no specific time was extracted, use default (now + 1 hour)
        if not event_data["start_time"]:
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
            event_data["start_time"] = now + timedelta(hours=1)
            event_data["end_time"] = now + timedelta(hours=2)

        # Clean up title based on extracted data
        event_data["title"] = self._clean_title(
            text,
            [
                event_data.get("location", ""),
                self._time_to_str(event_data.get("start_time")),
                self._time_to_str(event_data.get("end_time")),
            ],
        )

        return event_data

    def parse_task(self, text: str) -> Dict[str, Any]:
        """
        Parse natural language text to extract task information.

        Example:
        "Submit report by Friday high priority"
        -> {
            "title": "Submit report",
            "due_date": datetime object for next Friday,
            "priority": "high"
        }
        """
        # First try using Ollama if enabled
        if self.ollama_enabled:
            try:
                task_data = asyncio.run(self._parse_task_with_llm(text))
                if task_data and "title" in task_data:
                    return task_data
            except Exception as e:
                logger.warning(
                    f"Failed to parse task with LLM: {e}. Falling back to rule-based parsing."
                )

        # Fall back to rule-based parsing if LLM fails or is disabled
        doc = self.nlp(text)

        # Default values
        task_data = {
            "title": text[:50],  # Default title is truncated text
            "due_date": None,
            "priority": "medium",  # Default priority
            "description": None,
        }

        # Extract time information (due date)
        time_info = self._extract_time_info(text)
        if time_info and "start_time" in time_info:
            task_data["due_date"] = time_info["start_time"]

        # Extract priority
        priority = self._extract_priority(text)
        if priority:
            task_data["priority"] = priority

        # Clean up title based on extracted data
        task_data["title"] = self._clean_title(
            text,
            [
                self._time_to_str(task_data.get("due_date")),
                (
                    f"{task_data['priority']} priority"
                    if task_data.get("priority")
                    else ""
                ),
            ],
        )

        return task_data

    async def _parse_event_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Use LLM to extract event information from natural language text.

        Returns a structured event object with title, start_time, end_time, location, etc.
        """
        # Define the schema for event data
        event_schema = {
            "title": "string",
            "location": "string or null",
            "start_time": "ISO datetime string",
            "end_time": "ISO datetime string",
            "is_all_day": "boolean",
            "description": "string or null",
        }

        system_prompt = """
        You are a calendar assistant that extracts event information from user text.
        Extract the following details: event title, location, start time, end time, and whether it's an all-day event.
        If specific information is not provided, make a reasonable guess based on context.
        For all dates and times, use the current date as reference and return ISO format.
        """

        # Get structured output from LLM
        result = await self.ollama_service.generate_structured_output(
            text, event_schema, system_prompt
        )

        # Process the result
        event_data = {}

        if "title" in result:
            event_data["title"] = result["title"]

        if "location" in result:
            event_data["location"] = result["location"]

        if "description" in result:
            event_data["description"] = result["description"]

        if "is_all_day" in result:
            event_data["is_all_day"] = result["is_all_day"]

        # Parse datetime strings
        if "start_time" in result and result["start_time"]:
            try:
                event_data["start_time"] = datetime.fromisoformat(
                    result["start_time"].replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(f"Could not parse start_time: {result['start_time']}")

        if "end_time" in result and result["end_time"]:
            try:
                event_data["end_time"] = datetime.fromisoformat(
                    result["end_time"].replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(f"Could not parse end_time: {result['end_time']}")
                # If we have start_time but end_time parsing failed, set end_time to start_time + 1 hour
                if "start_time" in event_data:
                    event_data["end_time"] = event_data["start_time"] + timedelta(
                        hours=1
                    )

        return event_data

    async def _parse_task_with_llm(self, text: str) -> Dict[str, Any]:
        """
        Use LLM to extract task information from natural language text.

        Returns a structured task object with title, due_date, priority, etc.
        """
        # Define the schema for task data
        task_schema = {
            "title": "string",
            "due_date": "ISO datetime string or null",
            "priority": "string (low, medium, high)",
            "description": "string or null",
            "status": "string (todo, in_progress, done)",
        }

        system_prompt = """
        You are a task management assistant that extracts task information from user text.
        Extract the following details: task title, due date, priority level, description, and status.
        For priority, use only 'low', 'medium', or 'high'.
        For status, use only 'todo', 'in_progress', or 'done'.
        If specific information is not provided, make a reasonable guess based on context.
        For dates, use the current date as reference and return ISO format.
        """

        # Get structured output from LLM
        result = await self.ollama_service.generate_structured_output(
            text, task_schema, system_prompt
        )

        # Process the result
        task_data = {}

        if "title" in result:
            task_data["title"] = result["title"]

        if "description" in result:
            task_data["description"] = result["description"]

        if "priority" in result and result["priority"] in ["low", "medium", "high"]:
            task_data["priority"] = result["priority"]
        else:
            task_data["priority"] = "medium"  # Default

        if "status" in result and result["status"] in ["todo", "in_progress", "done"]:
            task_data["status"] = result["status"]
        else:
            task_data["status"] = "todo"  # Default

        # Parse datetime string for due_date
        if "due_date" in result and result["due_date"]:
            try:
                task_data["due_date"] = datetime.fromisoformat(
                    result["due_date"].replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(f"Could not parse due_date: {result['due_date']}")

        return task_data

    def _extract_time_info(self, text: str) -> Dict[str, datetime]:
        """Extract time information from text using regex patterns."""
        result = {}

        # Extract date references like "tomorrow", "next Monday", etc.
        today = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        # Tomorrow
        if re.search(r"\b(tomorrow)\b", text, re.I):
            result["start_time"] = today + timedelta(days=1)

        # Next week
        elif re.search(r"\b(next week|in a week)\b", text, re.I):
            result["start_time"] = today + timedelta(days=7)

        # Day of week (find the next occurrence)
        days = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        for day, day_num in days.items():
            if re.search(rf"\b({day})\b", text, re.I):
                current_day = today.weekday()
                days_ahead = day_num - current_day
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                result["start_time"] = today + timedelta(days=days_ahead)

        # Extract time
        time_match = re.search(
            r"\b(at|from)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?",
            text,
            re.I,
        )
        if time_match and "start_time" in result:
            hour = int(time_match.group(2))
            minute = int(time_match.group(3)) if time_match.group(3) else 0
            am_pm = time_match.group(4).lower() if time_match.group(4) else "am"

            # Adjust for PM
            if am_pm and ("pm" in am_pm or "p.m." in am_pm) and hour < 12:
                hour += 12

            # Adjust for 12 AM
            if hour == 12 and am_pm and ("am" in am_pm or "a.m." in am_pm):
                hour = 0

            start_time = result["start_time"].replace(hour=hour, minute=minute)
            result["start_time"] = start_time

            # Extract duration
            duration_match = re.search(r"for\s+(\d+)\s+(hour|hours|hr|hrs)", text, re.I)
            if duration_match:
                duration_hours = int(duration_match.group(1))
                result["end_time"] = start_time + timedelta(hours=duration_hours)
            else:
                # Default to 1 hour if no duration specified
                result["end_time"] = start_time + timedelta(hours=1)

        return result

    def _extract_location(self, doc) -> Optional[str]:
        """Extract location information from text using prepositions."""
        location = None

        # Look for prepositional phrases that might indicate location
        for token in doc:
            if token.dep_ == "prep" and token.text.lower() in ["at", "in"]:
                # Get the following noun phrase
                for np in doc.noun_chunks:
                    if np.start > token.i and (
                        location is None or np.start < location[0]
                    ):
                        location = (np.start, np.text)

        return location[1] if location else None

    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority level from text."""
        if re.search(
            r"\b(high|important|urgent)\s+(priority|importance)\b", text, re.I
        ) or re.search(r"\b(high-priority)\b", text, re.I):
            return "high"
        elif re.search(
            r"\b(low|minor)\s+(priority|importance)\b", text, re.I
        ) or re.search(r"\b(low-priority)\b", text, re.I):
            return "low"
        return None

    def _time_to_str(self, dt: Optional[datetime]) -> str:
        """Convert datetime to string for title cleaning purposes."""
        if not dt:
            return ""
        return dt.strftime("%A %I:%M %p")

    def _clean_title(self, text: str, items_to_remove: List[str]) -> str:
        """Clean up title by removing extracted information."""
        clean_title = text
        for item in items_to_remove:
            if item:
                clean_title = clean_title.replace(item, "")

        # Remove common fillers and clean up
        clean_title = re.sub(
            r"\b(schedule|create|add|set|remind me|to do)\b",
            "",
            clean_title,
            flags=re.I,
        )
        clean_title = re.sub(r"\s+", " ", clean_title).strip()

        return clean_title if clean_title else text[:50]
