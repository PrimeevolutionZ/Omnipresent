# splash_screen.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QTime
from PySide6.QtGui import QFont, QIcon
import os
import time


class SplashScreen(QDialog):
    """Окно загрузки при первом запуске"""

    Accepted = QDialog.DialogCode.Accepted
    Rejected = QDialog.DialogCode.Rejected

    def __init__(self, icon_path: str = None):
        super().__init__()
        self.setWindowTitle("Omnipresent — Инициализация")
        self.setFixedSize(500, 250)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Анимационные переменные
        self._current_progress = 0
        self._target_progress = 0
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(50)  # 20 fps
        self._animation_timer.timeout.connect(self._animate_progress)
        self._animation_start_time = QTime()
        self._animation_duration = 300  # 0.3 сек между вехами

        # Защита от спама и отката
        self._last_update_time = 0
        self._min_update_interval = 50  # ms
        self._max_progress = 0

        self._setup_ui()
        self._center_on_screen()

    def _setup_ui(self):
        """Построение интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("🚀 Omnipresent")
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00d4ff;")

        # Подзаголовок
        subtitle = QLabel("Подготовка к работе...")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #eaeaea; font-size: 14px;")

        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #aaa; font-size: 12px; padding: 10px;"
        )

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3a4a6b;
                border-radius: 8px;
                background-color: #252d42;
                text-align: center;
                color: #eaeaea;
                font-size: 13px;
                font-weight: bold;
                min-height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00d4ff, stop:1 #0099cc
                );
                border-radius: 6px;
            }
        """)

        # Детали
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet(
            "color: #666; font-size: 11px; font-style: italic;"
        )

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail_label)
        layout.addStretch()

        # Стиль окна
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e
                );
                border: 2px solid #00d4ff;
                border-radius: 10px;
            }
        """)

    def _center_on_screen(self):
        """Центрирование на экране"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def update_status(self, message: str, progress: int = None, detail: str = ""):
        """Обновить статус загрузки с защитой от спама"""
        current_time = time.time() * 1000
        if current_time - self._last_update_time < self._min_update_interval:
            return
        self._last_update_time = current_time

        self.status_label.setText(message)
        if detail:
            self.detail_label.setText(detail)

        if progress is not None:
            if progress <= self._max_progress:
                return
            self._max_progress = progress
            self.set_target_progress(progress)
        QApplication.processEvents()

    def set_target_progress(self, target_value: int):
        """Установить целевое значение прогресса с плавной анимацией"""
        if target_value <= self._target_progress:
            return

        self._animation_start_time = QTime.currentTime()
        self._current_progress = self.progress.value()
        self._target_progress = min(target_value, 100)

        # Адаптивная длительность
        diff = abs(self._target_progress - self._current_progress)
        self._animation_duration = 200 if diff > 10 else 300
        self._animation_timer.start()

    def _animate_progress(self):
        """Плавная анимация прогресса с easing-эффектом"""
        elapsed = self._animation_start_time.msecsTo(QTime.currentTime())
        if elapsed < 0:
            elapsed = 0

        progress_ratio = elapsed / self._animation_duration
        if progress_ratio >= 1.0:
            self.progress.setValue(self._target_progress)
            self._animation_timer.stop()
            return

        eased = progress_ratio * progress_ratio * (3.0 - 2.0 * progress_ratio)
        current_value = int(
            self._current_progress + (self._target_progress - self._current_progress) * eased
        )
        self.progress.setValue(current_value)
        QApplication.processEvents()

    def finish(self):
        """Завершить загрузку с плавной финальной анимацией"""
        self.set_target_progress(100)
        self.status_label.setText("✅ Готово!")
        if self.isVisible():
            QTimer.singleShot(1500, self.accept)


class DownloadWorker(QThread):
    """Поток для загрузки в фоне"""
    progress = Signal(str, int, str)  # message, percent, detail
    finished = Signal(bool, str)  # success, error_message

    def __init__(self):
        super().__init__()
        self._min_signal_interval = 50  # ms

    def run(self):
        """Выполнение загрузки с ограничением скорости сигналов"""
        try:
            from core.utils import ensure_binaries_with_progress
            last_emit_time = 0
            for msg, percent, detail in ensure_binaries_with_progress():
                current_time = time.time() * 1000
                if current_time - last_emit_time < self._min_signal_interval:
                    continue
                self.progress.emit(msg, percent, detail)
                last_emit_time = current_time
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))