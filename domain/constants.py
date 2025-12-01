"""Domain constants and type aliases"""
from typing import Literal

# Type aliases for message and event types
MessageType = Literal["user_message", "ai_response", "ai_request"]
EventType = Literal["user_message", "ai_response", "ai_request"]
ConversationId = Literal["default"]

# Message type constants
MESSAGE_TYPE_USER: MessageType = "user_message"
MESSAGE_TYPE_AI_RESPONSE: MessageType = "ai_response"
MESSAGE_TYPE_AI_REQUEST: MessageType = "ai_request"

# Conversation ID constants
CONVERSATION_DEFAULT: ConversationId = "default"

# Event type constants
EVENT_TYPE_USER_MESSAGE: EventType = "user_message"
EVENT_TYPE_AI_RESPONSE: EventType = "ai_response"
EVENT_TYPE_AI_REQUEST: EventType = "ai_request"
