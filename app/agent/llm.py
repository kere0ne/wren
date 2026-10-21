import httpx

from ..core.config import settings


class ModelNotConfigured(Exception):
    pass


def chat_completion(messages: list, tools: list | None = None) -> dict:
    if not settings.MODEL_API_KEY:
        raise ModelNotConfigured(
            "No model key is set on the server. Set MODEL_API_KEY (and optionally MODEL_BASE_URL / MODEL_NAME) in the backend environment."
        )
    body: dict = {"model": settings.MODEL_NAME, "messages": messages}
    if tools:
        body["tools"] = tools
    resp = httpx.post(
        f"{settings.MODEL_BASE_URL}/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {settings.MODEL_API_KEY}"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()
