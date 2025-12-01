#!/usr/bin/env python3
"""Test script to verify AIBot functionality"""

import asyncio
import json
import websockets

async def test_aibot():
    """Connect to chat server and test AIBot"""
    uri = "ws://localhost:8765/ws"
    
    async with websockets.connect(uri) as websocket:
        # Send username
        await websocket.send(json.dumps({"username": "TestUser"}))
        
        # Receive session info
        session_info = await websocket.recv()
        print(f"Session info: {session_info}")
        
        # Receive history
        history = await websocket.recv()
        print(f"History: {history}")
        
        # Send /AIBot message
        print("\nSending /AIBot python message...")
        await websocket.send(json.dumps({"text": "/AIBot What is Python?"}))
        
        # Wait for responses
        for i in range(5):
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                print(f"Response {i+1}: {response}")
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break

if __name__ == "__main__":
    asyncio.run(test_aibot())
