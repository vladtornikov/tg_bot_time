"""Pytest configuration and shared fixtures."""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from src.config.settings import Settings
from src.database.session import get_db_session
from src.database.connection import get_async_engine
from src.models.base import Base
from src.api.main import app


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
TEST_DATABASE_URL_SYNC = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Create test settings."""
    return Settings(
        environment="testing",
        debug=True,
        database_url=TEST_DATABASE_URL,
        database_url_sync=TEST_DATABASE_URL_SYNC,
        redis_url="redis://localhost:6379/1",  # Use different Redis DB for tests
        telegram_bot_token="test_token",
        google_client_id="test_client_id",
        google_client_secret="test_client_secret",
        google_redirect_uri="http://localhost:8000/oauth/google/callback",
        encryption_key="test_encryption_key_32_bytes_long",
        secret_key="test_secret_key",
        api_host="0.0.0.0",
        api_port=8000,
        worker_concurrency=2,
        log_level="DEBUG",
    )


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def test_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    
    def override_get_db():
        return test_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# Model fixtures
@pytest.fixture
async def test_user(test_session: AsyncSession):
    """Create test user."""
    from src.models.user import User
    
    user = User(
        telegram_id=12345,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def test_chat(test_session: AsyncSession):
    """Create test chat."""
    from src.models.user import Chat
    
    chat = Chat(
        telegram_id=-1001234567890,
        title="Test Group",
        chat_type="group",
    )
    test_session.add(chat)
    await test_session.commit()
    await test_session.refresh(chat)
    return chat


@pytest.fixture
async def test_chat_membership(test_session: AsyncSession, test_user, test_chat):
    """Create test chat membership."""
    from src.models.user import ChatMembership
    
    membership = ChatMembership(
        user_id=test_user.id,
        chat_id=test_chat.id,
        status="active",
    )
    test_session.add(membership)
    await test_session.commit()
    await test_session.refresh(membership)
    return membership


@pytest.fixture
async def test_oauth_token(test_session: AsyncSession, test_user):
    """Create test OAuth token."""
    from src.models.oauth import OAuthToken
    from datetime import datetime, timedelta
    
    token = OAuthToken(
        user_id=test_user.id,
        provider="google",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=datetime.utcnow() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
    )
    test_session.add(token)
    await test_session.commit()
    await test_session.refresh(token)
    return token


@pytest.fixture
async def test_meeting(test_session: AsyncSession, test_user, test_chat):
    """Create test meeting."""
    from src.models.meeting import Meeting
    from datetime import datetime, timedelta
    
    meeting = Meeting(
        title="Test Meeting",
        description="Test meeting description",
        creator_id=test_user.id,
        chat_id=test_chat.id,
        status="created",
        duration_minutes=60,
        earliest_start=datetime.utcnow() + timedelta(days=1),
        latest_end=datetime.utcnow() + timedelta(days=7),
        working_hours_start=9,
        working_hours_end=17,
        timezone="UTC",
    )
    test_session.add(meeting)
    await test_session.commit()
    await test_session.refresh(meeting)
    return meeting


@pytest.fixture
async def test_meeting_participant(test_session: AsyncSession, test_meeting, test_user):
    """Create test meeting participant."""
    from src.models.meeting import MeetingParticipant
    
    participant = MeetingParticipant(
        meeting_id=test_meeting.id,
        user_id=test_user.id,
        telegram_chat_id=test_user.telegram_id,
        username=test_user.username,
        status="active",
    )
    test_session.add(participant)
    await test_session.commit()
    await test_session.refresh(participant)
    return participant


@pytest.fixture
async def test_vote(test_session: AsyncSession, test_meeting_participant):
    """Create test vote."""
    from src.models.vote import Vote
    from datetime import datetime, timedelta
    
    vote = Vote(
        participant_id=test_meeting_participant.id,
        start_time=datetime.utcnow() + timedelta(days=1, hours=10),
        end_time=datetime.utcnow() + timedelta(days=1, hours=11),
        preference="available",
    )
    test_session.add(vote)
    await test_session.commit()
    await test_session.refresh(vote)
    return vote


# Mock fixtures
@pytest.fixture
def mock_telegram_provider():
    """Create mock Telegram provider."""
    mock = AsyncMock()
    mock.send_message.return_value = True
    mock.send_direct_message.return_value = True
    mock.edit_message_text.return_value = True
    mock.delete_message.return_value = True
    return mock


@pytest.fixture
def mock_google_provider():
    """Create mock Google Calendar provider."""
    mock = AsyncMock()
    mock.get_free_busy_times.return_value = {
        "success": True,
        "free_busy_times": [
            {
                "start": "2024-01-01T10:00:00Z",
                "end": "2024-01-01T11:00:00Z",
                "available": True,
            }
        ]
    }
    mock.create_calendar_event.return_value = {
        "success": True,
        "event_id": "test_event_id",
    }
    mock.refresh_token.return_value = True
    return mock


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_celery_app():
    """Create mock Celery app."""
    mock = MagicMock()
    mock.send_task.return_value = MagicMock(id="test_task_id")
    mock.control.inspect.return_value = MagicMock()
    return mock


# Test data fixtures
@pytest.fixture
def sample_meeting_data():
    """Sample meeting data for testing."""
    from datetime import datetime, timedelta
    
    return {
        "title": "Team Standup",
        "description": "Daily team standup meeting",
        "duration_minutes": 30,
        "earliest_start": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "latest_end": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "working_hours_start": 9,
        "working_hours_end": 17,
        "timezone": "UTC",
        "participants": [
            {"telegram_id": 12345, "username": "user1"},
            {"telegram_id": 67890, "username": "user2"},
        ]
    }


@pytest.fixture
def sample_oauth_data():
    """Sample OAuth data for testing."""
    return {
        "code": "test_auth_code",
        "state": "test_state",
        "scope": "https://www.googleapis.com/auth/calendar",
    }


@pytest.fixture
def sample_time_slots():
    """Sample time slots for testing."""
    from datetime import datetime, timedelta
    
    base_time = datetime.utcnow() + timedelta(days=1)
    return [
        {
            "start": (base_time + timedelta(hours=9)).isoformat(),
            "end": (base_time + timedelta(hours=10)).isoformat(),
            "available": True,
        },
        {
            "start": (base_time + timedelta(hours=10)).isoformat(),
            "end": (base_time + timedelta(hours=11)).isoformat(),
            "available": True,
        },
        {
            "start": (base_time + timedelta(hours=14)).isoformat(),
            "end": (base_time + timedelta(hours=15)).isoformat(),
            "available": False,
        },
    ]


# Utility fixtures
@pytest.fixture
def temp_file():
    """Create temporary file for testing."""
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("ENCRYPTION_KEY", "test_encryption_key_32_bytes_long")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key")


# Async test helpers
@pytest.fixture
def async_test():
    """Helper for async tests."""
    def _async_test(coro):
        return asyncio.get_event_loop().run_until_complete(coro)
    return _async_test


# Test markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_external: Tests requiring external services")
