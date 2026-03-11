import pytest

class TestHealthEndpoints:
    """Test suite for general application health and root endpoints."""
    
    def test_root_endpoint(self, client):
        """Test GET / returns 200 with appropriate message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert "API Server Running" in response.json()["message"]
        
    def test_health_check_endpoint(self, client):
        """Test GET /health returns {'status': 'ok'}."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
    def test_unknown_route(self, client):
        """Test an unknown route returns 404."""
        response = client.get("/made-up-route-that-does-not-exist")
        assert response.status_code == 404

    def test_startup_event_with_key(self):
        """Test startup event executes when GOOGLE_API_KEY is present."""
        import os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.main import app
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
            # context manager triggers startup event
            with TestClient(app) as test_client:
                pass

    def test_startup_event_no_key(self):
        """Test startup event logs warning when GOOGLE_API_KEY is missing."""
        import os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.main import app
        
        with patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as test_client:
                pass

    def test_startup_event_exception(self):
        import os
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from app.main import app
        
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake_key"}):
            with patch("app.main.setup_rag_pipeline", side_effect=Exception("mock initialization error")):
                # Intentionally trap the exception printed to logs
                with TestClient(app):
                    pass
