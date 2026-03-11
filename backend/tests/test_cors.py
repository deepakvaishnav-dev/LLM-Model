import pytest

class TestCORSMiddleware:
    """Test suite for CORS functionality."""
    
    def test_cors_options_preflight(self, client):
        """Test OPTIONS preflight request doesn't return 500 error."""
        response = client.options(
            "/api/chat/", 
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )
        assert response.status_code in [200, 204] # Should be OK or No Content
        # Assert proper CORS headers are present
        assert "access-control-allow-origin" in response.headers
        
    def test_cors_origin_header_get(self, client):
        """Test sending an Origin header doesn't break a simple GET request."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert "access-control-allow-origin" in response.headers
