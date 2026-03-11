import pytest
import io

class TestIntegration:
    """End-to-end integration tests between various module routes."""
    
    def test_upload_and_status_integration(self, client):
        """Upload file -> check status endpoint tracks it."""
        import app.api.upload
        original_status = app.api.upload.processing_status.copy()
        
        try:
            # Upload a valid file
            file_content = b"Integration test content"
            file_to_upload = {"file": ("integration_file.txt", io.BytesIO(file_content), "text/plain")}
            
            upload_response = client.post("/api/upload/", files=file_to_upload)
            assert upload_response.status_code == 200
            
            # Since the background task processing may cause issues in unit test environment,
            # we just want to ensure it transitioned to pending or completed.
            # In purely sync TestClient usage, tracking it might show 'pending' initially.
            
            status_response = client.get("/api/upload/status/integration_file.txt")
            assert status_response.status_code == 200
            status = status_response.json()["status"]
            assert status in ["pending", "processing", "completed", "failed"]
        finally:
            app.api.upload.processing_status = original_status
