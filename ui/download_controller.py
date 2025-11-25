from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox

from services.video_downloader import (
    VideoDownloader,
    DownloadTask,
    DownloadTaskResult,
    DownloadEventHandler,
)
from services.cookie_manager import CookieManager
from core.utils import Logger

logger = Logger("DownloadController")


class DownloadController(QObject):
    """Высокоуровневый контроллер загрузок для GUI."""

    progress  = Signal(str)
    finished  = Signal(bool)
    task_done = Signal(DownloadTaskResult)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._downloader = VideoDownloader(cookie_manager=CookieManager())
        self._thread: Optional[QThread] = None
        self._worker: Optional["DownloadWorker"] = None
        self._tasks: list[DownloadTask] = []
        self._cancelled = False

    # ---------- публичные методы ----------
    def start(self, tasks: list[DownloadTask]) -> None:
        """Запустить загрузку в отдельном потоке."""
        if self.is_running():
            logger.warning("Загрузка уже запущена")
            return

        self._cancelled = False
        self._tasks = tasks

        self._thread = QThread()
        self._worker = DownloadWorker(self._downloader, tasks, self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.emit)
        self._worker.task_done.connect(self._on_task_done)
        self._worker.finished.connect(self._on_finished)

        self._thread.start()
        logger.info("Загрузка запущена")

    def cancel(self) -> None:
        """Отменить текущую загрузку."""
        if self.is_running():
            self._cancelled = True
            self._downloader.cancel()
            logger.info("Загрузка отменена пользователем")

    def is_running(self) -> bool:
        """Проверка, выполняется ли загрузка."""
        return self._thread is not None and self._thread.isRunning()

    # ---------- слоты ----------
    def _on_task_done(self, result: DownloadTaskResult) -> None:
        self.task_done.emit(result)

    def _on_finished(self, success: bool) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._worker.deleteLater()
            self._thread = None
            self._worker = None
        self.finished.emit(success and not self._cancelled)

    # ---------- реализация DownloadEventHandler ----------
    def on_cookie_missing(self) -> bool:
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


# ---------- рабочий поток ----------
class DownloadWorker(QObject):
    progress  = Signal(str)
    task_done = Signal(DownloadTaskResult)
    finished  = Signal(bool)

    def __init__(
        self,
        downloader: VideoDownloader,
        tasks: list[DownloadTask],
        handler: DownloadEventHandler,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.downloader = downloader
        self.tasks = tasks
        self.handler = handler

    def run(self) -> None:
        try:
            for result in self.downloader.process_queue(self.tasks, self.handler):
                self.task_done.emit(result)
                self.progress.emit(result.message)
            self.finished.emit(True)
        except Exception as e:
            logger.error(f"Ошибка в потоке загрузки: {e}", exc=True)
            self.progress.emit(f"❌ Критическая ошибка: {e}")
            self.finished.emit(False)