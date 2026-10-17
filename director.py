"""Optional OpenAI API Game Designer / task planner. Existing ChatGPT chats are not accessible."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from office_core import atomic_json, read_json

ENDPOINT = "https://api.openai.com/v1/responses"


def extract_text(payload):
    if payload.get("output_text"):
        return payload["output_text"]
    parts = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts)


def chat(model, messages, gdd="", *, purpose="design"):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Для встроенного Game Designer нужен OPENAI_API_KEY. "
                           "Либо используй существующий чат ChatGPT и импорт GDD вручную.")
    if purpose == "planning":
        instructions = (
            "You are a game-development project planner. Do not add game design decisions. "
            "Split the user's approved request into up to six independent implementation tasks "
            "for Unity Codex agents. Return only JSON: "
            '{"tasks":[{"title":"task text","depends":[0]}]}. '
            "depends is a list of ZERO-BASED indexes of earlier tasks, "
            "no duplicate indexes. Return no Markdown."
        )
    else:
        instructions = (
            "You are Game Designer for a Unity game. Ask clarifying questions ONE AT A TIME, "
            "make concrete choices and maintain an approved GDD. New mechanics are proposals "
            "until the user explicitly approves them. Distinguish proposals from accepted "
            "decisions. Respond in Russian. Existing approved GDD:\n" + gdd[:45000]
        )
    body = {"model": model or "gpt-5.1",
            "instructions": instructions,
            "input": [{"role": m["role"], "content": m["content"][:12000]}
                      for m in messages[-16:]],
            "max_output_tokens": 2500}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(ENDPOINT, data=data, method="POST",
                                     headers={"Authorization": "Bearer " + key,
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1200).decode("utf-8", errors="replace")
        raise RuntimeError("OpenAI API HTTP " + str(exc.code) + ": " + detail) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Не удалось связаться с OpenAI: " + str(exc.reason)) from exc
    answer = extract_text(payload)
    if not answer.strip():
        raise RuntimeError("OpenAI не вернул текст ответа.")
    return answer


def make_plan(model, gdd, task):
    if not gdd.strip():
        raise ValueError("Нет утверждённого GDD для планирования.")
    raw = chat(model, [{"role": "user",
                        "content": "APPROVED GDD:\n" + gdd[:35000] + "\nREQUEST:\n" + task}],
               gdd, purpose="planning")
    return parse_plan(raw)


def parse_plan(raw):
    stripped = raw.strip()
    if stripped.startswith(chr(96) * 3):
        stripped = "\n".join(stripped.splitlines()[1:-1])
    plan = json.loads(stripped)
    result = plan.get("tasks", [])
    if not isinstance(result, list) or not 1 <= len(result) <= 6:
        raise ValueError("План должен содержать 1–6 задач.")
    parsed = []
    for index, item in enumerate(result):
        title = item.get("title", "")
        depends = item.get("depends", [])
        if not isinstance(title, str) or not title.strip() or len(title) > 8000:
            raise ValueError("Некорректная задача в плане.")
        if not isinstance(depends, list) or any(type(dep) is not int or dep < 0 or dep >= index for dep in depends):
            raise ValueError("Недопустимая зависимость в плане.")
        parsed.append((title, list(dict.fromkeys(depends))))
    return parsed


class DesignerHistory:
    def __init__(self, store):
        self.path = store.folder / "designer-chat.json"
        self.messages = read_json(self.path, [])

    def add(self, role, content):
        self.messages.append({"role": role, "content": content})
        atomic_json(self.path, self.messages)
