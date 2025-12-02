"""AI Agent for processing user requests and generating responses"""
import asyncio

from domain.constants import EVENT_TYPE_AI_RESPONSE
from domain.models import AIResponseEvent
from events.publisher import EventPublisher


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
            response_event = AIResponseEvent(
                type=EVENT_TYPE_AI_RESPONSE,
                text=ai_response,
                original_message=user_message,
                detected_intent=intent
            )
            await self.publisher.publish(response_event)
        except Exception as e:
            print(f"Error processing AI request: {e}")
            error_event = AIResponseEvent(
                type=EVENT_TYPE_AI_RESPONSE,
                text=f"Error processing request: {str(e)}"
            )
            await self.publisher.publish(error_event)
