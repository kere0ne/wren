import ast
import json
import operator as op
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..core.config import settings
from ..models import MemoryFact

MAX_OUTPUT = 4000
EXEC_TIMEOUT = 30

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a durable fact or preference about the user for future conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The fact, in one sentence."},
                    "kind": {"type": "string", "enum": ["preference", "fact", "project", "relationship"]},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "Search saved facts and preferences about the user.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_get",
            "description": "Fetch a public web page and return its readable text.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate an arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "now",
            "description": "Current date and time in UTC.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the user's workspace (a real directory). Use first when asked to work with code.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path; default is the workspace root."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the user's workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a text file in the user's workspace (creates parent folders).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a Python snippet in the workspace and return stdout/stderr. Use to execute and verify code.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_javascript",
            "description": "Run a Node.js snippet in the workspace and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a bash command in the workspace (installs, tests, builds) and return its output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]

_CALC_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def calculator(expr: str) -> str:
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPS:
            return _CALC_OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_OPS:
            return _CALC_OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsupported expression")

    return str(ev(ast.parse(expr.strip(), mode="eval").body))


def web_get(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "error: url must start with http:// or https://"
    try:
        resp = httpx.get(
            url,
            timeout=settings.WEB_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Wren/0.1 (+https://github.com/kere0ne/wren)"},
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"error: fetch failed ({exc.__class__.__name__})"
    html = resp.text
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "error: page returned no readable text (it may need JavaScript)"
    return text[:8000]


def _user_dir(user) -> Path:
    root = Path(settings.WORKSPACE_ROOT).resolve()
    d = root / str(user.id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_path(user, rel: str):
    d = _user_dir(user)
    if not rel or rel.strip() in (".", "/"):
        return d
    p = (d / rel).resolve()
    if not str(p).startswith(str(d) + os.sep):
        return None
    return p


def _run(cmd: list, cwd: Path, timeout: int = EXEC_TIMEOUT) -> str:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"error: timed out after {timeout}s"
    out = proc.stdout or ""
    if proc.stderr:
        out += "\n[stderr]\n" + proc.stderr
    if proc.returncode != 0:
        out += f"\n(exit code {proc.returncode})"
    out = out.strip() or "(no output)"
    return out[:MAX_OUTPUT]


def run_python(user, code: str, timeout: int = EXEC_TIMEOUT) -> str:
    d = _user_dir(user)
    f = d / "_exec_tmp.py"
    f.write_text(code)
    return _run([sys.executable, f.name], cwd=d, timeout=timeout)


def run_javascript(user, code: str, timeout: int = EXEC_TIMEOUT) -> str:
    node = settings.NODE_BIN or shutil.which("node")
    if not node:
        return "error: node is not installed on this host"
    d = _user_dir(user)
    f = d / "_exec_tmp.js"
    f.write_text(code)
    return _run([node, f.name], cwd=d, timeout=timeout)


def run_shell(user, command: str, timeout: int = EXEC_TIMEOUT) -> str:
    return _run(["bash", "-lc", command], cwd=_user_dir(user), timeout=timeout)


def list_files(user, path: str = ".") -> str:
    p = _safe_path(user, path)
    if p is None:
        return "error: path escapes the workspace"
    if not p.exists():
        return f"error: no such path: {path}"
    if p.is_file():
        return p.name
    entries = []
    base = _user_dir(user)
    for child in sorted(p.rglob("*")):
        rel = child.relative_to(base)
        entries.append(("/" if child.is_dir() else "") + str(rel))
        if len(entries) >= 500:
            entries.append("(truncated at 500 entries)")
            break
    return "\n".join(entries) or "(empty)"


def read_file(user, path: str) -> str:
    p = _safe_path(user, path)
    if p is None:
        return "error: path escapes the workspace"
    if not p.is_file():
        return f"error: no such file: {path}"
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError as exc:
        return f"error: {exc.__class__.__name__}"


def write_file(user, path: str, content: str) -> str:
    p = _safe_path(user, path)
    if p is None:
        return "error: path escapes the workspace"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {path}"


def dispatch(db, user, name: str, args: dict) -> str:
    if name == "save_memory":
        fact = MemoryFact(user_id=user.id, kind=args.get("kind", "fact"), content=args["content"].strip())
        db.add(fact)
        db.commit()
        return f"saved memory #{fact.id} ({fact.kind})"
    if name == "search_memory":
        q = args.get("query", "")
        rows = (
            db.query(MemoryFact)
            .filter(MemoryFact.user_id == user.id, MemoryFact.content.ilike(f"%{q}%"))
            .order_by(MemoryFact.created_at.desc())
            .limit(20)
            .all()
        )
        if not rows:
            return "(no matching memories)"
        return "\n".join(f"#{r.id} [{r.kind}] {r.content}" for r in rows)
    if name == "web_get":
        return web_get(args["url"])
    if name == "calculator":
        try:
            return calculator(args["expression"])
        except Exception:
            return "error: could not evaluate that expression"
    if name == "now":
        return datetime.now(timezone.utc).isoformat()
    if name == "list_files":
        return list_files(user, args.get("path", "."))
    if name == "read_file":
        return read_file(user, args["path"])
    if name == "write_file":
        return write_file(user, args["path"], args["content"])
    if name == "run_python":
        return run_python(user, args["code"])
    if name == "run_javascript":
        return run_javascript(user, args["code"])
    if name == "run_shell":
        return run_shell(user, args["command"])
    return f"error: unknown tool {name}"
