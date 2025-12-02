"""Pytest configuration and shared fixtures for all tests"""
import pytest
import asyncio
from unittest.mock import AsyncMock

from database.chat_database import ChatDatabase
from events.publisher import EventPublisher
from events.consumer import EventConsumer, AIEventConsumer
from ai.agent import MockedAIAgent
from websocket.connection_manager import ConnectionManager

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
async def event_queue():
    """Create a new event queue for each test"""
    return asyncio.Queue()


@pytest.fixture
async def in_memory_db():
    """Create an in-memory SQLite database for testing"""
    db = ChatDatabase(":memory:")
    await db.init()
    yield db
    await db.close()


@pytest.fixture
def connection_manager():
    """Create a ConnectionManager instance for testing"""
    return ConnectionManager()


@pytest.fixture
async def event_publisher(event_queue):
    """Create an EventPublisher instance for testing"""
    return EventPublisher(event_queue)


@pytest.fixture
async def mocked_ai_agent(event_publisher):
    """Create a MockedAIAgent with a mocked publisher"""
    return MockedAIAgent(event_publisher)


@pytest.fixture
async def event_consumer(event_queue, in_memory_db, mocked_ai_agent, connection_manager):
    """Create an EventConsumer instance for testing"""
    return EventConsumer(event_queue, in_memory_db, mocked_ai_agent, connection_manager)


@pytest.fixture
async def ai_event_consumer(event_queue, in_memory_db, mocked_ai_agent, connection_manager):
    """Create an AIEventConsumer instance for testing"""
    return AIEventConsumer(event_queue, in_memory_db, mocked_ai_agent, connection_manager)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_websocket_set():
    """Create a set of mock WebSockets for testing"""
    return {AsyncMock() for _ in range(3)}
