"""Unit tests for domain models"""
import pytest

from domain.models import (
    User,
    Message,
    HistoryMessage,
    UserMessageEvent,
    AIRequestEvent,
)
from domain.constants import (
    MESSAGE_TYPE_USER,
    MESSAGE_TYPE_AI_RESPONSE,
    MESSAGE_TYPE_AI_REQUEST,
    EVENT_TYPE_USER_MESSAGE,
    EVENT_TYPE_AI_REQUEST,
    EVENT_TYPE_AI_RESPONSE,
)


@pytest.mark.unit
class TestUser:
    """Test User dataclass"""

    def test_user_creation(self):
        """Test creating a User instance"""
        user = User(user_id="user_123", username="Test User")
        assert user.user_id == "user_123"
        assert user.username == "Test User"

    def test_user_with_different_ids(self):
        """Test creating users with different IDs"""
        user1 = User(user_id="user_1", username="User 1")
        user2 = User(user_id="user_2", username="User 2")
        assert user1.user_id != user2.user_id
        assert user1.username != user2.username


@pytest.mark.unit
class TestMessage:
    """Test Message dataclass"""

    def test_message_creation(self):
        """Test creating a Message instance"""
        msg = Message(
            sender_id="user_123",
            sender="Test User",
            text="Hello World",
            msg_type=MESSAGE_TYPE_USER,
        )
        assert msg.sender_id == "user_123"
        assert msg.sender == "Test User"
        assert msg.text == "Hello World"
        assert msg.msg_type == MESSAGE_TYPE_USER

    def test_message_with_ai_type(self):
        """Test creating an AI Message"""
        msg = Message(
            sender_id="ai_0",
            sender="AIBot",
            text="AI Response",
            msg_type=MESSAGE_TYPE_AI_RESPONSE,
        )
        assert msg.msg_type == MESSAGE_TYPE_AI_RESPONSE
        assert msg.sender == "AIBot"

    def test_message_empty_content(self):
        """Test creating a Message with empty text"""
        msg = Message(
            sender_id="user_1",
            sender="Test User",
            text="",
            msg_type=MESSAGE_TYPE_USER,
        )
        assert msg.text == ""

    def test_message_default_conversation_id(self):
        """Test Message default conversation ID"""
        msg = Message(
            sender_id="user_1",
            sender="Test User",
            text="test",
            msg_type=MESSAGE_TYPE_USER,
        )
        assert msg.conversation_id == "default"


@pytest.mark.unit
class TestHistoryMessage:
    """Test HistoryMessage dataclass"""

    def test_history_message_creation(self):
        """Test creating a HistoryMessage instance"""
        hist_msg = HistoryMessage(
            sender="Test User",
            text="Test message",
            msg_type=MESSAGE_TYPE_USER,
            timestamp="2024-01-01T12:00:00",
        )
        assert hist_msg.sender == "Test User"
        assert hist_msg.text == "Test message"
        assert hist_msg.msg_type == MESSAGE_TYPE_USER
        assert hist_msg.timestamp == "2024-01-01T12:00:00"

    def test_history_message_with_ai_message(self):
        """Test creating a HistoryMessage for AI responses"""
        hist_msg = HistoryMessage(
            sender="AIBot",
            text="AI thinks...",
            msg_type=MESSAGE_TYPE_AI_RESPONSE,
            timestamp="2024-01-01T12:00:01",
        )
        assert hist_msg.msg_type == MESSAGE_TYPE_AI_RESPONSE

    def test_history_message_composition(self):
        """Verify HistoryMessage has all required fields"""
        hist_msg = HistoryMessage(
            sender="User",
            text="test",
            msg_type=MESSAGE_TYPE_USER,
            timestamp="2024-01-01T12:00:00",
        )
        # Should have all fields
        assert hasattr(hist_msg, "sender")
        assert hasattr(hist_msg, "text")
        assert hasattr(hist_msg, "msg_type")
        assert hasattr(hist_msg, "timestamp")


@pytest.mark.unit
class TestUserMessageEvent:
    """Test UserMessageEvent dataclass"""

    def test_user_message_event_creation(self):
        """Test creating a UserMessageEvent"""
        event = UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            user_id="user_1",
            sender="Test User",
            text="Hello",
        )
        assert event.user_id == "user_1"
        assert event.sender == "Test User"
        assert event.text == "Hello"
        assert event.type == EVENT_TYPE_USER_MESSAGE

    def test_user_message_event_defaults(self):
        """Test UserMessageEvent default values"""
        event = UserMessageEvent()
        assert event.type == EVENT_TYPE_USER_MESSAGE
        assert event.user_id == ""
        assert event.sender == ""
        assert event.text == ""
        assert event.sender_ws is None


@pytest.mark.unit
class TestAIRequestEvent:
    """Test AIRequestEvent dataclass"""

    def test_ai_request_event_creation(self):
        """Test creating an AIRequestEvent"""
        event = AIRequestEvent(
            type=EVENT_TYPE_AI_REQUEST,
            user_id="user_1",
            sender="Test User",
            text="User asked something",
        )
        assert event.user_id == "user_1"
        assert event.sender == "Test User"
        assert event.text == "User asked something"
        assert event.type == EVENT_TYPE_AI_REQUEST

    def test_ai_request_event_defaults(self):
        """Test AIRequestEvent default values"""
        event = AIRequestEvent()
        assert event.type == EVENT_TYPE_AI_REQUEST
        assert event.user_id == ""
        assert event.sender == ""
        assert event.text == ""
        assert event.sender_ws is None


@pytest.mark.unit
class TestMessageTypeConstants:
    """Test MessageType constant values"""

    def test_message_type_user(self):
        """Test USER message type constant"""
        assert MESSAGE_TYPE_USER == "user_message"

    def test_message_type_ai_response(self):
        """Test AI_RESPONSE message type constant"""
        assert MESSAGE_TYPE_AI_RESPONSE == "ai_response"

    def test_message_type_ai_request(self):
        """Test AI_REQUEST message type constant"""
        assert MESSAGE_TYPE_AI_REQUEST == "ai_request"


@pytest.mark.unit
class TestEventTypeConstants:
    """Test EventType constant values"""

    def test_event_type_user_message(self):
        """Test USER_MESSAGE event type constant"""
        assert EVENT_TYPE_USER_MESSAGE == "user_message"

    def test_event_type_ai_request(self):
        """Test AI_REQUEST event type constant"""
        assert EVENT_TYPE_AI_REQUEST == "ai_request"

    def test_event_type_ai_response(self):
        """Test AI_RESPONSE event type constant"""
        assert EVENT_TYPE_AI_RESPONSE == "ai_response"
