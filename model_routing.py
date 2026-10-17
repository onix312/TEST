"""Model/task routing policy for local Unity orchestration.

ChatGPT tasks are deliberately read-only. They produce local reports for Codex
dependencies, never touch Unity sources or approve new GDD decisions.
"""
from __future__ import annotations

import os
import re

FAST = "gpt-6-luna"
BALANCED = "gpt-6.1-sol"
DEEP = "gpt-6-astra"

ROUTES = {
    "auto": "Авто — подбирает исполнитель",
    "chatgpt_fast": "ChatGPT • Luna — простые задачи",
    "chatgpt_balanced": "ChatGPT • Sol — анализ и план",
    "chatgpt_deep": "ChatGPT • Astra — сложная аналитика",
    "codex": "Codex • изменение Unity-проекта",
}

# Classifier errs towards Codex for any plausible file-system edit.
EDIT_WORDS = (
    "реализ", "напиши код", "созда" , "исправ", "измен", "добав", "удал",
    "перепиш", "передел", "внедр", "подключ", "собер", "запуст", "настро",
    "скрипт", "prefab", "префаб", "assets/", ".cs", ".unity", "unity editor",
    "сцен", "компиляц", "build", "обнови файл", "перемести", "переименуй файл",
    "implement", "fix", "build", "script", "write code", "modify", "edit file",
)
TEXT_WORDS = (
    "объясни", "предложи", "список", "описани", "придумай", "идеи", "сравни",
    "проанализ", "резюме", "кратко", "проверь текст", "документ", "названия",
    "вариант", "план", "разбей", "формулиров", "спецификац", "таблиц", "диалог",
    "выбери", "опиши", "подбери", "summarize", "plan", "describe", "brainstorm",
)
HARD_WORDS = ("архитектур", "баланс", "экономик", "системн", "сложн", "риск",
              "зависимост", "критическ", "производитель", "многопользователь")


def has_api_key(key=None):
    return bool((key or os.getenv("OPENAI_API_KEY") or "").strip())


def classify(task_text, route="auto", models=None):
    """Returns (backend, model, reason). No network/model inference needed."""
    models = models or {}
    if route not in ROUTES:
        raise ValueError("Unknown execution route: " + str(route))
    if route == "codex":
        return "codex", "Codex CLI", "Выбран исполнитель Unity/Codex."
    chosen = {
        "chatgpt_fast": models.get("fast") or FAST,
        "chatgpt_balanced": models.get("balanced") or BALANCED,
        "chatgpt_deep": models.get("deep") or DEEP,
    }
    if route in chosen:
        return "chatgpt", chosen[route], "Задача с текстовым результатом, без доступа к файлам."
    phrase = task_text.lower()
    # A real code/data change is never sent to a text-only model by AUTO.
    if any(word in phrase for word in EDIT_WORDS):
        return "codex", "Codex CLI", "Задача может менять проект Unity."
    if not any(word in phrase for word in TEXT_WORDS):
        return "codex", "Codex CLI", "Неоднозначная задача: безопасный маршрут Codex."
    if len(phrase) > 700 or any(word in phrase for word in HARD_WORDS):
        return "chatgpt", chosen["chatgpt_balanced"], "Текстовый анализ средней сложности."
    return "chatgpt", chosen["chatgpt_fast"], "Простая текстовая задача."


def dependency_notes(store, task, max_chars=16000):
    notes = []
    for dependency_id in task.get("depends", []):
        preceding = store.find(dependency_id)
        if not preceding or preceding.get("status") != "merged":
            raise RuntimeError("Предыдущая задача не завершена.")
        result = (preceding.get("summary") or "").strip()
        if result:
            notes.append("Задача " + dependency_id + ":\n" + result[:6000])
    return "\n\n".join(notes)[:max_chars]


def report_prompt(store, task):
    context = dependency_notes(store, task)
    return (
        "You are a helpful game development assistant working under an APPROVED "
        "Unity GDD. Complete a narrowly-scoped TEXT-ONLY task in Russian. "
        "Do not claim to have modified local files, run tests or accessed Unity. "
        "Do not invent approved mechanics. If design needs approval, explicitly "
        "mark it as a proposal, not an accepted decision. Give a concrete result "
        "that Codex can use in a subsequent development task.\n\n"
        "APPROVED GDD:\n" + store.gdd()[:30000] +
        "\n\nDEPENDENCY RESULTS:\n" + (context or "(none)") +
        "\n\nTASK:\n" + task["text"]
    )


def reviewer_prompt(store, task, preview):
    return (
        "You are a read-only Unity C# quality reviewer. Compare the changes "
        "to the approved GDD and requested task. You cannot execute code and "
        "must NOT claim a test passed. Return FIRST LINE exactly APPROVE or BLOCK. "
        "On subsequent lines explain specific risks, missing requirements, "
        "unsafe changes, or recommended focused tests. BLOCK only for a "
        "concrete substantive issue; don't block for missing execution access.\n\n"
        "GDD:\n" + store.gdd()[:18000] +
        "\n\nTASK:\n" + task["text"][:6000] +
        "\n\nPROPOSED CHANGES:\n" + preview[:25000]
    )


def review_verdict(text):
    first = text.lstrip().splitlines()[0].strip().upper() if text.strip() else ""
    if first == "APPROVE":
        return True
    if first == "BLOCK":
        return False
    return False
