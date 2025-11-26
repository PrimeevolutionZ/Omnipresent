# splash_screen.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QTime
from PySide6.QtGui import QFont, QIcon
import os


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
        self._animation_duration = 2500  # 2.5 секунды между вехами

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
        """Обновить статус загрузки"""
        self.status_label.setText(message)
        if detail:
            self.detail_label.setText(detail)
        if progress is not None:
            self.set_target_progress(progress)
        QApplication.processEvents()

    def set_target_progress(self, target_value: int):
        """Установить целевое значение прогресса с плавной анимацией"""
        if target_value == self._target_progress:
            return

        self._animation_start_time = QTime.currentTime()
        self._current_progress = self.progress.value()
        self._target_progress = min(target_value, 100)
        self._animation_timer.start()

    def _animate_progress(self):
        """Плавная анимация прогресса с easing-эффектом"""
        elapsed = self._animation_start_time.msecsTo(QTime.currentTime())
        if elapsed < 0:
            elapsed = 0

        progress_ratio = elapsed / self._animation_duration
        if progress_ratio >= 1.0:
            # Анимация завершена
            self.progress.setValue(self._target_progress)
            self._animation_timer.stop()
            return

        # Ease-in-out функция (Smoothstep) для плавной анимации
        eased = progress_ratio * progress_ratio * (3.0 - 2.0 * progress_ratio)

        # Вычисляем текущее значение
        current_value = int(
            self._current_progress + (self._target_progress - self._current_progress) * eased
        )
        self.progress.setValue(current_value)
        QApplication.processEvents()

    def finish(self):
        """Завершить загрузку с плавной финальной анимацией"""
        self.set_target_progress(100)
        self.status_label.setText("✅ Готово!")
        QTimer.singleShot(1500, self.accept)  # 1.5 секунды на финал


class DownloadWorker(QThread):
    """Поток для загрузки в фоне"""
    progress = Signal(str, int, str)  # message, percent, detail
    finished = Signal(bool, str)  # success, error_message

    def __init__(self):
        super().__init__()

    def run(self):
        """Выполнение загрузки"""
        try:
            from core.utils import ensure_binaries_with_progress
            for msg, percent, detail in ensure_binaries_with_progress():
                self.progress.emit(msg, percent, detail)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))