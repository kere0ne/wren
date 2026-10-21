import os


class Settings:
    def __init__(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wren.db")
        self.JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
        self.JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "10080"))
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
        # Brains, tried in order: free Workers AI chain, OpenAI-compatible, Ollama.
        self.CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", "")
        self.CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
        self.MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
        self.MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "").rstrip("/")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
        self.AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "12"))
        self.WEB_TIMEOUT = int(os.getenv("WEB_TIMEOUT", "20"))
        # Where agent file tools and code execution live (per-user subdirectory).
        self.WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "./workspaces")
        self.NODE_BIN = os.getenv("NODE_BIN", "")


settings = Settings()
