"""Local-model adapters for GEPA on Strix Halo.

GEPA's `reflection_lm` / `task_lm` accept EITHER a litellm model-id string
(needs `litellm` + a cloud key) OR a plain callable. This module gives you
callables wired to the local llama-server on :8002 (the coder model started
via `startup llm/mtp`), so GEPA runs fully offline on this box.

- `local_reflection_lm(prompt) -> str`   : single-prompt callable for reflection_lm
- `local_chat_lm`                          : ChatCompletionCallable for task_lm (DefaultAdapter)

Reflection is the quality-critical role — give it a generous token budget
(Qwen3.x is a thinking model; too small a budget and the trace eats it all,
returning empty content). Mirrors the strix-llama wrapper rationale.
"""

from __future__ import annotations

import json
import os
import urllib.request

LLAMA_BASE = os.environ.get("GEPA_LLAMA_BASE", "http://127.0.0.1:8002/v1")
REFLECT_MAX_TOKENS = int(os.environ.get("GEPA_REFLECT_MAX_TOKENS", "8192"))
TASK_MAX_TOKENS = int(os.environ.get("GEPA_TASK_MAX_TOKENS", "4096"))


def _chat(messages: list[dict], max_tokens: int, temperature: float = 0.7) -> str:
    payload = {
        "model": os.environ.get("GEPA_MODEL", "local"),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        f"{LLAMA_BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.load(resp)
    msg = body["choices"][0]["message"]
    # Qwen3.x thinking models may put the answer in reasoning_content if content is empty.
    return msg.get("content") or msg.get("reasoning_content") or ""


def local_reflection_lm(prompt: str) -> str:
    """reflection_lm callable: GEPA passes one big diagnostic prompt, expects text back."""
    return _chat(
        [{"role": "user", "content": prompt}],
        max_tokens=REFLECT_MAX_TOKENS,
        temperature=1.0,  # reflection benefits from exploration
    )


def local_chat_lm(messages, **kwargs) -> str:
    """task_lm ChatCompletionCallable for gepa's DefaultAdapter.

    DefaultAdapter calls task_lm(messages) where messages is an OpenAI-style list.
    """
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    return _chat(
        messages, max_tokens=TASK_MAX_TOKENS, temperature=kwargs.get("temperature", 0.0)
    )


if __name__ == "__main__":
    # Smoke test — requires `startup llm/mtp` running on :8002.
    print(
        "reflection_lm ->", local_reflection_lm("Reply with the single word: OK")[:200]
    )
