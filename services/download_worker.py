from PySide6.QtCore import QObject, Signal
from typing import List

from services.video_downloader import (
    VideoDownloader,
    DownloadTask,
    DownloadTaskResult,
    DownloadEventHandler,
)
from core.utils import Logger

logger = Logger("DownloadWorker")


class DownloadWorker(QObject):
    """Фоновый поток для VideoDownloader."""

    progress = Signal(str)          # str-сообщение в статус-бар
    task_done = Signal(DownloadTaskResult)  # после каждого видео
    finished = Signal(bool)         # True — всё успешно

    def __init__(
        self,
        downloader: VideoDownloader,
        tasks: List[DownloadTask],
        handler: DownloadEventHandler,
    ):
        super().__init__()
        self.downloader = downloader
        self.tasks = tasks
        self.handler = handler

    def run(self):
        """Выполняется в QThread."""
        try:
            for result in self.downloader.process_queue(self.tasks, self.handler):
                self.task_done.emit(result)
                self.progress.emit(result.message)

            self.finished.emit(True)

        except Exception as e:
            logger.error(f"Критическая ошибка в потоке: {e}")
            self.progress.emit(f"❌ Критическая ошибка: {e}")
            self.finished.emit(False)