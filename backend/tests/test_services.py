import pytest
import os
import zipfile
from unittest.mock import patch, MagicMock
from app.services.parser import process_document

class TestParserService:
    """Test suite for document parsing and indexing services."""
    
    def test_process_nonexistent_file(self):
        """Test process_document with nonexistent file -> returns []"""
        result = process_document("does_not_exist.txt")
        assert result == []
        
    @patch("app.services.parser.SimpleDirectoryReader")
    @patch("os.path.exists", return_value=True)
    def test_process_txt_file(self, mock_exists, mock_reader_class):
        """Test process_document with valid TXT -> list of docs"""
        # Mock the reader instance and load_data
        mock_reader_instance = MagicMock()
        mock_reader_instance.load_data.return_value = ["doc1", "doc2"]
        mock_reader_class.return_value = mock_reader_instance
        
        result = process_document("valid_file.txt")
        
        assert result == ["doc1", "doc2"]
        mock_reader_class.assert_called_once_with(input_files=["valid_file.txt"])
        mock_reader_instance.load_data.assert_called_once()
        
    @patch("app.services.parser.os.makedirs")
    @patch("app.services.parser.zipfile.ZipFile")
    @patch("app.services.parser.SimpleDirectoryReader")
    @patch("os.path.exists", return_value=True)
    def test_process_zip_file(self, mock_exists, mock_reader_class, mock_zip_class, mock_makedirs):
        """Test process_document with ZIP file -> extracted + parsed"""
        # Setup mocks
        mock_reader_instance = MagicMock()
        mock_reader_instance.load_data.return_value = ["parsed_extracted_doc"]
        mock_reader_class.return_value = mock_reader_instance
        
        mock_zip_instance = MagicMock()
        mock_zip_instance.namelist.return_value = ["file1.txt", "file2.pdf"]
        
        # We need mock_zip_class to return a context manager
        mock_zip_class.return_value.__enter__.return_value = mock_zip_instance
        
        result = process_document("archive.zip")
        
        assert result == ["parsed_extracted_doc"]
        
        # Verify extracted and reader called on extract_dir
        mock_makedirs.assert_called_once_with("archive.zip_extracted", exist_ok=True)
        # Note: os.path.abspath interactions make exact extraction path assertions tricky, 
        # but we verify ZipFile methods were executed
        mock_zip_instance.extract.assert_called()
        mock_reader_class.assert_called_once_with(input_dir="archive.zip_extracted", recursive=True)

    @patch("app.services.parser.os.makedirs")
    @patch("app.services.parser.zipfile.ZipFile")
    @patch("os.path.exists", return_value=True)
    def test_process_zip_unsafe_file(self, mock_exists, mock_zip_class, mock_makedirs, caplog):
        """Test process_document with ZIP file containing path traversal -> skipped"""
        mock_zip_instance = MagicMock()
        # Mock namelist to return a traversal path
        mock_zip_instance.namelist.return_value = ["../../../unsafe.txt"]
        mock_zip_class.return_value.__enter__.return_value = mock_zip_instance
        
        with patch("app.services.parser.SimpleDirectoryReader"):
            process_document("archive.zip")
            
        # Verify the file wasn't extracted by checking the warning log
        assert "Skipped unsafe file in zip" in caplog.text

    @patch("app.services.parser.SimpleDirectoryReader")
    @patch("os.path.exists", return_value=True)
    def test_process_empty_document(self, mock_exists, mock_reader_class, caplog):
        """Test process_document where reader finds no content -> []"""
        mock_reader_instance = MagicMock()
        mock_reader_instance.load_data.return_value = []
        mock_reader_class.return_value = mock_reader_instance
        
        result = process_document("empty.txt")
        assert result == []
        assert "No content could be extracted" in caplog.text

    @patch("os.path.exists", return_value=True)
    def test_process_exception(self, mock_exists, caplog):
        """Test process_document standard exception handling -> []"""
        # Force exception by making endswith fail or something similar if we pass a None
        # or just block SimpleDirectoryReader
        with patch("app.services.parser.SimpleDirectoryReader", side_effect=Exception("mocked reader fail")):
            result = process_document("error.txt")
            assert result == []
            assert "Error processing" in caplog.text

    @patch("app.services.indexer.time.sleep")
    def test_get_or_create_index_with_documents(self, mock_sleep):
        """Test get_or_create_index processing a list of documents with mocked sleep."""
        from app.services.indexer import get_or_create_index
        import sys
        
        docs = ["doc1", "doc2", "doc3"]
        # The indexer function creates mock instances since vector_stores are mocked
        # So it will successfully run all the lines in the loop.
        index = get_or_create_index(documents=docs)
        
        assert index is not None
        # It should sleep (len - 1) times = 2 times
        assert mock_sleep.call_count == 2

    def test_get_or_create_index_no_documents(self):
        """Test get_or_create_index when no documents are provided."""
        from app.services.indexer import get_or_create_index
        
        index = get_or_create_index()
        assert index is not None
