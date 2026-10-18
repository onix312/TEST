"""Interactive TOP-DOWN 2D agent office.

The scene is intentionally drawn with QPainter instead of external images: it
works offline and ships with the Windows EXE. The floor plan uses absolute world
coordinates, scroll-to-zoom and drag-to-pan. Agents are bound to actual task IDs.
"""
from __future__ import annotations

from math import hypot
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout


PALETTE = {
    "floor": "#473745", "wall": "#241d33", "trim": "#826386",
    "rug": "#55455d", "desk": "#996d59", "wood": "#c09271",
    "screen": "#352a52", "paper": "#e2cfb2", "plant": "#659b7a",
    "running": "#aa8bff", "ready": "#f4c878", "handoff": "#efa971",
    "conflict": "#ff8195", "failed": "#ff8195", "merged": "#78dfb3",
    "queued": "#7f748c", "idle": "#928b9e", "interrupted": "#e9ae7d",
}
AGENTS = ["CODEX 1", "CODEX 2", "GPT LUNA", "GPT SOL", "QA", "DIRECTOR"]
SEATS = [
    (140, 200), (356, 200), (572, 200), (790, 200),
    (275, 455), (680, 455),
]
WORLD = QRectF(0, 0, 960, 630)


class PixelOffice(QWidget):
    """An interactive 90° overhead 2D office; never isometric."""
    taskSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(380)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tasks = []
        self.chosen = None
        self.tick = 0
        self.zoom = 1.0
        self.offset = QPointF(0, 0)
        self.dragging = False
        self.drag_from = QPointF()
        self.moved = False
        self.hits = []
        self.reduced_motion = False
        self.walkers = {}
        timer = QTimer(self)
        timer.timeout.connect(self.animate)
        timer.start(250)
        self._timer = timer

    def animate(self):
        if not self.reduced_motion and self.isVisible():
            self.tick += 1
            for walker in self.walkers.values():
                x, y = walker["pos"]
                tx, ty = walker["target"]
                length = hypot(tx - x, ty - y)
                if length > 2:
                    step = min(length, 10)
                    walker["pos"] = (x + step * (tx-x)/length, y + step * (ty-y)/length)
                else:
                    walker["pos"] = walker["target"]
            self.update()

    def set_reduced_motion(self, value):
        self.reduced_motion = bool(value)
        self.update()

    def set_tasks(self, tasks):
        self.tasks = [dict(t) for t in tasks]
        visible = self.visible_tasks()
        current = set()
        for i, task in enumerate(visible[:len(SEATS)]):
            task_id = task["id"]
            current.add(task_id)
            target = self.destination(i, task)
            actor = self.walkers.setdefault(task_id, {"pos": (470, 350), "target": target})
            actor["target"] = target
            if self.reduced_motion:
                actor["pos"] = target
        self.walkers = {key: val for key, val in self.walkers.items() if key in current}
        self.update()

    def visible_tasks(self):
        priority = ("running", "ready", "conflict", "handoff",
                    "failed", "queued", "merged", "interrupted")
        return sorted(self.tasks, key=lambda item:
                      priority.index(item.get("status")) if item.get("status") in priority
                      else len(priority))

    def destination(self, slot, task):
        if task.get("status") == "handoff":
            return (350 + (slot % 2) * 65, 485)
        if task.get("status") in ("conflict", "failed", "ready"):
            return (740 + (slot % 2) * 70, 485)
        return SEATS[slot]

    def select_task(self, task_id):
        self.chosen = task_id
        self.update()

    def reset_camera(self):
        self.zoom = 1.0
        self.offset = QPointF()
        self.update()

    def _fit(self):
        scale = min(self.width() / WORLD.width(), self.height() / WORLD.height())
        scale = max(scale, .01) * self.zoom
        center = QPointF(self.width() / 2, self.height() / 2)
        shift = QPointF(center.x() - WORLD.width() * scale / 2 + self.offset.x(),
                        center.y() - WORLD.height() * scale / 2 + self.offset.y())
        return scale, shift

    def _to_world(self, screen):
        scale, shift = self._fit()
        return QPointF((screen.x() - shift.x()) / scale,
                       (screen.y() - shift.y()) / scale)

    def wheelEvent(self, event):
        old_scale, old_shift = self._fit()
        before = self._to_world(event.position())
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.zoom = max(.7, min(2.6, self.zoom * factor))
        new_scale, new_shift = self._fit()
        self.offset += QPointF(
            (before.x() * old_scale + old_shift.x()) -
            (before.x() * new_scale + new_shift.x()),
            (before.y() * old_scale + old_shift.y()) -
            (before.y() * new_scale + new_shift.y()),
        )
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.moved = False
            self.drag_from = event.position()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.position() - self.drag_from
            if abs(delta.x()) + abs(delta.y()) > 3:
                self.moved = True
            self.offset += delta
            self.drag_from = event.position()
            self.update()
        else:
            world = self._to_world(event.position())
            over = any(rect.contains(world) for rect, task_id in self.hits)
            self.setCursor(Qt.CursorShape.PointingHandCursor if over else Qt.CursorShape.OpenHandCursor)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            if not self.moved:
                world = self._to_world(event.position())
                for rect, task_id in reversed(self.hits):
                    if rect.contains(world):
                        self.chosen = task_id
                        self.taskSelected.emit(task_id)
                        break
            self.update()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if not any(rect.contains(self._to_world(event.position())) for rect, _ in self.hits):
            self.reset_camera()

    def _rect(self, p, x, y, w, h, color, radius=0):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(x, y, w, h), radius, radius)

    def _label(self, p, x, y, text, size=12, color="#eaddf0", bold=False):
        p.setPen(QColor(color))
        p.setFont(QFont("Consolas", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
        p.drawText(QPointF(x, y), str(text))

    def _room(self, p, x, y, w, h, title, floor):
        self._rect(p, x, y, w, h, floor, 8)
        p.setPen(QPen(QColor("#927394"), 5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(x, y, w, h), 7, 7)
        self._label(p, x + 15, y + 25, title, 12, "#f5dbff", True)

    def _desk(self, p, x, y, number):
        # Top-down desks and flat overhead monitor panels, not a side view.
        self._rect(p, x - 73, y - 80, 146, 101, "#271f30", 7)
        self._rect(p, x - 68, y - 76, 136, 90, PALETTE["desk"], 6)
        self._rect(p, x - 61, y - 68, 119, 9, PALETTE["wood"], 2)
        self._rect(p, x - 46, y - 55, 91, 55, PALETTE["screen"], 6)
        self._rect(p, x - 40, y - 48, 79, 41, "#23293f", 4)
        for line in range(3):
            self._rect(p, x - 33, y - 41 + 11 * line, 53 - 7 * line, 4,
                       "#b68ee6" if line == number % 3 else "#6592ba", 1)
        self._rect(p, x - 23, y + 2, 46, 7, "#dbc9ce", 2)
        self._rect(p, x - 27, y + 24, 54, 27, "#413646", 9)

    def _avatar(self, p, x, y, active, color):
        bob = (2 if self.tick % 2 else 0) if active and not self.reduced_motion else 0
        self._rect(p, x - 19, y + 43, 38, 22, "#31263e", 5)
        self._rect(p, x - 18, y + 39 - bob, 36, 24, color, 6)
        self._rect(p, x - 12, y + 28 - bob, 24, 19, "#ecc49f", 5)
        self._rect(p, x - 13, y + 24 - bob, 27, 8, "#533a58", 3)
        self._rect(p, x - 7, y + 37 - bob, 4, 4, "#37263e", 1)
        self._rect(p, x + 6, y + 37 - bob, 4, 4, "#37263e", 1)

    def _agent_model(self, task):
        label = (task.get("model") or "").lower()
        route = task.get("route") or ""
        if task.get("backend") == "chatgpt" or route.startswith("chatgpt_"):
            if "luna" in label or "fast" in route:
                return "GPT LUNA"
            if "astra" in label or "deep" in route:
                return "GPT ASTRA"
            return "GPT SOL"
        return (task.get("role") or "CODEX").upper()[:13]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.fillRect(self.rect(), QColor("#15111d"))
        scale, shift = self._fit()
        p.translate(shift)
        p.scale(scale, scale)
        self._rect(p, 6, 6, 948, 618, "#211a2d", 15)
        self._rect(p, 20, 20, 920, 590, PALETTE["floor"], 10)
        for x in range(30, 940, 30):
            for y in range(30, 608, 30):
                self._rect(p, x, y, 1, 1, "#594454")
        self._room(p, 36, 39, 884, 335, "DEVELOPMENT • GAMEDEV AI OFFICE", "#453544")
        self._room(p, 36, 393, 565, 203, "CHATGPT / GDD / PLANNING", "#42364d")
        self._room(p, 619, 393, 301, 203, "UNITY • QA", "#35414b")
        self._rect(p, 72, 71, 818, 17, "#6d506c", 5)
        self._rect(p, 72, 358, 818, 10, "#644a62", 3)
        # Library bookshelf and large overhead GDD planning board.
        self._rect(p, 67, 449, 133, 97, "#9e795d", 6)
        for i, color in enumerate(("#a8c58e", "#b093cb", "#dfb07b", "#c4a3ae") * 3):
            self._rect(p, 77 + i * 9, 462, 7, 53, color)
        self._rect(p, 210, 425, 343, 138, "#2d2840", 8)
        self._rect(p, 221, 436, 321, 115, "#756688", 4)
        for i in range(6):
            self._rect(p, 238 + i * 46, 451 + (i % 2) * 24, 38, 22,
                       ["#e2b47c", "#9ac6bf", "#c5a3ed"][i % 3], 3)
        self._rect(p, 658, 455, 224, 97, "#8c7268", 9)
        self._rect(p, 674, 469, 192, 64, "#323952", 5)
        self._rect(p, 689, 478, 156, 8, "#8fcfbd", 2)
        self._rect(p, 689, 496, 101, 7, "#b29bdf", 2)
        self._rect(p, 689, 515, 133, 7, "#dcaf80", 2)
        for x in (47, 907):
            self._rect(p, x, 106, 22, 42, "#765a58", 5)
            self._rect(p, x - 5, 96, 31, 26, PALETTE["plant"], 13)
        statuses = self.visible_tasks()
        self.hits = []
        waiting = [t for t in self.tasks if t.get("status") == "queued"]
        self._rect(p, 82, 91, 788, 31, "#30263e", 6)
        self._label(p, 91, 111, "QUEUE", 10, "#dbc0ec", True)
        for n, job in enumerate(waiting[:5]):
            xq = 170 + n * 134
            self._rect(p, xq, 95, 127, 23,
                       "#876c9e" if job["id"] == self.chosen else "#554361", 4)
            self._label(p, xq + 5, 111, job["text"][:13], 9, "#f2e5f4")
            self.hits.append((QRectF(xq, 95, 127, 23), job["id"]))
        if len(waiting) > 5:
            self._label(p, 850, 111, "+" + str(len(waiting)-5), 9)
        for i, (x, y) in enumerate(SEATS):
            if i < 4:
                self._desk(p, x, y, i)
            task = statuses[i] if i < len(statuses) else None
            status = task.get("status", "idle") if task else "idle"
            color = PALETTE.get(status, PALETTE["idle"])
            if task:
                actor = self.walkers.get(task["id"])
                ax, ay = actor["pos"] if actor else (x, y)
                self._avatar(p, ax, ay, status == "running",
                             "#8762be" if task.get("backend") == "chatgpt" else "#6baab1")
                label = self._agent_model(task)
                self._rect(p, x - 76, y + 79, 152, 42, "#2c2637", 8)
                self._label(p, x - 67, y + 95, label[:17], 11, "#eadcf3", True)
                self._rect(p, x - 69, y + 104, 7, 7, color, 2)
                self._label(p, x - 56, y + 112, status.upper()[:15], 10, color, True)
                hit = QRectF(x - 82, y - 78, 164, 203)
                self.hits.append((hit, task["id"]))
                self.hits.append((QRectF(ax-24, ay+22, 48, 48), task["id"]))
                if task["id"] == self.chosen:
                    p.setPen(QPen(QColor("#e8cbff"), 4))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRoundedRect(hit, 9, 9)
            elif i < 4:
                self._avatar(p, x, y, False, "#666071")
                self._label(p, x - 35, y + 104, "FREE", 10, "#c7b7d1", True)
        self._label(p, 43, 616, "DRAG TO PAN  •  SCROLL TO ZOOM  •  CLICK AGENT", 10, "#bca5cd")
        p.end()


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
