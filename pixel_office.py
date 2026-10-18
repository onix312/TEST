"""Native painted pixel-office status view and optional floating desktop island."""
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel


class PixelOffice(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(255)
        self.tasks = []
        self.tick = 0
        timer = QTimer(self)
        timer.timeout.connect(self.animate)
        timer.start(350)

    def animate(self):
        self.tick += 1
        self.update()

    def set_tasks(self, tasks):
        self.tasks = [dict(t) for t in tasks]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(self.rect(), QColor("#16111f"))
        sx, sy = self.width() / 900, self.height() / 280
        painter.scale(sx, sy)
        painter.fillRect(12, 8, 876, 185, QColor("#292038"))
        painter.fillRect(12, 193, 876, 75, QColor("#433045"))
        for x in range(12, 888, 32):
            painter.fillRect(x, 194, 1, 74, QColor("#604054"))
        for x in (75, 385, 695):
            painter.fillRect(x, 25, 135, 90, QColor("#393151"))
            painter.fillRect(x+8, 32, 119, 75, QColor("#54406b"))
            painter.fillRect(x+16, 40, 103, 59, QColor("#1e263e"))
            painter.fillRect(x+28, 55, 12, 6, QColor("#c09af4"))
            painter.fillRect(x+57, 55, 50, 6, QColor("#7d6db3"))
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#d9badf"))
        painter.drawText(25, 27, "GAMEDEV AI OFFICE")
        statuses = ["idle", "idle", "idle", "idle"]
        names = ["CODEX-1", "CODEX-2", "CODEX-3", "CODEX-4"]
        ordered = [t for t in self.tasks if t["status"] in ("running", "ready", "handoff", "conflict", "failed")]
        ordered += [t for t in self.tasks if t["status"] == "merged"]
        for index, task in enumerate(ordered[:4]):
            statuses[index] = task["status"]
            model = str(task.get("model") or "").lower()
            route = str(task.get("route") or "").lower()
            if task.get("backend") == "chatgpt" or route.startswith("chatgpt_"):
                if "luna" in model or route.endswith("fast"):
                    names[index] = "GPT LUNA"
                elif "astra" in model or route.endswith("deep"):
                    names[index] = "GPT ASTRA"
                else:
                    names[index] = "GPT SOL"
            else:
                names[index] = "CODEX-" + str(index + 1)
        for i, status in enumerate(statuses):
            x = 48 + i * 208
            painter.fillRect(x+12, 153, 157, 13, QColor("#77586e"))
            painter.fillRect(x+24, 165, 12, 52, QColor("#211a2e"))
            painter.fillRect(x+143, 165, 12, 52, QColor("#211a2e"))
            painter.fillRect(x+49, 112, 109, 50, QColor("#1b182c"))
            painter.fillRect(x+57, 119, 93, 35, QColor("#3b3d60"))
            light = {
                "running": "#b08dff", "merged": "#70d9ab", "ready": "#e7c679",
                "conflict": "#e97087", "failed": "#e97087",
                "handoff": "#f1c56b", "idle": "#6a587c"
            }.get(status, "#7d7db3")
            painter.fillRect(x+65, 126, 77, 20, QColor(light))
            painter.fillRect(x+68, 128, 71, 16, QColor("#28344b"))
            if status == "running":
                cursor = 3 + (self.tick % 8) * 7
                painter.fillRect(x+cursor+70, 135, 6, 3, QColor(light))
            painter.fillRect(x+89, 154, 8, 9, QColor("#867397"))
            if status in ("running", "ready", "conflict", "merged", "handoff"):
                bob = self.tick % 2 if status == "running" else 0
                painter.fillRect(x+89, 84+bob, 33, 24, QColor("#ffd2aa"))
                painter.fillRect(x+85, 77+bob, 40, 12, QColor("#6e426e"))
                painter.fillRect(x+92, 95+bob, 5, 5, QColor("#241c31"))
                painter.fillRect(x+111, 95+bob, 5, 5, QColor("#241c31"))
                painter.fillRect(x+81, 108+bob, 48, 29, QColor("#8060b4"))
            else:
                painter.fillRect(x+90, 98, 31, 22, QColor("#806b85"))
            painter.setPen(QColor("#eee2f2"))
            painter.drawText(x+30, 241, names[i])
            painter.setPen(QColor(light))
            painter.drawText(x+30, 258, status.upper())
        painter.end()


class MiniIsland(QWidget):
    def __init__(self, open_main):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(370, 52)
        row = QHBoxLayout(self)
        row.setContentsMargins(11, 6, 11, 6)
        self.button = QPushButton("◈  GAMEDEV  •  0 agents")
        self.button.clicked.connect(open_main)
        self.button.setStyleSheet(
            "QPushButton{border:1px solid #8a67cb;border-radius:18px;background:#251d34;"
            "color:#eee3ff;font:11pt Segoe UI;padding:8px;text-align:center;}")
        row.addWidget(self.button)

    def place(self):
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(rect.x() + (rect.width()-self.width())//2, rect.y()+8)

    def set_tasks(self, tasks):
        active = sum(t["status"] == "running" for t in tasks)
        pending = sum(t["status"] in ("ready", "conflict") for t in tasks)
        handoffs = sum(t["status"] == "handoff" for t in tasks)
        self.button.setText("◈  GAMEDEV • " + str(active) + " active • " +
                            str(pending) + " review • " + str(handoffs) + " GPT")
