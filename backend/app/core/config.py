import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AI Developer Knowledge Assistant API"
    GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
    
    _allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
    ALLOWED_ORIGINS: list[str] = [
        origin.strip() for origin in _allowed_origins_env.split(",")
    ] if _allowed_origins_env else ["*"]
    
    OLLAMA_FALLBACK_MODELS: str = os.getenv(
        "OLLAMA_FALLBACK_MODELS",
        "llama3.2:1b,llama3.2:latest,llama3.2",
    )

settings = Settings()
