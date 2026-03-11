import pytest
import io
from unittest.mock import patch

class TestUploadEndpoints:
    """Test suite for the file upload endpoints and processing status."""
    
    def test_upload_missing_file_returns_422(self, client):
        """Test POST without a file returns 422 Unprocessable Entity."""
        response = client.post("/api/upload/")
        assert response.status_code == 422
        
    def test_upload_accepted_extensions(self, client):
        """Test uploading accepted file types (.pdf, .txt, .md, .zip)."""
        valid_extensions = [("test.pdf", b"pdf content"), 
                            ("test.txt", b"txt content"), 
                            ("test.md", b"md content"), 
                            ("test.zip", b"zip content")]
                            
        for filename, content in valid_extensions:
            # Override background task processing to prevent errors
            with patch("app.api.upload.BackgroundTasks.add_task") as mock_add_task:
                file_to_upload = {"file": (filename, io.BytesIO(content), "text/plain")}
                response = client.post("/api/upload/", files=file_to_upload)
                
                assert response.status_code == 200
                assert "Successfully uploaded" in response.json()["message"]
                mock_add_task.assert_called_once()
                
    def test_upload_rejected_extensions(self, client):
        """Test uploading rejected file types (.exe, .js)."""
        invalid_extensions = [("malware.exe", b"bad code"), 
                              ("script.js", b"console.log('hi')")]
                              
        for filename, content in invalid_extensions:
            file_to_upload = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
            response = client.post("/api/upload/", files=file_to_upload)
            
            assert response.status_code == 400
            assert "File type not supported" in response.json()["detail"]
            
    def test_upload_no_extension(self, client):
        """Test uploading files with no extension is rejected."""
        file_to_upload = {"file": ("noextensionfile", io.BytesIO(b"content"), "text/plain")}
        response = client.post("/api/upload/", files=file_to_upload)
        
        assert response.status_code == 400
        assert "File must have an extension" in response.json()["detail"]
        
    def test_upload_file_size_limit(self, client):
        """Test files over 10MB are rejected."""
        # Create a file exactly 1 byte larger than 10MB
        large_content = b"0" * (10 * 1024 * 1024 + 1)
        file_to_upload = {"file": ("toolarge.txt", io.BytesIO(large_content), "text/plain")}
        
        response = client.post("/api/upload/", files=file_to_upload)
        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    def test_status_endpoint_tracking(self, client):
        """Test status endpoint tracks files correctly (not_found, pending, etc)."""
        # Initially not found
        response = client.get("/api/upload/status/unknown_file.pdf")
        assert response.status_code == 200
        assert response.json()["status"] == "not_found"
        
        # Test the global state update directly by mocking
        import app.api.upload
        original_status = app.api.upload.processing_status.copy()
        try:
            app.api.upload.processing_status["test_tracking.pdf"] = "processing"
            response = client.get("/api/upload/status/test_tracking.pdf")
            assert response.status_code == 200
            assert response.json()["status"] == "processing"
            
            app.api.upload.processing_status["test_tracking.pdf"] = "completed"
            response = client.get("/api/upload/status/test_tracking.pdf")
            assert response.status_code == 200
            assert response.json()["status"] == "completed"
        finally:
            app.api.upload.processing_status = original_status

    @patch("app.api.upload.process_document")
    def test_parse_and_index_exception(self, mock_process):
        """Test backend task sets status to failed on exception."""
        from app.api.upload import parse_and_index, processing_status
        mock_process.side_effect = Exception("Test error")
        
        parse_and_index("dummy_path", "fail_test.txt")
        assert processing_status.get("fail_test.txt") == "failed"

    def test_secure_filename_path_traversal(self, client):
        """Test uploading a file with path traversal attempts."""
        import io
        from unittest.mock import patch
        
        with patch("app.api.upload.BackgroundTasks.add_task"):
            malicious_name = "../../../etc/passwd.txt"
            file_to_upload = {"file": (malicious_name, io.BytesIO(b"content"), "text/plain")}
            response = client.post("/api/upload/", files=file_to_upload)
            
            assert response.status_code == 200
            # Should have stripped `../` and just been 'passwd.txt' or similar.
            assert "Successfully uploaded" in response.json()["message"]
            assert "../" not in response.json()["message"]

    def test_secure_filename_hidden(self, client):
        """Test uploading a file that results in a hidden or empty safe_name."""
        import io
        from unittest.mock import patch
        
        with patch("app.api.upload.BackgroundTasks.add_task"):
            hidden_name = ".config.txt"
            file_to_upload = {"file": (hidden_name, io.BytesIO(b"content"), "text/plain")}
            response = client.post("/api/upload/", files=file_to_upload)
            
            assert response.status_code == 200
            assert "default_upload_.config.txt" in response.json()["message"]
