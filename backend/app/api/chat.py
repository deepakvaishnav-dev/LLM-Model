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
        for attempt in range(max_retries):
            try:
                response = query_engine.query(request.query)
                break
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

                if is_rate_limit:
                    # If it's a DAILY quota — do NOT retry, surface it immediately
                    if _is_daily_quota_exceeded(err_str):
                        model = os.getenv("GEMINI_MODEL", "models/gemini-1.5-flash")
                        raise HTTPException(
                            status_code=429,
                            detail=(
                                f"Your Google API free-tier daily quota for '{model}' is exhausted. "
                                "Please wait until midnight (Pacific Time) for the quota to reset, "
                                "or upgrade your Google AI plan at https://ai.google.dev/pricing."
                            )
                        )

                    # Per-minute rate limit — retry with exponential back-off
                    if attempt < max_retries - 1:
                        wait_time = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        print(f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue

                raise e
                
        if response is None:
            raise Exception("Failed to get response from AI model after retries.")
            
        
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
