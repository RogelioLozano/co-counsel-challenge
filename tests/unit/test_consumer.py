"""Unit tests for EventConsumer and AIEventConsumer"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from events.consumer import EventConsumer, AIEventConsumer
from domain.models import Message
from domain.constants import (
    EVENT_TYPE_USER_MESSAGE,
    EVENT_TYPE_AI_REQUEST,
    EVENT_TYPE_AI_RESPONSE,
    MESSAGE_TYPE_USER,
    MESSAGE_TYPE_AI_RESPONSE,
    CONVERSATION_DEFAULT,
)


@pytest.mark.unit
class TestEventConsumerInitialization:
    """Test EventConsumer initialization"""

    def test_consumer_initialization(self):
        """Test creating EventConsumer instance"""
        queue = asyncio.Queue()
        db = MagicMock()
        ai_agent = MagicMock()
        connection_manager = MagicMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        assert consumer.queue is queue
        assert consumer.db is db
        assert consumer.ai_agent is ai_agent
        assert consumer.connection_manager is connection_manager


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventConsumerHandleEvent:
    """Test EventConsumer event handling routing"""

    async def test_handle_user_message_event_routed(self):
        """Test that USER_MESSAGE events are routed to handle_user_message"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_user_message = AsyncMock()
        consumer.handle_ai_response = AsyncMock()
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "User",
            "text": "Hello",
        }
        
        await consumer.handle_event(event)
        
        consumer.handle_user_message.assert_called_once_with(event)
        consumer.handle_ai_response.assert_not_called()

    async def test_handle_ai_response_event_routed(self):
        """Test that AI_RESPONSE events are routed to handle_ai_response"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_user_message = AsyncMock()
        consumer.handle_ai_response = AsyncMock()
        
        event = {
            "type": EVENT_TYPE_AI_RESPONSE,
            "text": "AI response",
        }
        
        await consumer.handle_event(event)
        
        consumer.handle_ai_response.assert_called_once_with(event)
        consumer.handle_user_message.assert_not_called()

    async def test_handle_event_with_unknown_type(self):
        """Test that unknown event types are ignored"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_user_message = AsyncMock()
        consumer.handle_ai_response = AsyncMock()
        
        event = {"type": "unknown_type"}
        
        await consumer.handle_event(event)
        
        consumer.handle_user_message.assert_not_called()
        consumer.handle_ai_response.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventConsumerHandleUserMessage:
    """Test EventConsumer user message handling"""

    async def test_handle_user_message_saves_to_db(self):
        """Test that user messages are saved to database"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "Test User",
            "text": "Hello world",
        }
        
        await consumer.handle_user_message(event)
        
        db.save_message.assert_called_once()
        saved_message = db.save_message.call_args[0][0]
        assert isinstance(saved_message, Message)
        assert saved_message.sender_id == "user_1"
        assert saved_message.sender == "Test User"
        assert saved_message.text == "Hello world"
        assert saved_message.msg_type == MESSAGE_TYPE_USER

    async def test_handle_user_message_broadcasts(self):
        """Test that user messages are broadcast to clients"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "Test User",
            "text": "Message",
        }
        
        await consumer.handle_user_message(event)
        
        connection_manager.broadcast.assert_called_once()
        broadcast_msg = connection_manager.broadcast.call_args[0][0]
        assert broadcast_msg["sender"] == "Test User"
        assert broadcast_msg["text"] == "Message"

    async def test_handle_user_message_with_sender_ws(self):
        """Test that user messages exclude sender WebSocket"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        sender_ws = MagicMock()
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "User",
            "text": "Message",
            "sender_ws": sender_ws,
        }
        
        await consumer.handle_user_message(event)
        
        connection_manager.broadcast_except.assert_called_once()
        args = connection_manager.broadcast_except.call_args[0]
        assert args[1] is sender_ws
        connection_manager.broadcast.assert_not_called()

    async def test_handle_user_message_skip_if_no_user_id(self):
        """Test that message is skipped if user_id is missing"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "",
            "sender": "User",
            "text": "Message",
        }
        
        await consumer.handle_user_message(event)
        
        db.save_message.assert_not_called()

    async def test_handle_user_message_skip_if_no_sender(self):
        """Test that message is skipped if sender is missing"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "",
            "text": "Message",
        }
        
        await consumer.handle_user_message(event)
        
        db.save_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventConsumerHandleAIResponse:
    """Test EventConsumer AI response handling"""

    async def test_handle_ai_response_saves_to_db(self):
        """Test that AI responses are saved to database"""
        queue = asyncio.Queue()
        db = AsyncMock()
        db.get_or_create_user = AsyncMock(return_value="ai_user_id")
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_AI_RESPONSE,
            "text": "AI response text",
        }
        
        await consumer.handle_ai_response(event)
        
        db.get_or_create_user.assert_called_once_with("AIBot")
        db.save_message.assert_called_once()
        saved_message = db.save_message.call_args[0][0]
        assert saved_message.sender == "AIBot"
        assert saved_message.text == "AI response text"
        assert saved_message.msg_type == MESSAGE_TYPE_AI_RESPONSE

    async def test_handle_ai_response_broadcasts(self):
        """Test that AI responses are broadcast to all clients"""
        queue = asyncio.Queue()
        db = AsyncMock()
        db.get_or_create_user = AsyncMock(return_value="ai_user_id")
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_AI_RESPONSE,
            "text": "AI response",
        }
        
        await consumer.handle_ai_response(event)
        
        connection_manager.broadcast.assert_called_once()
        broadcast_msg = connection_manager.broadcast.call_args[0][0]
        assert broadcast_msg["sender"] == "AIBot"
        assert broadcast_msg["text"] == "AI response"

    async def test_handle_ai_response_handles_save_error(self):
        """Test that save errors are handled gracefully"""
        queue = asyncio.Queue()
        db = AsyncMock()
        db.get_or_create_user = AsyncMock(side_effect=Exception("DB error"))
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        
        event = {
            "type": EVENT_TYPE_AI_RESPONSE,
            "text": "Response",
        }
        
        # Should not raise an exception
        await consumer.handle_ai_response(event)
        
        # Message should still be broadcast
        connection_manager.broadcast.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestAIEventConsumerHandleEvent:
    """Test AIEventConsumer event routing"""

    async def test_ai_event_consumer_handles_ai_request(self):
        """Test that AIEventConsumer handles AI_REQUEST events"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = AsyncMock()
        connection_manager = AsyncMock()
        
        consumer = AIEventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_user_message = AsyncMock()
        
        event = {
            "type": EVENT_TYPE_AI_REQUEST,
            "user_id": "user_1",
            "sender": "User",
            "text": "Process this",
        }
        
        await consumer.handle_event(event)
        
        # Should handle user message first
        consumer.handle_user_message.assert_called_once_with(event)
        # Then call AI agent
        ai_agent.process_request.assert_called_once_with(event)

    async def test_ai_event_consumer_handles_user_message(self):
        """Test that AIEventConsumer handles USER_MESSAGE events"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = AIEventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_user_message = AsyncMock()
        
        event = {
            "type": EVENT_TYPE_USER_MESSAGE,
            "user_id": "user_1",
            "sender": "User",
            "text": "Hello",
        }
        
        await consumer.handle_event(event)
        
        consumer.handle_user_message.assert_called_once_with(event)

    async def test_ai_event_consumer_handles_ai_response(self):
        """Test that AIEventConsumer handles AI_RESPONSE events"""
        queue = asyncio.Queue()
        db = AsyncMock()
        db.get_or_create_user = AsyncMock(return_value="ai_id")
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = AIEventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_ai_response = AsyncMock()
        
        event = {
            "type": EVENT_TYPE_AI_RESPONSE,
            "text": "Response",
        }
        
        await consumer.handle_event(event)
        
        consumer.handle_ai_response.assert_called_once_with(event)


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventConsumerConsume:
    """Test EventConsumer consume loop"""

    async def test_consume_gets_from_queue(self):
        """Test that consume gets events from queue"""
        queue = asyncio.Queue()
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_event = AsyncMock()
        
        # Add one event then make it stop
        event = {"type": EVENT_TYPE_USER_MESSAGE}
        queue.put_nowait(event)
        
        # Run consume for just one iteration
        consume_task = asyncio.create_task(consumer.consume())
        await asyncio.sleep(0.1)  # Let it process
        consume_task.cancel()
        
        try:
            await consume_task
        except asyncio.CancelledError:
            pass
        
        consumer.handle_event.assert_called_once_with(event)

    async def test_consume_calls_task_done(self):
        """Test that consume calls queue.task_done()"""
        queue = AsyncMock(spec=asyncio.Queue)
        queue.get = AsyncMock(side_effect=asyncio.CancelledError())
        db = AsyncMock()
        ai_agent = MagicMock()
        connection_manager = AsyncMock()
        
        consumer = EventConsumer(queue, db, ai_agent, connection_manager)
        consumer.handle_event = AsyncMock()
        
        consume_task = asyncio.create_task(consumer.consume())
        await asyncio.sleep(0.1)
        
        try:
            await consume_task
        except asyncio.CancelledError:
            pass


@pytest.mark.unit
class TestEventConsumerInheritance:
    """Test AIEventConsumer inheritance"""

    def test_ai_event_consumer_inherits_from_event_consumer(self):
        """Test that AIEventConsumer inherits from EventConsumer"""
        queue = asyncio.Queue()
        db = MagicMock()
        ai_agent = MagicMock()
        connection_manager = MagicMock()
        
        consumer = AIEventConsumer(queue, db, ai_agent, connection_manager)
        
        assert isinstance(consumer, EventConsumer)
        assert hasattr(consumer, "handle_user_message")
        assert hasattr(consumer, "handle_ai_response")
        assert hasattr(consumer, "handle_event")

    def test_ai_event_consumer_has_all_attributes(self):
        """Test that AIEventConsumer has all required attributes"""
        queue = asyncio.Queue()
        db = MagicMock()
        ai_agent = MagicMock()
        connection_manager = MagicMock()
        
        consumer = AIEventConsumer(queue, db, ai_agent, connection_manager)
        
        assert consumer.queue is queue
        assert consumer.db is db
        assert consumer.ai_agent is ai_agent
        assert consumer.connection_manager is connection_manager
