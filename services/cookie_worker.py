# services/cookie_worker.py
from PySide6.QtCore import QObject, Signal, QRunnable
from typing import Optional
from services.cookie_extractor import CookieExtractorService, CookieResult
from core.utils import Logger

logger = Logger("CookieWorker")


class CookieSignals(QObject):
    finished = Signal(CookieResult)
    progress = Signal(str)
    error = Signal(str)


class CookieRunnable(QRunnable):
    def __init__(self, extractor: CookieExtractorService, use_cache: bool = True):
        super().__init__()
        self.extractor = extractor
        self.use_cache = use_cache
        self.signals = CookieSignals()

    def run(self):
        try:
            self.signals.progress.emit("🔍 Ищу cookies...")
            result = self.extractor.extract(use_cache=self.use_cache)
            if result.success:
                self.signals.progress.emit(f"✅ Cookies получены через {result.source.value}")
                self.signals.finished.emit(result)
            else:
                self.signals.progress.emit("❌ Автоматическое получение не удалось")
                self.signals.error.emit(result.error or "Unknown")
        except Exception as e:
            logger.error(f"Ошибка в CookieRunnable: {e}")
            self.signals.error.emit(str(e))


class CookieManagerAsync:
    """Асинхронный менеджер cookies."""
    def __init__(self):
        self.extractor = CookieExtractorService()

    def fetch_cookies(self, use_cache: bool = True) -> CookieRunnable:
        task = CookieRunnable(self.extractor, use_cache)
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(task)
        return task