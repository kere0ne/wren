from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from .core.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="New chat")
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant | tool_call | tool_result
    content = Column(Text, default="")
    meta = Column(Text)  # json for tool rows
    created_at = Column(DateTime(timezone=True), default=utcnow)


class MemoryFact(Base):
    __tablename__ = "memory_facts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(30), default="fact")  # preference | fact | project | relationship
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
