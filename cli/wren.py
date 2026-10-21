#!/usr/bin/env python3
"""Wren CLI: your AI agent in the terminal.

Usage:
  python cli/wren.py login
  python cli/wren.py chat
  python cli/wren.py run "fix the failing test"
"""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path

import httpx

CONFIG_DIR = Path.home() / ".wren"
TOKEN_FILE = CONFIG_DIR / "token"


def base_url():
    return os.getenv("WREN_URL", "http://localhost:8000")


def save_token(token):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)


def load_token():
    return TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None


def cmd_login(args):
    email = input("email: ").strip()
    password = getpass.getpass("password: ")
    with httpx.Client(base_url=base_url(), timeout=30) as c:
        r = c.post("/api/auth/login", json={"email": email, "password": password})
        if r.status_code == 401:
            create = input("no account with that email. create one? [y/N] ")
            if create.strip().lower().startswith("y"):
                r = c.post("/api/auth/register", json={"email": email, "password": password})
        if r.status_code != 200:
            print(f"login failed: {r.status_code} {r.text.strip()}")
            sys.exit(1)
        save_token(r.json()["token"])
        print(f"signed in as {r.json()['email']}")


def ensure_thread(c, thread_id):
    if thread_id:
        return thread_id
    r = c.post("/api/threads", json={})
    r.raise_for_status()
    return r.json()["id"]


def stream(c, thread_id, message):
    events = []
    with c.stream("POST", f"/api/threads/{thread_id}/stream", json={"message": message}) as r:
        r.raise_for_status()
        buf = ""
        for chunk in r.iter_text():
            buf += chunk
            parts = buf.split("\n\n")
            buf = parts.pop()
            for part in parts:
                line = next((l for l in part.split("\n") if l.startswith("data: ")), None)
                if line:
                    events.append(json.loads(line[len("data: "):]))
    return events


def print_events(events):
    for ev in events:
        kind = ev.get("type")
        if kind == "assistant":
            print(ev.get("content") or "")
        elif kind == "tool_call":
            print(f"  [{ev['name']}] running...")
        elif kind == "tool_result":
            text = ev["content"].replace("\n", "\n    ")
            print(f"  [{ev['name']}] {text[:300]}")
        elif kind == "error":
            print(f"error: {ev['message']}", file=sys.stderr)
    last = next((e for e in reversed(events) if e.get("type") == "done"), None)
    if last and last.get("content"):
        print(last["content"])


def cmd_chat(args):
    if not load_token():
        print("not signed in. run: wren login")
        sys.exit(1)
    with httpx.Client(base_url=base_url(), timeout=300, headers={"Authorization": f"Bearer {load_token()}"}) as c:
        thread_id = ensure_thread(c, args.thread)
        print(f"thread {thread_id} - type your message, ctrl-c to exit")
        while True:
            try:
                message = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if not message:
                continue
            print_events(stream(c, thread_id, message))


def cmd_run(args):
    if not load_token():
        print("not signed in. run: wren login")
        sys.exit(1)
    with httpx.Client(base_url=base_url(), timeout=300, headers={"Authorization": f"Bearer {load_token()}"}) as c:
        thread_id = ensure_thread(c, args.thread)
        print_events(stream(c, thread_id, " ".join(args.task)))


def main():
    p = argparse.ArgumentParser(prog="wren", description="Wren CLI: your AI agent in the terminal")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="sign in or create an account")
    chat = sub.add_parser("chat", help="interactive chat")
    chat.add_argument("--thread", type=int, default=None)
    run = sub.add_parser("run", help="one-shot: give the agent a task")
    run.add_argument("task", nargs="+")
    run.add_argument("--thread", type=int, default=None)
    args = p.parse_args()
    {"login": cmd_login, "chat": cmd_chat, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
