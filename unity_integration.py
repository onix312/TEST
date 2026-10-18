"""Unity Editor integration: install bridge and run batch-mode editor operations."""
from __future__ import annotations

import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from office_core import resource_path
from safety import checkpoint

BRIDGE = Path("Assets/Editor/GameDevAIOfficeBridge.cs")
METHODS = {
    "scene": "GameDevAIOffice.EditorBridge.CreateSceneFromSpec",
    "report": "GameDevAIOffice.EditorBridge.ExportSceneReport",
    "build": "GameDevAIOffice.EditorBridge.BuildWindows",
}


def bridge_install(root):
    source = resource_path("unity_bridge", "GameDevAIOfficeBridge.cs")
    if not source.is_file():
        raise FileNotFoundError("Не найден Unity Bridge в установленном приложении.")
    target = root / BRIDGE
    if target.exists() and target.read_bytes() == source.read_bytes():
        return None
    backup = checkpoint(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return backup


def unity_locked(root):
    return (root / "Temp" / "UnityLockfile").exists()


def test_report_status(path):
    """Read fresh NUnit/Unity test XML as a QA gate, not just a printable label."""
    try:
        root = ET.parse(path).getroot()
        counts = {key: int(root.attrib.get(key, "-1"))
                  for key in ("total", "passed", "failed", "skipped")}
        result = root.attrib.get("result", "").lower()
        text = ("Tests: total={total}, passed={passed}, failed={failed}, skipped={skipped}"
                .format(**counts))
        good = (counts["total"] > 0 and counts["passed"] > 0 and
                counts["failed"] == 0 and
                counts["passed"] + counts["skipped"] == counts["total"] and
                result not in ("failed", "inconclusive", "error"))
        return good, text
    except (ET.ParseError, OSError, ValueError, TypeError):
        return False, "Отчёт тестов отсутствует или повреждён: " + str(path)


def test_report(path):
    """Compatibility helper for UI and existing callers."""
    return test_report_status(path)[1]


class UnityRunner(QObject):
    output = Signal(str)
    done = Signal(str, bool)

    def __init__(self, root, unity_exe):
        super().__init__()
        self.root = Path(root)
        self.unity_exe = unity_exe
        self.process = None
        self.worker = None

    @property
    def running(self):
        return self.worker is not None and self.worker.is_alive()

    def start(self, action):
        if self.running:
            raise RuntimeError("Unity уже выполняет операцию.")
        if action not in ("editmode", "playmode", *METHODS):
            raise ValueError("Неизвестная операция Unity")
        if not Path(self.unity_exe).is_file():
            raise FileNotFoundError("Выбери Unity.exe.")
        if unity_locked(self.root):
            raise RuntimeError("Unity уже открыл этот проект. Закрой редактор и повтори.")
        report_dir = self.root / ".ai-office" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        tag = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        logfile = report_dir / (action + "-" + tag + ".log")
        cmd = [self.unity_exe, "-batchmode", "-nographics", "-quit",
               "-projectPath", str(self.root), "-logFile", str(logfile)]
        if action in ("editmode", "playmode"):
            cmd += ["-runTests", "-testPlatform", "EditMode" if action == "editmode" else "PlayMode",
                    "-testResults", str(logfile.with_suffix(".xml"))]
        else:
            cmd += ["-executeMethod", METHODS[action]]
        self.worker = threading.Thread(target=self._run, args=(action, cmd, logfile),
                                       daemon=True, name="UnityRunner")
        self.worker.start()

    def _run(self, action, cmd, logfile):
        success = False
        try:
            self.output.emit("Unity: " + action + " — запуск")
            self.process = subprocess.Popen(cmd, cwd=self.root, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
            code = self.process.wait()
            success = code == 0
            self.output.emit("Unity exit code: " + str(code) + " | " + str(logfile))
            if action in ("editmode", "playmode"):
                passed, report = test_report_status(logfile.with_suffix(".xml"))
                self.output.emit(report)
                success = success and passed
        except OSError as exc:
            self.output.emit("Unity error: " + str(exc))
        finally:
            self.process = None
            self.done.emit(action, success)
