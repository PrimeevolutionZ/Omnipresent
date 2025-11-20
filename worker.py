from PySide6.QtCore import QObject, Signal, Slot
from downloader import VideoDownloader
from utils import Logger


class DownloadWorker(QObject):
    # Сигналы для общения с GUI
    progress_update = Signal(str)  # Текст статуса
    finished = Signal(bool)  # Успех/Провал
    log_message = Signal(str, str)  # Сообщение, Уровень

    def __init__(self, tasks, parent_window=None):
        super().__init__()
        self.tasks = tasks
        self.logger = Logger()
        self.parent_window = parent_window  # Для показа диалогов

    @Slot()
    def run(self):
        downloader = VideoDownloader(self.logger)
        success = False
        try:
            for status in downloader.process_queue(self.tasks, self.parent_window):
                self.progress_update.emit(status)

            success = True
            self.finished.emit(True)
        except Exception as e:
            self.progress_update.emit(f"Критическая ошибка: {e}")
            self.finished.emit(False)