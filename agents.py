"""Parallel Codex execution and dependency-aware local task dispatch."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from office_core import now
from workspaces import compute_changes, inspect_conflicts, integrate, provision

PROMPT = (
    "You are a Unity C# developer in an ISOLATED COPY of a game project. "
    "Read .ai-office/gdd/approved.md before editing. Implement only approved design; "
    "do not change the GDD or invent game rules. Only modify Assets/, Packages/, "
    "ProjectSettings/ and preserve Unity .meta files and their GUIDs. "
    "Never modify production paths outside this workspace. Do not install software, "
    "use network services, delete data, commit/push Git, or run Unity Editor. "
    "If requirements are unclear, report questions rather than guessing. "
    "Work autonomously on the scoped task, report what changed and what remains uncertain. "
    "Run narrow checks where feasible; do not start Unity Editor directly, because " 
    "the orchestration app handles Editor operations. Respond in Russian.\n\nTASK:\n"
)


def resolve_codex(command):
    value = str(command).strip() or "codex"
    found = shutil.which(value)
    if found:
        return found
    if Path(value).is_file():
        return str(Path(value).resolve())
    raise FileNotFoundError("Codex CLI не найден. Установи Codex и выполни codex login.")


def codex_args(executable, root, task):
    return [executable, "exec", "--json", "--skip-git-repo-check",
            "--sandbox", "workspace-write", "--cd", str(root), "-"]


class AgentManager(QObject):
    changed = Signal(str, str)
    activity = Signal(str, str)
    finished = Signal()

    def __init__(self, store, codex="codex", workers=2, auto_merge=True):
        super().__init__()
        self.store = store
        self.codex = codex
        self.workers = max(1, min(int(workers), 4))
        self.auto_merge = bool(auto_merge)
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.processes = {}
        self.thread = None

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def status(self, task_id, status, **fields):
        with self.lock:
            self.store.update(task_id, status=status, **fields)
        self.changed.emit(task_id, status)

    def log(self, task_id, message):
        self.activity.emit(task_id, str(message)[:900])

    def start(self):
        if self.running:
            return
        if not self.store.gdd().strip():
            raise ValueError("Сначала импортируй утверждённый GDD.")
        executable = resolve_codex(self.codex)
        self.cancel.clear()
        self.thread = threading.Thread(target=self._schedule, args=(executable,),
                                       daemon=True, name="AgentManager")
        self.thread.start()

    def stop(self):
        self.cancel.set()
        with self.lock:
            processes = list(self.processes.values())
        for process in processes:
            try:
                if process.poll() is None:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       timeout=10, check=False)
                    else:
                        process.terminate()
            except OSError:
                pass

    def _schedule(self, executable):
        active = {}
        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                while not self.cancel.is_set():
                    # New tasks are admitted as dependencies become merged.
                    with self.lock:
                        candidates = list(self.store.eligible())
                    for item in candidates[:max(0, self.workers - len(active))]:
                        if self.cancel.is_set():
                            break
                        task_id = item["id"]
                        self.status(task_id, "running")
                        active[pool.submit(self._run_agent, task_id, executable)] = task_id
                    if not active:
                        break
                    completed, _ = wait(active, timeout=.25, return_when=FIRST_COMPLETED)
                    for future in completed:
                        task_id = active.pop(future)
                        try:
                            future.result()
                        except Exception as exc:
                            self.status(task_id, "failed", error=str(exc))
                            self.log(task_id, "Agent failure: " + str(exc))
        finally:
            if self.cancel.is_set():
                with self.lock:
                    for task in self.store.tasks:
                        if task["status"] == "running":
                            self.store.update(task["id"], status="interrupted",
                                              error="Остановлено пользователем")
            self.finished.emit()

    def _run_agent(self, task_id, executable):
        task = self.store.find(task_id)
        try:
            workspace = provision(self.store.root, task_id, self.store.gdd())
            if self.cancel.is_set():
                self.status(task_id, "interrupted", workspace=str(workspace),
                            error="Остановлено после создания рабочей копии")
                return
            self.status(task_id, "running", workspace=str(workspace))
            logfile = self.store.folder / "logs" / (task_id + ".jsonl")
            argv = codex_args(executable, workspace, task["text"])
            self.log(task_id, "Workspace: " + str(workspace))
            summary = ""
            with logfile.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(argv, cwd=str(workspace), stdout=subprocess.PIPE,
                                           stdin=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                           encoding="utf-8", errors="replace", bufsize=1)
                process.stdin.write(PROMPT + task["text"])
                process.stdin.close()
                with self.lock:
                    self.processes[task_id] = process
                try:
                    for line in process.stdout:
                        log.write(line)
                        log.flush()
                        try:
                            data = json.loads(line)
                            event_type = data.get("type", "")
                            item = data.get("item", {})
                            if event_type == "item.completed" and isinstance(item, dict):
                                if item.get("type") == "agent_message":
                                    summary = item.get("text", "")[-8000:]
                            elif event_type == "turn.completed":
                                self.log(task_id, "Codex completed")
                            elif event_type in ("turn.failed", "error"):
                                self.log(task_id, str(data.get("error", data))[:500])
                        except json.JSONDecodeError:
                            if line.strip():
                                self.log(task_id, line.strip()[:300])
                    code = process.wait()
                finally:
                    with self.lock:
                        self.processes.pop(task_id, None)
            if self.cancel.is_set():
                self.status(task_id, "interrupted", summary=summary,
                            error="Прервано; рабочая копия сохранена")
                return
            if code != 0:
                self.status(task_id, "failed", summary=summary,
                            error="Codex exited with code " + str(code))
                return
            changes = compute_changes(self.store.root, task_id)
            if not changes:
                self.status(task_id, "merged", summary=summary or "Нет изменений файлов", changes=[])
                return
            conflicts = inspect_conflicts(self.store.root, changes)
            self.status(task_id, "ready", changes=changes, conflicts=conflicts, summary=summary)
            if conflicts:
                self.status(task_id, "conflict", error="\n".join(conflicts))
                return
            if self.auto_merge:
                backup, conflict = integrate(self.store.root, task_id, changes)
                if conflict:
                    self.status(task_id, "conflict", conflicts=conflict, error="\n".join(conflict))
                else:
                    self.status(task_id, "merged", checkpoint=str(backup or ""),
                                summary=summary or "Изменения интегрированы")
                    self.log(task_id, "Merged " + str(len(changes)) + " files")
        except Exception as exc:
            self.status(task_id, "interrupted" if self.cancel.is_set() else "failed", error=str(exc))
            self.log(task_id, str(exc))

    def approve(self, task_id, *, allow_deletions=False):
        task = self.store.find(task_id)
        if not task or task["status"] not in {"ready", "conflict"}:
            raise ValueError("Для применения выбери готовую задачу.")
        backup, conflicts = integrate(self.store.root, task_id, task["changes"],
                                      allow_deletions=allow_deletions)
        if conflicts:
            self.status(task_id, "conflict", conflicts=conflicts, error="\n".join(conflicts))
            raise ValueError("Конфликт с актуальным проектом:\n" + "\n".join(conflicts))
        self.status(task_id, "merged", checkpoint=str(backup or ""), conflicts=[], error="")
        return backup
