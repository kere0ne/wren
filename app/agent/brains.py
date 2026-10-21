import httpx

from ..core.config import settings

WORKERS_CHAIN = [
    "@cf/openai/gpt-oss-120b",
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
]


class ModelNotConfigured(Exception):
    pass


def _extract_message(data: dict) -> dict | None:
    if not isinstance(data, dict):
        return None
    result = data.get("result") if isinstance(data.get("result"), dict) else data
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message")
        if isinstance(msg, dict):
            return msg
    resp = result.get("response")
    if isinstance(resp, dict) and resp.get("message"):
        return resp["message"]
    if isinstance(resp, str):
        return {"role": "assistant", "content": resp}
    if isinstance(result.get("message"), dict):
        return result["message"]
    return None


def _workers_run(model: str, messages: list, tools: list | None) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CF_ACCOUNT_ID}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {settings.CF_API_TOKEN}"}
    body = {"messages": messages, "max_tokens": 8192}
    if tools:
        body["tools"] = tools
        resp = httpx.post(url, json=body, headers=headers, timeout=180)
        if resp.status_code >= 400:
            # Some models reject tool schemas; retry without them.
            body.pop("tools", None)
            resp = httpx.post(url, json=body, headers=headers, timeout=180)
    else:
        resp = httpx.post(url, json=body, headers=headers, timeout=180)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"non-json response ({resp.status_code})")
    if data.get("success") is False:
        raise RuntimeError(str(data.get("errors") or "workers-ai error"))
    msg = _extract_message(data)
    if not msg:
        raise RuntimeError("unrecognized workers-ai response shape")
    return msg


def _openai_compat(messages: list, tools: list | None) -> dict:
    body = {"model": settings.MODEL_NAME, "messages": messages}
    if tools:
        body["tools"] = tools
    resp = httpx.post(
        f"{settings.MODEL_BASE_URL}/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {settings.MODEL_API_KEY}"},
        timeout=180,
    )
    resp.raise_for_status()
    msg = _extract_message(resp.json())
    if not msg:
        raise RuntimeError("unrecognized response shape")
    return msg


def _ollama(messages: list) -> dict:
    resp = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={"model": settings.OLLAMA_MODEL, "messages": messages, "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    msg = resp.json().get("message")
    if not isinstance(msg, dict):
        raise RuntimeError("unrecognized ollama response shape")
    return msg


def chat_completion(messages: list, tools: list | None = None) -> dict:
    # Try every configured brain in order; return OpenAI-shaped output.
    errors = []
    if settings.CF_ACCOUNT_ID and settings.CF_API_TOKEN:
        for model in WORKERS_CHAIN:
            try:
                return {"choices": [{"message": _workers_run(model, messages, tools)}]}
            except Exception as exc:
                errors.append(f"workers-ai {model}: {exc}")
    if settings.MODEL_API_KEY:
        try:
            return {"choices": [{"message": _openai_compat(messages, tools)}]}
        except Exception as exc:
            errors.append(f"openai-compatible ({settings.MODEL_BASE_URL}): {exc}")
    if settings.OLLAMA_BASE_URL:
        try:
            return {"choices": [{"message": _ollama(messages)}]}
        except Exception as exc:
            errors.append(f"ollama: {exc}")
    if not (settings.CF_ACCOUNT_ID or settings.MODEL_API_KEY or settings.OLLAMA_BASE_URL):
        raise ModelNotConfigured(
            "No brain is configured on the server: set CF_ACCOUNT_ID + CF_API_TOKEN for the free Workers AI chain, or MODEL_API_KEY, or OLLAMA_BASE_URL."
        )
    raise RuntimeError("every brain failed: " + "; ".join(errors))
