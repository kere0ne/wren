from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import Base, engine
from .routers import auth, chat, memory

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wren", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(memory.router)


@app.get("/api/health")
def health():
    return {"ok": True, "service": "wren"}
