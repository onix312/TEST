"""Project settings, durable task state and ChatGPT handoff for GameDev AI Office."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".gamedev-office") / "GameDevAIOffice"
SETTINGS = APP_DIR / "settings.json"
TASK_STATES = {"queued", "running", "ready", "merged", "conflict", "failed", "cancelled", "interrupted", "rolled_back"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as file:
        tmp = Path(file.name)
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.flush()
        os.fsync(file.fileno())
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def validate_project(value):
    if not str(value).strip():
        raise ValueError("Выбери папку Unity-проекта.")
    root = Path(value).expanduser().resolve()
    if not root.is_dir() or not (root / "Assets").is_dir() or not (root / "ProjectSettings").is_dir():
        raise ValueError("В папке Unity-проекта должны находиться Assets и ProjectSettings.")
    return root


def office_dir(root):
    return Path(root) / ".ai-office"


def prepare(root):
    folder = office_dir(root)
    for name in ("gdd", "logs", "reports", "checkpoints", "workspaces"):
        (folder / name).mkdir(parents=True, exist_ok=True)
    return folder


def resource_path(*parts):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).joinpath(*parts)


def detect_codex():
    return shutil.which("codex") or shutil.which("codex.cmd") or shutil.which("codex.exe") or "codex"


def detect_unity(root=None):
    names = []
    if root:
        version_file = Path(root) / "ProjectSettings" / "ProjectVersion.txt"
        try:
            version = next((line.split(":", 1)[1].strip() for line in
                            version_file.read_text(encoding="utf-8").splitlines()
                            if line.startswith("m_EditorVersion:")), "")
            if version:
                names.append(version)
        except OSError:
            pass
    for base in (os.getenv("PROGRAMFILES", ""), os.getenv("PROGRAMFILES(X86)", ""), r"C:\Program Files"):
        if not base:
            continue
        directory = Path(base) / "Unity" / "Hub" / "Editor"
        if directory.exists():
            try:
                names.extend(str(child.name) for child in directory.iterdir() if child.is_dir())
            except OSError:
                pass
            for version in dict.fromkeys(names):
                candidate = directory / version / "Editor" / "Unity.exe"
                if candidate.is_file():
                    return str(candidate)
    return ""


def load_settings():
    return read_json(SETTINGS, {"project": "", "unity": "", "codex": "codex", "workers": 2,
                                "auto_merge": True, "model": "gpt-5.1", "mini": False})


def save_settings(data):
    safe = {key: data.get(key) for key in
            ("project", "unity", "codex", "workers", "auto_merge", "model", "mini")}
    atomic_json(SETTINGS, safe)


class ProjectStore:
    """A project's history lives beside its game; Git is never required."""
    def __init__(self, root):
        self._mutex = threading.RLock()
        self.root = validate_project(root)
        self.folder = prepare(self.root)
        self.tasks_path = self.folder / "tasks.json"
        self.tasks = read_json(self.tasks_path, [])
        # Crashed agent processes are not resumed silently against an old snapshot.
        touched = False
        for task in self.tasks:
            if task["status"] == "running":
                task["status"] = "interrupted"
                task["error"] = "Приложение закрылось до завершения агента. Проверь рабочую копию."
                touched = True
        if touched:
            self.save()

    def save(self):
        with self._mutex:
            atomic_json(self.tasks_path, self.tasks)

    def add(self, prompt, depends=None, role="Developer"):
        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Описание задачи пустое.")
        dependencies = list(dict.fromkeys(depends or []))
        if any(not self.find(dep) for dep in dependencies):
            raise ValueError("Указана несуществующая зависимость.")
        task = dict(id=uuid.uuid4().hex[:12], text=prompt, role=role, depends=dependencies,
                    status="queued", created=now(), updated=now(), error="", summary="",
                    workspace="", changes=[], conflicts=[], checkpoint="")
        with self._mutex:
            self.tasks.append(task)
            self.save()
        return task

    def find(self, task_id):
        return next((item for item in self.tasks if item["id"] == task_id), None)

    def update(self, task_id, **fields):
        task = self.find(task_id)
        if not task:
            raise ValueError("Задача не найдена.")
        with self._mutex:
            task.update(fields, updated=now())
            self.save()
        return task

    def reset(self, task_id):
        task = self.find(task_id)
        if not task or task["status"] not in {"failed", "cancelled", "interrupted", "conflict"}:
            raise ValueError("Для повторного запуска выбери ошибочную или прерванную задачу.")
        return self.update(task_id, status="queued", changes=[], conflicts=[], error="", workspace="")

    def eligible(self):
        for task in self.tasks:
            if task["status"] != "queued":
                continue
            predecessors = [self.find(x) for x in task["depends"]]
            if all(prev and prev["status"] == "merged" for prev in predecessors):
                yield task

    def import_gdd(self, path):
        source = Path(path)
        if not source.is_file() or source.stat().st_size > 5_000_000:
            raise ValueError("GDD не найден или больше 5 МБ.")
        content = source.read_text(encoding="utf-8-sig")
        if not content.strip():
            raise ValueError("GDD пуст.")
        return self.approve_gdd(content)

    def approve_gdd(self, content):
        if not content.strip():
            raise ValueError("GDD пуст.")
        target = self.folder / "gdd" / "approved.md"
        if target.exists():
            prior = target.read_bytes()
            if prior != content.encode("utf-8"):
                name = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:5] + ".md"
                (self.folder / "gdd" / name).write_bytes(prior)
        target.write_text(content, encoding="utf-8")
        return target

    def gdd(self):
        target = self.folder / "gdd" / "approved.md"
        return target.read_text(encoding="utf-8") if target.exists() else ""

    def handoff(self):
        return (
            "Ты Game Designer игры, Unity — игровой движок. Мы продолжаем вести GDD "
            "в этом чате; решение считается утверждённым только после моего согласия. "
            "Подготовь только полный актуальный утверждённый GDD в Markdown, сохрани номера "
            "решений, явно пометь нерешённые вопросы. Не придумывай недостающие согласования. "
            "Я сохраню ответ в GameDev AI Office, после чего Codex реализует утверждённое. "
            "Если содержимого текущего чата недостаточно, скажи об этом вместо выдумывания."
        )
