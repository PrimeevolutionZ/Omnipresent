import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
from datetime import datetime
from config import cfg

# ---------- ссылки для скачивания ----------
FFMPEG_URL = {
    "Windows": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    "Linux": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
    "Darwin": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.tar.xz"
}
YT_DLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


# ---------- вспомогательные функции ----------
def _download_file(url: str, dst: str, desc: str = "file") -> None:
    """Скачать файл с простым консольным прогресс-баром (тихий режим для GUI)"""
    try:
        urllib.request.urlretrieve(url, dst)
    except Exception as e:
        print(f"Ошибка загрузки {desc}: {e}")


def _unpack_ffmpeg(archive_path: str) -> None:
    """Извлечь только ffmpeg.exe из zip-архива"""
    tmp_dir = archive_path + "_tmp"

    try:
        with zipfile.ZipFile(archive_path) as z:
            z.extractall(tmp_dir)

        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower() == "ffmpeg.exe":
                    src = os.path.join(root, file)
                    os.rename(src, cfg.ffmpeg_path)
                    break

        # Очистка
        for root, dirs, files in os.walk(tmp_dir, topdown=False):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                except:
                    pass
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except:
                    pass

        try:
            os.rmdir(tmp_dir)
            os.remove(archive_path)
        except:
            pass

    except Exception as e:
        print(f"Ошибка распаковки ffmpeg: {e}")


# ---------- публичные функции ----------
def ensure_binaries() -> None:
    """Скачать отсутствующие yt-dlp.exe и ffmpeg.exe (тихий режим)"""
    os.makedirs(cfg.base_dir, exist_ok=True)

    # yt-dlp
    if not os.path.exists(cfg.yt_dlp_path):
        try:
            tmp = cfg.yt_dlp_path + ".tmp"
            _download_file(YT_DLP_URL, tmp, "yt-dlp")
            os.rename(tmp, cfg.yt_dlp_path)
            os.chmod(cfg.yt_dlp_path, 0o755)
        except Exception as e:
            print(f"Не удалось скачать yt-dlp: {e}")
    else:
        update_yt_dlp()

    # ffmpeg
    if not os.path.exists(cfg.ffmpeg_path):
        try:
            plat = platform.system()
            url = FFMPEG_URL.get(plat)
            if not url:
                return

            arch_path = os.path.join(cfg.base_dir, "ffmpeg.zip")
            _download_file(url, arch_path, "ffmpeg")

            if arch_path.endswith(".zip"):
                _unpack_ffmpeg(arch_path)
        except Exception as e:
            print(f"Не удалось скачать ffmpeg: {e}")


def update_yt_dlp() -> None:
    """Обновить уже существующий yt-dlp (тихий режим)"""
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
        pass  # Игнорируем ошибки обновления


def play_sound(success: bool = True) -> None:
    """Проиграть системный звук уведомления"""
    try:
        import winsound
        if success:
            # Звук завершения задачи
            winsound.MessageBeep(winsound.MB_OK)
        else:
            # Звук ошибки
            winsound.MessageBeep(winsound.MB_ICONHAND)
    except Exception:
        pass  # Если winsound недоступен (не Windows), игнорируем


# ---------- логгер ----------
class Logger:
    def __init__(self):
        self.log_file = os.path.join(cfg.base_dir, "download_log.txt")

    def log_start(self):
        """Начать новую сессию лога"""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"=== SESSION START: {start} ===\n\n")
        except Exception:
            pass

    def write(self, message: str, level: str = "INFO"):
        """Записать сообщение в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] [{level}] {message}"

        # Не печатаем в консоль для GUI-версии (только в файл)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(full_msg + "\n")
        except Exception:
            pass

    def open_log(self):
        """Открыть файл лога"""
        if os.path.exists(self.log_file):
            try:
                if os.name == "nt":
                    os.startfile(self.log_file)
                else:
                    subprocess.call(["xdg-open", self.log_file])
            except Exception:
                pass