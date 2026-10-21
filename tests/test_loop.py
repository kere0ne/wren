import json

from app.agent import loop
from app.core.db import SessionLocal
from app.models import Thread, User


def test_agent_runs_one_tool_then_answers(client, auth, monkeypatch):
    auth(email="loop@example.com")
    db = SessionLocal()
    user = db.query(User).filter(User.email == "loop@example.com").first()
    thread = Thread(user_id=user.id, title="t")
    db.add(thread)
    db.commit()

    calls = {"n": 0}

    def fake_completion(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "calculator",
                                        "arguments": json.dumps({"expression": "6*7"}),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        return {"choices": [{"message": {"role": "assistant", "content": "The answer is 42."}}]}

    monkeypatch.setattr(loop, "chat_completion", fake_completion)

    events = []
    loop.run_agent(db, user, thread, "what is 6*7?", lambda kind, payload: events.append((kind, payload)))

    kinds = [k for k, _ in events]
    assert "tool_call" in kinds and "tool_result" in kinds and "done" in kinds
    assert events[-1][1]["content"] == "The answer is 42."

    roles = [m.role for m in db.query(loop.Message).filter(loop.Message.thread_id == thread.id).all()]
    assert "user" in roles and "tool_call" in roles and "assistant" in roles
    db.close()


def test_agent_emits_error_without_model_key(client, auth, monkeypatch):
    auth(email="nokey@example.com")
    db = SessionLocal()
    user = db.query(User).filter(User.email == "nokey@example.com").first()
    thread = Thread(user_id=user.id, title="t")
    db.add(thread)
    db.commit()

    def fake_completion(messages, tools=None):
        raise loop.ModelNotConfigured("No model key is set on the server.")

    monkeypatch.setattr(loop, "chat_completion", fake_completion)
    events = []
    loop.run_agent(db, user, thread, "hi", lambda kind, payload: events.append((kind, payload)))
    assert events[-1][0] == "error"
    db.close()
