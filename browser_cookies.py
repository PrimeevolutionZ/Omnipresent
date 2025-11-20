import os
import json
import time
import subprocess
from config import cfg

# --- Импорты (тихая проверка) ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options

    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

try:
    import requests
    import websocket
    import psutil

    HAS_CDP_LIBS = True
except ImportError:
    HAS_CDP_LIBS = False

try:
    import browser_cookie3

    HAS_BC3 = True
except ImportError:
    HAS_BC3 = False

try:
    import rookiepy

    HAS_ROOKIE = True
except ImportError:
    HAS_ROOKIE = False


class SeleniumCookieExtractor:
    """Извлечение cookies через Selenium - самый надёжный метод"""

    @staticmethod
    def get_cookies_via_selenium():
        if not HAS_SELENIUM:
            return None

        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--log-level=3")  # Только критические ошибки
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.youtube.com")
            time.sleep(3)

            cookies = driver.get_cookies()
            driver.quit()

            # Фильтруем только YouTube/Google
            filtered = []
            for c in cookies:
                domain = c.get('domain', '')
                if 'youtube.com' in domain or 'google.com' in domain:
                    filtered.append(c)

            return filtered if filtered else None

        except Exception:
            return None


class ChromeDebugger:
    """Извлечение cookies через Chrome DevTools Protocol (запасной вариант)"""

    CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    USER_DATA_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")

    @staticmethod
    def find_chrome():
        for path in ChromeDebugger.CHROME_PATHS:
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def kill_chrome():
        if not HAS_CDP_LIBS:
            return False

        killed = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome.exe' in proc.info['name'].lower():
                        proc.kill()
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass

        if killed:
            time.sleep(1.5)
        return killed

    @staticmethod
    def get_cookies_via_debug():
        if not HAS_CDP_LIBS:
            return None

        chrome_exe = ChromeDebugger.find_chrome()
        if not chrome_exe:
            return None

        ChromeDebugger.kill_chrome()

        debug_port = 9222
        args = [
            chrome_exe,
            "--headless=new",
            "--disable-gpu",
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={ChromeDebugger.USER_DATA_DIR}",
            "--no-first-run",
            "--disable-fre",
            "about:blank"
        ]

        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cookies_list = []

        try:
            time.sleep(3)
            json_url = f"http://127.0.0.1:{debug_port}/json"
            ws_url = None

            for _ in range(5):
                try:
                    resp = requests.get(json_url, timeout=1)
                    if resp.status_code == 200:
                        tabs = resp.json()
                        if tabs:
                            ws_url = tabs[0].get("webSocketDebuggerUrl")
                            break
                except requests.exceptions.ConnectionError:
                    time.sleep(1)

            if ws_url:
                ws = websocket.create_connection(ws_url)
                ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
                result = ws.recv()
                ws.close()
                data = json.loads(result)
                cookies_list = data.get("result", {}).get("cookies", [])

        except Exception:
            pass
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

        return cookies_list


class BrowserDetector:
    """Универсальный добытчик cookies (тихий режим для пользователей)"""

    @staticmethod
    def _create_netscape_format(cookies) -> str:
        out_lines = [
            "# Netscape HTTP Cookie File",
            "# Generated by Omnipresent",
            ""
        ]

        for c in cookies:
            is_dict = isinstance(c, dict)
            domain = c.get('domain', '') if is_dict else getattr(c, 'domain', '')
            if not domain:
                continue

            if not domain.startswith('.') and not domain.startswith('http'):
                domain = '.' + domain

            flag = "TRUE" if domain.startswith('.') else "FALSE"
            path = c.get('path', '/') if is_dict else getattr(c, 'path', '/')

            if is_dict:
                secure = "TRUE" if c.get('secure', False) else "FALSE"
            else:
                secure = "TRUE" if getattr(c, 'secure', False) else "FALSE"

            if is_dict:
                expires = c.get('expiry', c.get('expires', 0))
                if expires == -1:
                    expires = 0
            else:
                expires = getattr(c, 'expires', 0)

            name = c.get('name', '') if is_dict else getattr(c, 'name', '')
            value = c.get('value', '') if is_dict else getattr(c, 'value', '')

            out_lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{int(expires)}\t{name}\t{value}")

        return "\n".join(out_lines)

    @staticmethod
    def extract_and_save_cookies(silent=False):
        """
        Извлечь и сохранить cookies
        silent=True: без вывода в консоль (для GUI)
        Возвращает: (success: bool, method: str)
        """
        cookies = []
        method = None

        # Способ 1: Selenium (лучший)
        if HAS_SELENIUM:
            raw_cookies = SeleniumCookieExtractor.get_cookies_via_selenium()
            if raw_cookies:
                cookies = raw_cookies
                method = "Selenium"

        # Способ 2: rookiepy
        if not cookies and HAS_ROOKIE:
            try:
                import rookiepy
                raw_cookies = rookiepy.chrome()
                if raw_cookies:
                    for c in raw_cookies:
                        domain = c.get('domain', '')
                        if 'youtube.com' in domain or 'google.com' in domain:
                            cookies.append(c)
                    if cookies:
                        method = "rookiepy"
            except Exception:
                pass

        # Способ 3: Chrome CDP (требует закрытия Chrome)
        if not cookies and HAS_CDP_LIBS:
            raw_cookies = ChromeDebugger.get_cookies_via_debug()
            if raw_cookies:
                for c in raw_cookies:
                    domain = c.get('domain', '')
                    if 'youtube.com' in domain or 'google.com' in domain:
                        cookies.append(c)
                if cookies:
                    method = "Chrome_CDP"

        # Способ 4: browser_cookie3 (Firefox)
        if not cookies and HAS_BC3:
            try:
                cj = browser_cookie3.firefox(domain_name="youtube.com")
                cookies = list(cj)
                if cookies:
                    method = "Firefox_BC3"
            except:
                pass

        if not cookies:
            return False, None

        # Сохранение
        try:
            content = BrowserDetector._create_netscape_format(cookies)
            with open(cfg.cookies_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True, method
        except Exception:
            return False, None

    @staticmethod
    def try_extract_cookies():
        """Попытка извлечения (для обратной совместимости)"""
        success, method = BrowserDetector.extract_and_save_cookies(silent=True)
        if success:
            return None, method
        return None, None

    @staticmethod
    def check_cookies_exist():
        """Проверить наличие файла cookies"""
        return os.path.exists(cfg.cookies_path)

    @staticmethod
    def get_cookies_age():
        """Получить возраст файла cookies в часах"""
        if not os.path.exists(cfg.cookies_path):
            return None

        try:
            mtime = os.path.getmtime(cfg.cookies_path)
            age_seconds = time.time() - mtime
            return age_seconds / 3600  # в часах
        except:
            return None


class CookiePromptDialog:
    """Диалог для ручного ввода (если автоматика не сработала)"""

    @staticmethod
    def show_manual_cookie_dialog(parent=None) -> bool:
        from PySide6.QtWidgets import QMessageBox, QInputDialog

        # Предлагаем автоматическую попытку
        ret = QMessageBox.question(
            parent,
            "Требуются cookies",
            "Для скачивания некоторых видео нужны cookies из браузера.\n\n"
            "Попробовать получить их автоматически?",
            QMessageBox.Yes | QMessageBox.No
        )

        if ret == QMessageBox.Yes:
            success, method = BrowserDetector.extract_and_save_cookies(silent=True)
            if success:
                return True

        # Если не получилось - инструкция для ручного ввода
        msg = (
            "Не удалось автоматически получить cookies.\n\n"
            "Ручной способ:\n"
            "1. Установите расширение 'Get cookies.txt LOCALLY' для браузера\n"
            "2. Откройте YouTube и экспортируйте cookies\n"
            "3. Сохраните файл 'cookies.txt' в папку с программой"
        )

        if not HAS_SELENIUM:
            msg += "\n\n💡 Совет: Установите Google Chrome для автоматического получения cookies"

        QMessageBox.information(parent, "Ручной ввод cookies", msg)
        return False