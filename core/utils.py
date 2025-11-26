# utils.py
import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import logging
from datetime import datetime
from typing import Iterator, Tuple
from .config import cfg

# ---------- ссылки для скачивания ----------
FFMPEG_URL = {
    "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "Linux": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
    "Darwin": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.tar.xz"
}
YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


# ---------- логгер ----------
class Logger:
    def __init__(self, name: str = "app"):
        self._log = logging.getLogger(name)
        self._log.setLevel(logging.DEBUG)

        from logging.handlers import RotatingFileHandler
        handler = RotatingFileHandler(
            os.path.join(cfg.base_dir, "download.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(fmt)
        self._log.addHandler(handler)

    def info(self, msg: str) -> None:
        self._log.info(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str, *, exc: bool = False) -> None:
        self._log.error(msg, exc_info=exc)


# ---------- прогресс-загрузка ----------
class DownloadProgressHook:
    """Хук для отслеживания прогресса загрузки"""

    def __init__(self):
        self.total_size = 0
        self.downloaded = 0

    def __call__(self, block_num, block_size, total_size):
        self.total_size = total_size
        self.downloaded = block_num * block_size


def _download_file_with_progress(url: str, dst: str, desc: str = "file") -> Iterator[Tuple[int, str]]:
    """
    Скачать файл с прогрессом
    Yields: (percent, detail_message)
    """
    try:
        hook = DownloadProgressHook()
        urllib.request.urlretrieve(url, dst, reporthook=hook)

        # Симуляция прогресса для плавной анимации
        for i in range(0, 101, 5):
            yield (i, f"Загружено {i}%")
            # Добавим небольшую задержку для замедления (опционально)
            # import time; time.sleep(0.01)

        yield (100, "Загрузка завершена")
    except Exception as e:
        yield (0, f"Ошибка: {e}")


def _unpack_ffmpeg(archive_path: str) -> Iterator[Tuple[int, str]]:
    """
    Распаковать ffmpeg с прогрессом
    Yields: (percent, detail_message)
    """
    tmp_dir = archive_path + "_tmp"
    try:
        yield (0, "Начинаю распаковку...")

        with zipfile.ZipFile(archive_path) as z:
            total_files = len(z.namelist())
            z.extractall(tmp_dir)

        yield (30, f"Распаковано {total_files} файлов")

        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower() == "ffmpeg.exe":
                    os.rename(os.path.join(root, file), cfg.ffmpeg_path)
                    yield (60, "ffmpeg.exe найден")
                    break

        yield (80, "Очистка временных файлов...")

        # очистка
        for root, dirs, files in os.walk(tmp_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except Exception:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except Exception:
                    pass
        os.rmdir(tmp_dir)
        os.remove(archive_path)

        yield (100, "Распаковка завершена")
    except Exception as e:
        yield (0, f"Ошибка распаковки: {e}")


# ---------- публичные функции ----------
def check_binaries_status() -> Tuple[bool, bool]:
    """
    Проверить наличие бинарников
    Returns: (yt_dlp_exists, ffmpeg_exists)
    """
    return (
        os.path.exists(cfg.yt_dlp_path),
        os.path.exists(cfg.ffmpeg_path)
    )


def ensure_binaries_with_progress() -> Iterator[Tuple[str, int, str]]:
    """
    Скачать необходимые бинарники с прогрессом
    Yields: (status_message, percent, detail)
    """
    os.makedirs(cfg.base_dir, exist_ok=True)

    yt_dlp_exists, ffmpeg_exists = check_binaries_status()

    # Если всё есть - просто обновляем yt-dlp
    if yt_dlp_exists and ffmpeg_exists:
        yield ("🔄 Проверка обновлений...", 5, "Инициализация...")
        yield ("🔄 Проверка обновлений...", 15, "Подключение к серверу...")
        yield ("🔄 Обновление yt-dlp...", 60, "Это может занять несколько секунд")
        try:
            update_yt_dlp()
            yield ("✅ Компоненты актуальны", 95, "Завершение...")
            yield ("✅ Компоненты актуальны", 100, "Всё готово к работе")
        except Exception as e:
            yield ("✅ Компоненты готовы", 95, "Работаем с текущей версией")
            yield ("✅ Компоненты готовы", 100, "Всё готово к работе")
        return

    total_steps = 0
    if not yt_dlp_exists:
        total_steps += 1
    if not ffmpeg_exists:
        total_steps += 1

    current_step = 0

    # yt-dlp - более детальная анимация
    if not yt_dlp_exists:
        yield ("📥 Загрузка yt-dlp...", 10, "Подготовка...")
        yield ("📥 Загрузка yt-dlp...", 20, "Подключение к серверу...")

        try:
            tmp = cfg.yt_dlp_path + ".tmp"
            urllib.request.urlretrieve(YT_DLP_URL, tmp)
            os.rename(tmp, cfg.yt_dlp_path)
            os.chmod(cfg.yt_dlp_path, 0o755)

            current_step += 1
            progress = int((current_step / total_steps) * 45)
            yield ("✅ yt-dlp загружен", progress, "~12 MB")
        except Exception as e:
            yield (f"❌ Ошибка загрузки yt-dlp", 0, str(e))
            return

    # ffmpeg - более детальная анимация
    if not ffmpeg_exists:
        yield ("📥 Загрузка ffmpeg...", 50, "Подготовка...")
        yield ("📥 Загрузка ffmpeg...", 55, "Подключение к серверам...")
        yield ("📥 Загрузка ffmpeg...", 60, "Это может занять 1-2 минуты")

        try:
            url = FFMPEG_URL.get(platform.system())
            if not url:
                yield ("⚠️ ffmpeg недоступен для вашей ОС", 60, "")
            else:
                arch_path = os.path.join(cfg.base_dir, "ffmpeg.zip")
                urllib.request.urlretrieve(url, arch_path)

                yield ("📦 Распаковка ffmpeg...", 65, "~120 MB архив")

                # Распаковка с прогрессом
                for percent, detail in _unpack_ffmpeg(arch_path):
                    base_progress = 65 + int(percent * 0.25)
                    yield ("📦 Распаковка ffmpeg...", base_progress, detail)

                current_step += 1
                yield ("✅ ffmpeg установлен", 90, "")
        except Exception as e:
            yield (f"❌ Ошибка установки ffmpeg", 50, str(e))
            return

    yield ("✅ Все компоненты готовы!", 95, "Инициализация интерфейса...")
    yield ("✅ Все компоненты готовы!", 100, "Запуск программы...")


def ensure_binaries() -> None:
    """Простая версия без прогресса (для обратной совместимости)"""
    for _ in ensure_binaries_with_progress():
        pass


def update_yt_dlp() -> None:
    if not os.path.exists(cfg.yt_dlp_path):
        return
    try:
        subprocess.run(
            [cfg.yt_dlp_path, "-U"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=30
        )
    except Exception:
        pass


def play_sound(success: bool = True) -> None:
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_OK if success else winsound.MB_ICONHAND)
    except Exception:
        pass