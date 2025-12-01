import json
import asyncio
from typing import Set
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

# Set to store connected clients
connected_clients: Set[WebSocket] = set()

# Event queue for message pipeline
event_queue: asyncio.Queue[dict] = asyncio.Queue()


class EventPublisher:
    """Publishes events to the event queue"""
    
    def __init__(self, queue: asyncio.Queue[dict]) -> None:
        self.queue = queue
    
    async def publish(self, event: dict) -> None:
        """Publish an event to the queue"""
        await self.queue.put(event)


class EventConsumer:
    """Consumes events from the queue and handles them"""
    
    def __init__(self, queue: asyncio.Queue[dict]) -> None:
        self.queue = queue
    
    async def consume(self) -> None:
        """Continuously consume and process events"""
        while True:
            event = await self.queue.get()
            await self.handle_event(event)
            self.queue.task_done()
    
    async def handle_event(self, event: dict) -> None:
        """Route event to appropriate handler"""
        if event["type"] == "user_message":
            await self.handle_user_message(event)
        elif event["type"] == "ai_response":
            await self.handle_ai_response(event)
    
    async def handle_user_message(self, event: dict) -> None:
        """Handle user message events"""
        broadcast_message: str = json.dumps({
            "sender": event["sender"],
            "text": event["text"]
        })
        
        # Send to all connected clients except sender
        for client in connected_clients:
            if client != event["sender_ws"]:
                try:
                    await client.send_text(broadcast_message)
                except Exception as e:
                    print(f"Error sending message: {e}")
    
    async def handle_ai_response(self, event: dict) -> None:
        """Handle AI response events"""
        broadcast_message: str = json.dumps({
            "sender": "AIBot",
            "text": event["text"]
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
        user_message: str = request_event["text"]
        
        # Detect intent
        intent = self.detect_intent(user_message)
        
        # Simulate AI processing
        await asyncio.sleep(0.5)
        
        # Get response based on intent
        ai_response: str = self.get_response(intent, user_message)
        
        # Publish AI response event
        response_event: dict = {
            "type": "ai_response",
            "text": ai_response,
            "original_message": user_message,
            "detected_intent": intent
        }
        await self.publisher.publish(response_event)
class AIEventConsumer(EventConsumer):
    """Extended consumer that also handles AI requests"""
    
    def __init__(self, queue: asyncio.Queue[dict], ai_agent: MockedAIAgent) -> None:
        super().__init__(queue)
        self.ai_agent = ai_agent
    
    async def handle_event(self, event: dict) -> None:
        """Route event to appropriate handler, including AI requests"""
        if event["type"] == "user_message":
            await self.handle_user_message(event)
        elif event["type"] == "ai_request":
            await self.handle_user_message(event)  # Handle user message first
            await self.ai_agent.process_request(event)
        elif event["type"] == "ai_response":
            await self.handle_ai_response(event)


# Initialize publisher, AI agent, and consumer
publisher = EventPublisher(event_queue)
ai_agent = MockedAIAgent(publisher)
consumer = AIEventConsumer(event_queue, ai_agent)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup: Start the event consumer
    consumer_task = asyncio.create_task(consumer.consume())
    yield
    # Shutdown: Cancel the event consumer
    consumer_task.cancel()


app = FastAPI(lifespan=lifespan)


def parse_message_event(websocket: WebSocket, message: str) -> dict:
    """Parse incoming message and determine event type"""
    data: dict[str, str] = json.loads(message)
    sender: str = data.get("sender", "Anonymous")
    text: str = data.get("text", "")
    
    # Check if message is an AI request
    if text.startswith("/AIBot"):
        return {
            "type": "ai_request",
            "sender_ws": websocket,
            "sender": sender,
            "text": text.replace("/AIBot", "").strip()
        }
    else:
        return {
            "type": "user_message",
            "sender_ws": websocket,
            "sender": sender,
            "text": text
        }


async def process_message(websocket: WebSocket, message: str) -> None:
    """Process incoming message and publish to event queue"""
    event = parse_message_event(websocket, message)
    await publisher.publish(event)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle WebSocket connection"""
    await websocket.accept()
    connected_clients.add(websocket)
    print(f"Client connected. Total clients: {len(connected_clients)}")
    
    try:
        while True:
            message = await websocket.receive_text()
            await process_message(websocket, message)
                    
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8765)
