import json
from datetime import datetime, timezone

from ..core.config import settings
from ..models import Message
from .brains import ModelNotConfigured, chat_completion
from .tools import TOOLS, dispatch

SYSTEM_TEMPLATE = (
    "You are Wren, the user's personal AI agent: a sharp, warm, proactive assistant "
    "that can also write and run real code.\n"
    "Today is {today} (UTC).\n"
    "Your tools:\n"
    "- memory: save_memory stores durable facts or preferences the user states; search_memory before claiming you don't know something about them.\n"
    "- web: web_get fetches a public page's readable text.\n"
    "- math/time: calculator, now.\n"
    "- workspace (a real directory per user): list_files, read_file, write_file, run_python, run_javascript, run_shell.\n"
    "When asked to build, fix, or analyze code: explore with list_files first (repos can be full monorepos with many packages), "
    "read files before editing them, make changes with write_file, then VERIFY by running the code or tests "
    "with run_python / run_javascript / run_shell, and iterate until it actually works. "
    "Prefer small, correct changes. Report honestly what you ran and what happened. "
    "Answer in the user's language. Keep replies short unless the task needs detail."
)


def build_history(db, thread_id: int) -> list:
    out = []
    for m in db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.id).all():
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            out.append({"role": "assistant", "content": m.content})
        elif m.role == "tool_call":
            tc = json.loads(m.content)
            out.append(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": tc["call_id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]},
                        }
                    ],
                }
            )
        elif m.role == "tool_result":
            meta = json.loads(m.meta or "{}")
            out.append({"role": "tool", "tool_call_id": meta.get("call_id"), "content": m.content})
    return out


def run_agent(db, user, thread, user_text: str, emit) -> None:
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    db.add(Message(thread_id=thread.id, role="user", content=user_text))
    db.commit()

    messages = [{"role": "system", "content": SYSTEM_TEMPLATE.format(today=today)}]
    messages += build_history(db, thread.id)

    try:
        for _ in range(settings.AGENT_MAX_STEPS):
            response = chat_completion(messages, tools=TOOLS)
            msg = response["choices"][0]["message"]
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                content = msg.get("content") or ""
                db.add(Message(thread_id=thread.id, role="assistant", content=content))
                db.commit()
                emit("done", {"content": content})
                return

            if msg.get("content"):
                emit("assistant", {"content": msg["content"]})

            llm_tool_calls = []
            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                emit("tool_call", {"name": name, "arguments": args})
                result = dispatch(db, user, name, args)
                db.add(
                    Message(
                        thread_id=thread.id,
                        role="tool_call",
                        content=json.dumps({"call_id": tc["id"], "name": name, "arguments": json.dumps(args)}),
                    )
                )
                db.add(
                    Message(
                        thread_id=thread.id,
                        role="tool_result",
                        content=result,
                        meta=json.dumps({"call_id": tc["id"]}),
                    )
                )
                db.commit()
                emit("tool_result", {"name": name, "content": result[:600]})
                llm_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                )
            messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": llm_tool_calls})
            for tc, call in zip(tool_calls, llm_tool_calls):
                result_row = (
                    db.query(Message)
                    .filter(Message.thread_id == thread.id, Message.role == "tool_result")
                    .order_by(Message.id.desc())
                    .first()
                )
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result_row.content})

        db.add(Message(thread_id=thread.id, role="assistant", content="(stopped: too many tool steps)"))
        db.commit()
        emit("error", {"message": "The agent stopped after too many tool steps."})
    except ModelNotConfigured as exc:
        emit("error", {"message": str(exc)})
    except Exception as exc:
        emit("error", {"message": f"Agent error: {exc.__class__.__name__}: {exc}"})
