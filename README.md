# Minimal Chat System

A simple WebSocket-based chat system using FastAPI and HTML client.

## Setup

1. Activate the virtual environment:
```bash
source .venv/bin/activate
```

2. Start the server:
```bash
uv run server.py
```

The WebSocket server will start on `ws://localhost:8765/ws`

## Usage

1. Open `client.html` in multiple browser tabs/windows
2. Type a message and press Enter or click Send
3. Messages are broadcast to all other connected clients

## How It Works

- **server.py**: FastAPI WebSocket server with endpoint at `/ws` that maintains connected clients and broadcasts messages to all except the sender
- **client.html**: Single-file HTML client with WebSocket connection, auto-reconnect, and message display

## Project Management

This project uses `uv` for Python package management with Python 3.12.
