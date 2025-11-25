import os
import re
import json
import subprocess
from datetime import datetime
from typing import List, Optional, Literal, Iterator, Protocol
from dataclasses import dataclass

from core.config import cfg
from services.cookie_manager import CookieManager
from core.utils import Logger

logger = Logger("VideoDownloader")

# ---------- протоколы ----------
class DownloadEventHandler(Protocol):
    def on_cookie_missing(self) -> bool: ...
    def on_progress(self, message: str) -> None: ...
    def on_task_finished(self, result: "DownloadTaskResult") -> None: ...

# ---------- модели ----------
@dataclass
class DownloadTask:
    url: str
    path: str
    mode: Literal["audio", "video", "together", "none"]
    quality_format: str
    time_section: Optional[tuple[int, int]] = None
    download_cover: bool = False


@dataclass
class DownloadProgress:
    index: int
    status: Literal["pending", "downloading", "converting", "finished", "error"]
    percent: float = 0.0
    speed: Optional[str] = None
    eta: Optional[str] = None
    message: str = ""


@dataclass
class DownloadTaskResult:
    index: int
    status: Literal["success", "auth_error", "network_error", "unknown"]
    message: str
    cookie_source: Optional[str] = None


# ---------- основной класс ----------
class VideoDownloader:
    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        self.cookie_manager = cookie_manager or CookieManager()
        self.cookie_source: Optional[str] = None
        self._cancelled = False

    # ---------- публичный метод для одной задачи с прогрессом ----------
    def download_with_progress(
        self,
        task: DownloadTask,
        idx: int,
        handler: Optional[DownloadEventHandler] = None,
    ) -> Iterator[DownloadProgress]:
        """Генератор, выдающий промежуточное состояние загрузки."""
        self._cancelled = False

        # 1. Обложка (если нужна)
        if task.download_cover:
            try:
                self._download_cover(task.url, task.path)
                yield DownloadProgress(
                    index=idx, status="finished", message=f"Обложка #{idx} сохранена"
                )
            except Exception as e:
                logger.warning(f"Ошибка обложки #{idx}: {e}")
                yield DownloadProgress(
                    index=idx, status="error", message=f"Ошибка обложки #{idx}"
                )

        if task.mode == "none":
            return

        # 2. Собираем команду
        cmd = self._build_command(task, idx, handler)
        logger.info(f"Команда yt-dlp: {' '.join(cmd)}")

        # 3. Запускаем процесс с JSON-прогрессом
        cmd.extend([
            "--progress-template",
            '{"status":"%(progress.status)s",'
            '"downloaded":%(progress.downloaded_bytes)s,'
            '"total":%(progress.total_bytes)s,'
            '"speed":"%(progress.speed)s",'
            '"eta":"%(progress.eta)s"}'
        ])

        yield DownloadProgress(index=idx, status="downloading", message="Старт...")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get("status") == "downloading":
                        downloaded = data.get("downloaded", 0)
                        total = data.get("total", 1) or 1
                        percent = (downloaded / total) * 100
                        yield DownloadProgress(
                            index=idx,
                            status="downloading",
                            percent=percent,
                            speed=data.get("speed"),
                            eta=data.get("eta"),
                            message=f"{percent:.1f}% | {data.get('speed')} | ETA {data.get('eta')}",
                        )
                except json.JSONDecodeError:
                    # не-json строка
                    if "error" in line.lower():
                        yield DownloadProgress(index=idx, status="error", message=line)

            proc.wait(timeout=600)
            if proc.returncode == 0:
                yield DownloadProgress(index=idx, status="finished", message="✅ Готово")
            else:
                err = proc.stderr.read()[:150]
                yield DownloadProgress(index=idx, status="error", message=f"❌ {err}")

        except subprocess.TimeoutExpired:
            proc.kill()
            yield DownloadProgress(index=idx, status="error", message="⏱️ Таймаут")
        except Exception as e:
            logger.error(f"Критическая ошибка #{idx}: {e}")
            yield DownloadProgress(index=idx, status="error", message=f"Сбой: {e}")

    # ---------- вспомогательные методы ----------
    def _build_command(
        self,
        task: DownloadTask,
        idx: int,
        handler: Optional[DownloadEventHandler],
    ) -> List[str]:
        cmd = [cfg.yt_dlp_path]
        cmd.extend(["--ffmpeg-location", cfg.ffmpeg_path])
        cmd.extend(["--paths", task.path])
        cmd.extend(["--no-overwrites"])
        cmd.extend(["--extractor-args", "youtube:player_client=default,-tv_simply"])
        cmd.extend(self._get_cookies_args(handler))

        timestamp = datetime.now().strftime("%H-%M-%S")
        if task.time_section:
            start, end = task.time_section
            cmd.extend(["--download-sections", f"*{start}-{end}"])
            out_tmpl = f"%(title)s_frag_{idx}_{timestamp}.%(ext)s"
        else:
            out_tmpl = f"%(title)s_%(resolution)s.%(ext)s"
        cmd.extend(["--output", out_tmpl])

        if task.mode == "audio":
            cmd.extend(["-f", "bestaudio[ext=m4a][acodec=aac]/bestaudio"])
        elif task.mode == "video":
            cmd.extend(["-f", "bestvideo"])
        elif task.mode == "together":
            cmd.extend(["-f", task.quality_format])

        cmd.append(task.url)
        return cmd

    def _get_cookies_args(
        self,
        handler: Optional[DownloadEventHandler],
    ) -> List[str]:
        if os.path.exists(cfg.cookies_path):
            self.cookie_source = "file"
            return ["--cookies", cfg.cookies_path]

        status = self.cookie_manager.get_status()
        if status.is_ready:
            self.cookie_source = status.source.value if status.source else "auto"
            return ["--cookies", cfg.cookies_path]

        if handler and not handler.on_cookie_missing():
            raise RuntimeError("Пользователь отменил загрузку из-за отсутствия cookies")

        logger.warning("Работаем без cookies (могут быть ограничения)")
        return []

    def _download_cover(self, url: str, path: str) -> None:
        cmd = [
            cfg.yt_dlp_path,
            "--write-thumbnail",
            "--skip-download",
            "--quiet",
            "--convert-thumbnails",
            "jpg",
            "--ffmpeg-location",
            cfg.ffmpeg_path,
            "--paths",
            path,
            "--output",
            "%(title)s.%(ext)s",
            url,
        ]
        subprocess.run(
            cmd,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=30,
        )

    def cancel(self) -> None:
        self._cancelled = True