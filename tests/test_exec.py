import shutil

from app.agent.tools import dispatch
from app.core.db import SessionLocal
from app.models import User


def _user(email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    return db, user


def test_run_python_executes_real_code(client, auth):
    auth(email="exec@example.com")
    db, user = _user("exec@example.com")
    out = dispatch(db, user, "run_python", {"code": "print(6*7)"})
    assert "42" in out
    db.close()


def test_run_shell_echo(client, auth):
    auth(email="shell@example.com")
    db, user = _user("shell@example.com")
    out = dispatch(db, user, "run_shell", {"command": "echo wren-shell-ok"})
    assert "wren-shell-ok" in out
    db.close()


def test_run_javascript(client, auth):
    auth(email="js@example.com")
    db, user = _user("js@example.com")
    out = dispatch(db, user, "run_javascript", {"code": "console.log(2 ** 10)"})
    if shutil.which("node") is None and "not installed" in out:
        assert "node is not installed" in out
    else:
        assert "1024" in out
    db.close()


def test_file_tools_roundtrip_and_traversal_blocked(client, auth):
    auth(email="files@example.com")
    db, user = _user("files@example.com")

    out = dispatch(db, user, "write_file", {"path": "src/app.py", "content": "print('wren')\n"})
    assert "wrote" in out

    out = dispatch(db, user, "read_file", {"path": "src/app.py"})
    assert "print('wren')" in out

    out = dispatch(db, user, "list_files", {})
    assert "src/app.py" in out

    out = dispatch(db, user, "write_file", {"path": "../escape.txt", "content": "no"})
    assert "escapes" in out
    db.close()
