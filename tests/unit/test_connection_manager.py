"""Unit tests for WebSocket ConnectionManager"""
import pytest
import json
from unittest.mock import AsyncMock

from websocket.connection_manager import ConnectionManager


@pytest.mark.unit
class TestConnectionManagerInitialization:
    """Test ConnectionManager initialization"""

    def test_initialization_creates_empty_connections(self):
        """Test that ConnectionManager initializes with empty connections"""
        manager = ConnectionManager()
        assert hasattr(manager, "active_connections")
        assert isinstance(manager.active_connections, list)
        assert len(manager.active_connections) == 0

    def test_get_connection_count_on_empty(self):
        """Test connection count on newly initialized manager"""
        manager = ConnectionManager()
        assert manager.get_connection_count() == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestConnectionManagerConnect:
    """Test ConnectionManager connection handling"""

    async def test_connect_adds_websocket(self):
        """Test that connect() adds WebSocket to active connections"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        
        assert len(manager.active_connections) == 1
        assert ws in manager.active_connections

    async def test_connect_calls_accept(self):
        """Test that connect() calls websocket.accept()"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        
        ws.accept.assert_called_once()

    async def test_connect_multiple_websockets(self):
        """Test connecting multiple WebSockets"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        assert manager.get_connection_count() == 3
        assert ws1 in manager.active_connections
        assert ws2 in manager.active_connections
        assert ws3 in manager.active_connections

    async def test_connect_maintains_connection_order(self):
        """Test that connections maintain insertion order"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        assert manager.active_connections[0] is ws1
        assert manager.active_connections[1] is ws2
        assert manager.active_connections[2] is ws3


@pytest.mark.unit
class TestConnectionManagerDisconnect:
    """Test ConnectionManager disconnection handling"""

    async def test_disconnect_removes_websocket(self):
        """Test that disconnect() removes WebSocket from active connections"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        assert manager.get_connection_count() == 1
        
        manager.disconnect(ws)
        assert manager.get_connection_count() == 0
        assert ws not in manager.active_connections

    async def test_disconnect_specific_websocket(self):
        """Test disconnecting specific WebSocket from multiple"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        manager.disconnect(ws2)
        
        assert manager.get_connection_count() == 2
        assert ws1 in manager.active_connections
        assert ws2 not in manager.active_connections
        assert ws3 in manager.active_connections

    def test_disconnect_nonexistent_connection(self):
        """Test disconnecting a connection that doesn't exist"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        # Should not raise an error
        manager.disconnect(ws)
        assert manager.get_connection_count() == 0

    async def test_disconnect_does_not_affect_others(self):
        """Test that disconnecting one client doesn't affect others"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        
        manager.disconnect(ws1)
        
        assert ws2 in manager.active_connections
        assert ws1 not in manager.active_connections


@pytest.mark.unit
@pytest.mark.asyncio
class TestConnectionManagerBroadcast:
    """Test ConnectionManager broadcast functionality"""

    async def test_broadcast_sends_to_all_connections(self):
        """Test that broadcast() sends message to all connections"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        message = {"type": "test", "content": "Hello"}
        await manager.broadcast(message)
        
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()
        ws3.send_text.assert_called_once()

    async def test_broadcast_serializes_message_to_json(self):
        """Test that broadcast() serializes message to JSON"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        
        message = {"type": "test", "value": 42}
        await manager.broadcast(message)
        
        # Check that send_text was called with JSON string
        ws.send_text.assert_called_once()
        sent_text = ws.send_text.call_args[0][0]
        assert isinstance(sent_text, str)
        
        # Verify it can be decoded back to original message
        decoded = json.loads(sent_text)
        assert decoded == message

    async def test_broadcast_to_empty_connections(self):
        """Test broadcast with no active connections"""
        manager = ConnectionManager()
        message = {"type": "test"}
        
        # Should not raise an error
        await manager.broadcast(message)

    async def test_broadcast_removes_disconnected_connections(self):
        """Test that broadcast removes disconnected clients"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        
        # Make ws1 raise an exception to simulate disconnection
        ws1.send_text.side_effect = Exception("Connection closed")
        
        message = {"type": "test"}
        await manager.broadcast(message)
        
        # ws1 should be removed from active connections
        assert manager.get_connection_count() == 1
        assert ws1 not in manager.active_connections
        assert ws2 in manager.active_connections

    async def test_broadcast_continues_after_error(self):
        """Test that broadcast continues sending after error on one connection"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        # Make ws2 raise an exception
        ws2.send_text.side_effect = Exception("Connection failed")
        
        message = {"type": "test"}
        await manager.broadcast(message)
        
        # ws1 and ws3 should still have been sent the message
        ws1.send_text.assert_called_once()
        ws3.send_text.assert_called_once()
        
        # ws1 and ws3 should still be in connections, ws2 removed
        assert ws1 in manager.active_connections
        assert ws2 not in manager.active_connections
        assert ws3 in manager.active_connections

    async def test_broadcast_message_format(self):
        """Test that broadcast sends correct message format"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        
        message = {"sender": "user1", "text": "Hello all", "type": "message"}
        await manager.broadcast(message)
        
        sent_text = ws.send_text.call_args[0][0]
        decoded = json.loads(sent_text)
        
        assert decoded["sender"] == "user1"
        assert decoded["text"] == "Hello all"
        assert decoded["type"] == "message"


@pytest.mark.unit
@pytest.mark.asyncio
class TestConnectionManagerBroadcastExcept:
    """Test ConnectionManager broadcast_except functionality"""

    async def test_broadcast_except_sends_to_all_except_one(self):
        """Test that broadcast_except() excludes specified connection"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        message = {"type": "test"}
        await manager.broadcast_except(message, ws2)
        
        # ws1 and ws3 should receive message, ws2 should not
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()
        ws3.send_text.assert_called_once()

    async def test_broadcast_except_serializes_to_json(self):
        """Test that broadcast_except serializes message to JSON"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        
        message = {"type": "notification", "count": 5}
        await manager.broadcast_except(message, ws1)
        
        sent_text = ws2.send_text.call_args[0][0]
        decoded = json.loads(sent_text)
        assert decoded == message

    async def test_broadcast_except_with_single_connection(self):
        """Test broadcast_except when excluding the only connection"""
        manager = ConnectionManager()
        ws = AsyncMock()
        
        await manager.connect(ws)
        
        message = {"type": "test"}
        await manager.broadcast_except(message, ws)
        
        # Message should not be sent since we're excluding the only client
        ws.send_text.assert_not_called()

    async def test_broadcast_except_removes_disconnected(self):
        """Test that broadcast_except removes disconnected clients"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        # Make ws2 raise an exception
        ws2.send_text.side_effect = Exception("Disconnected")
        
        message = {"type": "test"}
        await manager.broadcast_except(message, ws1)
        
        # ws1 is excluded, ws2 fails and is removed, ws3 receives message
        ws1.send_text.assert_not_called()
        ws3.send_text.assert_called_once()
        
        # After broadcast, ws2 should be removed
        assert manager.get_connection_count() == 2
        assert ws1 in manager.active_connections
        assert ws2 not in manager.active_connections
        assert ws3 in manager.active_connections

    async def test_broadcast_except_continues_after_error(self):
        """Test that broadcast_except continues after error on other connection"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        # Make ws1 raise an exception
        ws1.send_text.side_effect = Exception("Error")
        
        message = {"type": "test"}
        await manager.broadcast_except(message, ws2)
        
        # ws3 should still receive message despite ws1 error
        ws3.send_text.assert_called_once()
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_not_called()

    async def test_broadcast_except_exclude_not_in_connections(self):
        """Test broadcast_except when excluded connection not in list"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        exclude_ws = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        
        message = {"type": "test"}
        # Exclude a connection that doesn't exist - should still broadcast to all
        await manager.broadcast_except(message, exclude_ws)
        
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()


@pytest.mark.unit
class TestConnectionManagerState:
    """Test ConnectionManager state management"""

    async def test_connection_count_updates_correctly(self):
        """Test that connection count stays accurate"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        assert manager.get_connection_count() == 0
        
        await manager.connect(ws1)
        assert manager.get_connection_count() == 1
        
        await manager.connect(ws2)
        assert manager.get_connection_count() == 2
        
        await manager.connect(ws3)
        assert manager.get_connection_count() == 3
        
        manager.disconnect(ws2)
        assert manager.get_connection_count() == 2
        
        manager.disconnect(ws1)
        assert manager.get_connection_count() == 1

    async def test_active_connections_list_accurate(self):
        """Test that active_connections list accurately reflects state"""
        manager = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        
        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        
        connections = manager.active_connections
        assert len(connections) == 3
        assert all(ws in connections for ws in [ws1, ws2, ws3])
        
        manager.disconnect(ws2)
        assert len(manager.active_connections) == 2
        assert ws2 not in manager.active_connections
