import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..agent.loop import run_agent
from ..core.db import get_db
from ..core.security import get_current_user
from ..models import Message, Thread, User
from ..schemas import MessageOut, StreamIn, ThreadCreate, ThreadOut

router = APIRouter(prefix="/api", tags=["chat"])


def owned_thread(db: Session, thread_id: int, user: User) -> Thread:
    thread = db.get(Thread, thread_id)
    if not thread or thread.user_id != user.id:
        raise HTTPException(status_code=404, detail="thread not found")
    return thread


@router.post("/threads", response_model=ThreadOut)
def create_thread(body: ThreadCreate | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    title = (body.title if body else None) or "New chat"
    thread = Thread(user_id=user.id, title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Thread).filter(Thread.user_id == user.id).order_by(Thread.id.desc()).all()


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(thread_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    thread = owned_thread(db, thread_id, user)
    return db.query(Message).filter(Message.thread_id == thread.id).order_by(Message.id).all()


@router.post("/threads/{thread_id}/stream")
def stream(thread_id: int, body: StreamIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    thread = owned_thread(db, thread_id, user)

    def generate():
        def emit(kind, payload):
            payload = dict(payload)
            payload["type"] = kind
            yield f"data: {json.dumps(payload)}\n\n"

        yield from run_agent(db, user, thread, body.message, emit)

    return StreamingResponse(generate(), media_type="text/event-stream")
