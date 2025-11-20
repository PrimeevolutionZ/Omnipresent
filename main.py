import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QCheckBox, QComboBox, QLineEdit,
                               QPushButton, QLabel, QFileDialog, QScrollArea,
                               QMessageBox, QFrame)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon, QFont
from config import cfg
from utils import update_yt_dlp, play_sound, ensure_binaries
from ui_qt_widgets import UrlInputRow
from worker import DownloadWorker

# Константы
VIDEO_QUALITIES = {
    "Авто": "bestvideo+bestaudio/best",
    "1080p": "bestvideo*[height<=1080]+bestaudio/best",
    "720p": "bestvideo*[height<=720]+bestaudio/best",
    "2160p (4K)": "bestvideo*[height=2160]+bestaudio/best",
    "Только Аудио": "audio"
}

# --- Современная тёмная тема ---
STYLESHEET = """
QMainWindow { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #1a1a2e, stop:1 #16213e);
}

QWidget { 
    color: #eaeaea; 
    font-family: 'Segoe UI', 'Roboto', sans-serif; 
    font-size: 13px; 
}

/* Заголовки */
QLabel#TitleLabel {
    font-size: 24px;
    font-weight: bold;
    color: #00d4ff;
    padding: 10px;
}

QLabel#SectionLabel {
    font-size: 14px;
    font-weight: 600;
    color: #00d4ff;
    padding: 5px 0px;
}

/* Чекбоксы */
QCheckBox { 
    spacing: 8px;
    padding: 5px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #555;
    background-color: #2b2b2b;
}
QCheckBox::indicator:checked {
    background-color: #00d4ff;
    border-color: #00d4ff;
}
QCheckBox::indicator:hover {
    border-color: #00d4ff;
}

/* Поля ввода */
QLineEdit { 
    background-color: #252d42; 
    border: 2px solid #3a4a6b; 
    border-radius: 6px; 
    padding: 8px 12px;
    selection-background-color: #00d4ff;
    color: #eaeaea;
}
QLineEdit:focus {
    border-color: #00d4ff;
    background-color: #2d3548;
}
QLineEdit:hover {
    border-color: #4a5a7b;
}

/* Комбобоксы */
QComboBox { 
    background-color: #252d42; 
    border: 2px solid #3a4a6b; 
    padding: 8px 12px; 
    border-radius: 6px;
    min-height: 25px;
}
QComboBox:hover {
    border-color: #4a5a7b;
}
QComboBox:focus {
    border-color: #00d4ff;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #00d4ff;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #252d42;
    border: 2px solid #00d4ff;
    selection-background-color: #00d4ff;
    selection-color: #000;
}

/* Кнопки */
QPushButton { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #00d4ff, stop:1 #0099cc);
    color: #000; 
    border: none; 
    padding: 10px 20px; 
    border-radius: 8px; 
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover { 
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #00e5ff, stop:1 #00b8e6);
}
QPushButton:pressed {
    background: #0088bb;
}
QPushButton:disabled { 
    background-color: #3a3a3a; 
    color: #666; 
}

/* Вторичные кнопки */
QPushButton#SecondaryBtn { 
    background: transparent;
    border: 2px solid #00d4ff;
    color: #00d4ff;
    padding: 8px 16px;
}
QPushButton#SecondaryBtn:hover { 
    background-color: rgba(0, 212, 255, 0.1);
}

/* Кнопка скачивания */
QPushButton#DownloadBtn {
    min-height: 50px;
    font-size: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00d4ff, stop:1 #0099cc);
}
QPushButton#DownloadBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00e5ff, stop:1 #00b8e6);
}

/* Скроллбар */
QScrollArea { 
    border: none; 
    background-color: transparent; 
}
QScrollBar:vertical { 
    background-color: #1a1a2e; 
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical { 
    background-color: #00d4ff; 
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #00e5ff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Спинбоксы */
QSpinBox { 
    background-color: #252d42; 
    border: 2px solid #3a4a6b; 
    border-radius: 4px;
    padding: 5px;
    color: #eaeaea;
}
QSpinBox:focus {
    border-color: #00d4ff;
}

/* Панели */
QFrame#LeftPanel {
    background-color: rgba(37, 45, 66, 0.7);
    border-radius: 12px;
    border: 1px solid #3a4a6b;
}

QFrame#StatusBar {
    background-color: rgba(37, 45, 66, 0.5);
    border-radius: 8px;
    padding: 10px;
}

/* Статус cookies */
QLabel#CookieStatus {
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 4px;
    background-color: rgba(0, 0, 0, 0.3);
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Omnipresent — YouTube Downloader")
        self.resize(1200, 650)
        if os.path.exists(cfg.icon_path):
            self.setWindowIcon(QIcon(cfg.icon_path))

        self.cookies_ready = False

        # Главный контейнер
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- ЛЕВАЯ ПАНЕЛЬ (Настройки) ---
        left_panel = QFrame()
        left_panel.setObjectName("LeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_panel.setFixedWidth(350)

        # Заголовок
        title = QLabel("⚙️ Настройки")
        title.setObjectName("TitleLabel")
        left_layout.addWidget(title)

        # Чекбоксы
        section_format = QLabel("Формат загрузки")
        section_format.setObjectName("SectionLabel")
        left_layout.addWidget(section_format)

        self.cb_audio = QCheckBox("🎵 Аудио отдельно")
        self.cb_video = QCheckBox("🎬 Видео отдельно")
        self.cb_together = QCheckBox("📦 Объединить аудио+видео")
        self.cb_cover = QCheckBox("🖼️ Обложка")

        for cb in [self.cb_audio, self.cb_video, self.cb_together, self.cb_cover]:
            left_layout.addWidget(cb)

        # Дополнительно
        section_extra = QLabel("Дополнительно")
        section_extra.setObjectName("SectionLabel")
        left_layout.addWidget(section_extra)

        self.cb_fragment = QCheckBox("✂️ Фрагмент (Timecode)")
        self.cb_queue = QCheckBox("📝 Очередь ссылок")

        for cb in [self.cb_fragment, self.cb_queue]:
            left_layout.addWidget(cb)

        # Путь сохранения
        section_path = QLabel("Папка сохранения")
        section_path.setObjectName("SectionLabel")
        left_layout.addWidget(section_path)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("📁 Выберите папку...")
        path_btn = QPushButton("📂 Выбрать папку")
        path_btn.setObjectName("SecondaryBtn")
        path_btn.clicked.connect(self.choose_path)
        left_layout.addWidget(self.path_edit)
        left_layout.addWidget(path_btn)

        # Качество
        section_quality = QLabel("Качество видео")
        section_quality.setObjectName("SectionLabel")
        left_layout.addWidget(section_quality)

        self.combo_quality = QComboBox()
        self.combo_quality.addItems(list(VIDEO_QUALITIES.keys()))
        left_layout.addWidget(self.combo_quality)

        # Статус cookies
        section_cookies = QLabel("Статус авторизации")
        section_cookies.setObjectName("SectionLabel")
        left_layout.addWidget(section_cookies)

        self.cookies_status = QLabel("⏳ Проверка...")
        self.cookies_status.setObjectName("CookieStatus")
        left_layout.addWidget(self.cookies_status)

        self.manual_cookies_btn = QPushButton("🔄 Обновить cookies")
        self.manual_cookies_btn.setObjectName("SecondaryBtn")
        self.manual_cookies_btn.setVisible(False)
        self.manual_cookies_btn.clicked.connect(self.manual_cookie_input)
        left_layout.addWidget(self.manual_cookies_btn)

        left_layout.addStretch()

        # Логи
        log_btn = QPushButton("📋 Открыть логи")
        log_btn.setObjectName("SecondaryBtn")
        log_btn.clicked.connect(
            lambda: os.startfile("download_log.txt") if os.path.exists("download_log.txt") else None)
        left_layout.addWidget(log_btn)

        # --- ПРАВАЯ ПАНЕЛЬ (Ввод) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        title_right = QLabel("🔗 Ссылки на видео")
        title_right.setObjectName("TitleLabel")
        right_layout.addWidget(title_right)

        # Скролл зона
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(400)
        self.scroll_content = QWidget()
        self.rows_layout = QVBoxLayout(self.scroll_content)
        self.rows_layout.setAlignment(Qt.AlignTop)
        self.rows_layout.setSpacing(10)
        scroll.setWidget(self.scroll_content)
        right_layout.addWidget(scroll)

        # Нижняя панель (Статус + Кнопка)
        bottom_bar = QFrame()
        bottom_bar.setObjectName("StatusBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 10, 15, 10)

        self.status_label = QLabel("✅ Готов к работе")
        self.status_label.setStyleSheet("color: #00d4ff; font-size: 14px;")

        self.btn_download = QPushButton("⬇️ СКАЧАТЬ")
        self.btn_download.setObjectName("DownloadBtn")
        self.btn_download.setFixedHeight(50)
        self.btn_download.setMinimumWidth(200)
        self.btn_download.clicked.connect(self.start_download)

        bottom_layout.addWidget(self.status_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_download)
        right_layout.addWidget(bottom_bar)

        # Добавляем панели в окно
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

        # --- Логика UI ---
        self.url_rows = []
        self.add_row()

        self.cb_fragment.stateChanged.connect(self.toggle_fragments)
        self.cb_queue.stateChanged.connect(self.toggle_queue)

        # Загрузка конфига
        last_path = cfg.load_setting("download_path")
        if last_path:
            self.path_edit.setText(last_path)

        # Проверяем cookies
        self._check_cookies_status()

    def _check_cookies_status(self):
        """Проверка статуса cookies и обновление UI"""
        from browser_cookies import BrowserDetector

        if BrowserDetector.check_cookies_exist():
            age = BrowserDetector.get_cookies_age()

            if age and age < 168:  # Меньше 7 дней
                self.cookies_status.setText("✅ Cookies актуальны")
                self.cookies_status.setStyleSheet(
                    "color: #4CAF50; background-color: rgba(76, 175, 80, 0.2); padding: 5px 10px; border-radius: 4px;")
                self.manual_cookies_btn.setText("🔄 Обновить")
                self.manual_cookies_btn.setVisible(True)
                self.cookies_ready = True
            else:
                self.cookies_status.setText("⚠️ Cookies устарели")
                self.cookies_status.setStyleSheet(
                    "color: #FFC107; background-color: rgba(255, 193, 7, 0.2); padding: 5px 10px; border-radius: 4px;")
                self.manual_cookies_btn.setText("🔄 Обновить")
                self.manual_cookies_btn.setVisible(True)
                self.cookies_ready = True
        else:
            self.cookies_status.setText("⏳ Получение cookies...")
            success, method = BrowserDetector.extract_and_save_cookies(silent=True)

            if success:
                self.cookies_status.setText("✅ Cookies получены")
                self.cookies_status.setStyleSheet(
                    "color: #4CAF50; background-color: rgba(76, 175, 80, 0.2); padding: 5px 10px; border-radius: 4px;")
                self.manual_cookies_btn.setText("🔄 Обновить")
                self.manual_cookies_btn.setVisible(True)
                self.cookies_ready = True
            else:
                self.cookies_status.setText("❌ Cookies не найдены")
                self.cookies_status.setStyleSheet(
                    "color: #F44336; background-color: rgba(244, 67, 54, 0.2); padding: 5px 10px; border-radius: 4px;")
                self.manual_cookies_btn.setText("🔐 Получить")
                self.manual_cookies_btn.setVisible(True)
                self.cookies_ready = False

    def manual_cookie_input(self):
        """Обновление cookies по кнопке"""
        from browser_cookies import BrowserDetector, CookiePromptDialog

        self.cookies_status.setText("⏳ Обновление...")
        self.manual_cookies_btn.setEnabled(False)

        success, method = BrowserDetector.extract_and_save_cookies(silent=True)

        self.manual_cookies_btn.setEnabled(True)

        if success:
            self.cookies_status.setText("✅ Cookies обновлены")
            self.cookies_status.setStyleSheet(
                "color: #4CAF50; background-color: rgba(76, 175, 80, 0.2); padding: 5px 10px; border-radius: 4px;")
            self.cookies_ready = True
            QMessageBox.information(self, "Успех", "✅ Cookies успешно обновлены!")
        else:
            self.cookies_status.setText("❌ Не удалось обновить")
            self.cookies_status.setStyleSheet(
                "color: #F44336; background-color: rgba(244, 67, 54, 0.2); padding: 5px 10px; border-radius: 4px;")
            CookiePromptDialog.show_manual_cookie_dialog(self)

    def add_row(self):
        if len(self.url_rows) >= 8:
            return

        idx = len(self.url_rows)
        row = UrlInputRow(idx)

        if self.cb_fragment.isChecked():
            row.toggle_time(True)

        row.text_started.connect(self.on_row_typing)
        self.rows_layout.addWidget(row)
        self.url_rows.append(row)

    def on_row_typing(self):
        if self.cb_queue.isChecked():
            self.add_row()

    def toggle_fragments(self, state):
        show = (state == Qt.Checked)
        for row in self.url_rows:
            row.toggle_time(show)

    def toggle_queue(self, state):
        if state == Qt.Unchecked:
            while len(self.url_rows) > 1:
                row = self.url_rows.pop()
                self.rows_layout.removeWidget(row)
                row.deleteLater()
        else:
            if self.url_rows[-1].get_url():
                self.add_row()

    def choose_path(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path:
            self.path_edit.setText(path)
            cfg.save_setting("download_path", path)

    def start_download(self):
        path = self.path_edit.text()
        if not path or not os.path.exists(path):
            self.status_label.setText("❌ Укажите папку")
            play_sound(False)
            return

        if not self.cookies_ready:
            ret = QMessageBox.question(
                self,
                "Продолжить без cookies?",
                "⚠️ Cookies не настроены. Некоторые видео могут быть недоступны.\n\n"
                "Продолжить скачивание?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ret == QMessageBox.No:
                return

        tasks = []
        fmt_key = self.combo_quality.currentText()
        yt_fmt = VIDEO_QUALITIES[fmt_key]

        for i, row in enumerate(self.url_rows):
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
                modes.append('together')
            if self.cb_audio.isChecked():
                modes.append('audio')
            if self.cb_video.isChecked():
                modes.append('video')
            if not modes and self.cb_cover.isChecked():
                modes.append('none')

            if not modes:
                self.status_label.setText("❌ Выберите формат")
                play_sound(False)
                return

            for mode in modes:
                tasks.append({
                    'url': url,
                    'path': path,
                    'mode': mode,
                    'quality_format': yt_fmt,
                    'cookie_mode': 'not use',
                    'time_section': time_sec,
                    'download_cover': self.cb_cover.isChecked() and mode == modes[0]
                })

        if not tasks:
            self.status_label.setText("❌ Добавьте ссылки")
            play_sound(False)
            return

        # Запуск потока
        self.thread = QThread()
        self.worker = DownloadWorker(tasks, self)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.progress_update.connect(self.status_label.setText)
        self.worker.finished.connect(self.on_download_finished)

        self.btn_download.setDisabled(True)
        self.btn_download.setText("⏳ Загрузка...")
        self.thread.start()

    def on_download_finished(self, success):
        self.btn_download.setDisabled(False)
        self.btn_download.setText("⬇️ СКАЧАТЬ")

        if success:
            self.status_label.setText("✅ Все файлы загружены!")
            play_sound(True)
        else:
            ret = QMessageBox.question(
                self,
                "Ошибка загрузки",
                "❌ Не удалось скачать видео.\n\n"
                "Возможно, cookies устарели. Попробовать обновить?",
                QMessageBox.Yes | QMessageBox.No
            )

            if ret == QMessageBox.Yes:
                self.manual_cookie_input()

            self.status_label.setText("⚠️ Ошибка (см. логи)")
            play_sound(False)


if __name__ == "__main__":
    ensure_binaries()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())