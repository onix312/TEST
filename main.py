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
from agents import codex_args
from orchestra import ModelOrchestrator
from model_routing import ROUTES, FAST, BALANCED, DEEP, classify
from director import DesignerHistory, chat, make_plan, parse_plan
from pixel_office import MiniIsland, PixelOffice
from unity_integration import UnityRunner, bridge_install, unity_locked
from workspaces import file_preview, undo_merge

STATUS_LABELS = {
    "queued": "ОЧЕРЕДЬ", "running": "РАБОТАЕТ", "ready": "НА ПРОВЕРКЕ",
    "merged": "ГОТОВО", "conflict": "КОНФЛИКТ", "failed": "ОШИБКА",
    "interrupted": "ПРЕРВАНО", "cancelled": "ОТМЕНЕНО", "rolled_back": "ОТКАТ",
    "handoff": "ЖДЁТ CHATGPT"
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
        self._api_key = ""
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
        self.style_ui()
        self.project_path.setText(self.prefs.get("project") or "")
        self.unity_path.setText(self.prefs.get("unity") or "")
        self.codex_path.setText(self.prefs.get("codex") or detect_codex())
        self.model_name.setText(self.prefs.get("model") or "gpt-6.1-sol")
        self.worker_count.setValue(int(self.prefs.get("workers") or 2))
        self.fast_model.setText(self.prefs.get("model_fast") or FAST)
        self.balanced_model.setText(self.prefs.get("model_balanced") or BALANCED)
        self.deep_model.setText(self.prefs.get("model_deep") or DEEP)
        self.review_model.setText(self.prefs.get("model_review") or BALANCED)
        self.review_enabled.setChecked(bool(self.prefs.get("review_enabled", False)))
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
        box.addWidget(QLabel("TOP-DOWN OFFICE  •  Колесо мыши: масштаб  •  Перетаскивание: перемещение  •  Нажатие: задача"))
        scene_row = QHBoxLayout()
        self.pixel = PixelOffice()
        self.pixel.taskSelected.connect(self.open_task_in_office)
        scene_row.addWidget(self.pixel, 7)
        detail_panel = QWidget()
        detail_panel.setMinimumWidth(260)
        detail_panel.setMaximumWidth(350)
        detail_box = QVBoxLayout(detail_panel)
        detail_box.addWidget(QLabel("АГЕНТ / ЗАДАЧА"))
        self.office_task = QLabel("Нажми на персонажа, чтобы посмотреть его текущую задачу.")
        self.office_task.setWordWrap(True)
        detail_box.addWidget(self.office_task)
        self.office_detail = QPlainTextEdit()
        self.office_detail.setReadOnly(True)
        self.office_detail.setPlaceholderText("Здесь появится отчёт, исполнитель, статус и результат.")
        detail_box.addWidget(self.office_detail, 1)
        detail_box.addWidget(button("Открыть задачу", self.office_open_agents))
        detail_box.addWidget(button("Применить выбранные изменения", self.approve_task))
        detail_box.addWidget(button("Передать ChatGPT", self.copy_task_handoff))
        detail_box.addStretch()
        scene_row.addWidget(detail_panel, 3)
        box.addLayout(scene_row, 5)
        self.dashboard = QLabel("Проект не выбран.")
        box.addWidget(self.dashboard)
        self.office_command = QLineEdit()
        self.office_command.setPlaceholderText("Поставить задачу на естественном языке...")
        box.addLayout(row(self.office_command,
                          button("Поставить задачу", self.queue_from_office),
                          button("Запустить оркестр", self.start_agents)))
        line = QHBoxLayout()
        line.addWidget(button("Центрировать камеру", self.pixel.reset_camera))
        line.addWidget(button("Агенты и изменения", lambda: self.tabs.setCurrentIndex(1)))
        line.addWidget(button("Game Designer / GDD", lambda: self.tabs.setCurrentIndex(2)))
        line.addWidget(button("Unity", lambda: self.tabs.setCurrentIndex(3)))
        box.addLayout(line)
        self.tabs.addTab(panel, "◈  Pixel Office")

    def open_task_in_office(self, task_id):
        if not self.store:
            return
        task = self.store.find(task_id)
        if not task:
            return
        self.selected_id = task_id
        self.office_task.setText(
            (task.get("model") or task.get("role") or "Agent") + "  •  " +
            STATUS_LABELS.get(task["status"], task["status"]))
        self.office_detail.setPlainText(
            "Задача:\n" + task["text"] + "\n\n"
            "Модель: " + str(task.get("model") or "Авто") + "\n" +
            "Исполнитель: " + str(task.get("backend") or "в очереди") + "\n" +
            "Статус: " + STATUS_LABELS.get(task["status"], task["status"]) + "\n\n" +
            "Отчёт:\n" + (task.get("summary") or "Пока нет результата.")[:12000] +
            "\n\nОшибки:\n" + (task.get("error") or "нет")[:2000])
        # Preserve the office scene; the full task is one click away.
        self.write_log("Выбран агент: " + task_id + ". Открой вкладку Agents для подробностей.")

    def office_open_agents(self):
        if not self.selected_id:
            self.write_log("Для начала выбери персонажа.")
            return
        self.tabs.setCurrentIndex(1)
        for index in range(self.tasks_view.count()):
            item = self.tasks_view.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == self.selected_id:
                self.tasks_view.setCurrentItem(item)
                break

    def queue_from_office(self):
        try:
            self.require_project()
            prompt = self.office_command.text().strip()
            if not prompt:
                raise ValueError("Введи задачу.")
            task = self.store.add(prompt, route="auto")
            self.office_command.clear()
            self.selected_id = task["id"]
            self.refresh_tasks()
            self.open_task_in_office(task["id"])
        except Exception as exc:
            self.alert(exc)

    def make_agents_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Новая задача. Каждый Codex получает свою локальную копию Unity-проекта."))
        self.task_prompt = QPlainTextEdit()
        self.task_prompt.setPlaceholderText("Например: Реализуй механики скрытности из GDD-046...")
        self.task_prompt.setMaximumHeight(110)
        box.addWidget(self.task_prompt)
        self.depends = QComboBox()
        self.agent_role = QComboBox()
        self.agent_role.addItems(["Gameplay Developer", "Systems Developer", "UI Developer",
                                  "Unity Tools Developer", "QA / Bugfix", "Game Analyst", "GDD Assistant"])
        self.task_route = QComboBox()
        for key, value in ROUTES.items():
            self.task_route.addItem(value, key)
        box.addLayout(row("Специализация:", self.agent_role, "Исполнитель:", self.task_route))
        box.addLayout(row("После задачи:", self.depends))
        commands = QHBoxLayout()
        commands.addWidget(button("Добавить задачу", self.add_task))
        commands.addWidget(button("AI → план", self.plan_task))
        commands.addWidget(button("Запрос плана для ChatGPT", self.copy_plan_prompt))
        commands.addWidget(button("Вставить план ChatGPT", self.import_plan_clipboard))
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
        commands.addWidget(button("Откатить задачу", self.undo_task))
        commands.addWidget(button("Папка агента", self.open_agent_folder))
        box.addLayout(commands)
        chatgpt_commands = QHBoxLayout()
        chatgpt_commands.addWidget(button("Задание → ChatGPT", self.copy_task_handoff))
        chatgpt_commands.addWidget(button("Ответ ChatGPT ← буфер", self.finish_chatgpt_handoff))
        chatgpt_commands.addWidget(button("Результат → задача Codex", self.result_to_codex))
        box.addLayout(chatgpt_commands)
        self.tabs.addTab(panel, "⌘  Codex Agents")

    def make_gdd_tab(self):
        panel = QWidget()
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("Существующий чат ChatGPT — Game Designer. "
                             "Скопируй запрос в этот чат и вставь утверждённый GDD ниже."))
        commands = QHBoxLayout()
        commands.addWidget(button("Скопировать запрос для ChatGPT", self.copy_handoff))
        commands.addWidget(button("Импорт Markdown", self.import_gdd))
        commands.addWidget(button("GDD из буфера", self.gdd_from_clipboard))
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
        commands = QHBoxLayout()
        commands.addWidget(button("Открыть отчёты / снимки", self.open_reports))
        commands.addWidget(button("Создать задачу из Unity-ошибок", self.repair_unity_errors))
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
        self.fast_model = QLineEdit()
        self.balanced_model = QLineEdit()
        self.deep_model = QLineEdit()
        self.review_model = QLineEdit()
        self.review_enabled = QCheckBox("Проверять изменения Codex отдельной моделью до автоприменения")
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
        form.addRow("ChatGPT быстрый • Luna", self.fast_model)
        form.addRow("ChatGPT аналитик • Sol", self.balanced_model)
        form.addRow("ChatGPT сложный • Astra", self.deep_model)
        form.addRow("ChatGPT ревьюер", self.review_model)
        form.addRow("AI-ревью перед слиянием", self.review_enabled)
        form.addRow("OpenAI API ключ (опция)", self.api_key)
        box.addLayout(form)
        box.addWidget(button("Сохранить и подключить проект", self.configure))
        box.addWidget(button("Войти в Codex через терминал", self.login_codex))
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
            "mini": self.mini_toggle.isChecked(),
            "model_fast": self.fast_model.text().strip() or FAST,
            "model_balanced": self.balanced_model.text().strip() or BALANCED,
            "model_deep": self.deep_model.text().strip() or DEEP,
            "model_review": self.review_model.text().strip() or BALANCED,
            "review_enabled": self.review_enabled.isChecked(),
        }
        self.prefs = prefs
        save_settings(prefs)
        key = self.api_key.text().strip()
        if key:
            self._api_key = key
            self.api_key.clear()
        if self.manager is not None and not self.manager.running:
            self.manager.api_key = self._api_key or os.getenv("OPENAI_API_KEY", "").strip()
            self.manager.models.update({
                "fast": prefs["model_fast"], "balanced": prefs["model_balanced"],
                "deep": prefs["model_deep"], "review": prefs["model_review"],
            })
            self.manager.review_enabled = prefs["review_enabled"]
            self.manager.auto_merge = prefs["auto_merge"]
            self.manager.workers = prefs["workers"]
        return prefs

    def attach_project(self):
        root = validate_project(self.project_path.text())
        if self.manager and self.manager.running:
            raise RuntimeError("Останови агентов перед переключением проекта.")
        if self.is_busy:
            raise RuntimeError("Сначала дождись ответа Game Designer.")
        self.store = ProjectStore(root)
        self.manager = ModelOrchestrator(
            self.store, self.codex_path.text(), self.worker_count.value(),
            self.auto_merge.isChecked(), api_key=self._api_key,
            models={"fast": self.fast_model.text(), "balanced": self.balanced_model.text(),
                    "deep": self.deep_model.text(), "review": self.review_model.text()},
            review_enabled=self.review_enabled.isChecked())
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
            backend = task.get("model") or task.get("route", "auto").upper()
            title = STATUS_LABELS.get(task["status"], "?") + "  [" + backend + "]  " + task["text"][:100]
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
        self.pixel.select_task(self.selected_id)
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
        if self.selected_id and self.store.find(self.selected_id):
            current = self.store.find(self.selected_id)
            text = STATUS_LABELS.get(current["status"], current["status"])
            self.office_task.setText((current.get("model") or current.get("role") or "Agent") + " • " + text)
            self.office_detail.setPlainText(
                current["text"] + "\n\n" + (current.get("summary") or "Пока нет результата.")[:12000] +
                "\n\n" + (current.get("error") or ""))
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
            predicted_backend, predicted_model, predicted_reason = classify(
                task["text"], task.get("route", "auto"),
                self.manager.models if self.manager else {})
            report = [
                "ID: " + task["id"], "Роль: " + task["role"],
                "Плановый исполнитель: " + predicted_model + " — " + predicted_reason,
                "Статус: " + STATUS_LABELS.get(task["status"], task["status"]),
                "Маршрут: " + task.get("route", "auto"),
                "Исполнитель: " + task.get("backend", "не определён"),
                "Модель: " + task.get("model", "не определена"),
                "AI-ревью:\n" + task.get("review", ""),
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
                             depends=[dependency] if dependency else [],
                             role=self.agent_role.currentText(),
                             route=self.task_route.currentData())
            self.selected_id = item["id"]
            self.task_prompt.clear()
            self.refresh_tasks()
        except Exception as exc:
            self.alert(exc)


    def copy_task_handoff(self):
        """No API key required: user sends a scoped text task in existing ChatGPT."""
        try:
            self.require_project()
            task = self.store.find(self.selected_id)
            if not task:
                raise ValueError("Выбери простую ChatGPT-задачу из списка.")
            if self.manager.running:
                raise RuntimeError("Останови оркестр перед ручной передачей задачи.")
            if task["status"] not in ("queued", "handoff", "failed"):
                raise ValueError("Можно передать только ожидающую ChatGPT-задачу.")
            prompt = self.manager.handoff_prompt(task["id"])
            QApplication.clipboard().setText(prompt)
            self.store.update(task["id"], status="handoff", backend="chatgpt",
                              error="Скопировано в буфер. Вставь ответ ChatGPT обратно.")
            self.refresh_tasks()
            self.write_log("Задание скопировано. Отправь его в ChatGPT, затем скопируй ответ.")
        except Exception as exc:
            self.alert(exc)

    def finish_chatgpt_handoff(self):
        try:
            self.require_project()
            task = self.store.find(self.selected_id)
            if not task or task["status"] != "handoff":
                raise ValueError("Выбери задачу в статусе «ЖДЁТ CHATGPT».")
            answer = QApplication.clipboard().text().strip()
            if not answer:
                raise ValueError("Сначала скопируй ответ ChatGPT.")
            if QMessageBox.question(
                    self, "Результат ChatGPT",
                    "Сохранить этот ответ как результат задачи? GDD не будет изменён.") != QMessageBox.StandardButton.Yes:
                return
            self.manager.finish_text_task(task["id"], answer)
            self.refresh_tasks()
            self.write_log("Ответ ChatGPT сохранён; можно запустить следующие задачи.")
        except Exception as exc:
            self.alert(exc)

    def result_to_codex(self):
        """Create an explicit code task rather than letting a text model edit Unity."""
        try:
            self.require_project()
            task = self.store.find(self.selected_id)
            if not task or task["status"] != "merged" or task.get("backend") != "chatgpt":
                raise ValueError("Выбери завершённую текстовую задачу ChatGPT.")
            prompt = ("Применить результат предыдущего ChatGPT-анализа при реализации "
                      "утверждённого Unity GDD. Не принимать предложенные новые правила "
                      "игры без согласования. Напиши необходимые Unity C# скрипты "
                      "и файлы проекта, если они следуют утверждённому GDD. "
                      "Если это только аналитическая записка — сообщи, что писать код не требуется.")
            created = self.store.add(prompt, depends=[task["id"]], role="Gameplay Developer",
                                     route="codex")
            self.selected_id = created["id"]
            self.refresh_tasks()
            self.write_log("Создана Codex-задача на основе отчёта ChatGPT.")
        except Exception as exc:
            self.alert(exc)

    def start_agents(self):
        try:
            self.require_project()
            self.manager.start()
            self.write_log("Оркестр моделей запущен: ChatGPT / Codex.")
        except Exception as exc:
            self.alert(exc)

    def stop_agents(self):
        if self.manager:
            self.manager.stop()
            self.write_log("Остановка оркестра запрошена.")

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

    def undo_task(self):
        try:
            store = self.require_project()
            task = store.find(self.selected_id)
            if not task or task["status"] != "merged" or not task.get("checkpoint"):
                raise ValueError("У этой задачи нет применённых изменений с архивом.")
            if self.manager.running or (self.unity_runner and self.unity_runner.running):
                raise RuntimeError("Останови операции перед откатом.")
            if unity_locked(store.root):
                raise RuntimeError("Закрой Unity Editor перед откатом.")
            if any(t["status"] == "merged" and task["id"] in t.get("depends", [])
                   for t in store.tasks):
                raise RuntimeError("Сначала откати зависимые применённые задачи.")
            if QMessageBox.question(self, "Откат изменений",
                    "Отменить файлы этой задачи? Программа создаст ещё один checkpoint. "
                    "Более новые изменения защищены проверкой хэшей.") != QMessageBox.StandardButton.Yes:
                return
            backup = undo_merge(store.root, task)
            store.update(task["id"], status="rolled_back", error="Откат выполнен; backup перед откатом: " + str(backup))
            self.refresh_tasks()
            self.write_log("Изменения задачи откатили.")
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

    def gdd_from_clipboard(self):
        try:
            store = self.require_project()
            if self.manager.running:
                raise RuntimeError("Останови агентов перед обновлением GDD.")
            content = QApplication.clipboard().text().strip()
            if content.startswith(chr(96) * 3):
                content = "\n".join(content.splitlines()[1:-1])
            if not content:
                raise ValueError("Буфер обмена пуст.")
            self.gdd_editor.setPlainText(content)
            self.write_log("GDD скопирован в редактор. Нажми «Утвердить содержимое редактора».")
            self.tabs.setCurrentIndex(2)
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
            threading.Thread(target=self._designer_worker,
                             args=(messages, store.gdd(), self.model_name.text().strip()),
                             daemon=True).start()
        except Exception as exc:
            self.alert(exc)

    def _designer_worker(self, messages, gdd, model):
        try:
            answer = chat(model, messages, gdd, api_key=self._api_key)
            self.events.response.emit(answer)
        except Exception as exc:
            self.events.error.emit(str(exc))

    def designer_response(self, answer):
        self.is_busy = False
        self.history.add("assistant", answer)
        self.designer_messages.appendPlainText("\nCHATGPT GAME DESIGNER:\n" + answer)
        self.write_log("Game Designer ответил. Утверждение GDD — отдельно.")

    def copy_plan_prompt(self):
        try:
            store = self.require_project()
            request = self.task_prompt.toPlainText().strip()
            if not request:
                raise ValueError("Сначала опиши задачу.")
            handoff = (
                "Ты Game Designer, помоги спланировать Unity-реализацию уже утверждённых "
                "решений. Не добавляй новые правила игры. Разбей задачу максимум на 6 "
                "подзадач: лёгкие аналитические и текстовые задачи делай через ChatGPT, "
                "изменения файлов Unity поручай Codex. "
                "Верни ТОЛЬКО JSON вида "
                + '{"tasks":[{"title":"опиши варианты","depends":[],"route":"chatgpt_fast"},'
                '{"title":"реализуй скрипт","depends":[0],"route":"codex"}]}' +
                "; depends — индексы предыдущих задач с нуля. "
                "\n\nAPPROVED GDD:\n" + store.gdd()[:32000] +
                "\n\nTASK:\n" + request)
            QApplication.clipboard().setText(handoff)
            self.write_log("Запрос плана для существующего чата ChatGPT скопирован.")
        except Exception as exc:
            self.alert(exc)

    def import_plan_clipboard(self):
        try:
            self.require_project()
            plan = parse_plan(QApplication.clipboard().text())
            self.planner_response(plan)
        except Exception as exc:
            self.alert(exc)

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
            self.events.plan.emit(make_plan(model, gdd, task, api_key=self._api_key))
        except Exception as exc:
            self.events.error.emit(str(exc))

    def planner_response(self, plan):
        self.is_busy = False
        try:
            store = self.require_project()
            created = []
            for entry in plan:
                title, deps, route = (entry[0], entry[1],
                                      entry[2] if len(entry) > 2 else "auto")
                role = "Game Analyst" if route.startswith("chatgpt_") else "Gameplay Developer"
                task = store.add(title, depends=[created[n] for n in deps],
                                 route=route, role=role)
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
            return True
        except Exception as exc:
            self.alert(exc)
            return False

    def unity_action(self, action):
        try:
            store = self.require_project()
            if self.manager.running:
                raise RuntimeError("Unity batch нельзя запускать одновременно с агентами.")
            if action == "scene" and not self.save_scene_spec():
                return
            if action in ("build", "scene", "report"):
                if not (store.root / "Assets" / "Editor" / "GameDevAIOfficeBridge.cs").exists():
                    raise RuntimeError("Сначала установи Unity Bridge.")
            self.unity_runner.unity_exe = self.unity_path.text().strip()
            self.unity_runner.start(action)
        except Exception as exc:
            self.alert(exc)

    def open_reports(self):
        try:
            store = self.require_project()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(store.folder / "reports")))
        except Exception as exc:
            self.alert(exc)

    def repair_unity_errors(self):
        try:
            store = self.require_project()
            logs = sorted((store.folder / "reports").glob("*.log"),
                          key=lambda p: p.stat().st_mtime, reverse=True)
            if not logs:
                raise ValueError("Нет отчётов Unity. Сначала запусти проверку в приложении.")
            excerpt = logs[0].read_text(encoding="utf-8", errors="replace")[-16000:]
            errors = [line for line in excerpt.splitlines()
                      if "error" in line.lower() or "exception" in line.lower()]
            if not errors:
                raise ValueError("В последнем Unity-логе нет явных ошибок.")
            note = (
                "Исправь перечисленные ошибки Unity Editor в рамках утверждённого GDD. "
                "Не меняй игровую механику; используй существующие классы и Unity .meta. "
                "Ошибки (из " + logs[0].name + "):\n" + "\n".join(errors[-65:])[:8000])
            item = store.add(note)
            self.selected_id = item["id"]
            self.refresh_tasks()
            self.tabs.setCurrentIndex(1)
        except Exception as exc:
            self.alert(exc)

    def login_codex(self):
        try:
            if os.name != "nt":
                raise RuntimeError("Вход в Codex через кнопку рассчитан на Windows.")
            command = subprocess.list2cmdline([self.codex_path.text().strip() or "codex", "login"])
            subprocess.Popen(["cmd.exe", "/k", command],
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
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
