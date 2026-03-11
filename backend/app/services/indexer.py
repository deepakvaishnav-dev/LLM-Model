from llama_index.core import Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex
import chromadb
import os
import time

def setup_rag_pipeline(google_api_key: str):
    # Read model name from env; default to Gemini flash latest.
    model_name = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")

    Settings.text_splitter = SentenceSplitter(chunk_size=4096, chunk_overlap=256)
    
    # Reduce embed_batch_size to stay within embedding rate limits
    Settings.embed_model = GoogleGenAIEmbedding(
        api_key=google_api_key,
        model_name="models/gemini-embedding-001",
        embed_batch_size=3,
    )
    
    Settings.llm = GoogleGenAI(model=model_name, api_key=google_api_key)
    print(f"RAG pipeline initialized with model: {model_name}")
    
def get_or_create_index(documents=None, persist_dir="./chroma_db"):
   
    db = chromadb.PersistentClient(path=persist_dir)
    chroma_collection = db.get_or_create_collection("ai_knowledge_base")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    if documents:
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
        
        # Ek-ek karke document process karein taaki limit hit na ho
        # Chota batch size rakhein (1 document at a time)
        for i, doc in enumerate(documents):
            print(f"Indexing document {i+1} of {len(documents)}...")
            index.insert(doc)
            
            # Har batch (document) ke baad thoda wait karein (Gemini 15 RPM limit)
            if i < len(documents) - 1:
                time.sleep(4)
    else:
        index = VectorStoreIndex.from_vector_store(
            vector_store, storage_context=storage_context
        )
        
    return index
