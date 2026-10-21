from app.agent.tools import calculator, dispatch
from app.core.db import SessionLocal
from app.models import User


def test_calculator():
    assert calculator("2+2*3") == "8"
    assert calculator("(1+2)/3") == "1.0"


def test_memory_tools(client, auth):
    auth(email="tools@example.com")
    db = SessionLocal()
    user = db.query(User).filter(User.email == "tools@example.com").first()

    out = dispatch(db, user, "save_memory", {"content": "runs projects on Cloudflare", "kind": "fact"})
    assert "saved" in out

    out = dispatch(db, user, "search_memory", {"query": "cloudflare"})
    assert "cloudflare" in out.lower()

    out = dispatch(db, user, "unknown_tool", {})
    assert "unknown tool" in out
    db.close()
