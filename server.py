import json
import asyncio
import uuid
from typing import Set, Literal
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import aiosqlite
import uvicorn

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

# Set to store connected clients
connected_clients: Set[WebSocket] = set()

# Event queue for message pipeline
event_queue: asyncio.Queue[dict] = asyncio.Queue()

# Database path
DB_PATH = "chat_history.db"


class ChatDatabase:
    """Manages SQLite database for chat history and sessions"""
    
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self.conn: aiosqlite.Connection | None = None
    
    async def init(self) -> None:
        """Initialize database and create tables"""
        self.conn = await aiosqlite.connect(self.db_path)
        assert self.conn is not None
        
        # Enable foreign keys
        await self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Create users table (each user has a profile)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create conversations table (shared conversations)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create conversation participants table (tracks which users are in which conversations)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_participants (
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (conversation_id, user_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Create messages table (all messages in all conversations)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                text TEXT NOT NULL,
                message_type TEXT DEFAULT 'user_message',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                FOREIGN KEY (sender_id) REFERENCES users(user_id)
            )
        """)
        
        # Create index for faster queries
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, created_at)
        """)
        
        # Create index for username lookups
        await self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username 
            ON users(username)
        """)
        
        # Create default conversation (main chat room)
        await self.conn.execute("""
            INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)
        """, (CONVERSATION_DEFAULT,))
        
        await self.conn.commit()
        print("Database initialized successfully")
    
    async def close(self) -> None:
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    async def get_or_create_user(self, username: str) -> str:
        """Get existing user_id by username or create new user, returns user_id"""
        assert self.conn is not None
        
        # Try to get existing user
        cursor = await self.conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )
        row = await cursor.fetchone()
        if row:
            # Update last_activity
            await self.conn.execute(
                "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE username = ?",
                (username,)
            )
            await self.conn.commit()
            return row[0]
        
        # Create new user
        user_id = str(uuid.uuid4())
        await self.conn.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await self.conn.commit()
        return user_id
    
    async def add_user_to_conversation(self, user_id: str, conversation_id: str = CONVERSATION_DEFAULT) -> None:
        """Add user to a conversation if not already in it"""
        assert self.conn is not None
        try:
            await self.conn.execute(
                "INSERT INTO conversation_participants (conversation_id, user_id) VALUES (?, ?)",
                (conversation_id, user_id)
            )
            await self.conn.commit()
        except:
            # User already in conversation
            pass
    
    async def save_message(self, sender_id: str, sender_name: str, text: str, msg_type: str = MESSAGE_TYPE_USER, conversation_id: str = CONVERSATION_DEFAULT) -> None:
        """Save message to database in a conversation"""
        assert self.conn is not None
        await self.conn.execute(
            "INSERT INTO messages (conversation_id, sender_id, sender_name, text, message_type) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, sender_id, sender_name, text, msg_type)
        )
        # Update conversation updated_at timestamp
        await self.conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
            (conversation_id,)
        )
        await self.conn.commit()
    
    async def get_conversation_history(self, conversation_id: str = CONVERSATION_DEFAULT, limit: int = 50) -> list[dict]:
        """Get chat history for a conversation (all messages regardless of user)"""
        assert self.conn is not None
        cursor = await self.conn.execute(
            "SELECT sender_name, text, message_type, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
            (conversation_id, limit)
        )
        rows = await cursor.fetchall()
        return [
            {
                "sender": row[0],
                "text": row[1],
                "type": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]


class EventPublisher:
    """Publishes events to the event queue"""
    
    def __init__(self, queue: asyncio.Queue[dict]) -> None:
        self.queue = queue
    
    async def publish(self, event: dict) -> None:
        """Publish an event to the queue"""
        await self.queue.put(event)


class EventConsumer:
    """Consumes events from the queue and handles them"""
    
    def __init__(self, queue: asyncio.Queue[dict], db: ChatDatabase) -> None:
        self.queue = queue
        self.db = db
    
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
            await self.db.save_message(user_id, sender, text, MESSAGE_TYPE_USER, CONVERSATION_DEFAULT)
        
        broadcast_message: str = json.dumps({
            "sender": sender,
            "text": text
        })
        
        # Send to all connected clients except sender
        sender_ws: WebSocket | None = event.get("sender_ws")
        for client in connected_clients:
            if client != sender_ws:
                try:
                    await client.send_text(broadcast_message)
                except Exception as e:
                    print(f"Error sending message: {e}")
    
    async def handle_ai_response(self, event: dict) -> None:
        """Handle AI response events and save to database"""
        # Save to database using AIBot's username
        try:
            text: str = event.get("text", "")
            ai_user_id = await self.db.get_or_create_user("AIBot")
            await self.db.save_message(ai_user_id, "AIBot", text, MESSAGE_TYPE_AI_RESPONSE, CONVERSATION_DEFAULT)
        except Exception as e:
            print(f"Error saving AI response to database: {e}")
        
        broadcast_message: str = json.dumps({
            "sender": "AIBot",
            "text": event.get("text", "")
        })
        
        # Send to all connected clients
        for client in connected_clients:
            try:
                await client.send_text(broadcast_message)
            except Exception as e:
                print(f"Error sending AI response: {e}")


class MockedAIAgent:
    """Mocked AI agent that processes requests using intent matching"""
    
    # Intent definitions - keywords that trigger specific responses
    intents = {
        "python": {
            "keywords": ["python", "py", "django", "flask", "fastapi"],
            "response": "Python is a versatile, high-level programming language known for its simplicity and readability. It's widely used in web development, data science, AI/ML, and automation. FastAPI is a modern Python framework for building APIs with WebSocket support!"
        },
        "async": {
            "keywords": ["async", "await", "asyncio", "concurrent", "asynchronous"],
            "response": "Async/await enables non-blocking, concurrent programming. Asyncio allows multiple operations to run without blocking the event loop. This is perfect for I/O-bound operations like WebSockets, network requests, and database queries!"
        },
        "websocket": {
            "keywords": ["websocket", "ws://", "real-time", "bidirectional", "connection"],
            "response": "WebSockets enable persistent, bidirectional communication between client and server. Unlike HTTP, WebSockets keep the connection open for real-time messaging. This is what powers our chat system!"
        },
        "event": {
            "keywords": ["event", "queue", "publisher", "consumer", "event-driven"],
            "response": "Event-driven architecture uses events to trigger actions. Our system uses asyncio.Queue for an event pipeline: events are published, consumed, and processed asynchronously. This enables scalability and loose coupling!"
        },
        "database": {
            "keywords": ["database", "sqlite", "sql", "store", "persistence"],
            "response": "SQLite is a lightweight, file-based database perfect for MVP applications. It can store conversation history, user messages, and AI responses. This allows context-aware AI responses based on past conversations!"
        }
    }
    
    def __init__(self, publisher: EventPublisher) -> None:
        self.publisher = publisher
    
    def detect_intent(self, message: str) -> str:
        """Detect intent from user message based on keywords"""
        message_lower = message.lower()
        
        # Check each intent's keywords
        for intent_name, intent_data in self.intents.items():
            for keyword in intent_data["keywords"]:
                if keyword in message_lower:
                    return intent_name
        
        # Default intent if no match
        return "default"
    
    def get_response(self, intent: str, original_message: str) -> str:
        """Get response based on detected intent"""
        if intent in self.intents:
            return self.intents[intent]["response"]
        else:
            return f"I'm a mocked AI assistant in development. You asked about: '{original_message}'. I can help with questions about Python, async programming, WebSockets, event-driven architecture, and databases. Ask me anything!"
    
    async def process_request(self, request_event: dict) -> None:
        """Process AI request and publish response"""
        user_message: str = request_event.get("text", "")
        
        try:
            # Detect intent
            intent = self.detect_intent(user_message)
            print(f"Detected intent: {intent}")
            
            # Simulate AI processing
            await asyncio.sleep(0.5)
            
            # Get response based on intent
            ai_response: str = self.get_response(intent, user_message)
            print(f"AI response: {ai_response}")
            
            # Publish AI response event
            response_event: dict = {
                "type": EVENT_TYPE_AI_RESPONSE,
                "text": ai_response,
                "original_message": user_message,
                "detected_intent": intent
            }
            await self.publisher.publish(response_event)
        except Exception as e:
            print(f"Error processing AI request: {e}")
            error_event: dict = {
                "type": "ai_response",
                "text": f"Error processing request: {str(e)}"
            }
            await self.publisher.publish(error_event)

class AIEventConsumer(EventConsumer):
    """Extended consumer that also handles AI requests"""
    
    def __init__(self, queue: asyncio.Queue[dict], db: ChatDatabase, ai_agent: MockedAIAgent) -> None:
        super().__init__(queue, db)
        self.ai_agent = ai_agent
    
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


# Initialize database, publisher, AI agent, and consumer
db = ChatDatabase()
publisher = EventPublisher(event_queue)
ai_agent = MockedAIAgent(publisher)
consumer: AIEventConsumer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global consumer
    
    # Startup: Initialize database and start event consumer
    await db.init()
    
    # Ensure AIBot user exists
    try:
        await db.get_or_create_user("AIBot")
    except:
        pass
    
    consumer = AIEventConsumer(event_queue, db, ai_agent)
    consumer_task = asyncio.create_task(consumer.consume())
    
    yield
    
    # Shutdown: Cancel event consumer and close database
    consumer_task.cancel()
    await db.close()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get_index():
    """Serve the client HTML file"""
    return FileResponse("client.html")


def parse_message_event(websocket: WebSocket, user_id: str, sender: str, message: str) -> dict:
    """Parse incoming message and determine event type"""
    data: dict[str, str] = json.loads(message)
    msg_type: str = data.get("type", "message").strip()
    text: str = data.get("text", "")
    
    # Check if message is an AI request
    if text.startswith("/AIBot"):
        return {
            "type": "ai_request",
            "sender_ws": websocket,
            "user_id": user_id,
            "sender": sender,
            "text": text.replace("/AIBot", "").strip()
        }
    else:
        return {
            "type": "user_message",
            "sender_ws": websocket,
            "user_id": user_id,
            "sender": sender,
            "text": text
        }


async def process_message(websocket: WebSocket, user_id: str, sender: str, message: str) -> None:
    """Process incoming message and publish to event queue"""
    event = parse_message_event(websocket, user_id, sender, message)
    await publisher.publish(event)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connection with username from query parameter"""
    # Extract username from query params BEFORE accepting connection
    username: str = websocket.query_params.get("username", "").strip()
    
    if not username:
        # Reject connection at handshake with WebSocket close code
        await websocket.close(code=1008, reason="Username required. Connect with: ws://localhost:8765/ws?username=YourName")
        return
    
    # Now accept the authenticated connection
    await websocket.accept()
    
    try:
        # Get or create user
        user_id = await db.get_or_create_user(username)
        
        # Add user to default conversation
        await db.add_user_to_conversation(user_id, "default")
        
        connected_clients.add(websocket)
        print(f"User '{username}' (ID: {user_id}) connected. Total clients: {len(connected_clients)}")
        
        # Send connection success
        await websocket.send_text(json.dumps({
            "type": "connected",
            "user_id": user_id,
            "username": username
        }))
        
        # Send full conversation history (all messages from all users)
        history = await db.get_conversation_history("default")
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
                await process_message(websocket, user_id, username, message)
                
            except json.JSONDecodeError:
                print(f"Invalid JSON received from {username}")
                # Send error but don't close connection - client can recover
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                    
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print(f"Client '{username}' disconnected. Total clients: {len(connected_clients)}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        connected_clients.discard(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8765)
