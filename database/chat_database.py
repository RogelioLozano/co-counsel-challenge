"""Database access layer for chat system"""
import uuid
import aiosqlite

from domain.constants import CONVERSATION_DEFAULT
from domain.models import Message

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
    
    async def save_message(self, message: Message) -> None:
        """Save message to database in a conversation"""
        assert self.conn is not None
        await self.conn.execute(
            "INSERT INTO messages (conversation_id, sender_id, sender_name, text, message_type) VALUES (?, ?, ?, ?, ?)",
            (message.conversation_id, message.sender_id, message.sender_name, message.text, message.msg_type)
        )
        # Update conversation updated_at timestamp
        await self.conn.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE conversation_id = ?",
            (message.conversation_id,)
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
