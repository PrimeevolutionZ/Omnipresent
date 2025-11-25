from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal

# --- Cookies ---
@dataclass
class CookieResult:
    success: bool
    cookies: List[dict]
    source: Optional[str] = None        # CookieSource.value
    error: Optional[str] = None
    age_hours: Optional[float] = None

# --- Загрузка ---
@dataclass
class DownloadTask:
    url: str
    path: str
    mode: Literal["audio", "video", "together", "none"]
    quality_format: str
    time_section: Optional[Tuple[int, int]] = None
    download_cover: bool = False

@dataclass
class DownloadTaskResult:
    index: int
    status: Literal["success", "auth_error", "network_error", "unknown"]
    message: str
    cookie_source: Optional[str] = None