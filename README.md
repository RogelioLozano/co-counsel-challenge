# Multi-User Chat System with AI Integration

A real-time WebSocket-based chat system using FastAPI, SQLite, and event-driven architecture with shared conversations and mocked AI responses.

## Features

- **Real-time multi-user messaging** via WebSockets
- **Shared conversation history** - All users in a conversation see all messages and full history
- **Username-based persistence** - Users identified by username with auto-reconnect via localStorage
- **Event-driven architecture** - asyncio.Queue for async message pipeline
- **Mocked AI agent** - Intent-based responses for Python, async, WebSocket, event-driven, and database topics
- **SQLite persistence** - Full conversation history with user tracking
- **Auto-reconnect** - Users resume their session automatically when rejoining

## Setup

1. Create and activate the virtual environment:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies with uv:
```bash
uv add fastapi uvicorn aiosqlite
```

3. Start the server:
```bash
uv run server.py
```

The WebSocket server will start on `ws://localhost:8765/ws`
The Frontend client page is served on `http://localhost:8765/`

## Usage

1. Open `client.html` directly in your browser (file:// protocol) or open http://localhost:8765/
2. Enter a username and join the chat
3. All users see each other's messages in real-time
4. View full conversation history from all users
5. Send regular messages or ask `/AIBot <question>` for AI responses

**AI Bot Examples:**
- `/AIBot What is Python?` - Get Python-specific information
- `/AIBot How does async work?` - Learn about asynchronous programming
- `/AIBot Explain WebSockets` - Understand WebSocket communication
- `/AIBot What is event-driven architecture?` - Learn about event systems
- `/AIBot Tell me about databases` - Get database information

## Architecture

### Database Schema

**users** table
- `user_id` - UUID primary key
- `username` - UNIQUE, identifies the user
- `created_at`, `last_activity` - Timestamps

**conversations** table
- `conversation_id` - Primary key (currently using 'default' for main chat room)
- `created_at`, `updated_at` - Timestamps

**conversation_participants** table
- Links users to conversations they've joined
- Tracks when each user joined

**messages** table
- `id` - Auto-incrementing primary key
- `conversation_id` - Which conversation the message belongs to
- `sender_id` - FK to users table
- `sender_name` - Username of the sender
- `text` - Message content
- `message_type` - 'user_message' or 'ai_response'
- `created_at` - Timestamp
- Indexed on `(conversation_id, created_at)` for efficient retrieval

### Event Pipeline

```
WebSocket Message Received
    ↓
parse_message_event() - Determine if user_message or ai_request
    ↓
EventPublisher.publish() - Add to asyncio.Queue
    ↓
EventConsumer.handle_event()
    ├─ user_message → save to DB → broadcast to all clients
    ├─ ai_request → handle_user_message() → ai_agent.process_request()
    └─ ai_response → save to DB → broadcast to all clients
```

### Session Management

- **Username as identifier** - Each username gets a unique `user_id` in the database
- **Shared conversation** - All users automatically join the 'default' conversation
- **Chat history** - New users see all previous messages from all users in that conversation
- **Persistence** - Username stored in browser localStorage for auto-reconnect
- **No authentication** - Currently no passwords; can be added for security

### AI Agent

**MockedAIAgent** uses keyword matching to detect intents:

| Intent | Keywords | Response |
|--------|----------|----------|
| python | python, py, django, flask, fastapi | Python explanation with FastAPI info |
| async | async, await, asyncio, concurrent, asynchronous | Async/await and event loop explanation |
| websocket | websocket, ws://, real-time, bidirectional | WebSocket communication explanation |
| event | event, queue, publisher, consumer, event-driven | Event-driven architecture explanation |
| database | database, sqlite, sql, store, persistence | SQLite and persistence explanation |
| default | (no keywords match) | Generic fallback response |

## Project Management

- **Python**: 3.12 (latest stable)
- **Package Manager**: uv (fast, modern Python package manager)
- **Web Framework**: FastAPI with Uvicorn ASGI server
- **Database**: SQLite with aiosqlite for async operations
- **Architecture**: Event-driven with asyncio for concurrent connections
