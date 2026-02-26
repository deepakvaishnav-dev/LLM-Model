import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, chat
from app.services.indexer import setup_rag_pipeline
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Developer Knowledge Assistant API")

@app.on_event("startup")
async def startup_event():
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        try:
            setup_rag_pipeline(google_key)
            logger.info("Successfully initialized RAG pipeline with Google Gemini Key.")
        except Exception as e:
            logger.error(f"Failed to initialize RAG pipeline: {e}")
            logger.warning("Backend started but AI features may not work. Check GEMINI_MODEL in .env")
    else:
        logger.warning("WARNING: GOOGLE_API_KEY not found in environment.")

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")] if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "AI Developer Knowledge Assistant API Server Running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
