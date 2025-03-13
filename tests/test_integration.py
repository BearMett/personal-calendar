import sys
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app
from personal_calendar.app import app
from personal_calendar.app.models import Base, get_db
from personal_calendar.app.utils.auth import get_password_hash

# Create test database
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def test_db():
    # Create the test database and tables
    Base.metadata.create_all(bind=engine)

    # Create test data
    db = TestingSessionLocal()
    from personal_calendar.app.models.user import User

    # Create test user
    hashed_password = get_password_hash("testpassword")
    test_user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        full_name="Test User",
        is_active=True,
    )
    db.add(test_user)
    db.commit()

    yield db

    # Teardown - drop all tables
    Base.metadata.drop_all(bind=engine)


# Override the dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user_token(client):
    """Get authentication token for test user."""
    response = client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    return response.json()["access_token"]


def test_register_user(client):
    """Test user registration endpoint."""
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "newpassword",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert "id" in data


def test_login(client):
    """Test login endpoint."""
    response = client.post(
        "/api/auth/login", json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_create_event(client, user_token):
    """Test creating an event."""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/api/events",
        headers=headers,
        json={
            "title": "Test Event",
            "description": "Test description",
            "start_time": "2023-01-01T10:00:00",
            "end_time": "2023-01-01T11:00:00",
            "is_all_day": False,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Event"
    assert "id" in data


def test_create_task(client, user_token):
    """Test creating a task."""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/api/tasks",
        headers=headers,
        json={
            "title": "Test Task",
            "description": "Test task description",
            "due_date": "2023-01-01T10:00:00",
            "priority": "medium",
            "status": "todo",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert "id" in data


def test_create_event_from_text(client, user_token):
    """Test creating an event from natural language text."""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/api/events/parse", headers=headers, json={"text": "Meeting tomorrow at 3pm"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "Meeting" in data["title"]
    assert "id" in data


def test_agent_command(client, user_token):
    """Test the agent command endpoint."""
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(
        "/api/agent/command",
        headers=headers,
        json={"command": "Show my events for this week"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"]["command_type"] == "show_events"
