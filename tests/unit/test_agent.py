"""Unit tests for MockedAIAgent"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from ai.agent import MockedAIAgent
from domain.constants import EVENT_TYPE_AI_RESPONSE
from events.publisher import EventPublisher


@pytest.mark.unit
class TestMockedAIAgentIntentDetection:
    """Test MockedAIAgent intent detection logic"""

    def test_detect_python_intent(self):
        """Test detecting Python-related intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("How do I use Python?")
        assert intent == "python"

    def test_detect_python_intent_with_framework(self):
        """Test detecting Python intent with framework keyword"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("Tell me about FastAPI")
        assert intent == "python"

    def test_detect_async_intent(self):
        """Test detecting async-related intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("How does asyncio work?")
        assert intent == "async"

    def test_detect_websocket_intent(self):
        """Test detecting WebSocket-related intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("Explain WebSockets please")
        assert intent == "websocket"

    def test_detect_event_intent(self):
        """Test detecting event-driven intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("What's event-driven architecture?")
        assert intent == "event"

    def test_detect_database_intent(self):
        """Test detecting database-related intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("How do I persist data with SQLite?")
        assert intent == "database"

    def test_detect_intent_case_insensitive(self):
        """Test that intent detection is case-insensitive"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent1 = agent.detect_intent("PYTHON")
        intent2 = agent.detect_intent("python")
        intent3 = agent.detect_intent("PyThOn")
        
        assert intent1 == intent2 == intent3 == "python"

    def test_detect_default_intent_no_match(self):
        """Test default intent when no keywords match"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        intent = agent.detect_intent("Random unrelated question about cats")
        assert intent == "default"

    def test_detect_first_matching_intent(self):
        """Test that detection returns first matching intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        # Message with multiple keywords - should match first intent found
        intent = agent.detect_intent("Python and asyncio together")
        assert intent in ["python", "async"]  # Should match one of these


@pytest.mark.unit
class TestMockedAIAgentResponses:
    """Test MockedAIAgent response generation"""

    def test_get_response_python(self):
        """Test getting response for Python intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        response = agent.get_response("python", "Tell me about Python")
        assert "Python" in response
        assert len(response) > 0
        assert "versatile" in response or "high-level" in response

    def test_get_response_async(self):
        """Test getting response for async intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        response = agent.get_response("async", "How does async work?")
        assert "async" in response.lower() or "Async" in response
        assert len(response) > 0

    def test_get_response_websocket(self):
        """Test getting response for WebSocket intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        response = agent.get_response("websocket", "What are WebSockets?")
        assert "WebSocket" in response
        assert len(response) > 0

    def test_get_response_event(self):
        """Test getting response for event intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        response = agent.get_response("event", "Explain events")
        assert "event" in response.lower() or "Event" in response
        assert len(response) > 0

    def test_get_response_database(self):
        """Test getting response for database intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        response = agent.get_response("database", "SQLite?")
        assert "SQLite" in response or "database" in response.lower()
        assert len(response) > 0

    def test_get_response_default_intent(self):
        """Test getting response for unknown intent"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        original_msg = "Something random"
        response = agent.get_response("unknown", original_msg)
        assert "mocked" in response.lower() and "ai" in response.lower()
        assert original_msg in response

    def test_response_includes_original_message(self):
        """Test that default response includes original message"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        original = "What is the meaning of life?"
        response = agent.get_response("nonexistent", original)
        assert original in response


@pytest.mark.unit
@pytest.mark.asyncio
class TestMockedAIAgentProcessRequest:
    """Test MockedAIAgent request processing"""

    async def test_process_request_creates_event(self):
        """Test that processing request publishes an event"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {"text": "Tell me about Python"}
        await agent.process_request(request_event)
        
        # Verify publisher.publish was called
        assert publisher.publish.called

    async def test_process_request_publishes_ai_response_event(self):
        """Test that published event is AIResponseEvent"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {"text": "Python programming"}
        await agent.process_request(request_event)
        
        # Get the published event
        published_event = publisher.publish.call_args[0][0]
        assert published_event.type == EVENT_TYPE_AI_RESPONSE
        assert published_event.detected_intent == "python"

    async def test_process_request_detects_intent(self):
        """Test that processing detects intent correctly"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {"text": "How does asyncio work?"}
        await agent.process_request(request_event)
        
        published_event = publisher.publish.call_args[0][0]
        assert published_event.detected_intent == "async"

    async def test_process_request_includes_response_text(self):
        """Test that published event includes AI response"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {"text": "WebSocket question"}
        await agent.process_request(request_event)
        
        published_event = publisher.publish.call_args[0][0]
        assert len(published_event.text) > 0
        assert "WebSocket" in published_event.text

    async def test_process_request_with_empty_message(self):
        """Test processing request with empty message"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {"text": ""}
        await agent.process_request(request_event)
        
        # Should still publish event with default intent
        assert publisher.publish.called
        published_event = publisher.publish.call_args[0][0]
        assert published_event.detected_intent == "default"

    async def test_process_request_handles_missing_text_key(self):
        """Test processing request with missing 'text' key"""
        publisher = AsyncMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        request_event = {}
        await agent.process_request(request_event)
        
        # Should still publish an event
        assert publisher.publish.called
        published_event = publisher.publish.call_args[0][0]
        assert published_event.type == EVENT_TYPE_AI_RESPONSE

    async def test_process_request_publishes_error_on_exception(self):
        """Test that errors are published as events"""
        publisher = AsyncMock(spec=EventPublisher)
        
        # Mock agent to raise an error
        agent = MockedAIAgent(publisher)
        agent.detect_intent = MagicMock(side_effect=Exception("Test error"))
        
        request_event = {"text": "Trigger error"}
        await agent.process_request(request_event)
        
        # Should publish error event
        assert publisher.publish.called
        published_event = publisher.publish.call_args[0][0]
        assert "Error" in published_event.text or "error" in published_event.text


@pytest.mark.unit
class TestMockedAIAgentInitialization:
    """Test MockedAIAgent initialization"""

    def test_agent_initialization(self):
        """Test creating MockedAIAgent instance"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        assert agent.publisher is publisher
        assert hasattr(agent, "intents")

    def test_agent_has_intents_dict(self):
        """Test that agent has intents dictionary"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        assert isinstance(agent.intents, dict)
        assert len(agent.intents) > 0

    def test_all_intents_have_keywords(self):
        """Test that all intents have keywords"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        for intent_name, intent_data in agent.intents.items():
            assert "keywords" in intent_data
            assert isinstance(intent_data["keywords"], list)
            assert len(intent_data["keywords"]) > 0

    def test_all_intents_have_responses(self):
        """Test that all intents have response text"""
        publisher = MagicMock(spec=EventPublisher)
        agent = MockedAIAgent(publisher)
        
        for intent_name, intent_data in agent.intents.items():
            assert "response" in intent_data
            assert isinstance(intent_data["response"], str)
            assert len(intent_data["response"]) > 0
