import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import logging
from datetime import datetime
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


# ---------- вспомогательные функции ----------
def _download_file(url: str, dst: str, desc: str = "file") -> None:
    try:
        urllib.request.urlretrieve(url, dst)
    except Exception as e:
        print(f"Ошибка загрузки {desc}: {e}")


def _unpack_ffmpeg(archive_path: str) -> None:
    tmp_dir = archive_path + "_tmp"
    try:
        with zipfile.ZipFile(archive_path) as z:
            z.extractall(tmp_dir)

        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower() == "ffmpeg.exe":
                    os.rename(os.path.join(root, file), cfg.ffmpeg_path)
                    break

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
    except Exception as e:
        print(f"Ошибка распаковки ffmpeg: {e}")


# ---------- публичные функции ----------
def ensure_binaries() -> None:
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
            url = FFMPEG_URL.get(platform.system())
            if not url:
                return
            arch_path = os.path.join(cfg.base_dir, "ffmpeg.zip")
            _download_file(url, arch_path, "ffmpeg")
            if arch_path.endswith(".zip"):
                _unpack_ffmpeg(arch_path)
        except Exception as e:
            print(f"Не удалось скачать ffmpeg: {e}")


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