from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QSpinBox,
                               QLabel, QFrame)
from PySide6.QtCore import Qt, Signal


class TimeSpinBox(QSpinBox):

    def __init__(self, max_val=59):
        super().__init__()
        self.setRange(0, max_val)
        self.setButtonSymbols(QSpinBox.NoButtons)  # Убираем стрелочки
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(35)

    def textFromValue(self, val):
        return f"{val:02d}"


class TimeSectionWidget(QWidget):
    """Группа: Начало (ЧЧ:ММ:СС) — Конец (ЧЧ:ММ:СС)"""

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.start_h = TimeSpinBox(23)
        self.start_m = TimeSpinBox(59)
        self.start_s = TimeSpinBox(59)

        self.end_h = TimeSpinBox(23)
        self.end_m = TimeSpinBox(59)
        self.end_s = TimeSpinBox(59)

        # Добавляем виджеты (Начало)
        for w in [self.start_h, self.start_m, self.start_s]:
            layout.addWidget(w)

        layout.addWidget(QLabel(" — "))

        # Добавляем виджеты (Конец)
        for w in [self.end_h, self.end_m, self.end_s]:
            layout.addWidget(w)

    def get_seconds(self):
        """Возвращает (start_sec, end_sec) или None"""
        start = (self.start_h.value() * 3600 +
                 self.start_m.value() * 60 +
                 self.start_s.value())

        end = (self.end_h.value() * 3600 +
               self.end_m.value() * 60 +
               self.end_s.value())

        # Проверка на валидность
        if start >= end and end > 0:
            return None
        return (start, end)


class UrlInputRow(QWidget):
    """Строка: [Поле ввода URL] [Виджет времени (скрыт/показан)]"""
    text_started = Signal()

    def __init__(self, index):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 5)
        self.layout.setSpacing(10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(f"Ссылка #{index + 1}")
        self.url_input.textChanged.connect(self._on_text_change)

        self.time_widget = TimeSectionWidget()
        self.time_widget.setVisible(False)  # Скрыто по умолчанию

        self.layout.addWidget(self.url_input)
        self.layout.addWidget(self.time_widget)

        self._emitted = False

    def _on_text_change(self, text):
        if text and not self._emitted:
            self.text_started.emit()
            self._emitted = True

    def toggle_time(self, show):
        """Показать/скрыть виджет времени с обновлением layout."""
        self.time_widget.setVisible(show)
        self.time_widget.updateGeometry()
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def get_url(self):
        return self.url_input.text().strip()