import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

from personal_calendar.app.services.nlp import NLPService


class TestNLPService(unittest.TestCase):
    
    def setUp(self):
        self.nlp_service = NLPService()
        
    def test_parse_event(self):
        """Test parsing text into an event."""
        # Test with full details
        text = "Meeting with John at 2pm tomorrow for 1 hour at coffee shop"
        
        # Mock today's date for consistent testing
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        with patch('personal_calendar.app.services.nlp.datetime') as mock_datetime:
            mock_datetime.now.return_value = today
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            event = self.nlp_service.parse_event(text)
            
            # Check basic properties
            self.assertIn("Meeting with John", event["title"])
            self.assertEqual(event["location"], "coffee shop")
            
            # Check time properties - should be tomorrow at 2pm
            expected_start = tomorrow.replace(hour=14, minute=0)
            self.assertEqual(event["start_time"].day, expected_start.day)
            self.assertEqual(event["start_time"].hour, expected_start.hour)
            
            # Duration should be 1 hour
            expected_end = expected_start + timedelta(hours=1)
            self.assertEqual(event["end_time"].hour, expected_end.hour)
            
    def test_parse_task(self):
        """Test parsing text into a task."""
        # Test task with due date and priority
        text = "Submit report by Friday high priority"
        
        # Mock today as Monday for consistent testing
        monday = datetime(2023, 1, 2)  # A Monday
        friday = datetime(2023, 1, 6)  # The following Friday
        
        with patch('personal_calendar.app.services.nlp.datetime') as mock_datetime:
            mock_datetime.now.return_value = monday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            task = self.nlp_service.parse_task(text)
            
            # Check basic properties
            self.assertIn("Submit report", task["title"])
            self.assertEqual(task["priority"], "high")
            
            # Check due date - should be Friday
            self.assertEqual(task["due_date"].day, friday.day)
            self.assertEqual(task["due_date"].month, friday.month)
            
    def test_extract_location(self):
        """Test extracting location from text."""
        # Create a simple mock for spaCy doc
        mock_doc = Mock()
        token1 = Mock()
        token1.dep_ = "prep"
        token1.text = "at"
        token1.i = 3
        
        token2 = Mock()
        token2.dep_ = "other"
        token2.text = "some"
        token2.i = 4
        
        mock_doc.__iter__ = lambda self: iter([token1, token2])
        
        # Create mock noun chunk that follows the "at" preposition
        chunk = Mock()
        chunk.start = 4
        chunk.text = "coffee shop"
        mock_doc.noun_chunks = [chunk]
        
        # Test extraction
        location = self.nlp_service._extract_location(mock_doc)
        self.assertEqual(location, "coffee shop")
        
    def test_extract_priority(self):
        """Test extracting priority from text."""
        # Test high priority
        text1 = "This is high priority task"
        priority1 = self.nlp_service._extract_priority(text1)
        self.assertEqual(priority1, "high")
        
        # Test low priority
        text2 = "This is low priority task"
        priority2 = self.nlp_service._extract_priority(text2)
        self.assertEqual(priority2, "low")
        
        # Test no priority mentioned
        text3 = "This is a regular task"
        priority3 = self.nlp_service._extract_priority(text3)
        self.assertIsNone(priority3)


if __name__ == "__main__":
    unittest.main()