import os
import json
import time
import tempfile
import subprocess
import pickle
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from core.config import cfg
from core.utils import Logger

logger = Logger("CookieExtractor")

# --- Протоколы и модели ---
class CookieSource(Enum):
    SELENIUM = "selenium"
    ROOKIEPY = "rookiepy"
    CDP = "chrome_cdp"
    MANUAL = "manual"

@dataclass
class CookieResult:
    success: bool
    cookies: List[dict]
    source: Optional[CookieSource]
    error: Optional[str] = None
    age_hours: Optional[float] = None

# --- Кэш ---
class CookieCache:
    CACHE_FILE = os.path.join(cfg.base_dir, ".cookies_cache.pkl")
    TTL = 86400  # 24 часа

    @staticmethod
    def get() -> Optional[CookieResult]:
        if not os.path.exists(CookieCache.CACHE_FILE):
            return None
        try:
            with open(CookieCache.CACHE_FILE, 'rb') as f:
                cached = pickle.load(f)
            if time.time() - cached['timestamp'] > CookieCache.TTL:
                return None
            return cached['result']
        except Exception as e:
            logger.error(f"Ошибка чтения кэша cookies: {e}")
            return None

    @staticmethod
    def set(result: CookieResult):
        try:
            with open(CookieCache.CACHE_FILE, 'wb') as f:
                pickle.dump({'timestamp': time.time(), 'result': result}, f)
        except Exception as e:
            logger.error(f"Ошибка записи кэша cookies: {e}")

# --- Базовый интерфейс стратегии ---
class ExtractionStrategy:
    def extract(self) -> CookieResult:
        raise NotImplementedError

# --- Selenium стратегия ---
class SeleniumExtractor(ExtractionStrategy):
    def __init__(self):
        self._driver = None

    def _get_driver(self):
        if self._driver is None:
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options

                options = Options()
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--log-level=3")
                options.add_experimental_option('excludeSwitches', ['enable-logging'])

                # Используем временный профиль, чтобы не трогать основной
                profile_dir = tempfile.mkdtemp(prefix="yt_cookies_profile_")
                options.add_argument(f"--user-data-dir={profile_dir}")

                self._driver = webdriver.Chrome(options=options)
            except Exception as e:
                logger.error(f"Не удалось запустить Selenium: {e}")
        return self._driver

    def extract(self) -> CookieResult:
        try:
            driver = self._get_driver()
            if not driver:
                return CookieResult(success=False, cookies=[], source=None, error="Selenium не доступен")

            driver.get("https://www.youtube.com")
            time.sleep(3)
            cookies = driver.get_cookies()

            filtered = [c for c in cookies if 'youtube.com' in c.get('domain', '') or 'google.com' in c.get('domain', '')]

            return CookieResult(success=True, cookies=filtered, source=CookieSource.SELENIUM)
        except Exception as e:
            logger.error(f"Ошибка извлечения cookies через Selenium: {e}")
            return CookieResult(success=False, cookies=[], source=None, error=str(e))

# --- RookiePy стратегия ---
class RookiePyExtractor(ExtractionStrategy):
    def extract(self) -> CookieResult:
        try:
            import rookiepy
            cookies = rookiepy.chrome()
            filtered = [c for c in cookies if 'youtube.com' in c.get('domain', '') or 'google.com' in c.get('domain', '')]
            return CookieResult(success=True, cookies=filtered, source=CookieSource.ROOKIEPY)
        except Exception as e:
            logger.error(f"Ошибка извлечения cookies через rookiepy: {e}")
            return CookieResult(success=False, cookies=[], source=None, error=str(e))

# --- Chrome CDP стратегия (без убийства процессов) ---
class ChromeCDPExtractor(ExtractionStrategy):
    CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]

    def _find_chrome(self) -> Optional[str]:
        for path in self.CHROME_PATHS:
            if os.path.exists(path):
                return path
        return None

    def _is_debug_port_open(self, port: int = 9222) -> bool:
        try:
            import requests
            response = requests.get(f"http://127.0.0.1:{port}/json", timeout=1)
            return response.status_code == 200
        except:
            return False

    def extract(self) -> CookieResult:
        try:
            import requests
            import websocket
        except ImportError:
            return CookieResult(success=False, cookies=[], source=None, error="Отсутствуют библиотеки для CDP")

        chrome_exe = self._find_chrome()
        if not chrome_exe:
            return CookieResult(success=False, cookies=[], source=None, error="Chrome не найден")

        if self._is_debug_port_open():
            return self._get_cookies_from_existing_debug_port()

        # Запускаем Chrome в дебаг-режиме с временным профилем
        profile_dir = tempfile.mkdtemp(prefix="yt_cdp_profile_")
        port = 9222
        args = [
            chrome_exe,
            "--headless=new",
            "--disable-gpu",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--disable-fre",
            "about:blank"
        ]

        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        try:
            time.sleep(3)
            ws_url = self._get_ws_url(port)
            if ws_url:
                cookies = self._fetch_cookies(ws_url)
                filtered = [c for c in cookies if 'youtube.com' in c.get('domain', '') or 'google.com' in c.get('domain', '')]
                return CookieResult(success=True, cookies=filtered, source=CookieSource.CDP)
            else:
                return CookieResult(success=False, cookies=[], source=None, error="Не удалось подключиться к Chrome")
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    def _get_ws_url(self, port: int) -> Optional[str]:
        import requests
        for _ in range(5):
            try:
                tabs = requests.get(f"http://127.0.0.1:{port}/json", timeout=1).json()
                if tabs:
                    return tabs[0].get("webSocketDebuggerUrl")
            except:
                time.sleep(1)
        return None

    def _fetch_cookies(self, ws_url: str) -> List[dict]:
        import websocket
        ws = websocket.create_connection(ws_url)
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        result = ws.recv()
        ws.close()
        return json.loads(result).get("result", {}).get("cookies", [])

# --- Основной менеджер ---
class CookieExtractorService:
    def __init__(self):
        self.strategies = [
            SeleniumExtractor(),
            RookiePyExtractor(),
            ChromeCDPExtractor()
        ]

    def extract(self, use_cache: bool = True) -> CookieResult:
        if use_cache:
            cached = CookieCache.get()
            if cached:
                logger.info("Используем кэшированные cookies")
                return cached

        for strategy in self.strategies:
            result = strategy.extract()
            if result.success:
                result.age_hours = 0
                CookieCache.set(result)
                logger.info(f"Cookies получены через {result.source.value}")
                return result

        logger.error("Все стратегии извлечения cookies провалились")
        return CookieResult(success=False, cookies=[], error="Не удалось получить cookies")

    def get_cached_age(self) -> Optional[float]:
        cached = CookieCache.get()
        if cached:
            return (time.time() - os.path.getmtime(CookieCache.CACHE_FILE)) / 3600
        return None