import os
import zipfile
import logging
from llama_index.core import SimpleDirectoryReader

logger = logging.getLogger(__name__)

def process_document(file_path: str):
    """
    Parses a document (PDF, MD, TXT, or ZIP) using LlamaIndex SimpleDirectoryReader 
    and prepares it for chunking and embedding.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    try:
        if file_path.endswith('.zip'):
            extract_dir = file_path + "_extracted"
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    member_path = os.path.abspath(os.path.join(extract_dir, member))
                    if member_path.startswith(os.path.abspath(extract_dir)):
                        zip_ref.extract(member, extract_dir)
                    else:
                        logger.warning(f"Skipped unsafe file in zip: {member}")
                        
            reader = SimpleDirectoryReader(input_dir=extract_dir, recursive=True)
        else:
            reader = SimpleDirectoryReader(input_files=[file_path])
            
        documents = reader.load_data()
        
        if not documents:
            logger.warning(f"No content could be extracted from {file_path}. Document might be empty.")
            return []
            
        logger.info(f"Loaded {len(documents)} document chunks from {file_path}")
        return documents
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return []
