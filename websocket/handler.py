"""WebSocket connection handling and message parsing"""
import json
from fastapi import WebSocket, WebSocketDisconnect

from domain.constants import EVENT_TYPE_AI_REQUEST, EVENT_TYPE_USER_MESSAGE, CONVERSATION_DEFAULT
from domain.models import UserMessageEvent, AIRequestEvent
from database.chat_database import ChatDatabase
from events.publisher import EventPublisher
from websocket.connection_manager import ConnectionManager


def parse_message_event(websocket: WebSocket, user_id: str, sender: str, message: str) -> UserMessageEvent | AIRequestEvent:
    """Parse incoming message and determine event type"""
    data: dict[str, str] = json.loads(message)
    msg_type: str = data.get("type", "message").strip()
    text: str = data.get("text", "")
    
    # Check if message is an AI request
    if text.startswith("/AIBot"):
        return AIRequestEvent(
            type=EVENT_TYPE_AI_REQUEST,
            sender_ws=websocket,
            user_id=user_id,
            sender=sender,
            text=text.replace("/AIBot", "").strip()
        )
    else:
        return UserMessageEvent(
            type=EVENT_TYPE_USER_MESSAGE,
            sender_ws=websocket,
            user_id=user_id,
            sender=sender,
            text=text
        )


async def process_message(websocket: WebSocket, user_id: str, sender: str, message: str, publisher) -> None:
    """Process incoming message and publish to event queue"""
    event = parse_message_event(websocket, user_id, sender, message)
    await publisher.publish(event)


async def handle_websocket_connection(websocket: WebSocket, db: ChatDatabase, publisher: EventPublisher, connection_manager: ConnectionManager) -> None:
    """Handle WebSocket connection with username from query parameter"""
    username: str = ""
    
    try:
        # Extract username from query params BEFORE accepting connection
        username = websocket.query_params.get("username", "").strip()
        
        if not username:
            # Reject connection at handshake with WebSocket close code
            await websocket.close(code=1008, reason="Username required. Connect with: ws://localhost:8765/ws?username=YourName")
            return
        
        # Accept connection and add to manager
        await connection_manager.connect(websocket)
        
        # Get or create user
        user_id = await db.get_or_create_user(username)
        
        # Add user to default conversation
        await db.add_user_to_conversation(user_id, CONVERSATION_DEFAULT)
        
        print(f"User '{username}' (ID: {user_id}) connected. Total clients: {connection_manager.get_connection_count()}")
        
        # Send connection success
        await websocket.send_text(json.dumps({
            "type": "connected",
            "user_id": user_id,
            "username": username
        }))
        
        # Send full conversation history (all messages from all users)
        history = await db.get_conversation_history_dict(CONVERSATION_DEFAULT)
        await websocket.send_text(json.dumps({
            "type": "history",
            "messages": history,
            "count": len(history)
        }))
        
        # Now listen for messages - all are regular chat messages
        while True:
            message = await websocket.receive_text()
            try:
                msg_data: dict = json.loads(message)
                text: str = msg_data.get("text", "").strip()
                
                if not text:
                    continue
                
                # Process and publish message
                await process_message(websocket, user_id, username, message, publisher)
                
            except json.JSONDecodeError:
                print(f"Invalid JSON received from {username}")
                # Send error but don't close connection - client can recover
                try:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    print(f"Error sending error message: {e}")
                    
    except WebSocketDisconnect:
        print(f"Client '{username}' disconnected. Total clients: {connection_manager.get_connection_count() - 1}")
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)
