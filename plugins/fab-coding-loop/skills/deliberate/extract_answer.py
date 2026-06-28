#!/usr/bin/env python3
"""Extract the clean assistant answer from a `fab-agent-runtime call ... consult` reply.

The runtime wraps each agent's *entire pi/claude session* (a JSONL event stream) inside
`parts[].text`. The clean final answer is the `result` field of the trailing
`{"type":"result", ...}` event — NOT the whole blob. Appending the raw blob to the team
channel (a) pollutes `<recent_blackboard>` injected into later consults (→ context overflow)
and (b) overflows the libSQL append size. This pulls out just the answer.

Usage:
    fab-agent-runtime call <url> consult "..." --output-format json | extract_answer.py
Exit 0 with the answer on stdout; prints nothing and exits 3 if the agent produced an
empty result (model error / context overflow → treat as a failed consult upstream).
"""

from __future__ import annotations

import json
import sys


def _events_text(raw: str) -> str:
    """Return the embedded JSONL session text, whether the outer payload is the
    `{"skill","parts":[...]}` json envelope or already the bare JSONL stream (text mode)."""
    raw = raw.strip()
    if not raw:
        return ""
    if raw[0] == "{":
        try:
            outer = json.loads(raw)
        except json.JSONDecodeError:
            return raw  # already bare JSONL
        if isinstance(outer, dict) and "parts" in outer:
            return "".join(
                p.get("text", "")
                for p in outer.get("parts", [])
                if p.get("type") == "text"
            )
    return raw


def extract(raw: str) -> str:
    text = _events_text(raw)
    # Lean path (mesh-consult): parts[].text is already the clean prose answer,
    # not a pi JSONL session. If it has no JSONL event lines, return it as-is.
    has_jsonl = any(
        ln.strip().startswith('{"type"') or ln.strip().startswith("{'type'")
        for ln in text.splitlines()
    )
    if not has_jsonl:
        return text.strip()

    # Legacy path (pi-fab-agent-runtime): unwrap the JSONL session -> final result.
    result = ""
    last_assistant = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] != "{":
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "result" and ev.get("result"):
            result = ev["result"]
        elif t == "message_start":
            msg = ev.get("message", {})
            if msg.get("role") == "assistant":
                for c in msg.get("content", []):
                    if c.get("type") == "text" and c.get("text"):
                        last_assistant = c["text"]
    return (result or last_assistant).strip()


if __name__ == "__main__":
    ans = extract(sys.stdin.read())
    if not ans:
        sys.exit(3)
    print(ans)
