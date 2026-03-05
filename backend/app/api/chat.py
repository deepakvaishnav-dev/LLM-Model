from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.indexer import get_or_create_index
from llama_index.core import PromptTemplate
import os
import time

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessage]] = []

def _is_daily_quota_exceeded(err_str: str) -> bool:
    """
    Returns True when the error is a DAILY quota exhaustion (cannot be fixed by waiting).
    Per-minute / per-token limits are transient and worth retrying.
    """
    daily_quota_indicators = [
        "PerDay",
        "free_tier_requests",
        "quota, please check your plan",
        "GenerateRequestsPerDayPerProject",
    ]
    return any(indicator in err_str for indicator in daily_quota_indicators)

@router.post("/")
def chat_query(request: ChatRequest):
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set in backend.")
        
    try:
        index = get_or_create_index()
        
        # Create a query engine
        query_engine = index.as_query_engine(
            similarity_top_k=3,
        )
        
        max_retries = 3
        response = None
        gemini_error = None
        for attempt in range(max_retries):
            try:
                response = query_engine.query(request.query)
                break
            except Exception as e:
                err_str = str(e)
                gemini_error = err_str
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

                if is_rate_limit:
                    # If it's a DAILY quota, we just break out of the retry loop and go to fallback immediately
                    if _is_daily_quota_exceeded(err_str):
                        break

                    # Per-minute rate limit — retry with exponential back-off
                    if attempt < max_retries - 1:
                        wait_time = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        print(f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                else:
                    # Not a rate limit error, break and go to fallback
                    break

        # Fallback to Ollama if Gemini failed
        if response is None:
            print(f"Gemini API failed: {gemini_error}. Falling back to local Ollama model...")
            try:
                from llama_index.llms.ollama import Ollama
                ollama_llm = Ollama(model="llama3.2", request_timeout=120.0)
                
                # Try Ollama WITH RAG first
                try:
                    fallback_query_engine = index.as_query_engine(
                        similarity_top_k=3,
                        llm=ollama_llm
                    )
                    response = fallback_query_engine.query(request.query)
                    print("Successfully generated response using Ollama with RAG.")
                except Exception as rag_err:
                    print(f"Ollama with RAG failed (possibly due to embedding error): {rag_err}. Falling back to Ollama without RAG...")
                    # Try Ollama WITHOUT RAG (Direct completion)
                    ollama_response = ollama_llm.complete(request.query)
                    
                    # Create a mock response object that matches LlamaIndex's expected structure
                    class MockNode:
                        def __init__(self):
                            self.metadata = {"file_name": "No Context (Fallback Mode)"}
                            self.text = "The context could not be retrieved due to embedding API failure."
                            self.score = 0.0
                            
                    class MockResponse:
                        def __init__(self, text):
                            self.source_nodes = [MockNode()]
                            self.text = text
                            
                        def __str__(self):
                            return self.text
                            
                    response = MockResponse(str(ollama_response))
                    print("Successfully generated response using Ollama without RAG.")
            except Exception as fallback_err:
                raise Exception(f"Both Gemini and Ollama fallback failed. Gemini Error: {gemini_error}. Ollama Error: {fallback_err}")
            
        
        # Extract sources from the response
        sources = []
        for node in response.source_nodes:
            sources.append({
                "file": node.metadata.get("file_name", "Unknown File"),
                "text": node.text[:200] + "...",
                "score": node.score
            })
            
        return {
            "response": str(response),
            "sources": sources
        }
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is (already formatted)
    except Exception as e:
        err_str = str(e)
        print(f"Chat error: {err_str}")
        
        if "Both Gemini and Ollama fallback failed" in err_str:
            raise HTTPException(
                status_code=500,
                detail=f"AI processing failed. {err_str}"
            )
        
        # Detect Gemini API quota / rate-limit errors
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exceeded. Please wait a moment and try again, or upgrade your Google AI plan."
            )
        # Detect authentication / invalid key errors
        elif "401" in err_str or "API_KEY_INVALID" in err_str or "UNAUTHENTICATED" in err_str:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing Google API key. Please check your GOOGLE_API_KEY in the backend .env file."
            )
        # Detect no documents indexed yet
        elif "empty" in err_str.lower() or "no documents" in err_str.lower():
            raise HTTPException(
                status_code=400,
                detail="No documents have been indexed yet. Please upload and index files in the Knowledge Base first."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process query. Error: {err_str}"
            )
