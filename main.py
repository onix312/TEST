"""GameDev AI Office — local Windows cockpit for Unity, approved GDD and Codex agents."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget
)

from office_core import (ProjectStore, atomic_json, detect_codex, detect_unity,
                         load_settings, save_settings, validate_project)
from agents import AgentManager, codex_args
from director import DesignerHistory, chat, make_plan
from pixel_office import MiniIsland, PixelOffice
from unity_integration import UnityRunner, bridge_install
from workspaces import file_preview

STATUS_LABELS = {
    "queued": "ОЧЕРЕДЬ", "running": "РАБОТАЕТ", "ready": "НА ПРОВЕРКЕ",
    "merged": "ГОТОВО", "conflict": "КОНФЛИКТ", "failed": "ОШИБКА",
    "interrupted": "ПРЕРВАНО", "cancelled": "ОТМЕНЕНО"
}


def button(text, action, parent=None):
    item = QPushButton(text, parent)
    item.clicked.connect(action)
    return item


def row(*widgets):
    layout = QHBoxLayout()
    for part in widgets:
        if isinstance(part, str):
            layout.addWidget(QLabel(part))
        else:
            layout.addWidget(part)
    return layout


class Background(QObject):
    response = Signal(str)
    plan = Signal(object)
    error = Signal(str)


class Office(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GameDev AI Office — Unity • Codex • Game Designer")
        self.resize(1240, 850)
        self.prefs = load_settings()
        self.store = None
        self.manager = None
        self.unity_runner = None
        self.history = None
        self.events = Background()
        self.events.response.connect(self.designer_response)
        self.events.plan.connect(self.planner_response)
        self.events.error.connect(self.display_error)
        self.is_busy = False
        self.selected_id = None

        outer = QWidget()
        self.setCentralWidget(outer)
        vertical = QVBoxLayout(outer)
        vertical.setContentsMargins(14, 10, 14, 12)
        header = QLabel("◈  GAMEDEV AI OFFICE")
        header.setObjectName("Header")
        vertical.addWidget(header)
        vertical.addWidget(QLabel("CHATGPT GAME DESIGNER   →   APPROVED GDD   →   CODEX AGENTS   →   UNITY"))
        self.tabs = QTabWidget()
        vertical.addWidget(self.tabs, 1)
        self.make_office_tab()
        self.make_agents_tab()
        self.make_gdd_tab()
        self.make_unity_tab()
        self.make_settings_tab()
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(400)
        self.console.setMaximumHeight(116)
        self.console.setPlaceholderText("Журнал операций")
        vertical.addWidget(self.console)

        self.island = MiniIsland(self.open_window)
        self.island.place()
        self.island.toggle = None
        self.style_ui()
        self.project_path.setText(self.prefs.get("project") or "")
        self.unity_path.setText(self.prefs.get("unity") or "")
        self.codex_path.setText(self.prefs.get("codex") or detect_codex())
        self.model_name.setText(self.prefs.get("model") or "gpt-5.1")
        self.worker_count.setValue(int(self.prefs.get("workers") or 2))
        self.auto_merge.setChecked(bool(self.prefs.get("auto_merge", True)))
        self.mini_toggle.setChecked(bool(self.prefs.get("mini", False)))
        self.toggle_island(self.mini_toggle.isChecked())
        self.poll = QTimer(self)
        self.poll.timeout.connect(self.refresh_status)
        self.poll.start(800)
        if self.project_path.text().strip():
            try:
                self.attach_project()
            except Exception as exc:
                self.write_log(str(exc))
        self.write_log("Выбери Unity-проект. Git не требуется.")

    def style_ui(self):
        self.setStyleSheet("""
          QMainWindow,QWidget{background:#1d1727;color:#efe8f2;font:10pt 'Segoe UI';}
          #Header{font-size:25px;font-weight:bold;color:#e2c5ff;padding:8px;}
          QTabWidget::pane{border:1px solid #584368;background:#221a2e;border-radius:9px;}
          QTabBar::tab{padding:11px 19px;background:#30243c;color:#d6c4e2;margin:2px;border-radius:6px;}
          QTabBar::tab:selected{background:#7555ac;color:white;}
          QLineEdit,QPlainTextEdit,QListWidget,QComboBox,QSpinBox{
              background:#30253c;border:1px solid #57476b;border-radius:7px;padding:8px;color:#f2e9fb;}
          QPushButton{background:#7050ae;color:#fcf8ff;border:1px solid #8966c6;
              border-radius:8px;padding:9px 13px;font-weight:600;}
          QPushButton:hover{background:#926ccd;}
          QPushButton:disabled{background:#453a51;color:#968ba1;}
          QCheckBox{padding:5px;}
          QLabel{padding:3px;}
        """)

    def make_office_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Анимированный офис • каждый рабочий стол отражает реальный статус Codex"))
        self.pixel = PixelOffice()
        box.addWidget(self.pixel)
        self.dashboard = QLabel("Проект не выбран.")
        box.addWidget(self.dashboard)
        box.addWidget(QLabel("Планирование и GDD — во вкладке Game Designer. "
                             "Разработка — во вкладке Agents. Unity — во вкладке Unity."))
        line = QHBoxLayout()
        line.addWidget(button("Открыть агентов", lambda: self.tabs.setCurrentIndex(1)))
        line.addWidget(button("Открыть GDD", lambda: self.tabs.setCurrentIndex(2)))
        line.addWidget(button("Открыть Unity", lambda: self.tabs.setCurrentIndex(3)))
        box.addLayout(line)
        box.addStretch()
        self.tabs.addTab(panel, "◈  Pixel Office")

    def make_agents_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Новая задача. Каждый Codex получает свою локальную копию Unity-проекта."))
        self.task_prompt = QPlainTextEdit()
        self.task_prompt.setPlaceholderText("Например: Реализуй механики скрытности из GDD-046...")
        self.task_prompt.setMaximumHeight(110)
        box.addWidget(self.task_prompt)
        self.depends = QComboBox()
        box.addLayout(row("После задачи:", self.depends))
        commands = QHBoxLayout()
        commands.addWidget(button("Добавить задачу", self.add_task))
        commands.addWidget(button("ChatGPT → план", self.plan_task))
        commands.addWidget(button("▶ Запустить агентов", self.start_agents))
        commands.addWidget(button("■ Остановить", self.stop_agents))
        box.addLayout(commands)
        self.tasks_view = QListWidget()
        self.tasks_view.itemSelectionChanged.connect(self.select_task)
        box.addWidget(self.tasks_view, 2)
        self.task_detail = QPlainTextEdit()
        self.task_detail.setReadOnly(True)
        self.task_detail.setMaximumBlockCount(500)
        box.addWidget(self.task_detail, 2)
        commands = QHBoxLayout()
        commands.addWidget(button("Применить изменения", self.approve_task))
        commands.addWidget(button("Перезапустить задачу", self.retry_task))
        commands.addWidget(button("Папка агента", self.open_agent_folder))
        box.addLayout(commands)
        self.tabs.addTab(panel, "⌘  Codex Agents")

    def make_gdd_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Существующий чат ChatGPT — Game Designer. "
                             "Скопируй запрос в этот чат и вставь утверждённый GDD ниже."))
        commands = QHBoxLayout()
        commands.addWidget(button("Скопировать запрос для ChatGPT", self.copy_handoff))
        commands.addWidget(button("Импорт Markdown", self.import_gdd))
        commands.addWidget(button("Утвердить содержимое редактора", self.approve_gdd))
        box.addLayout(commands)
        self.gdd_editor = QPlainTextEdit()
        self.gdd_editor.setPlaceholderText("Вставь только утверждённый GDD (Markdown). Черновики не применяются автоматически.")
        box.addWidget(self.gdd_editor, 2)
        box.addWidget(QLabel("Дополнительно: отдельный Game Designer через OpenAI API "
                             "(не получает историю существующего чата ChatGPT)."))
        self.designer_messages = QPlainTextEdit()
        self.designer_messages.setReadOnly(True)
        box.addWidget(self.designer_messages, 1)
        self.question = QPlainTextEdit()
        self.question.setMaximumHeight(75)
        self.question.setPlaceholderText("Сообщение Game Designer; новые идеи не утверждаются автоматически")
        box.addWidget(self.question)
        box.addWidget(button("Спросить Game Designer (API)", self.ask_designer))
        self.tabs.addTab(panel, "✎  Game Designer / GDD")

    def make_unity_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Unity Bridge: сцены, отчёты, Windows-сборка, EditMode и PlayMode."))
        box.addWidget(QLabel("Для batch-операций Unity Editor должен быть закрыт. "
                             "Установка Bridge создаёт резервную копию."))
        commands = QHBoxLayout()
        commands.addWidget(button("Установить Unity Bridge", self.install_bridge))
        commands.addWidget(button("Открыть проект в Unity", self.open_unity))
        box.addLayout(commands)
        box.addWidget(QLabel("Спецификация новой сцены (JSON, только после утверждения GDD)"))
        self.scene_spec = QPlainTextEdit()
        self.scene_spec.setPlainText(json.dumps({
            "name": "GamePrototype",
            "objects": [
                {"name": "Ground", "primitive": "Cube",
                 "position": [0, -0.5, 0], "scale": [14, 1, 14]},
                {"name": "PlayerPlaceholder", "primitive": "Capsule",
                 "position": [0, 1, 0], "scale": [1, 1, 1]}
            ]}, indent=2))
        box.addWidget(self.scene_spec, 2)
        commands = QHBoxLayout()
        commands.addWidget(button("Сохранить спецификацию", self.save_scene_spec))
        commands.addWidget(button("Создать сцену", lambda: self.unity_action("scene")))
        commands.addWidget(button("Отчёт о сцене", lambda: self.unity_action("report")))
        box.addLayout(commands)
        commands = QHBoxLayout()
        commands.addWidget(button("Unity EditMode", lambda: self.unity_action("editmode")))
        commands.addWidget(button("Unity PlayMode", lambda: self.unity_action("playmode")))
        commands.addWidget(button("Собрать Windows Game", lambda: self.unity_action("build")))
        box.addLayout(commands)
        box.addStretch()
        self.tabs.addTab(panel, "▣  Unity")

    def make_settings_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        form = QFormLayout()
        self.project_path = QLineEdit()
        self.unity_path = QLineEdit()
        self.codex_path = QLineEdit()
        self.model_name = QLineEdit()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Не сохраняется на диск; либо задай OPENAI_API_KEY")
        self.worker_count = QSpinBox()
        self.worker_count.setRange(1, 4)
        self.auto_merge = QCheckBox("Автоматически переносить бесконфликтные изменения")
        self.mini_toggle = QCheckBox("Показывать плавающую мини-панель")
        self.mini_toggle.toggled.connect(self.toggle_island)
        form.addRow("Корень Unity-проекта", row(self.project_path, button("Обзор", self.pick_project)))
        form.addRow("Unity.exe", row(self.unity_path, button("Найти Unity", self.pick_unity)))
        form.addRow("Codex CLI", self.codex_path)
        form.addRow("Параллельных агентов", self.worker_count)
        form.addRow("Применение", self.auto_merge)
        form.addRow("Мини-панель", self.mini_toggle)
        form.addRow("Модель Game Designer", self.model_name)
        form.addRow("OpenAI API ключ (опция)", self.api_key)
        box.addLayout(form)
        box.addWidget(button("Сохранить и подключить проект", self.configure))
        box.addWidget(QLabel(
            "Codex: установи CLI и выполни codex login в терминале.\n"
            "ChatGPT: существующий Game Designer чат остаётся в ChatGPT; перенос утверждённого "
            "GDD производится через Markdown.\n"
            "OpenAI API оплачивается отдельно от подписки ChatGPT. Git не требуется."))
        box.addStretch()
        self.tabs.addTab(panel, "⚙  Настройки")

    def write_log(self, message):
        self.console.appendPlainText(str(message)[:1500])

    def alert(self, exc):
        self.write_log("Ошибка: " + str(exc))
        QMessageBox.warning(self, "GameDev AI Office", str(exc))

    def display_error(self, error):
        self.is_busy = False
        self.alert(error)

    def pick_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Корень Unity-проекта")
        if directory:
            self.project_path.setText(directory)
            if not self.unity_path.text():
                self.unity_path.setText(detect_unity(directory))

    def pick_unity(self):
        found = detect_unity(self.project_path.text().strip() or None)
        if found:
            self.unity_path.setText(found)
        else:
            directory, _ = QFileDialog.getOpenFileName(self, "Выбери Unity.exe", "", "Unity.exe (Unity.exe)")
            if directory:
                self.unity_path.setText(directory)

    def save_prefs(self):
        prefs = {
            "project": self.project_path.text().strip(),
            "unity": self.unity_path.text().strip(),
            "codex": self.codex_path.text().strip() or "codex",
            "workers": self.worker_count.value(),
            "auto_merge": self.auto_merge.isChecked(),
            "model": self.model_name.text().strip() or "gpt-5.1",
            "mini": self.mini_toggle.isChecked()
        }
        self.prefs = prefs
        save_settings(prefs)
        key = self.api_key.text().strip()
        if key:
            os.environ["OPENAI_API_KEY"] = key
            self.api_key.clear()
        return prefs

    def attach_project(self):
        root = validate_project(self.project_path.text())
        if self.manager and self.manager.running:
            raise RuntimeError("Останови агентов перед переключением проекта.")
        self.store = ProjectStore(root)
        self.manager = AgentManager(self.store, self.codex_path.text(),
                                    self.worker_count.value(), self.auto_merge.isChecked())
        self.manager.activity.connect(self.agent_log)
        self.manager.changed.connect(self.agent_changed)
        self.manager.finished.connect(lambda: self.write_log("Агенты завершили очередь."))
        self.unity_runner = UnityRunner(root, self.unity_path.text())
        self.unity_runner.output.connect(self.write_log)
        self.unity_runner.done.connect(lambda action, ok:
            self.write_log("Unity " + action + ": " + ("готово" if ok else "ошибка")))
        self.history = DesignerHistory(self.store)
        self.designer_messages.setPlainText("\n\n".join(
            m["role"].upper() + ": " + m["content"] for m in self.history.messages[-30:]))
        self.gdd_editor.setPlainText(self.store.gdd())
        self.refresh_tasks()
        self.write_log("Подключён Unity-проект: " + str(root))

    def configure(self):
        try:
            self.save_prefs()
            self.attach_project()
            self.tabs.setCurrentIndex(0)
        except Exception as exc:
            self.alert(exc)

    def require_project(self):
        if self.store is None:
            raise ValueError("Сначала укажи Unity-проект в настройках.")
        return self.store

    def refresh_tasks(self):
        if not self.store:
            return
        selected = self.selected_id
        self.tasks_view.blockSignals(True)
        self.tasks_view.clear()
        self.depends.clear()
        self.depends.addItem("Без зависимости", "")
        for task in self.store.tasks:
            self.depends.addItem(task["text"][:75], task["id"])
            title = STATUS_LABELS.get(task["status"], "?") + "  " + task["text"][:110]
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, task["id"])
            if task["status"] in ("failed", "conflict"):
                item.setForeground(QColor("#f48da2"))
            elif task["status"] == "merged":
                item.setForeground(QColor("#82e2bb"))
            self.tasks_view.addItem(item)
            if task["id"] == selected:
                self.tasks_view.setCurrentItem(item)
        self.tasks_view.blockSignals(False)
        self.select_task()
        self.pixel.set_tasks(self.store.tasks)
        self.island.set_tasks(self.store.tasks)

    def refresh_status(self):
        if not self.store:
            return
        tasks = self.store.tasks
        running = sum(t["status"] == "running" for t in tasks)
        merged = sum(t["status"] == "merged" for t in tasks)
        needs_review = sum(t["status"] in ("ready", "conflict") for t in tasks)
        self.dashboard.setText(
            "Проект: " + self.store.root.name + "     "
            "Агенты: " + str(running) + "     "
            "Готово: " + str(merged) + "     "
            "Требуют решения: " + str(needs_review) + "     "
            "Задач всего: " + str(len(tasks)))
        self.pixel.set_tasks(tasks)
        self.island.set_tasks(tasks)

    def select_task(self):
        item = self.tasks_view.currentItem()
        if item is None:
            self.selected_id = None
            self.task_detail.setPlainText("")
            return
        self.selected_id = item.data(Qt.ItemDataRole.UserRole)
        task = self.store.find(self.selected_id)
        if task:
            report = [
                "ID: " + task["id"], "Роль: " + task["role"],
                "Статус: " + STATUS_LABELS.get(task["status"], task["status"]),
                "Задача: " + task["text"],
                "Зависимости: " + (", ".join(task["depends"]) or "нет"),
                "Рабочая копия: " + task.get("workspace", ""),
                "Резервная копия: " + task.get("checkpoint", ""),
                "Ошибка: " + task.get("error", ""),
                "Отчёт агента:\n" + task.get("summary", ""),
                "\nФайлы и предпросмотр:\n" +
                (file_preview(self.store.root, task["id"], task["changes"])
                 if task.get("changes") else "Нет изменений")
            ]
            self.task_detail.setPlainText("\n\n".join(report))

    def agent_log(self, task_id, message):
        self.write_log("[" + task_id + "] " + message)

    def agent_changed(self, task_id, status):
        self.write_log("[" + task_id + "] " + STATUS_LABELS.get(status, status))
        self.refresh_tasks()

    def add_task(self):
        try:
            store = self.require_project()
            dependency = self.depends.currentData()
            item = store.add(self.task_prompt.toPlainText(),
                             depends=[dependency] if dependency else [])
            self.selected_id = item["id"]
            self.task_prompt.clear()
            self.refresh_tasks()
        except Exception as exc:
            self.alert(exc)

    def start_agents(self):
        try:
            self.require_project()
            self.manager.start()
            self.write_log("Codex agents started.")
        except Exception as exc:
            self.alert(exc)

    def stop_agents(self):
        if self.manager:
            self.manager.stop()
            self.write_log("Остановка агентов запрошена.")

    def approve_task(self):
        try:
            store = self.require_project()
            task = store.find(self.selected_id)
            if not task:
                raise ValueError("Выбери задачу.")
            deletes = any(c["action"] == "delete" for c in task.get("changes", []))
            allow_deletions = False
            if deletes:
                answer = QMessageBox.question(self, "Подтверждение удаления",
                    "Агент предлагает удалить файлы. Ты проверил список и хочешь применить удаления?")
                if answer != QMessageBox.StandardButton.Yes:
                    return
                allow_deletions = True
            self.manager.approve(task["id"], allow_deletions=allow_deletions)
            self.refresh_tasks()
        except Exception as exc:
            self.alert(exc)

    def retry_task(self):
        try:
            self.require_project().reset(self.selected_id)
            self.refresh_tasks()
        except Exception as exc:
            self.alert(exc)

    def open_agent_folder(self):
        try:
            store = self.require_project()
            task = store.find(self.selected_id)
            if not task or not task.get("workspace"):
                raise ValueError("У задачи пока нет рабочей папки.")
            QDesktopServices.openUrl(QUrl.fromLocalFile(task["workspace"]))
        except Exception as exc:
            self.alert(exc)

    def copy_handoff(self):
        try:
            QApplication.clipboard().setText(self.require_project().handoff())
            self.write_log("Запрос для существующего чата ChatGPT скопирован.")
        except Exception as exc:
            self.alert(exc)

    def import_gdd(self):
        try:
            store = self.require_project()
            path, _ = QFileDialog.getOpenFileName(self, "Импорт утверждённого GDD",
                                                  "", "Markdown и текст (*.md *.txt)")
            if path:
                if self.manager.running:
                    raise RuntimeError("Нельзя обновлять GDD во время работы агентов.")
                destination = store.import_gdd(path)
                self.gdd_editor.setPlainText(store.gdd())
                self.write_log("GDD утверждён: " + str(destination))
        except Exception as exc:
            self.alert(exc)

    def approve_gdd(self):
        try:
            store = self.require_project()
            if self.manager.running:
                raise RuntimeError("Сначала останови Codex-агентов.")
            if QMessageBox.question(self, "Утвердить GDD",
                "Это согласованная версия дизайна? Codex будет следовать ей.") != QMessageBox.StandardButton.Yes:
                return
            destination = store.approve_gdd(self.gdd_editor.toPlainText())
            self.write_log("Утверждённый GDD: " + str(destination))
        except Exception as exc:
            self.alert(exc)

    def ask_designer(self):
        try:
            store = self.require_project()
            if self.is_busy:
                return
            self.save_prefs()
            text = self.question.toPlainText().strip()
            if not text:
                raise ValueError("Введи вопрос.")
            self.history.add("user", text)
            self.designer_messages.appendPlainText("\nYOU: " + text)
            self.question.clear()
            self.is_busy = True
            messages = list(self.history.messages)
            threading.Thread(target=self._designer_worker, args=(messages, store.gdd()),
                             daemon=True).start()
        except Exception as exc:
            self.alert(exc)

    def _designer_worker(self, messages, gdd):
        try:
            answer = chat(self.model_name.text().strip(), messages, gdd)
            self.events.response.emit(answer)
        except Exception as exc:
            self.events.error.emit(str(exc))

    def designer_response(self, answer):
        self.is_busy = False
        self.history.add("assistant", answer)
        self.designer_messages.appendPlainText("\nCHATGPT GAME DESIGNER:\n" + answer)
        self.write_log("Game Designer ответил. Утверждение GDD — отдельно.")

    def plan_task(self):
        try:
            store = self.require_project()
            if self.is_busy:
                return
            self.save_prefs()
            task = self.task_prompt.toPlainText().strip()
            if not task:
                raise ValueError("Сначала опиши крупную задачу.")
            self.is_busy = True
            threading.Thread(target=self._planner_worker,
                             args=(store.gdd(), task, self.model_name.text().strip()), daemon=True).start()
            self.write_log("ChatGPT составляет план задач...")
        except Exception as exc:
            self.alert(exc)

    def _planner_worker(self, gdd, task, model):
        try:
            self.events.plan.emit(make_plan(model, gdd, task))
        except Exception as exc:
            self.events.error.emit(str(exc))

    def planner_response(self, plan):
        self.is_busy = False
        try:
            store = self.require_project()
            created = []
            for title, deps in plan:
                task = store.add(title, depends=[created[n] for n in deps])
                created.append(task["id"])
            self.task_prompt.clear()
            self.refresh_tasks()
            self.write_log("Создан план из " + str(len(created)) + " задач.")
        except Exception as exc:
            self.alert(exc)

    def install_bridge(self):
        try:
            store = self.require_project()
            if self.manager.running:
                raise RuntimeError("Останови Codex перед установкой Bridge.")
            if QMessageBox.question(self, "Unity Bridge",
                "Установить Assets/Editor/GameDevAIOfficeBridge.cs? "
                "Будет создан локальный checkpoint.") != QMessageBox.StandardButton.Yes:
                return
            backup = bridge_install(store.root)
            self.write_log("Unity Bridge установлен. Backup: " + str(backup))
        except Exception as exc:
            self.alert(exc)

    def save_scene_spec(self):
        try:
            store = self.require_project()
            parsed = json.loads(self.scene_spec.toPlainText())
            if not isinstance(parsed, dict) or not isinstance(parsed.get("objects", []), list):
                raise ValueError("Некорректная спецификация сцены.")
            destination = store.folder / "scene-spec.json"
            atomic_json(destination, parsed)
            self.write_log("Сцена: " + str(destination))
        except Exception as exc:
            self.alert(exc)

    def unity_action(self, action):
        try:
            store = self.require_project()
            if self.manager.running:
                raise RuntimeError("Unity batch нельзя запускать одновременно с агентами.")
            if action == "scene":
                self.save_scene_spec()
                if not (store.folder / "scene-spec.json").exists():
                    return
            if action in ("build", "scene", "report"):
                if not (store.root / "Assets" / "Editor" / "GameDevAIOfficeBridge.cs").exists():
                    raise RuntimeError("Сначала установи Unity Bridge.")
            self.unity_runner.unity_exe = self.unity_path.text().strip()
            self.unity_runner.start(action)
        except Exception as exc:
            self.alert(exc)

    def open_unity(self):
        try:
            store = self.require_project()
            exe = Path(self.unity_path.text())
            if not exe.is_file():
                raise ValueError("Не указан Unity.exe.")
            subprocess.Popen([str(exe), "-projectPath", str(store.root)])
            self.write_log("Unity Editor запущен.")
        except Exception as exc:
            self.alert(exc)

    def toggle_island(self, enabled):
        if enabled:
            self.island.place()
            self.island.show()
        else:
            self.island.hide()

    def open_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.manager and self.manager.running:
            if QMessageBox.question(self, "Завершить",
                "Codex-агенты работают. Остановить их и выйти?") != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.manager.stop()
        self.island.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("GameDev AI Office")
    window = Office()
    window.show()
    sys.exit(app.exec())
