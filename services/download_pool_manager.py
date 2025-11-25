from PySide6.QtCore import QObject, Signal, QThreadPool
from typing import List, Dict
from collections import deque

from models import DownloadTask
from services.single_download_worker import SingleDownloadRunnable
from services.video_downloader import VideoDownloader
from core.utils import Logger

logger = Logger("DownloadPoolManager")


class DownloadPoolManager(QObject):
    """Управляет пулом параллельных загрузок"""

    # Сигналы для UI
    task_progress = Signal(int, object)  # index, DownloadProgress
    task_finished = Signal(int, object)  # index, DownloadTaskResult
    pool_status = Signal(int, int)  # active, queued

    def __init__(self, max_threads: int = 3):
        super().__init__()
        self.pool = QThreadPool()
        self.pool.setMaxThreadCount(max_threads)
        self.downloader = VideoDownloader()
        self.active_tasks: Dict[int, SingleDownloadRunnable] = {}
        self.queue = deque()

    def add_tasks(self, tasks: List[DownloadTask]):
        """Добавить список задач в очередь"""
        for idx, task in enumerate(tasks, 1):
            self.queue.append((idx, task))

        self._process_queue()

    def _process_queue(self):
        """Запускаем задачи из очереди, пока есть свободные слоты"""
        while self.queue and len(self.active_tasks) < self.pool.maxThreadCount():
            idx, task = self.queue.popleft()

            worker = SingleDownloadRunnable(
                task=task,
                index=idx,
                downloader=self.downloader
            )

            # Подключаем сигналы
            worker.signals.progress.connect(
                lambda prog, idx=idx: self.task_progress.emit(idx, prog)
            )
            worker.signals.finished.connect(
                lambda res, idx=idx: self._on_task_finished(idx, res)
            )

            self.active_tasks[idx] = worker
            self.pool.start(worker)

        self._update_status()

    def _on_task_finished(self, index: int, result):
        """Когда задача завершена, запускаем следующую из очереди"""
        self.active_tasks.pop(index, None)
        self.task_finished.emit(index, result)
        self._process_queue()  # Запускаем следующую задачу
        self._update_status()

    def _update_status(self):
        """Обновляем статус пула"""
        active = len(self.active_tasks)
        queued = len(self.queue)
        self.pool_status.emit(active, queued)

    def cancel_all(self):
        """Отменить все активные задачи"""
        # QRunnable нельзя принудительно остановить, но можно пометить отмененными
        self.downloader.cancel()
        self.queue.clear()
        logger.info("Все загрузки отменены")