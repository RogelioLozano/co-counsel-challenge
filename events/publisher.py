"""Event publishing for the chat system"""
import asyncio

from domain.constants import EVENT_TYPE_USER_MESSAGE, EVENT_TYPE_AI_REQUEST, EVENT_TYPE_AI_RESPONSE
from domain.models import UserMessageEvent, AIRequestEvent, AIResponseEvent


class EventPublisher:
    """Publishes events to the event queue"""
    
    def __init__(self, queue: asyncio.Queue[dict]) -> None:
        self.queue = queue
    
    async def publish(self, event: UserMessageEvent | AIRequestEvent | AIResponseEvent | dict) -> None:
        """Publish an event to the queue (accepts dataclass or dict)"""
        # Convert dataclass to dict manually to avoid asdict() serialization issues
        if isinstance(event, UserMessageEvent):
            event_dict = {
                "type": event.type,
                "user_id": event.user_id,
                "sender": event.sender,
                "text": event.text,
                "sender_ws": event.sender_ws,
            }
        elif isinstance(event, AIRequestEvent):
            event_dict = {
                "type": event.type,
                "user_id": event.user_id,
                "sender": event.sender,
                "text": event.text,
                "sender_ws": event.sender_ws,
            }
        elif isinstance(event, AIResponseEvent):
            event_dict = {
                "type": event.type,
                "text": event.text,
                "original_message": event.original_message,
                "detected_intent": event.detected_intent,
            }
        else:
            event_dict = event
        await self.queue.put(event_dict)

