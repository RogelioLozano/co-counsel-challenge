"""Event consuming and handling for the chat system"""
import asyncio
from fastapi import WebSocket

from domain.constants import EVENT_TYPE_USER_MESSAGE, EVENT_TYPE_AI_REQUEST, EVENT_TYPE_AI_RESPONSE, MESSAGE_TYPE_USER, MESSAGE_TYPE_AI_RESPONSE, CONVERSATION_DEFAULT
from domain.models import Message
from websocket.connection_manager import ConnectionManager


class EventConsumer:
    """Consumes events from the queue and handles them"""
    
    def __init__(self, queue: asyncio.Queue[dict], db, ai_agent, connection_manager: ConnectionManager) -> None:
        self.queue = queue
        self.db = db
        self.ai_agent = ai_agent
        self.connection_manager = connection_manager
    
    async def consume(self) -> None:
        """Continuously consume and process events"""
        while True:
            event = await self.queue.get()
            await self.handle_event(event)
            self.queue.task_done()
    
    async def handle_event(self, event: dict) -> None:
        """Route event to appropriate handler"""
        event_type: str = event.get("type", "")
        
        if event_type == EVENT_TYPE_USER_MESSAGE:
            await self.handle_user_message(event)
        elif event_type == EVENT_TYPE_AI_RESPONSE:
            await self.handle_ai_response(event)
    
    async def handle_user_message(self, event: dict) -> None:
        """Handle user message events and save to database"""
        # Save to database
        user_id: str = event.get("user_id", "")
        sender: str = event.get("sender", "")
        text: str = event.get("text", "")
        
        if user_id and sender:
            message = Message(
                sender_id=user_id,
                sender=sender,
                text=text,
                msg_type=MESSAGE_TYPE_USER,
                conversation_id=CONVERSATION_DEFAULT
            )
            await self.db.save_message(message)
        
        broadcast_message = {
            "sender": sender,
            "text": text
        }
        
        # Send to all connected clients except sender
        sender_ws: WebSocket | None = event.get("sender_ws")
        if sender_ws:
            await self.connection_manager.broadcast_except(broadcast_message, sender_ws)
        else:
            await self.connection_manager.broadcast(broadcast_message)
    
    async def handle_ai_response(self, event: dict) -> None:
        """Handle AI response events and save to database"""
        # Save to database using AIBot's username
        try:
            text: str = event.get("text", "")
            ai_user_id = await self.db.get_or_create_user("AIBot")
            message = Message(
                sender_id=ai_user_id,
                sender="AIBot",
                text=text,
                msg_type=MESSAGE_TYPE_AI_RESPONSE,
                conversation_id=CONVERSATION_DEFAULT
            )
            await self.db.save_message(message)
        except Exception as e:
            print(f"Error saving AI response to database: {e}")
        
        broadcast_message = {
            "sender": "AIBot",
            "text": event.get("text", "")
        }
        
        # Send to all connected clients
        await self.connection_manager.broadcast(broadcast_message)


class AIEventConsumer(EventConsumer):
    """Extended consumer that also handles AI requests"""
    
    def __init__(self, queue: asyncio.Queue[dict], db, ai_agent, connection_manager: ConnectionManager) -> None:
        super().__init__(queue, db, ai_agent, connection_manager)
    
    async def handle_event(self, event: dict) -> None:
        """Route event to appropriate handler, including AI requests"""
        event_type: str = event.get("type", "")
        
        if event_type == EVENT_TYPE_USER_MESSAGE:
            await self.handle_user_message(event)
        elif event_type == EVENT_TYPE_AI_REQUEST:
            request_text: str = event.get("text", "")
            print(f"AI Request received: {request_text}")
            await self.handle_user_message(event)  # Handle user message first
            await self.ai_agent.process_request(event)
        elif event_type == EVENT_TYPE_AI_RESPONSE:
            response_text: str = event.get("text", "")
            print(f"AI Response: {response_text}")
            await self.handle_ai_response(event)
