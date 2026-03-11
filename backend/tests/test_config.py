import pytest
import os
from unittest.mock import patch
import importlib

class TestConfiguration:
    """Test suite for application configuration and environment variables."""
    
    @patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:5173", "GOOGLE_API_KEY": "test_key"})
    def test_settings_loads_from_env(self):
        """Test that settings load correctly from environment variables."""
        # Test the main module parsing logic
        import app.main
        importlib.reload(app.main)
        
        # Test that ALLOWED_ORIGINS is parsed into a list correctly
        assert isinstance(app.main.allowed_origins, list)
        assert len(app.main.allowed_origins) == 2
        assert "http://localhost:3000" in app.main.allowed_origins
        
        # If the user has a separate config module, test it
        try:
            import app.core.config as config
            importlib.reload(config)
            assert hasattr(config, "ALLOWED_ORIGINS")
            assert isinstance(config.ALLOWED_ORIGINS, list)
        except ImportError:
            pass
            
    @patch.dict(os.environ, {}, clear=True)
    def test_settings_empty_env(self):
        """Test configuration defaults when environment variables are not set."""
        import app.main
        importlib.reload(app.main)
        
        assert isinstance(app.main.allowed_origins, list)
        assert app.main.allowed_origins == ["*"]
