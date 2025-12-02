"""Main FastAPI application - WebSocket chat server with event-driven architecture"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
import uvicorn

from database.chat_database import ChatDatabase
from events.publisher import EventPublisher
from events.consumer import AIEventConsumer
from ai.agent import MockedAIAgent
from websocket.handler import handle_websocket_connection
from websocket.connection_manager import ConnectionManager

# Initialize event queue, database, publisher, AI agent, and connection manager
event_queue: asyncio.Queue[dict] = asyncio.Queue()
db = ChatDatabase()
publisher = EventPublisher(event_queue)
ai_agent = MockedAIAgent(publisher)
consumer: AIEventConsumer | None = None
connection_manager = ConnectionManager()  # Manage WebSocket connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global consumer
    
    # Startup: Initialize database and start event consumer
    await db.init()
    
    # Ensure AIBot user exists
    await db.get_or_create_user("AIBot")
    
    # Create consumer with AI agent support
    consumer = AIEventConsumer(event_queue, db, ai_agent, connection_manager)
    
    # Start event consumer task (runs in background)
    consumer_task = asyncio.create_task(consumer.consume())
    print("Event consumer started")
    
    yield
    
    # Shutdown: Stop consumer and close database
    consumer_task.cancel()
    await db.close()
    print("Application shutdown complete")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def get_index():
    """Serve the client HTML file"""
    return FileResponse("client.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint that delegates to handler"""
    await handle_websocket_connection(websocket, db, publisher, connection_manager)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8765)
