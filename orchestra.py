"""Local multi-model orchestrator: ChatGPT researchers + Codex Unity developers.

A text-only model never writes Unity source. Its persisted result is delivered
as dependency context to Codex, which edits isolated copies of the project.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from agents import AgentManager, resolve_codex
from director import invoke_model
from model_routing import (
    BALANCED, DEEP, FAST, classify, has_api_key, report_prompt,
    reviewer_prompt, review_verdict,
)
from workspaces import file_preview


class ModelOrchestrator(AgentManager):
    def __init__(self, store, codex="codex", workers=2, auto_merge=True, *,
                 api_key=None, models=None, review_enabled=False):
        super().__init__(store, codex, workers, auto_merge)
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self.models = {
            "fast": FAST, "balanced": BALANCED, "deep": DEEP, "review": BALANCED
        }
        self.models.update({k: v for k, v in (models or {}).items() if v and k in self.models})
        self.review_enabled = bool(review_enabled)

    def start(self):
        if self.running:
            return
        if not self.store.gdd().strip():
            raise ValueError("Сначала утверди GDD, прежде чем запускать оркестр.")
        self.cancel.clear()
        # Codex is resolved lazily: all-ChatGPT queues work without the CLI.
        self.thread = threading.Thread(target=self._schedule, args=(None,), daemon=True,
                                       name="ModelOrchestrator")
        self.thread.start()

    def _run_agent(self, task_id, executable):
        task = self.store.find(task_id)
        route = task.get("route") or "auto"
        backend, model, reason = classify(task["text"], route, self.models)
        self.status(task_id, "running", backend=backend, model=model)
        self.log(task_id, model + ": " + reason)
        if backend == "codex":
            try:
                executable = resolve_codex(self.codex)
            except Exception as exc:
                self.status(task_id, "failed", error=str(exc))
                return
            super()._run_agent(task_id, executable)
        else:
            self._run_text_agent(task_id, model)

    def _run_text_agent(self, task_id, model):
        task = self.store.find(task_id)
        if self.cancel.is_set():
            self.status(task_id, "interrupted", error="Отменено до обращения к ChatGPT")
            return
        if not has_api_key(self.api_key):
            self.status(task_id, "handoff", error=(
                "Для автоматического ChatGPT нужен OpenAI API key. "
                "Можно отправить задачу в существующий чат вручную и вставить ответ."))
            self.log(task_id, "Ожидается ручная передача задачи в ChatGPT.")
            return
        prompt = report_prompt(self.store, task)
        self.log(task_id, "ChatGPT " + model + ": подготовка текстового результата")
        result = invoke_model(
            model,
            "You are one assistant in a multi-model Unity game development office. "
            "Perform a narrow read-only research/writing/analysis task. Follow "
            "the approved GDD, and pass usable findings to the Codex developer.",
            prompt,
            api_key=self.api_key,
            max_output_tokens=2800,
        )
        if self.cancel.is_set():
            self.status(task_id, "interrupted", error="Остановлено; ответ не был принят")
            return
        self.finish_text_task(task_id, result, model=model)

    def finish_text_task(self, task_id, answer, *, model=None):
        """Also used for answers pasted back from the existing ChatGPT conversation."""
        task = self.store.find(task_id)
        if not task or task.get("status") not in {"handoff", "running"}:
            raise ValueError("Ответ можно принять только для ожидающей ChatGPT-задачи.")
        if not answer or not answer.strip():
            raise ValueError("ChatGPT не вернул содержательного ответа.")
        report = self.store.folder / "reports" / (task_id + "-chatgpt.md")
        report.write_text(answer, encoding="utf-8")
        self.status(task_id, "merged", backend="chatgpt",
                    model=model or task.get("model") or FAST,
                    summary=answer[:32000], error="", report=str(report),
                    review="Текстовый результат; Unity-файлы не изменялись.")
        self.log(task_id, "Отчёт сохранён: " + str(report))

    def handoff_prompt(self, task_id):
        task = self.store.find(task_id)
        if not task or task.get("status") not in {"handoff", "queued", "failed"}:
            raise ValueError("Выбери текстовую задачу ChatGPT.")
        backend, _, _ = classify(task["text"], task.get("route", "auto"), self.models)
        if backend != "chatgpt":
            raise ValueError("Выбрана задача для Codex, а не ChatGPT.")
        return report_prompt(self.store, task)

    def review_before_merge(self, task_id, changes):
        if not self.review_enabled:
            return True
        task = self.store.find(task_id)
        if not self.api_key:
            self.status(task_id, "ready", review="AI-ревью недоступно: нет API key.",
                        error="Автоприменение остановлено до ручной проверки.")
            self.log(task_id, "Нужна ручная проверка: API key для модели-ревью не задан.")
            return False
        model = self.models["review"]
        self.log(task_id, "ChatGPT " + model + ": независимое ревью изменений...")
        try:
            preview = file_preview(self.store.root, task_id, changes, max_lines=100)
            response = invoke_model(
                model,
                "You are an independent read-only code reviewer for a Unity project.",
                reviewer_prompt(self.store, task, preview),
                api_key=self.api_key,
                max_output_tokens=1300,
            )
        except Exception as exc:
            self.status(task_id, "ready", review="AI-ревью не удалось: " + str(exc),
                        error="Автоприменение остановлено; можно проверить изменения вручную.")
            return False
        self.status(task_id, "ready", review=response[:12000])
        if not review_verdict(response):
            self.log(task_id, "Ревью не одобрило автоматическое применение.")
            return False
        self.log(task_id, "AI-ревью: APPROVE. Изменения всё равно требуют Unity-проверки.")
        return True
