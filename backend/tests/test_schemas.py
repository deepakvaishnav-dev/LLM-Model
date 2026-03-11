import pytest
from pydantic import ValidationError
from app.api.chat import ChatRequest, ChatMessage
# OR from app.schemas.chat if the user provides it. Using api.chat as fallback.
try:
    from app.schemas.chat import ChatRequest, ChatMessage
except ImportError:
    pass

class TestChatSchemas:
    """Test suite for Pydantic models/schemas validation."""
    
    def test_chat_request_without_history(self):
        """Test ChatRequest can be instantiated without history."""
        req = ChatRequest(query="What is FastAPI?")
        assert req.query == "What is FastAPI?"
        assert req.history == []
        
    def test_chat_request_with_history(self):
        """Test ChatRequest correctly validates with history provided."""
        history = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there!")
        ]
        req = ChatRequest(query="Next question", history=history)
        
        assert req.query == "Next question"
        assert len(req.history) == 2
        assert req.history[0].role == "user"
        
    def test_chat_message_validation(self):
        """Test ChatMessage requires both role and content."""
        with pytest.raises(ValidationError):
            ChatMessage(role="user") # Missing content
            
        with pytest.raises(ValidationError):
            ChatMessage(content="Hi") # Missing role
            
        valid_msg = ChatMessage(role="system", content="You are an AI.")
        assert valid_msg.role == "system"
        assert valid_msg.content == "You are an AI."
