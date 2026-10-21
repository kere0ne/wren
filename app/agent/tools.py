import ast
import json
import operator as op
import re
from datetime import datetime, timezone

import httpx

from ..core.config import settings
from ..models import MemoryFact

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
    return f"error: unknown tool {name}"
