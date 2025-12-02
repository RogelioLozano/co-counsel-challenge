"""WebSocket connection management for handling multiple concurrent clients"""
import json
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections with lifecycle and broadcast support"""

    def __init__(self) -> None:
        """Initialize connection manager with empty active connections"""
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from active connections"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients
        
        Args:
            message: Dictionary to be JSON-serialized and sent to all clients
        """
        message_text = json.dumps(message)
        disconnected: list[WebSocket] = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                print(f"Error sending message to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_except(self, message: dict, exclude: WebSocket) -> None:
        """Send a message to all connected clients except one
        
        Args:
            message: Dictionary to be JSON-serialized and sent
            exclude: WebSocket connection to exclude from broadcast
        """
        message_text = json.dumps(message)
        disconnected: list[WebSocket] = []
        
        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_text(message_text)
            except Exception as e:
                print(f"Error sending message to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
