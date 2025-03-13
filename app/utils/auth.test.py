import unittest
from datetime import timedelta
from unittest.mock import Mock, patch
from jose import jwt

from personal_calendar.app.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    authenticate_user,
)
from personal_calendar.config import settings


class TestAuth(unittest.TestCase):

    def test_password_hashing(self):
        """Test that password hashing works correctly."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        # Hash should be different than original password
        self.assertNotEqual(password, hashed)

        # Verification should pass
        self.assertTrue(verify_password(password, hashed))

        # Wrong password should fail
        self.assertFalse(verify_password("wrongpassword", hashed))

    def test_create_access_token(self):
        """Test that JWT tokens are created correctly."""
        # Create a token with test data
        test_data = {"sub": "testuser"}
        token = create_access_token(test_data)

        # Token should be a string
        self.assertIsInstance(token, str)

        # Decode the token and verify the payload
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        self.assertEqual(payload["sub"], "testuser")

        # Should have an expiration claim
        self.assertIn("exp", payload)

        # Test with explicit expiration time
        expires = timedelta(minutes=10)
        token_with_expires = create_access_token(test_data, expires)
        self.assertIsInstance(token_with_expires, str)

    @patch("personal_calendar.app.utils.auth.verify_password")
    def test_authenticate_user(self, mock_verify_password):
        """Test user authentication."""
        # Mock the database session and query
        db = Mock()
        user = Mock()
        user.username = "testuser"
        user.hashed_password = "hashedpassword"

        # Set up the query to return our mock user
        db.query.return_value.filter.return_value.first.return_value = user

        # Test successful authentication
        mock_verify_password.return_value = True
        result = authenticate_user(db, "testuser", "correctpassword")
        self.assertEqual(result, user)

        # Test failed authentication - wrong password
        mock_verify_password.return_value = False
        result = authenticate_user(db, "testuser", "wrongpassword")
        self.assertIsNone(result)

        # Test failed authentication - user not found
        db.query.return_value.filter.return_value.first.return_value = None
        result = authenticate_user(db, "nonexistentuser", "anypassword")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
