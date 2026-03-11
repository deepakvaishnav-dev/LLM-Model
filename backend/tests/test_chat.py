import pytest
from unittest.mock import patch, MagicMock

from app.api.chat import _ollama_model_candidates, _is_daily_quota_exceeded, _is_memory_error
import os

class TestChatEndpoints:
    """Test suite for Chat API endpoints, Gemini integration, and Ollama fallbacks."""

    def test_missing_query_returns_422(self, client):
        """Test POST without 'query' returns 422 Unprocessable Entity."""
        response = client.post("/api/chat/", json={"history": []})
        assert response.status_code == 422
        assert "query" in response.text
        
    @patch("app.api.chat.get_or_create_index")
    def test_valid_query_returns_response_and_sources(self, mock_get_index, client):
        """Test a valid query returns standard {response, sources} shape."""
        # Mocking the engine and nodes
        mock_node = MagicMock()
        mock_node.metadata = {"file_name": "test_doc.pdf"}
        mock_node.text = "This is some test content."
        mock_node.score = 0.95
        
        mock_response = MagicMock()
        mock_response.__str__.return_value = "This is the AI answer."
        mock_response.source_nodes = [mock_node]
        
        mock_engine = MagicMock()
        mock_engine.query.return_value = mock_response
        
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        # Test with proper google key
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid_key"}):
            req_data = {"query": "What is test content?", "history": [{"role": "user", "content": "hi"}]}
            response = client.post("/api/chat/", json=req_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert data["response"] == "This is the AI answer."
            assert "sources" in data
            assert len(data["sources"]) == 1
            assert data["sources"][0]["file"] == "test_doc.pdf"
            assert data["sources"][0]["score"] == 0.95

    @patch("app.api.chat.get_or_create_index")
    def test_invalid_api_key_401(self, mock_get_index, client):
        """Test invalid API key throws 401."""
        mock_engine = MagicMock()
        # Mock engine throwing a 401 API key invalid error
        mock_engine.query.side_effect = Exception("API_KEY_INVALID")
        
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "bad_key"}):
            with patch("app.api.chat._ollama_model_candidates", return_value=[]):
                response = client.post("/api/chat/", json={"query": "test query"})
                assert response.status_code == 401
                assert "Invalid or missing Google API key" in response.json()["detail"]

    @patch("app.api.chat.get_or_create_index")
    def test_gemini_429_rate_limit(self, mock_get_index, client):
        """Test Gemini rate limit error throws 429."""
        mock_engine = MagicMock()
        mock_engine.query.side_effect = Exception("429 Too Many Requests")
        
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid_key"}):
            with patch("app.api.chat._ollama_model_candidates", return_value=[]):
                response = client.post("/api/chat/", json={"query": "test query"})
                assert response.status_code == 429
                assert "Gemini API quota exceeded" in response.json()["detail"]
                
    @patch("app.api.chat.get_or_create_index")
    def test_no_documents_indexed_400(self, mock_get_index, client):
        """Test throwing 400 when index is empty."""
        mock_get_index.side_effect = Exception("empty node collection")
        
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid_key"}):
            response = client.post("/api/chat/", json={"query": "test query"})
            assert response.status_code == 400
            assert "No documents have been indexed" in response.json()["detail"]

    @patch("app.api.chat.get_or_create_index")
    @patch("app.api.chat._ollama_model_candidates")
    def test_all_providers_fail_503(self, mock_candidates, mock_get_index, client):
        """Test throwing 503 when all AI providers fail."""
        # Force Gemini to fail
        mock_engine = MagicMock()
        mock_engine.query.side_effect = Exception("Unexpected Gemini Error")
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        # Mock Ollama also failing
        mock_candidates.return_value = ["model1"]
        with patch("llama_index.llms.ollama.Ollama") as mock_ollama_class:
            mock_ollama_instance = MagicMock()
            mock_ollama_instance.complete.side_effect = Exception("Ollama Error")
            mock_ollama_class.return_value = mock_ollama_instance
            
            with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid_key"}):
                # We need the fallback query engine to also fail
                mock_index.as_query_engine.side_effect = [mock_engine, Exception("rag_err")]
                
                response = client.post("/api/chat/", json={"query": "fail totally"})
                
                assert response.status_code == 503
                assert "All AI providers failed" in response.json()["detail"]

    @patch("app.api.chat.get_or_create_index")
    def test_daily_quota_exceeded(self, mock_get_index, client):
        mock_engine = MagicMock()
        mock_engine.query.side_effect = Exception("429 error: PerDay quota hit")
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "valid"}):
            with patch("app.api.chat._ollama_model_candidates", return_value=[]):
                response = client.post("/api/chat/", json={"query": "quota"})
                assert response.status_code == 429
                assert "Gemini API quota exceeded" in response.json()["detail"]

    @patch("app.api.chat.subprocess.run")
    def test_ollama_model_candidates_with_subprocess(self, mock_run):
        """Test _ollama_model_candidates logic parsing CLI output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "NAME\nllama3.2:1b \nphi3:latest \n"
        mock_run.return_value = mock_result
        
        with patch.dict("os.environ", {"OLLAMA_FALLBACK_MODELS": "llama3.2:1b,not_installed"}):
            candidates = _ollama_model_candidates()
            # Prioritizes configured+installed, then remaining installed
            assert candidates == ["llama3.2:1b", "phi3:latest"]

    @patch("app.api.chat.subprocess.run")
    def test_ollama_model_candidates_subprocess_fails(self, mock_run):
        mock_run.side_effect = Exception("cli not found")
        with patch.dict("os.environ", {"OLLAMA_FALLBACK_MODELS": "llama3.2"}):
            assert _ollama_model_candidates() == ["llama3.2"]

    @patch("app.api.chat.get_or_create_index")
    @patch("app.api.chat._ollama_model_candidates")
    def test_ollama_direct_completion_fallback_and_memory(self, mock_candidates, mock_get_index, client):
        mock_candidates.return_value = ["tinyllama", "phi3"]
        mock_get_index.return_value = MagicMock()
        
        with patch.dict("os.environ", {}, clear=True):  # Force Google API empty
            with patch("llama_index.llms.ollama.Ollama") as mock_ollama_class:
                mock_ollama_1 = MagicMock()
                mock_ollama_1.complete.side_effect = Exception("requires more system memory")
                
                mock_ollama_2 = MagicMock()
                mock_response = MagicMock()
                mock_response.__str__.return_value = "Direct Answer"
                mock_ollama_2.complete.return_value = mock_response
                
                # First model fails with memory, second succeeds direct completion
                mock_ollama_class.side_effect = [mock_ollama_1, mock_ollama_2]
                
                # Mock memory error on both RAG usages to force direct completion
                mock_get_index.return_value.as_query_engine.side_effect = [
                    Exception("not enough memory"),  
                    Exception("rag error"),         
                ]
                
                response = client.post("/api/chat/", json={"query": "fallback test"})
                
                assert response.status_code == 200
                assert response.json()["response"] == "Direct Answer"
                assert "fallback" in response.json()["sources"][0]["file"].lower()

    @patch("app.api.chat.get_or_create_index")
    def test_generic_500_error(self, mock_get_index, client):
        mock_get_index.side_effect = Exception("Unknown catastrophic failure")
        response = client.post("/api/chat/", json={"query": "boom"})
        assert response.status_code == 500
        assert "Unknown catastrophic failure" in response.json()["detail"]

    @patch("app.api.chat.get_or_create_index")
    @patch("app.api.chat._ollama_model_candidates")
    def test_ollama_rag_fallback_success(self, mock_candidates, mock_get_index, client):
        mock_candidates.return_value = ["tinyllama"]
        
        mock_engine = MagicMock()
        mock_response = MagicMock()
        mock_response.__str__.return_value = "Ollama RAG Success"
        mock_response.source_nodes = []
        mock_engine.query.return_value = mock_response
        
        mock_index = MagicMock()
        mock_index.as_query_engine.return_value = mock_engine
        mock_get_index.return_value = mock_index
        
        with patch.dict("os.environ", {}, clear=True):
            with patch("llama_index.llms.ollama.Ollama"):
                response = client.post("/api/chat/", json={"query": "rag text"})
                assert response.status_code == 200
                assert response.json()["response"] == "Ollama RAG Success"

    @patch("app.api.chat.get_or_create_index")
    def test_http_exception_passthrough(self, mock_get_index, client):
        from fastapi import HTTPException
        mock_get_index.side_effect = HTTPException(status_code=418, detail="I'm a teapot")
        response = client.post("/api/chat/", json={"query": "teapot test"})
        assert response.status_code == 418
        assert "teapot" in response.json()["detail"]

    def test_daily_quota_function(self):
        assert _is_daily_quota_exceeded("has PerDay quota") is True
        assert _is_daily_quota_exceeded("just a normal error") is False

    def test_memory_error_function(self):
        assert _is_memory_error("requires more system memory") is True
        assert _is_memory_error("normal error") is False
