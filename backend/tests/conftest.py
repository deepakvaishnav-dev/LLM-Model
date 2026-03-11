import sys
import pytest
from unittest.mock import MagicMock

# Mock heavy dependencies before any app imports
class MockModule(MagicMock):
    __spec__ = None
    __path__ = []
    __file__ = "mock.py"

modules_to_mock = [
    'llama_index', 'llama_index.core', 'llama_index.core.prompts', 'llama_index.core.node_parser',
    'llama_index.llms', 'llama_index.llms.ollama', 'llama_index.llms.google_genai',
    'llama_index.embeddings', 'llama_index.embeddings.google_genai', 
    'llama_index.vector_stores', 'llama_index.vector_stores.chroma', 'chromadb', 'google',
    'google.genai', 'google.generativeai'
]

for name in modules_to_mock:
    sys.modules[name] = MockModule()

# Now we can safely import our app modules
import app.services.indexer

from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Returns a FastAPI TestClient instance for testing."""
    return TestClient(app)
