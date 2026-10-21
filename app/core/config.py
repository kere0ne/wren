import os


class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wren.db")
        self.JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
        self.JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "10080"))
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        # OpenAI-compatible endpoint: OpenAI, OpenRouter, Groq, Ollama, etc.
        self.MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
        self.WEB_TIMEOUT = int(os.getenv("WEB_TIMEOUT", "20"))


settings = Settings()
