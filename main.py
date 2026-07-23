import sys
import os
import platform
import subprocess
import urllib.request
import zipfile
import shutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QFrame, QScrollArea, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

# --- CONFIGURACIÓN DE RUTAS ---
def get_base_dir():
    user_home = os.path.expanduser("~")
    base_folder = os.path.join(user_home, "NextFoxRLG")
    os.makedirs(base_folder, exist_ok=True)
    return base_folder

# Lista completa de emuladores con sus binarios y URLs portables
EMULATORS_DATA = [
    {
        "console": "PlayStation 1",
        "name": "DuckStation",
        "exec_win": "duckstation-qt-x64-ReleaseLTCG.exe",
        "exec_linux": "DuckStation-x86_64.AppImage",
        "folder": "PS1_DuckStation",
        "url_win": "https://github.com/stenzek/duckstation/releases/download/latest/duckstation-windows-x64-release.zip",
        "url_linux": "https://github.com/stenzek/duckstation/releases/download/latest/DuckStation-x86_64.AppImage"
    },
    {
        "console": "PlayStation 2",
        "name": "PCSX2",
        "exec_win": "pcsx2-qt.exe",
        "exec_linux": "pcsx2-qt-x86_64.AppImage",
        "folder": "PS2_PCSX2",
        "url_win": "https://github.com/PCSX2/pcsx2/releases/download/v1.7.5900/pcsx2-v1.7.5900-windows-x64-Qt.zip",
        "url_linux": "https://github.com/PCSX2/pcsx2/releases/download/v1.7.5900/pcsx2-v1.7.5900-linux-appimage-x64.AppImage"
    },
    {
        "console": "PSP",
        "name": "PPSSPP",
        "exec_win": "PPSSPPWindows64.exe",
        "exec_linux": "PPSSPPQt",
        "folder": "PSP_PPSSPP",
        "url_win": "https://www.ppsspp.org/files/1_17_1/ppsspp_win.zip",
        "url_linux": "https://www.ppsspp.org/files/1_17_1/ppsspp_linux.zip"
    },
    {
        "console": "Xbox Classic",
        "name": "xemu",
        "exec_win": "xemu.exe",
        "exec_linux": "xemu-x86_64.AppImage",
        "folder": "XboxClassic_xemu",
        "url_win": "https://github.com/xemu-project/xemu/releases/latest/download/xemu-win-x86_64.zip",
        "url_linux": "https://github.com/xemu-project/xemu/releases/latest/download/xemu-x86_64.AppImage"
    },
    {
        "console": "Xbox 360",
        "name": "Xenia",
        "exec_win": "xenia_canary.exe",
        "exec_linux": "xenia_canary",
        "folder": "Xbox360_Xenia",
        "url_win": "https://github.com/xenia-canary/xenia-canary/releases/latest/download/xenia_canary.zip",
        "url_linux": ""
    }
]

class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, url, dest_folder, is_zip):
        super().__init__()
        self.url = url
        self.dest_folder = dest_folder
        self.is_zip = is_zip

    def run(self):
        try:
            temp_file = os.path.join(self.dest_folder, "download_temp")
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(self.url, headers=headers)
            
            with urllib.request.urlopen(req) as response, open(temp_file, 'wb') as out_file:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if total_size > 0:
                        percent = int(downloaded * 100 / total_size)
                        self.progress.emit(min(percent, 100))

            if self.is_zip:
                with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                    zip_ref.extractall(self.dest_folder)
                os.remove(temp_file)
            else:
                # Si es un AppImage o binario directo
                target_name = os.path.basename(self.url)
                final_path = os.path.join(self.dest_folder, target_name)
                if os.path.exists(final_path):
                    os.remove(final_path)
                os.rename(temp_file, final_path)
                os.chmod(final_path, 0o755)

            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class NextFoxRLG(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NextFox Retro-Launcher-Gamer (Portable Build)")
        self.resize(950, 650)
        self.base_dir = get_base_dir()

        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
            QFrame { background-color: #1E1E1E; border-radius: 8px; }
            QPushButton#stars_btn {
                background-color: #FF0055; color: white;
                font-size: 26px; font-weight: bold; border-radius: 12px; padding: 18px 50px;
            }
            QPushButton#stars_btn:hover { background-color: #FF2A75; }
            QPushButton#action_btn_install { background-color: #007ACC; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px; }
            QPushButton#action_btn_play { background-color: #28A745; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px; }
            QProgressBar {
                border: 1px solid #444; border-radius: 5px; text-align: center; color: white; background: #222;
            }
            QProgressBar::chunk { background-color: #FF0055; border-radius: 4px; }
        """)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.init_start_menu()
        self.init_consoles_menu()

    def init_start_menu(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("NEXTFOX RLG")
        title.setFont(QFont("Arial", 36, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("NextFox Retro-Launcher-Gamer — Portable Edition")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setStyleSheet("color: #888888; margin-bottom: 40px;")
        subtitle.setAlignment(Qt.AlignCenter)

        stars_btn = QPushButton("STARS")
        stars_btn.setObjectName("stars_btn")
        stars_btn.setCursor(Qt.PointingHandCursor)
        stars_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(stars_btn)
        self.stacked_widget.addWidget(page)

    def init_consoles_menu(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)

        header_layout = QHBoxLayout()
        header_title = QLabel("CATÁLOGO DE CONSOLAS")
        header_title.setFont(QFont("Arial", 20, QFont.Bold))
        
        back_btn = QPushButton("← Volver")
        back_btn.setStyleSheet("color: white; background: #333; padding: 8px 16px; border-radius: 4px; font-weight: bold;")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        header_layout.addWidget(back_btn)
        main_layout.addLayout(header_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        is_windows = platform.system() == "Windows"
        
        for item in EMULATORS_DATA:
            card = QFrame()
            card_layout = QHBoxLayout(card)

            info_layout = QVBoxLayout()
            console_lbl = QLabel(item["console"])
            console_lbl.setFont(QFont("Arial", 15, QFont.Bold))
            emu_lbl = QLabel(f"Emulador: {item['name']}")
            emu_lbl.setStyleSheet("color: #AAAAAA;")
            
            pbar = QProgressBar()
            pbar.setVisible(False)
            pbar.setFixedHeight(12)

            info_layout.addWidget(console_lbl)
            info_layout.addWidget(emu_lbl)
            info_layout.addWidget(pbar)

            emu_dir = os.path.join(self.base_dir, item["folder"])
            os.makedirs(emu_dir, exist_ok=True)

            target_exec = item["exec_win"] if is_windows else item["exec_linux"]
            exec_path = os.path.join(emu_dir, target_exec)
            is_installed = os.path.exists(exec_path)

            action_btn = QPushButton("JUGAR" if is_installed else "DESCARGAR")
            action_btn.setObjectName("action_btn_play" if is_installed else "action_btn_install")
            action_btn.setCursor(Qt.PointingHandCursor)

            url = item["url_win"] if is_windows else item["url_linux"]

            action_btn.clicked.connect(
                lambda checked, p=exec_path, d=emu_dir, u=url, btn=action_btn, pb=pbar, name=item['name']: 
                self.handle_action(p, d, u, btn, pb, name)
            )

            card_layout.addLayout(info_layout)
            card_layout.addStretch()
            card_layout.addWidget(action_btn)
            scroll_layout.addWidget(card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.stacked_widget.addWidget(page)

    def handle_action(self, exec_path, emu_dir, url, btn, pbar, name):
        if os.path.exists(exec_path):
            try:
                subprocess.Popen([exec_path], cwd=emu_dir)
            except Exception as e:
                QMessageBox.critical(self, "Error de Ejecución", f"No se pudo iniciar {name}:\n{e}")
        else:
            if not url:
                QMessageBox.warning(self, "Sin enlace", f"No hay enlace portable configurado para {name} en esta plataforma.")
                return

            btn.setEnabled(False)
            pbar.setVisible(True)
            pbar.setValue(0)

            is_zip = url.endswith('.zip')
            self.worker = DownloadWorker(url, emu_dir, is_zip)
            self.worker.progress.connect(pbar.setValue)
            
            def on_finish(success, err_msg):
                pbar.setVisible(False)
                if success and os.path.exists(exec_path):
                    btn.setText("JUGAR")
                    btn.setObjectName("action_btn_play")
                    btn.setStyleSheet("background-color: #28A745; color: white; font-weight: bold; border-radius: 6px; padding: 10px 20px;")
                    btn.setEnabled(True)
                else:
                    btn.setText("DESCARGAR")
                    btn.setEnabled(True)
                    QMessageBox.warning(self, "Error de Descarga", f"Ocurrió un error descargando {name}:\n{err_msg}")

            self.worker.finished.connect(on_finish)
            self.worker.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NextFoxRLG()
    window.show()
    sys.exit(app.exec())
