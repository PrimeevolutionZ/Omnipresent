import os
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from services.cookie_extractor import (
    CookieExtractorService,
    CookieSource,
)
from core.config import cfg
from core.utils import Logger

logger = Logger("CookieManager")

# --- UI-утилиты (без PySide6) ---
class CookieUIGuide:
    """Тексты для GUI, если cookies не найдены или устарели."""

    MANUAL_INSTRUCTION = (
        "Не удалось автоматически получить cookies.\n\n"
        "Ручной способ:\n"
        "1. Установите расширение 'Get cookies.txt LOCALLY' для браузера\n"
        "2. Откройте YouTube и экспортируйте cookies\n"
        "3. Сохраните файл 'cookies.txt' в папку с программой"
    )

    CHROME_SUGGESTION = (
        "\n\n💡 Совет: Установите Google Chrome для автоматического получения cookies"
    )

# --- Состояние cookies ---
class CookieState(Enum):
    MISSING = "missing"
    STALE = "stale"
    FRESH = "fresh"
    AUTO_FETCHED = "auto_fetched"

@dataclass
class CookieStatus:
    state: CookieState
    source: Optional[CookieSource]
    age_hours: Optional[float]
    error: Optional[str] = None

    @property
    def is_ready(self) -> bool:
        return self.state in (CookieState.FRESH, CookieState.AUTO_FETCHED)

# --- Основной менеджер ---
class CookieManager:
    def __init__(self, extractor: Optional[CookieExtractorService] = None):
        self.extractor = extractor or CookieExtractorService()
        self._last_status: Optional[CookieStatus] = None

    # --- Публичные методы ---
    def get_status(self) -> CookieStatus:
        """Получить текущее состояние cookies (с кэшированием)."""
        if self._last_status:
            return self._last_status

        # Проверяем кэш
        cached = self.extractor.get_cached_age()
        if cached is not None:
            if cached < 24:
                self._last_status = CookieStatus(
                    state=CookieState.FRESH,
                    source=CookieSource.MANUAL,
                    age_hours=cached
                )
                return self._last_status
            else:
                self._last_status = CookieStatus(
                    state=CookieState.STALE,
                    source=CookieSource.MANUAL,
                    age_hours=cached
                )
                return self._last_status

        # Пробуем автоматически
        result = self.extractor.extract(use_cache=True)
        if result.success:
            self._last_status = CookieStatus(
                state=CookieState.AUTO_FETCHED,
                source=result.source,
                age_hours=0
            )
            return self._last_status

        # 3. Нет cookies
        self._last_status = CookieStatus(
            state=CookieState.MISSING,
            source=None,
            age_hours=None,
            error=result.error
        )
        return self._last_status

    def try_auto_fetch(self) -> CookieStatus:
        """Попытаться автоматически получить cookies (с обновлением кэша)."""
        logger.info("Попытка автоматического обновления cookies...")
        result = self.extractor.extract(use_cache=False)
        if result.success:
            self._last_status = CookieStatus(
                state=CookieState.AUTO_FETCHED,
                source=result.source,
                age_hours=0
            )
            logger.info(f"Cookies успешно получены через {result.source.value}")
        else:
            self._last_status = CookieStatus(
                state=CookieState.MISSING,
                source=None,
                age_hours=None,
                error=result.error
            )
            logger.error(f"Авто-обновление cookies провалилось: {result.error}")
        return self._last_status

    def get_manual_guide(self) -> str:
        """Получить инструкцию для ручного ввода cookies."""
        text = CookieUIGuide.MANUAL_INSTRUCTION
        try:
            from selenium import webdriver
        except ImportError:
            text += CookieUIGuide.CHROME_SUGGESTION
        return text

    def get_cookie_file_path(self) -> str:
        """Путь к cookies.txt (для ручного ввода)."""
        return cfg.cookies_path

    def is_cookie_file_exists(self) -> bool:
        """Существует ли cookies.txt."""
        return os.path.exists(cfg.cookies_path)

    # --- UI-helpers (без PySide6) ---
    def get_status_label(self) -> tuple[str, str]:
        """Возвращает (текст, стиль CSS) для отображения в UI."""
        status = self.get_status()
        if status.state == CookieState.FRESH:
            return ("✅ Cookies актуальны", "color: #4CAF50;")
        elif status.state == CookieState.STALE:
            return ("⚠️ Cookies устарели", "color: #FFC107;")
        elif status.state == CookieState.AUTO_FETCHED:
            return ("✅ Cookies получены", "color: #4CAF50;")
        else:
            return ("❌ Cookies не найдены", "color: #F44336;")

    # --- Сброс кэша (при необходимости) ---
    def reset(self):
        """Сбросить кэш и статус."""
        self._last_status = None
        cache_file = os.path.join(cfg.base_dir, ".cookies_cache.pkl")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                logger.info("Кэш cookies сброшен")
            except Exception as e:
                logger.error(f"Не удалось сбросить кэш: {e}")