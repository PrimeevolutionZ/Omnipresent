#!/usr/bin/env python3
"""
Entry-point для YouTube-Downloader.
"""

import sys
from PySide6.QtWidgets import QApplication

# Импорт в порядке слоёв
from core.utils import ensure_binaries
from core.config import cfg
from ui.main_window import MainWindow

# ---------- Тёмная тема (полностью) ----------
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
QLabel#TitleLabel {
    font-size: 24px; font-weight: bold; color: #00d4ff; padding: 10px;
}
QLabel#SectionLabel {
    font-size: 14px; font-weight: 600; color: #00d4ff; padding: 5px 0;
}
QCheckBox { spacing: 8px; padding: 5px; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 4px; border: 2px solid #555;
    background-color: #2b2b2b;
}
QCheckBox::indicator:checked {
    background-color: #00d4ff; border-color: #00d4ff;
}
QCheckBox::indicator:hover { border-color: #00d4ff; }
QLineEdit {
    background-color: #252d42; border: 2px solid #3a4a6b; border-radius: 6px;
    padding: 8px 12px; selection-background-color: #00d4ff; color: #eaeaea;
}
QLineEdit:focus { border-color: #00d4ff; background-color: #2d3548; }
QComboBox {
    background-color: #252d42; border: 2px solid #3a4a6b; padding: 8px 12px;
    border-radius: 6px; min-height: 25px;
}
QComboBox:focus { border-color: #00d4ff; }
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d4ff, stop:1 #0099cc);
    color: #000; border: none; padding: 10px 20px; border-radius: 8px;
    font-weight: bold; font-size: 13px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00e5ff, stop:1 #00b8e6);
}
QPushButton:disabled { background-color: #3a3a3a; color: #666; }
QPushButton#SecondaryBtn {
    background: transparent; border: 2px solid #00d4ff; color: #00d4ff;
    padding: 8px 16px;
}
QPushButton#SecondaryBtn:hover {
    background-color: rgba(0, 212, 255, 0.1);
}
QPushButton#DownloadBtn {
    min-height: 50px; font-size: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #0099cc);
}
QScrollArea { border: none; background-color: transparent; }
QScrollBar:vertical {
    background-color: #1a1a2e; width: 12px; border-radius: 6px;
}
QScrollBar::handle:vertical {
    background-color: #00d4ff; border-radius: 6px; min-height: 30px;
}
"""


def main() -> None:
    ensure_binaries()
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()