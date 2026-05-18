from pydantic_settings import BaseSettings
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    BENCHMARK_API_KEY: str

    # LLM (all calls go through OpenRouter)
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MINI_MODEL: str = "openai/gpt-4.1-mini"
    LLM_FULL_MODEL: str = "openai/gpt-4.1"

    # Embedding (OpenAI directly)
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1024

    # Query thresholds
    KB_SIMILARITY_THRESHOLD: float = 0.70
    QA_CACHE_HIT_THRESHOLD: float = 0.93
    QA_CACHE_SOFT_THRESHOLD: float = 0.82

    class Config:
        env_file = (PROJECT_ROOT / ".env", BACKEND_ROOT / ".env", ".env")
        extra = "ignore"

settings = Settings()
