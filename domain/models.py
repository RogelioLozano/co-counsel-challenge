"""Domain models for the chat system"""
from dataclasses import dataclass
from fastapi import WebSocket

from .constants import MessageType, EventType, MESSAGE_TYPE_USER, CONVERSATION_DEFAULT, ConversationId, EVENT_TYPE_USER_MESSAGE, EVENT_TYPE_AI_REQUEST, EVENT_TYPE_AI_RESPONSE


@dataclass
class User:
    """Represents a user in the chat system"""
    user_id: str
    username: str # corresponds to 'sender' in messages


@dataclass
class Message:
    """Represents a message in the chat system"""
    sender_id: str
    sender: str
    text: str
    msg_type: MessageType = MESSAGE_TYPE_USER
    conversation_id: ConversationId = CONVERSATION_DEFAULT


@dataclass
class HistoryMessage:
    """Message as it appears in conversation history (from database/persistence layer)
    
    Represents a message retrieved from the database with timestamp.
    
    Fields:
    - sender: Name of the message sender
    - text: Message content
    - msg_type: Type of message (user_message, ai_response, etc.)
    - timestamp: When the message was created
    """
    sender: str
    text: str
    msg_type: MessageType
    timestamp: str


@dataclass
class UserMessageEvent:
    """Event: A user sends a message"""
    type: EventType = EVENT_TYPE_USER_MESSAGE
    user_id: str = ""
    sender: str = ""
    text: str = ""
    sender_ws: WebSocket | None = None


@dataclass
class AIRequestEvent:
    """Event: AI processing requested"""
    type: EventType = EVENT_TYPE_AI_REQUEST
    user_id: str = ""
    sender: str = ""
    text: str = ""
    sender_ws: WebSocket | None = None


@dataclass
class AIResponseEvent:
    """Event: AI response ready"""
    type: EventType = EVENT_TYPE_AI_RESPONSE
    text: str = ""
    original_message: str = ""
    detected_intent: str = ""
