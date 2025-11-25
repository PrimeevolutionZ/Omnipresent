from typing import Optional
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox

from services.download_pool_manager import DownloadPoolManager
from services.video_downloader import DownloadTask, DownloadTaskResult, DownloadProgress
from services.cookie_worker import CookieManagerAsync, CookieRunnable
from core.utils import Logger

logger = Logger("DownloadController")


class DownloadController(QObject):
    """Высокоуровневый контроллер загрузок для GUI. Работает через пул потоков."""

    # --- сигналы для UI ---
    progress = Signal(str)          # текст в статус-бар
    task_done = Signal(DownloadTaskResult)
    pool_status = Signal(int, int)  # активные, в очереди
    finished = Signal(bool)         # True – всё успешно
    cookie_progress = Signal(str)   # прогресс получения cookies

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # --- пул параллельных загрузок ---
        self.pool = DownloadPoolManager(max_threads=3)
        self.pool.task_progress.connect(self._on_task_progress)
        self.pool.task_finished.connect(self.task_done.emit)
        self.pool.pool_status.connect(self.pool_status.emit)

        # --- асинхронные cookies ---
        self.cookie_async = CookieManagerAsync()
        self._current_cookie_worker: Optional[CookieRunnable] = None

    # ---------- публичные методы ----------
    def start(self, tasks: list[DownloadTask]) -> None:
        """Запустить загрузки в пуле."""
        if self.pool.active_tasks or self.pool.queue:
            logger.warning("Загрузка уже запущена")
            return

        self.pool.add_tasks(tasks)

    def cancel(self) -> None:
        """Отменить все загрузки."""
        self.pool.cancel_all()
        logger.info("Загрузки отменены пользователем")

    def fetch_cookies_async(self) -> None:
        """Получить cookies в фоне."""
        if self._current_cookie_worker:
            logger.debug("Cookies уже запрашиваются")
            return
        worker = self.cookie_async.fetch_cookies(use_cache=False)
        worker.signals.progress.connect(self.cookie_progress.emit)
        worker.signals.finished.connect(self._on_cookies_finished)
        self._current_cookie_worker = worker

    # ---------- слоты ----------
    def _on_task_progress(self, index: int, progress: DownloadProgress):
        """Пересылаем живой прогресс в UI."""
        self.progress.emit(progress.message)

    def _on_cookies_finished(self, result):
        """Cookies получены – можно обновить UI."""
        self._current_cookie_worker = None
        if result.success:
            self.progress.emit(f"✅ Cookies обновлены через {result.source.value}")
        else:
            self.progress.emit("❌ Не удалось обновить cookies")

    # ---------- реализация DownloadEventHandler (для вызовов из пула) ----------
    def on_cookie_missing(self) -> bool:
        """UI-запрос на разрешение работы без cookies."""
        reply = QMessageBox.question(
            None,
            "Продолжить без cookies?",
            "⚠️ Cookies не найдены. Некоторые видео могут быть недоступны.\n\n"
            "Продолжить скачивание?",
            QMessageBox.Yes | QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def on_progress(self, message: str) -> None:
        self.progress.emit(message)

    def on_task_finished(self, result: DownloadTaskResult) -> None:
        self.task_done.emit(result)