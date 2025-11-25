import os
import sys
import json

class Config:
    def __init__(self):
        self.base_dir = self._get_base_dir()
        self.config_file = os.path.join(self.base_dir, "settings.json")
        self.ffmpeg_path = os.path.join(self.base_dir, 'ffmpeg.exe')
        self.yt_dlp_path = os.path.join(self.base_dir, 'yt-dlp.exe')
        self.icon_path = os.path.join(self.base_dir, "ic.ico")
        self.cookies_path = os.path.join(self.base_dir, "cookies.txt")

    @staticmethod
    def _get_base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def load_setting(self, key, default=None):
        try:
            if not os.path.exists(self.config_file):
                return default
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(key, default)
        except (json.JSONDecodeError, OSError):
            return default

    def save_setting(self, key, value):
        data = {}
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            pass

        data[key] = value
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except OSError as e:
            print(f"Ошибка сохранения конфига: {e}")


# Глобальный экземпляр конфига
cfg = Config()

VIDEO_QUALITIES = {
    "Авто": "bestvideo+bestaudio/best",
    "1080p": "bestvideo*[height<=1080]+bestaudio/best",
    "720p": "bestvideo*[height<=720]+bestaudio/best",
    "2160p (4K)": "bestvideo*[height=2160]+bestaudio/best"
}