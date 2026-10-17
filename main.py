"""GameDev AI Office: simple local Unity + Codex workbench (Windows)."""
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from safety import checkpoint
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget)

SETTINGS = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "GameDevAIOffice" / "settings.json"


def validate_project(path):
    root = Path(path).expanduser().resolve()
    if not (root / "Assets").is_dir() or not (root / "ProjectSettings").is_dir():
        raise ValueError("Select a Unity project directory containing Assets and ProjectSettings.")
    return root


def prepare(root):
    office = root / ".ai-office"
    for name in ("gdd", "logs", "reports"):
        (office / name).mkdir(parents=True, exist_ok=True)
    return office


def codex_args(executable, root, task):
    gdd = root / ".ai-office" / "gdd" / "approved.md"
    instruction = ("You are working on a local Unity project. "
        "Read the approved GDD when available; do not change its approved game design. "
        "Do not delete data, install software or commit or push to git. "
        "Make scoped changes and run focused checks. Report in Russian.\n")
    if gdd.exists():
        instruction += "Read approved GDD at: " + str(gdd) + "\n"
    return [executable, "exec", "--json", "--skip-git-repo-check", "--sandbox", "workspace-write", "--cd", str(root), instruction + task]


class Events(QObject):
    event = Signal(str)


class Office(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GameDev AI Office — Unity + Codex")
        self.resize(1000, 700)
        self.events = Events()
        self.events.event.connect(self.write_log)
        self.jobs = []
        self.process = None
        self.active = False
        try:
            prefs = json.loads(SETTINGS.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prefs = {}
        panel = QWidget()
        self.setCentralWidget(panel)
        box = QVBoxLayout(panel)
        header = QLabel("GAMEDEV AI OFFICE")
        header.setStyleSheet("font-size:26px;font-weight:bold")
        box.addWidget(header)
        box.addWidget(QLabel("ChatGPT Game Designer → Approved GDD → Codex → Unity"))
        self.project = QLineEdit(prefs.get("project", ""))
        self.unity = QLineEdit(prefs.get("unity", ""))
        self.codex = QLineEdit(prefs.get("codex", "codex"))
        for label, field, callback in (
            ("Unity project", self.project, self.pick_project),
            ("Unity.exe", self.unity, self.pick_unity),
            ("Codex command", self.codex, None),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(field)
            if callback:
                button = QPushButton("Browse")
                button.clicked.connect(callback)
                row.addWidget(button)
            box.addLayout(row)
        row = QHBoxLayout()
        for caption, callback in (("Save", self.save), ("Import GDD", self.import_gdd),
                                  ("Unity EditMode tests", self.unity_tests)):
            button = QPushButton(caption)
            button.clicked.connect(callback)
            row.addWidget(button)
        box.addLayout(row)
        self.task = QTextEdit()
        self.task.setPlaceholderText("Task for Codex based on approved GDD...")
        self.task.setMaximumHeight(110)
        box.addWidget(self.task)
        row = QHBoxLayout()
        for label, cb in (("Queue task", self.queue), ("Run queue", self.run), ("Stop", self.stop)):
            button = QPushButton(label)
            button.clicked.connect(cb)
            row.addWidget(button)
        box.addLayout(row)
        self.listing = QListWidget()
        box.addWidget(self.listing)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        box.addWidget(self.log)
        self.setStyleSheet(
            "QWidget{background:#18141f;color:#eee6f5;font:12pt Segoe UI;}"
            "QLineEdit,QTextEdit,QListWidget{background:#292335;border:1px solid #574675;"
            "border-radius:7px;padding:8px;}"
            "QPushButton{background:#7653b9;border:0;border-radius:7px;padding:9px;}"
            "QPushButton:hover{background:#9171cf;}")
        self.write_log("Choose a Unity project, import approved GDD, queue a task.")

    def write_log(self, value):
        self.log.append(str(value)[:1500])

    def pick_project(self):
        path = QFileDialog.getExistingDirectory(self, "Unity project")
        if path:
            self.project.setText(path)

    def pick_unity(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Unity.exe", "", "Executable (*.exe)")
        if path:
            self.unity.setText(path)

    def save(self):
        try:
            root = validate_project(self.project.text())
            prepare(root)
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps({"project": str(root),
                "unity": self.unity.text(), "codex": self.codex.text()}, indent=2),
                encoding="utf-8")
            return root
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Project setup", str(exc))
            return None

    def import_gdd(self):
        root = self.save()
        if root is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Approved GDD", "", "Markdown (*.md *.txt)")
        if not path:
            return
        source = Path(path)
        try:
            if source.stat().st_size > 5_000_000:
                raise ValueError("GDD exceeds 5 MB")
            target = prepare(root) / "gdd" / "approved.md"
            target.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
            self.write_log("Imported approved GDD: " + str(target))
        except (ValueError, UnicodeError, OSError) as exc:
            QMessageBox.warning(self, "GDD", str(exc))

    def queue(self):
        if self.save() is None:
            return
        title = self.task.toPlainText().strip()
        if title:
            self.jobs.append(title)
            self.listing.addItem("Queued: " + title[:100])
            self.task.clear()

    def run(self):
        root = self.save()
        if root is None or self.active or not self.jobs:
            return
        executable = self.codex.text().strip() or "codex"
        resolved = shutil.which(executable) or shutil.which(executable + ".cmd")
        if not resolved and not Path(executable).is_file():
            QMessageBox.warning(self, "Codex", "Install Codex CLI and run codex login first.")
            return
        if not (root / ".ai-office" / "gdd" / "approved.md").exists():
            QMessageBox.warning(self, "GDD", "Import approved GDD before running tasks.")
            return
        self.active = True
        threading.Thread(target=self.run_worker, args=(root, resolved or executable), daemon=True).start()

    def run_worker(self, root, executable):
        while self.jobs and self.active:
            title = self.jobs.pop(0)
            self.events.event.emit("Preparing checkpoint: " + title[:100])
            try:
                backup = checkpoint(root)
                self.events.event.emit("Checkpoint saved: " + str(backup))
            except (OSError, ValueError) as exc:
                self.events.event.emit("Cannot start without checkpoint: " + str(exc))
                break
            self.events.event.emit("Starting: " + title[:100])
            log_path = prepare(root) / "logs" / "codex.jsonl"
            try:
                with log_path.open("a", encoding="utf-8") as log:
                    self.process = subprocess.Popen(codex_args(executable, root, title),
                        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace")
                    for line in self.process.stdout:
                        log.write(line)
                        try:
                            event = json.loads(line)
                            if event.get("type") in ("turn.completed", "turn.failed", "error"):
                                self.events.event.emit(str(event))
                        except ValueError:
                            self.events.event.emit(line.strip())
                    result = self.process.wait()
                self.events.event.emit("Finished: exit code " + str(result))
                if result != 0:
                    self.events.event.emit("Stopped queue after failed task; check partial changes.")
                    break
            except OSError as exc:
                self.events.event.emit("Error: " + str(exc))
                break
            finally:
                self.process = None
        self.active = False
        self.events.event.emit("Queue finished")

    def stop(self):
        self.active = False
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def unity_tests(self):
        root = self.save()
        if root is None:
            return
        exe = Path(self.unity.text())
        if not exe.is_file():
            QMessageBox.warning(self, "Unity", "Select Unity.exe first")
            return
        if QMessageBox.question(self, "Unity tests",
            "Close this project in Unity Editor first. Run tests?") != QMessageBox.StandardButton.Yes:
            return
        folder = prepare(root) / "reports"
        cmd = [str(exe), "-batchmode", "-nographics", "-runTests",
               "-testPlatform", "EditMode", "-projectPath", str(root),
               "-testResults", str(folder / "tests.xml"), "-logFile", str(folder / "editor.log")]
        try:
            subprocess.Popen(cmd, cwd=root)
            self.write_log("Unity tests launched; see .ai-office/reports")
        except OSError as exc:
            QMessageBox.warning(self, "Unity", str(exc))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    office = Office()
    office.show()
    sys.exit(app.exec())
