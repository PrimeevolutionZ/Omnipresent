import os
import subprocess
from datetime import datetime
from config import cfg
from utils import Logger
from browser_cookies import BrowserDetector


class VideoDownloader:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.cookie_source = None

    def _get_cookies_argument(self, options, parent_widget=None) -> list:
        """Получить аргумент cookies для yt-dlp"""
        cmd_args = []

        # Проверяем наличие файла cookies
        if os.path.exists(cfg.cookies_path):
            self.cookie_source = "file"
            cmd_args.extend(['--cookies', cfg.cookies_path])
            return cmd_args

        # Если файла нет - пробуем получить автоматически (тихо)
        self.logger.write("Cookies не найдены, пробуем получить автоматически", "INFO")
        success, method = BrowserDetector.extract_and_save_cookies(silent=True)

        if success:
            self.cookie_source = f"auto_{method}"
            cmd_args.extend(['--cookies', cfg.cookies_path])
            self.logger.write(f"Cookies получены автоматически ({method})", "INFO")
            return cmd_args

        # Если ничего не вышло - работаем без cookies
        self.cookie_source = None
        self.logger.write("Работаю без cookies (могут быть ограничения)", "WARN")

        # Показываем диалог только если есть GUI и это первая попытка
        if parent_widget and not hasattr(self, '_cookie_warning_shown'):
            self._cookie_warning_shown = True
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                parent_widget,
                "Cookies недоступны",
                "Не удалось получить cookies из браузера.\n"
                "Некоторые видео могут быть недоступны.\n\n"
                "Для решения проблемы:\n"
                "1. Нажмите 'Обновить cookies' в главном окне\n"
                "2. Или установите Google Chrome"
            )

        return cmd_args

    def build_command(self, url, options, idx, parent_widget=None):
        """Генерация списка аргументов для yt-dlp"""
        cmd = [cfg.yt_dlp_path]

        # Базовые пути
        cmd.extend(['--ffmpeg-location', cfg.ffmpeg_path])
        cmd.extend(['--paths', options['path']])
        cmd.extend(['--no-overwrites'])

        # Оптимизация клиента
        cmd.extend(['--extractor-args', 'youtube:player_client=default,-tv_simply'])

        # Cookies
        cmd.extend(self._get_cookies_argument(options, parent_widget))

        # Форматы и выходные файлы
        timestamp = datetime.now().strftime("%H-%M-%S")

        # Обработка фрагментов
        if options.get('time_section'):
            start, end = options['time_section']
            cmd.extend(['--download-sections', f'*{start}-{end}'])
            output_tmpl = f'%(title)s_frag_{idx}_{timestamp}.%(ext)s'
        else:
            output_tmpl = f'%(title)s_%(resolution)s.%(ext)s'

        cmd.extend(['--output', output_tmpl])

        # Выбор режима (audio/video/merge)
        mode = options['mode']
        quality = options['quality_format']

        if mode == 'audio':
            cmd.extend(['-f', 'bestaudio[ext=m4a][acodec=aac]/bestaudio'])
        elif mode == 'video':
            cmd.extend(['-f', quality])
        elif mode == 'together':
            cmd.extend(['-f', quality])

        cmd.append(url)
        return cmd

    def download_cover(self, url, path):
        """Скачать обложку видео"""
        cmd = [
            cfg.yt_dlp_path,
            '--write-thumbnail', '--skip-download', '--quiet',
            '--convert-thumbnails', 'jpg',
            '--ffmpeg-location', cfg.ffmpeg_path,
            '--paths', path,
            '--output', '%(title)s.%(ext)s',
            url
        ]
        try:
            subprocess.run(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                timeout=30
            )
        except Exception:
            pass

    def process_queue(self, tasks, parent_widget=None):
        """Обработка очереди загрузок"""
        self.logger.log_start()
        success_count = 0

        for i, task in enumerate(tasks, 1):
            url = task['url']
            if not url:
                continue

            self.logger.write(f"Задача #{i}: {url}")

            # Скачивание обложки
            if task.get('download_cover'):
                try:
                    self.download_cover(url, task['path'])
                    self.logger.write(f"Обложка #{i} скачана")
                except Exception as e:
                    self.logger.write(f"Ошибка обложки #{i}: {e}", "WARN")

            # Если только обложка
            if task['mode'] == 'none':
                success_count += 1
                continue

            # Основная загрузка
            try:
                cmd = self.build_command(url, task, i, parent_widget)

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )

                if result.returncode == 0:
                    self.logger.write(f"Успешно #{i}")
                    success_count += 1
                    yield f"Загружено: {i}/{len(tasks)}"
                else:
                    # Анализируем ошибку
                    err_msg = result.stderr.strip()

                    # Проверяем, не связана ли ошибка с cookies
                    if any(x in err_msg.lower() for x in
                           ['sign in', 'login', 'private', 'members-only', 'unavailable']):
                        self.logger.write(f"Ошибка #{i}: Требуется авторизация", "ERROR")
                        yield f"Ошибка #{i}: требуется авторизация"
                    else:
                        self.logger.write(f"Ошибка #{i}: {err_msg[:200]}", "ERROR")
                        yield f"Ошибка #{i}"

            except Exception as e:
                self.logger.write(f"Критическая ошибка #{i}: {e}", "CRITICAL")
                yield f"Сбой #{i}"

        # Финальный отчёт
        if self.cookie_source:
            self.logger.write(f"Источник cookies: {self.cookie_source}")

        if success_count == len(tasks):
            yield "Готово"
        elif success_count > 0:
            yield f"Завершено: {success_count}/{len(tasks)}"
        else:
            yield "Ошибки при загрузке"

        return success_count == len(tasks)