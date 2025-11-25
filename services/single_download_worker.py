from PySide6.QtCore import QObject, Signal, QRunnable
from typing import List, Optional
from models import DownloadTask, DownloadTaskResult
from services.video_downloader import VideoDownloader, DownloadProgress
from core.utils import Logger

logger = Logger("SingleDownloadWorker")


class DownloadSignals(QObject):
    progress = Signal(DownloadProgress)  # Живой прогресс
    finished = Signal(DownloadTaskResult)


class SingleDownloadRunnable(QRunnable):
    """Worker для одного видео с промежуточным прогрессом"""

    def __init__(
            self,
            task: DownloadTask,
            index: int,
            downloader: VideoDownloader,
            handler=None
    ):
        super().__init__()
        self.task = task
        self.index = index
        self.downloader = downloader
        self.handler = handler
        self.signals = DownloadSignals()

    def run(self):
        try:
            # Генерируем промежуточные события
            for progress in self.downloader.download_with_progress(self.task, self.index, self.handler):
                self.signals.progress.emit(progress)

                if progress.status == "finished":
                    result = DownloadTaskResult(
                        index=self.index,
                        status="success",
                        message=progress.message,
                        cookie_source=self.downloader.cookie_source
                    )
                    self.signals.finished.emit(result)
                    break

                elif progress.status == "error":
                    result = DownloadTaskResult(
                        index=self.index,
                        status="unknown",
                        message=progress.message
                    )
                    self.signals.finished.emit(result)
                    break

        except Exception as e:
            logger.error(f"Критическая ошибка в worker #{self.index}: {e}", exc=True)
            result = DownloadTaskResult(
                index=self.index,
                status="unknown",
                message=f"Сбой: {e}"
            )
            self.signals.finished.emit(result)