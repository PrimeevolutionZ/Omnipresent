import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QComboBox,
    QLineEdit, QPushButton, QLabel, QFileDialog, QScrollArea, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon

from core.config import cfg, VIDEO_QUALITIES
from core.utils import play_sound
from ui.ui_qt_widgets import UrlInputRow
from ui.download_controller import DownloadController
from services.video_downloader import DownloadTask, DownloadTaskResult, DownloadProgress


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Omnipresent — Prime_evolution EDITION")
        self.resize(1200, 650)
        if os.path.exists(cfg.icon_path):
            self.setWindowIcon(QIcon(cfg.icon_path))

        self._build_ui()
        self._controller = DownloadController(self)

        # --- подключение новых сигналов ---
        self._controller.progress.connect(self.status_label.setText)
        self._controller.pool_status.connect(self._on_pool_status)
        self._controller.task_done.connect(self._on_task_done)
        self._controller.finished.connect(self._on_download_finished)
        self._controller.cookie_progress.connect(self.status_label.setText)

        self._load_settings()
        self._check_cookies_status()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def _build_left_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("LeftPanel")
        panel.setFixedWidth(350)
        lay = QVBoxLayout(panel)
        lay.setSpacing(15)
        lay.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚙️ Настройки")
        title.setObjectName("TitleLabel")
        lay.addWidget(title)

        lay.addWidget(self._section("Формат загрузки"))
        self.cb_audio = QCheckBox("🎵 Аудио отдельно")
        self.cb_video = QCheckBox("🎬 Видео отдельно")
        self.cb_together = QCheckBox("📦 Объединить аудио+видео")
        self.cb_cover = QCheckBox("🖼️ Обложка")
        for w in (self.cb_audio, self.cb_video, self.cb_together, self.cb_cover):
            lay.addWidget(w)

        lay.addWidget(self._section("Дополнительно"))
        self.cb_fragment = QCheckBox("✂️ Фрагмент (Timecode)")
        self.cb_queue = QCheckBox("📝 Очередь ссылок")
        lay.addWidget(self.cb_fragment)
        lay.addWidget(self.cb_queue)

        lay.addWidget(self._section("Папка сохранения"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("📁 Выберите папку...")
        btn_path = QPushButton("📂 Выбрать папку")
        btn_path.setObjectName("SecondaryBtn")
        btn_path.clicked.connect(self._choose_path)
        lay.addWidget(self.path_edit)
        lay.addWidget(btn_path)

        lay.addWidget(self._section("Качество видео"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(list(VIDEO_QUALITIES.keys()))
        lay.addWidget(self.combo_quality)

        lay.addWidget(self._section("Статус авторизации"))
        self.cookies_status = QLabel("⏳ Проверка...")
        self.cookies_status.setObjectName("CookieStatus")
        lay.addWidget(self.cookies_status)

        self.btn_cookies = QPushButton("🔄 Обновить cookies")
        self.btn_cookies.setObjectName("SecondaryBtn")
        self.btn_cookies.clicked.connect(self._on_update_cookies)
        lay.addWidget(self.btn_cookies)

        lay.addStretch()

        btn_log = QPushButton("📋 Открыть логи")
        btn_log.setObjectName("SecondaryBtn")
        btn_log.clicked.connect(self._open_logs)
        lay.addWidget(btn_log)

        return panel

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(15)

        title = QLabel("🔗 Ссылки на видео")
        title.setObjectName("TitleLabel")
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(400)
        self.scroll_content = QWidget()
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setAlignment(Qt.AlignTop)
        self.rows_layout.setSpacing(10)
        scroll.setWidget(self.scroll_content)
        lay.addWidget(scroll)

        bottom = QFrame()
        bottom.setObjectName("StatusBar")
        blay = QHBoxLayout(bottom)
        blay.setContentsMargins(15, 10, 15, 10)

        self.status_label = QLabel("✅ Готов к работе")
        self.status_label.setStyleSheet("color: #00d4ff; font-size: 14px;")

        self.btn_download = QPushButton("⬇️ СКАЧАТЬ")
        self.btn_download.setObjectName("DownloadBtn")
        self.btn_download.setFixedHeight(50)
        self.btn_download.setMinimumWidth(200)
        self.btn_download.clicked.connect(self._start_download)

        blay.addWidget(self.status_label)
        blay.addStretch()
        blay.addWidget(self.btn_download)

        lay.addWidget(bottom)
        return w

    # ---------- служебные ----------
    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SectionLabel")
        return lbl

    def _load_settings(self) -> None:
        if path := cfg.load_setting("download_path"):
            self.path_edit.setText(path)

        self.cb_fragment.clicked.connect(lambda: self._toggle_fragments(self.cb_fragment.isChecked()))
        self.cb_queue.clicked.connect(lambda: self._toggle_queue(self.cb_queue.isChecked()))
        self.add_row()

    # ---------- cookies ----------
    def _check_cookies_status(self) -> None:
        from services.cookie_manager import CookieManager
        mgr = CookieManager()
        text, style = mgr.get_status_label()
        self.cookies_status.setText(text)
        self.cookies_status.setStyleSheet(style + "padding: 5px 10px; border-radius: 4px;")

    def _choose_path(self) -> None:
        if path := QFileDialog.getExistingDirectory(self, "Выберите папку"):
            self.path_edit.setText(path)
            cfg.save_setting("download_path", path)

    def _open_logs(self) -> None:
        log = os.path.join(cfg.base_dir, "download.log")
        if os.path.exists(log):
            os.startfile(log)

    def _on_update_cookies(self) -> None:
        """Запускаем фоновое обновление cookies."""
        self._controller.fetch_cookies_async()

    # ---------- строки URL ----------
    def add_row(self) -> None:
        if len(self.url_rows) >= 8:
            return
        idx = len(self.url_rows)
        row = UrlInputRow(idx)
        row.text_started.connect(self._on_row_typing)
        self.rows_layout.addWidget(row)
        self.url_rows.append(row)
        QTimer.singleShot(0, lambda: row.toggle_time(self.cb_fragment.isChecked()))

    def _on_row_typing(self) -> None:
        if self.cb_queue.isChecked():
            self.add_row()

    # ---------- фрагменты ----------
    def _toggle_fragments(self, show: bool) -> None:
        for row in self.url_rows:
            QTimer.singleShot(0, lambda r=row, s=show: r.toggle_time(s))
        QTimer.singleShot(10, self.scroll_content.adjustSize)

    # ---------- очередь ----------
    def _toggle_queue(self, state: bool) -> None:
        if not state:
            QTimer.singleShot(0, self._clear_extra_rows)
        else:
            if self.url_rows and self.url_rows[-1].get_url():
                self.add_row()

    def _clear_extra_rows(self) -> None:
        while len(self.url_rows) > 1:
            row = self.url_rows.pop()
            self.rows_layout.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        if self.url_rows:
            self.url_rows[0].url_input.clear()
            self.url_rows[0]._emitted = False

    # ---------- загрузка ----------
    def _start_download(self) -> None:
        path = self.path_edit.text()
        if not path or not os.path.exists(path):
            self.status_label.setText("❌ Укажите папку")
            play_sound(False)
            return

        tasks = self._collect_tasks()
        if not tasks:
            self.status_label.setText("❌ Добавьте ссылки или выберите формат")
            play_sound(False)
            return

        if not self._confirm_cookies():
            return

        self.btn_download.setDisabled(True)
        self.btn_download.setText("⏳ Загрузка...")
        self._controller.start(tasks)

    def _collect_tasks(self) -> list[DownloadTask]:
        tasks: list[DownloadTask] = []
        fmt_key = self.combo_quality.currentText()
        quality = VIDEO_QUALITIES[fmt_key]

        for row in self.url_rows:
            url = row.get_url()
            if not url:
                continue

            time_sec = None
            if self.cb_fragment.isChecked():
                time_sec = row.time_widget.get_seconds()
                if not time_sec:
                    continue

            modes = []
            if self.cb_together.isChecked():
                modes.append("together")
            if self.cb_audio.isChecked():
                modes.append("audio")
            if self.cb_video.isChecked():
                modes.append("video")
            if not modes and self.cb_cover.isChecked():
                modes.append("none")

            for mode in modes:
                tasks.append(
                    DownloadTask(
                        url=url,
                        path=self.path_edit.text(),
                        mode=mode,
                        quality_format=quality,
                        time_section=time_sec,
                        download_cover=self.cb_cover.isChecked() and mode == modes[0],
                    )
                )
        return tasks

    def _confirm_cookies(self) -> bool:
        from services.cookie_manager import CookieManager
        mgr = CookieManager()
        if not mgr.get_status().is_ready:
            ans = QMessageBox.question(
                self,
                "Продолжить без cookies?",
                "⚠️ Cookies не настроены. Некоторые видео могут быть недоступны.\n\n"
                "Продолжить скачивание?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return False
        return True

    # ---------- слоты ----------
    def _on_task_done(self, result: DownloadTaskResult):
        # можно добавить индивидуальные уведомления
        pass

    def _on_pool_status(self, active: int, queued: int):
        self.status_label.setText(f"Активно: {active}  |  В очереди: {queued}")

    def _on_download_finished(self, success: bool):
        self.btn_download.setDisabled(False)
        self.btn_download.setText("⬇️ СКАЧАТЬ")

        if success:
            self.status_label.setText("✅ Все файлы загружены!")
            play_sound(True)
        else:
            ans = QMessageBox.question(
                self,
                "Ошибка загрузки",
                "❌ Не удалось скачать видео.\n\n"
                "Возможно, cookies устарели. Попробовать обновить?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans == QMessageBox.Yes:
                self._controller.fetch_cookies_async()
            self.status_label.setText("⚠️ Ошибка (см. логи)")
            play_sound(False)

    # ---------- свойства ----------
    @property
    def url_rows(self):
        if not hasattr(self, "_url_rows"):
            self._url_rows: list[UrlInputRow] = []
        return self._url_rows