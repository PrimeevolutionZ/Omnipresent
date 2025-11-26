# utils.py
import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import logging
import threading
import queue
import time
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
def _download_with_progress(url: str, dst: str, desc: str = "file") -> Iterator[Tuple[int, str]]:
    try:
        # Пробуем сначала с requests (потоковая загрузка)
        try:
            import requests
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(dst, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = min(int(downloaded * 100 / total_size), 99)
                            mb = downloaded / (1024 * 1024)
                            yield (percent, f"Загружено {mb:.1f} MB")
                        else:
                            # Если размер неизвестен, эмулируем прогресс
                            mb = downloaded / (1024 * 1024)
                            percent = min(int(mb * 2), 95)  # Примерно 50MB = 100%
                            yield (percent, f"Загружено {mb:.1f} MB")

            yield (100, f"Загрузка завершена ({mb:.1f} MB)")

        except ImportError:
            hook = type('Hook', (), {'total': 0, 'downloaded': 0})()

            def progress_hook(block_num, block_size, total_size):
                hook.total = total_size
                hook.downloaded = block_num * block_size

            urllib.request.urlretrieve(url, dst, reporthook=progress_hook)

            # Симуляция прогресса
            for i in range(0, 101, 10):
                yield (i, f"Загружено {i}%")

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


# ---------- новая версия update_yt_dlp ----------
def update_yt_dlp_with_progress() -> Iterator[Tuple[int, str]]:
    """Обновить yt-dlp с плавной анимацией прогресса на основе реального времени"""
    if not os.path.exists(cfg.yt_dlp_path):
        yield (0, "yt-dlp не найден")
        return

    result_queue = queue.Queue()

    def run_update():
        try:
            process = subprocess.Popen(
                [cfg.yt_dlp_path, "-U"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            output, _ = process.communicate(timeout=30)
            result_queue.put(('finished', process.returncode, output))
        except Exception as e:
            result_queue.put(('error', str(e)))

    thread = threading.Thread(target=run_update, daemon=True)
    thread.start()

    start_time = datetime.now()
    stages = [
        (0, 25, "Инициализация обновления..."),
        (25, 50, "Проверка версии на сервере..."),
        (50, 75, "Загрузка обновления..."),
        (75, 95, "Применение обновления..."),
        (95, 100, "Финализация..."),
    ]

    stage_index = 0
    while thread.is_alive():
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > (stage_index + 1) * 0.6 and stage_index < len(stages) - 1:
            stage_index += 1

        start, end, stage_msg = stages[stage_index]
        stage_progress = min((elapsed % 0.6) / 0.6, 1.0)
        eased = stage_progress * stage_progress * (3.0 - 2.0 * stage_progress)
        current_progress = start + int((end - start) * eased)
        yield (current_progress, stage_msg)

        try:
            msg_type, *data = result_queue.get_nowait()
            if msg_type == 'finished':
                yield (100, "✅ Обновление завершено")
                return
            elif msg_type == 'error':
                yield (0, f"❌ Ошибка: {data[0]}")
                return
        except queue.Empty:
            pass
        time.sleep(0.05)

    thread.join(timeout=1)
    yield (100, "✅ Обновление завершено")


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
    Скачать необходимые бинарники с плавным прогрессом
    Yields: (status_message, percent, detail)
    """
    os.makedirs(cfg.base_dir, exist_ok=True)

    yt_dlp_exists, ffmpeg_exists = check_binaries_status()

    # Если всё есть — обновляем yt-dlp
    if yt_dlp_exists and ffmpeg_exists:
        yield ("🔄 Проверка обновлений...", 0, "Запуск...")
        for progress, detail in update_yt_dlp_with_progress():
            scaled = max(5, min(95, int(progress * 0.90)))
            yield ("🔄 Обновление yt-dlp...", scaled, detail)
        yield ("✅ Компоненты актуальны", 95, "Завершение...")
        yield ("✅ Компоненты актуальны", 100, "Готово!")
        return

    total_steps = 0
    if not yt_dlp_exists:
        total_steps += 1
    if not ffmpeg_exists:
        total_steps += 1


    if not yt_dlp_exists:
        try:
            tmp = cfg.yt_dlp_path + ".tmp"

            # Загрузка с промежуточными вехами
            for percent, detail in _download_with_progress(YT_DLP_URL, tmp, "yt-dlp"):
                # Масштабируем 0-100% -> 10-40%
                progress = 10 + int(percent * 0.30)
                yield ("📥 Загрузка yt-dlp...", progress, detail)

            os.rename(tmp, cfg.yt_dlp_path)
            os.chmod(cfg.yt_dlp_path, 0o755)
            yield ("✅ yt-dlp загружен", 45, "~12 MB")
        except Exception as e:
            yield (f"❌ Ошибка загрузки yt-dlp", 0, str(e))
            return


    if not ffmpeg_exists:
        try:
            url = FFMPEG_URL.get(platform.system())
            if not url:
                yield ("⚠️ ffmpeg недоступен для вашей ОС", 50, "")
            else:
                arch_path = os.path.join(cfg.base_dir, "ffmpeg.zip")

                # Загрузка с промежуточными вехами
                for percent, detail in _download_with_progress(url, arch_path, "ffmpeg"):
                    # Масштабируем 0-100% -> 50-75%
                    progress = 50 + int(percent * 0.25)
                    yield ("📥 Загрузка ffmpeg...", progress, detail)

                yield ("📦 Распаковка ffmpeg...", 75, "~120 MB архив")

                # Распаковка с прогрессом
                for percent, detail in _unpack_ffmpeg(arch_path):
                    base_progress = 75 + int(percent * 0.15)
                    yield ("📦 Распаковка ffmpeg...", base_progress, detail)

                yield ("✅ ffmpeg установлен", 90, "")
        except Exception as e:
            yield (f"❌ Ошибка установки ffmpeg", 50, str(e))
            return

    yield ("✅ Все компоненты готовы!", 95, "Инициализация интерфейса...")
    yield ("✅ Все компоненты готовы!", 100, "Запуск программы...")


def ensure_binaries() -> None:
    """Простая версия без прогресса"""
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