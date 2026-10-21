from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..core.security import get_current_user
from ..models import MemoryFact, User
from ..schemas import MemoryCreate, MemoryOut

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("", response_model=list[MemoryOut])
def list_memory(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(MemoryFact)
        .filter(MemoryFact.user_id == user.id)
        .order_by(MemoryFact.created_at.desc())
        .limit(200)
        .all()
    )


@router.post("", response_model=MemoryOut)
def add_memory(body: MemoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fact = MemoryFact(user_id=user.id, kind=body.kind, content=body.content.strip())
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return fact


@router.delete("/{fact_id}")
def delete_memory(fact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fact = db.get(MemoryFact, fact_id)
    if not fact or fact.user_id != user.id:
        raise HTTPException(status_code=404, detail="memory not found")
    db.delete(fact)
    db.commit()
    return {"ok": True}
