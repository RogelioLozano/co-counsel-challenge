"""Unit tests for EventPublisher"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from events.publisher import EventPublisher
from domain.models import UserMessageEvent, AIRequestEvent, AIResponseEvent
from domain.constants import (
    EVENT_TYPE_USER_MESSAGE,
    EVENT_TYPE_AI_REQUEST,
    EVENT_TYPE_AI_RESPONSE,
)


@pytest.mark.unit
class TestEventPublisherInitialization:
    """Test EventPublisher initialization"""

    def test_publisher_initialization(self):
        """Test creating EventPublisher instance"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        assert publisher.queue is queue

    def test_publisher_with_mocked_queue(self):
        """Test EventPublisher with mocked queue"""
        queue = MagicMock()
        publisher = EventPublisher(queue)
        
        assert publisher.queue is queue


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherPublishUserMessageEvent:
    """Test EventPublisher publishing UserMessageEvent"""

    async def test_publish_user_message_event(self):
        """Test publishing a UserMessageEvent"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="Test User",
            text="Hello",
        )
        
        await publisher.publish(event)
        
        # Event should be in queue
        assert not queue.empty()
        published = await queue.get()
        
        assert published["type"] == EVENT_TYPE_USER_MESSAGE
        assert published["user_id"] == "user_1"
        assert published["sender"] == "Test User"
        assert published["text"] == "Hello"

    async def test_publish_user_message_converts_to_dict(self):
        """Test that UserMessageEvent is converted to dict"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="User",
            text="Test message",
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert isinstance(published, dict)
        assert set(published.keys()) == {"type", "user_id", "sender", "text", "sender_ws"}

    async def test_publish_user_message_includes_sender_ws(self):
        """Test that sender_ws is included in published event"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        ws = MagicMock()
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="User",
            text="Message",
            sender_ws=ws,
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert published["sender_ws"] is ws


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherPublishAIRequestEvent:
    """Test EventPublisher publishing AIRequestEvent"""

    async def test_publish_ai_request_event(self):
        """Test publishing an AIRequestEvent"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIRequestEvent(
            type=EVENT_TYPE_AI_REQUEST,
            user_id="user_1",
            sender="Test User",
            text="Process this",
        )
        
        await publisher.publish(event)
        
        published = await queue.get()
        assert published["type"] == EVENT_TYPE_AI_REQUEST
        assert published["user_id"] == "user_1"
        assert published["sender"] == "Test User"
        assert published["text"] == "Process this"

    async def test_publish_ai_request_converts_to_dict(self):
        """Test that AIRequestEvent is converted to dict"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIRequestEvent(
            type=EVENT_TYPE_AI_REQUEST,
            user_id="user_1",
            sender="User",
            text="AI request",
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert isinstance(published, dict)
        assert published["type"] == EVENT_TYPE_AI_REQUEST

    async def test_publish_ai_request_preserves_all_fields(self):
        """Test that all AIRequestEvent fields are preserved"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        ws = MagicMock()
        event = AIRequestEvent(
            type=EVENT_TYPE_AI_REQUEST,
            user_id="user_123",
            sender="Alice",
            text="Request text",
            sender_ws=ws,
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert published["user_id"] == "user_123"
        assert published["sender"] == "Alice"
        assert published["text"] == "Request text"
        assert published["sender_ws"] is ws


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherPublishAIResponseEvent:
    """Test EventPublisher publishing AIResponseEvent"""

    async def test_publish_ai_response_event(self):
        """Test publishing an AIResponseEvent"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIResponseEvent(
            type=EVENT_TYPE_AI_RESPONSE,
            text="AI response",
            original_message="User message",
            detected_intent="python",
        )
        
        await publisher.publish(event)
        
        published = await queue.get()
        assert published["type"] == EVENT_TYPE_AI_RESPONSE
        assert published["text"] == "AI response"
        assert published["original_message"] == "User message"
        assert published["detected_intent"] == "python"

    async def test_publish_ai_response_converts_to_dict(self):
        """Test that AIResponseEvent is converted to dict"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIResponseEvent(
            type=EVENT_TYPE_AI_RESPONSE,
            text="Response",
            original_message="Original",
            detected_intent="test",
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert isinstance(published, dict)

    async def test_publish_ai_response_includes_all_fields(self):
        """Test that all AIResponseEvent fields are in published dict"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIResponseEvent(
            type=EVENT_TYPE_AI_RESPONSE,
            text="Test response",
            original_message="Test message",
            detected_intent="database",
        )
        
        await publisher.publish(event)
        published = await queue.get()
        
        assert set(published.keys()) == {
            "type",
            "text",
            "original_message",
            "detected_intent",
        }


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherPublishDict:
    """Test EventPublisher publishing plain dict"""

    async def test_publish_dict_directly(self):
        """Test publishing a plain dict"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event_dict = {"type": "custom", "data": "test"}
        await publisher.publish(event_dict)
        
        published = await queue.get()
        assert published == event_dict

    async def test_publish_dict_passthrough(self):
        """Test that plain dict is passed through unchanged"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        original_dict = {"key": "value", "nested": {"data": 123}}
        await publisher.publish(original_dict)
        
        published = await queue.get()
        assert published == original_dict


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherQueueBehavior:
    """Test EventPublisher queue interaction"""

    async def test_publish_adds_to_queue(self):
        """Test that publish adds event to queue"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        assert queue.empty()
        
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="User",
            text="Message",
        )
        
        await publisher.publish(event)
        
        assert not queue.empty()
        assert queue.qsize() == 1

    async def test_publish_multiple_events(self):
        """Test publishing multiple events"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event1 = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="User 1",
            text="Message 1",
        )
        event2 = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_2",
            sender="User 2",
            text="Message 2",
        )
        
        await publisher.publish(event1)
        await publisher.publish(event2)
        
        assert queue.qsize() == 2
        
        first = await queue.get()
        second = await queue.get()
        
        assert first["sender"] == "User 1"
        assert second["sender"] == "User 2"

    async def test_publish_maintains_event_order(self):
        """Test that events are published in order"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        events = []
        for i in range(5):
            event = UserMessageEvent(
                type=EVENT_TYPE_USER_MESSAGE,
                user_id=f"user_{i}",
                sender=f"User {i}",
                text=f"Message {i}",
            )
            events.append(event)
            await publisher.publish(event)
        
        for i in range(5):
            published = await queue.get()
            assert published["sender"] == f"User {i}"

    async def test_publish_with_mocked_queue(self):
        """Test publish with mocked queue"""
        queue = AsyncMock()
        publisher = EventPublisher(queue)
        
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="User",
            text="Message",
        )
        
        await publisher.publish(event)
        
        queue.put.assert_called_once()
        call_args = queue.put.call_args[0][0]
        assert call_args["type"] == EVENT_TYPE_USER_MESSAGE


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventPublisherEventTypePreservation:
    """Test that event types are correctly preserved"""

    async def test_user_message_event_type_preserved(self):
        """Test USER_MESSAGE type is preserved"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = UserMessageEvent(type=EVENT_TYPE_USER_MESSAGE)
        await publisher.publish(event)
        
        published = await queue.get()
        assert published["type"] == EVENT_TYPE_USER_MESSAGE

    async def test_ai_request_event_type_preserved(self):
        """Test AI_REQUEST type is preserved"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIRequestEvent(type=EVENT_TYPE_AI_REQUEST)
        await publisher.publish(event)
        
        published = await queue.get()
        assert published["type"] == EVENT_TYPE_AI_REQUEST

    async def test_ai_response_event_type_preserved(self):
        """Test AI_RESPONSE type is preserved"""
        queue = asyncio.Queue()
        publisher = EventPublisher(queue)
        
        event = AIResponseEvent(type=EVENT_TYPE_AI_RESPONSE)
        await publisher.publish(event)
        
        published = await queue.get()
        assert published["type"] == EVENT_TYPE_AI_RESPONSE
