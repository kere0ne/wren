import pytest

from app.agent import brains
from app.core.config import settings


class FakeResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _set_cf(monkeypatch, account="acc", token="tok"):
    monkeypatch.setattr(settings, "CF_ACCOUNT_ID", account)
    monkeypatch.setattr(settings, "CF_API_TOKEN", token)
    monkeypatch.setattr(settings, "MODEL_API_KEY", "")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "")


def test_workers_chain_falls_back_to_second_model(monkeypatch):
    _set_cf(monkeypatch)
    urls = []

    def fake_post(url, **kw):
        urls.append(url)

        class R:
            status_code = 200

            def json(self):
                if "gpt-oss" in url:
                    return {"success": False, "errors": ["model exploded"]}
                return {"success": True, "result": {"response": "hi from llama"}}

        return R()

    monkeypatch.setattr(brains.httpx, "post", fake_post)
    out = brains.chat_completion([{"role": "user", "content": "hi"}])
    assert "gpt-oss" in urls[0] and "llama-3.3" in urls[1]
    assert out["choices"][0]["message"]["content"] == "hi from llama"


def test_workers_retries_without_tools_on_rejection(monkeypatch):
    _set_cf(monkeypatch)
    bodies = []

    class R:
        def __init__(self, bad):
            self.status_code = 400 if bad else 200
            self._bad = bad

        def json(self):
            if self._bad:
                return {"success": False, "errors": ["bad tools"]}
            return {"success": True, "result": {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}}

    def fake_post(url, json=None, **kw):
        bodies.append(dict(json) if json else json)
        return R("tools" in (json or {}))

    monkeypatch.setattr(brains.httpx, "post", fake_post)
    tools = [{"type": "function", "function": {"name": "x", "parameters": {}}}]
    out = brains.chat_completion([{"role": "user", "content": "hi"}], tools=tools)
    assert "tools" in bodies[0] and "tools" not in bodies[1]
    assert out["choices"][0]["message"]["content"] == "ok"


def test_falls_back_to_openai_compatible(monkeypatch):
    _set_cf(monkeypatch)

    def fake_post(url, **kw):
        assert "/chat/completions" in url

        class R(FakeResp):
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"role": "assistant", "content": "from openai"}}]}

        return R()

    monkeypatch.setattr(settings, "MODEL_API_KEY", "k")
    monkeypatch.setattr(brains.httpx, "post", fake_post)
    out = brains.chat_completion([{"role": "user", "content": "hi"}])
    assert out["choices"][0]["message"]["content"] == "from openai"


def test_no_brain_configured(monkeypatch):
    _set_cf(monkeypatch, account="", token="")
    with pytest.raises(brains.ModelNotConfigured):
        brains.chat_completion([{"role": "user", "content": "hi"}])
