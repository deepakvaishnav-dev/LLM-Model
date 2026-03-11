from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.indexer import get_or_create_index
from llama_index.core import PromptTemplate
from llama_index.core.prompts import PromptType
import subprocess
import time
from app.core.config import settings
from app.schemas.chat import ChatRequest

# Strict PDF-only prompt - LLM sirf uploaded document se answer dega
STRICT_PDF_PROMPT = PromptTemplate(
    "You are a helpful AI assistant that ONLY answers questions based on the provided document context.\n"
    "\n"
    "STRICT RULES:\n"
    "1. You MUST only use information from the CONTEXT below to answer the question.\n"
    "2. Do NOT use any external knowledge, internet knowledge, or training data knowledge.\n"
    "3. If the answer is NOT found in the provided context, respond EXACTLY with:\n"
    "   'Yeh information uploaded documents mein nahi mili. Please related document upload karein.'\n"
    "4. Never make up or guess information not present in the context.\n"
    "5. Always base your answer strictly on what is written in the context.\n"
    "\n"
    "CONTEXT FROM UPLOADED DOCUMENTS:\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "\n"
    "USER QUESTION: {query_str}\n"
    "\n"
    "ANSWER (strictly from the documents above only):\n",
    prompt_type=PromptType.QUESTION_ANSWER,
)

router = APIRouter()

def _build_sources_from_response(response):
    source_nodes = getattr(response, "source_nodes", []) or []
    sources = []
    for node in source_nodes:
        metadata = getattr(node, "metadata", {}) or {}
        node_text = getattr(node, "text", "") or ""
        node_score = getattr(node, "score", 0.0)
        sources.append(
            {
                "file": metadata.get("file_name", "Unknown File"),
                "text": f"{node_text[:200]}...",
                "score": node_score,
            }
        )
    return sources


def _ollama_model_candidates() -> List[str]:
    configured = settings.OLLAMA_FALLBACK_MODELS
    configured_models = [m.strip() for m in configured.split(",") if m.strip()]

    installed_models = []
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()[1:]  # skip header
            for line in lines:
                parts = line.split()
                if parts:
                    installed_models.append(parts[0].strip())
    except Exception:
        pass

    if not installed_models:
        return configured_models

    # Prefer configured models that are actually installed, then add other installed models.
    prioritized = [m for m in configured_models if m in installed_models]
    remaining_installed = [m for m in installed_models if m not in prioritized]
    return prioritized + remaining_installed


def _is_memory_error(err_str: str) -> bool:
    lowered = err_str.lower()
    return "requires more system memory" in lowered or "not enough memory" in lowered


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
    google_key = settings.GOOGLE_API_KEY

    try:
        index = get_or_create_index()

        response = None
        gemini_error = None

        # Try Gemini first when key is available.
        if google_key:
            query_engine = index.as_query_engine(
                similarity_top_k=5,
                text_qa_template=STRICT_PDF_PROMPT,
            )
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = query_engine.query(request.query)
                    break
                except Exception as e:
                    err_str = str(e)
                    gemini_error = err_str
                    is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str

                    if not is_rate_limit:
                        break

                    # DAILY quota cannot be solved by waiting.
                    if _is_daily_quota_exceeded(err_str):
                        break

                    if attempt < max_retries - 1:
                        wait_time = 10 * (2 ** attempt)  # 10s, 20s, 40s
                        print(
                            f"Rate limit hit. Retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
        else:
            gemini_error = "GOOGLE_API_KEY not set; Gemini skipped."

        # Fallback to Ollama if Gemini failed or was skipped.
        if response is None:
            print(
                f"Gemini unavailable/failed: {gemini_error}. Falling back to local Ollama models..."
            )
            from llama_index.llms.ollama import Ollama

            ollama_errors = []
            for ollama_model in _ollama_model_candidates():
                try:
                    ollama_llm = Ollama(model=ollama_model, request_timeout=120.0)

                    # Prefer RAG path first.
                    try:
                        fallback_query_engine = index.as_query_engine(
                            similarity_top_k=5,
                            llm=ollama_llm,
                            text_qa_template=STRICT_PDF_PROMPT,
                        )
                        response = fallback_query_engine.query(request.query)
                        print(
                            f"Successfully generated response using Ollama with RAG (model: {ollama_model})."
                        )
                        break
                    except Exception as rag_err:
                        # Fall back to direct completion if retriever path fails.
                        ollama_response = ollama_llm.complete(request.query)

                        class MockNode:
                            def __init__(self):
                                self.metadata = {
                                    "file_name": "No Context (Fallback Mode)"
                                }
                                self.text = f"The context could not be retrieved due to retriever error: {rag_err}"
                                self.score = 0.0

                        class MockResponse:
                            def __init__(self, text):
                                self.source_nodes = [MockNode()]
                                self.text = text

                            def __str__(self):
                                return self.text

                        response = MockResponse(str(ollama_response))
                        print(
                            f"Successfully generated response using Ollama direct completion (model: {ollama_model}). "
                            f"Retriever error was: {rag_err}"
                        )
                        break
                except Exception as ollama_err:
                    ollama_err_str = str(ollama_err)
                    ollama_errors.append(f"{ollama_model}: {ollama_err_str}")
                    if _is_memory_error(ollama_err_str):
                        print(
                            f"Ollama model {ollama_model} skipped due to memory limits."
                        )
                        continue
                    print(f"Ollama model {ollama_model} failed: {ollama_err_str}")
                    continue

            if response is None:
                raise Exception(
                    "All AI providers failed. "
                    f"Gemini Error: {gemini_error}. "
                    f"Ollama Errors: {' | '.join(ollama_errors) if ollama_errors else 'No Ollama models configured.'}"
                )

        return {
            "response": str(response),
            "sources": _build_sources_from_response(response),
        }
    except HTTPException:
        raise
    except Exception as e:
        err_str = str(e)
        print(f"Chat error: {err_str}")

        if "All AI providers failed" in err_str:
            raise HTTPException(
                status_code=503,
                detail=(
                    "AI processing failed. Gemini quota may be exhausted and local Ollama models could not run. "
                    "Set OLLAMA_FALLBACK_MODELS to small installed models (for example: llama3.2:1b,phi3:mini), "
                    "or upgrade Gemini quota. "
                    f"Debug: {err_str}"
                ),
            )

        # Detect Gemini API quota / rate-limit errors
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            raise HTTPException(
                status_code=429,
                detail="Gemini API quota exceeded. Please wait a moment and try again, or upgrade your Google AI plan.",
            )
        # Detect authentication / invalid key errors
        elif (
            "401" in err_str
            or "API_KEY_INVALID" in err_str
            or "UNAUTHENTICATED" in err_str
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing Google API key. Please check your GOOGLE_API_KEY in the backend .env file.",
            )
        # Detect no documents indexed yet
        elif "empty" in err_str.lower() or "no documents" in err_str.lower():
            raise HTTPException(
                status_code=400,
                detail="No documents have been indexed yet. Please upload and index files in the Knowledge Base first.",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process query. Error: {err_str}",
            )
