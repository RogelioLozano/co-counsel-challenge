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
            "sender": "AI",
            "text": event["text"]
        })
        
        # Send to all connected clients
        for client in connected_clients:
            try:
                await client.send_text(broadcast_message)
            except Exception as e:
                print(f"Error sending AI response: {e}")


# Initialize publisher and consumer
publisher = EventPublisher(event_queue)
consumer = EventConsumer(event_queue)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup: Start the event consumer
    consumer_task = asyncio.create_task(consumer.consume())
    yield
    # Shutdown: Cancel the event consumer
    consumer_task.cancel()


app = FastAPI(lifespan=lifespan)


async def process_message(websocket: WebSocket, message: str) -> None:
    """Process incoming message and publish to event queue"""
    data: dict[str, str] = json.loads(message)
    event: dict = {
        "type": "user_message",
        "sender_ws": websocket,
        "sender": data.get("sender", "Anonymous"),
        "text": data.get("text", "")
    }
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
