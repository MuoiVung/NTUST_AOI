import os
import sys
import shutil
import socket
import webbrowser
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QTextEdit, QGridLayout, QFrame, QCheckBox, QMessageBox, QLineEdit, QFileDialog
)
from PySide6.QtCore import QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon

# ─── PATH CONFIG ──────────────────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"

if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(sys.executable)
    _project_subdir = os.path.join(_exe_dir, "ntust_aoi")
    if os.path.isdir(_project_subdir) and os.path.isdir(os.path.join(_project_subdir, "ntust_aoi_pcb_db")):
        BASE_DIR = _project_subdir
    else:
        BASE_DIR = _exe_dir
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "ntust_aoi_pcb_db")
UI_DIR = os.path.join(BASE_DIR, "NTUST-AOI-UI")

PYTHON_EXE = getattr(sys, "executable", shutil.which("python") or shutil.which("python3") or "python")
NPM_EXE = shutil.which("npm") or (r"C:\Program Files\nodejs\npm.cmd" if IS_WINDOWS else "npm")
DOCKER_EXE = shutil.which("docker") or "docker"

# ─── STYLE ────────────────────────────────────────────────────────────────────
DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
QFrame#ServiceCard {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}
QPushButton#BtnStart {
    background-color: #238636;
    color: white;
    border: none;
}
QPushButton#BtnStart:hover { background-color: #2ea043; }
QPushButton#BtnStop {
    background-color: #da3633;
    color: white;
    border: none;
}
QPushButton#BtnStop:hover { background-color: #f85149; }
QTabWidget::pane {
    border: 1px solid #30363d;
    border-radius: 4px;
    background: #0d1117;
}
QTabBar::tab {
    background: #161b22;
    border: 1px solid #30363d;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #21262d;
    border-bottom-color: #21262d;
}
QTextEdit {
    background-color: #010409;
    border: none;
    font-family: Consolas, monospace;
    font-size: 13px;
    color: #e6edf3;
    padding: 8px;
}
"""

SERVICES_DEF = [
    ("docker", "🐳 Docker", "Manage DB & Nginx"),
    ("backend", "⚡ API", "FastAPI Port 8000"),
    ("machine", "⚙️ PLC", "Core Machine Logic"),
    ("monitor", "📷 Camera", "Folder Monitor"),
    ("sync", "☁️ Cloud", "Sync to MinIO"),
    ("ui", "🎨 Web UI", "React Port 3001"),
]

# ─── UTILS ────────────────────────────────────────────────────────────────────
def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False

# ─── CUSTOM WIDGETS ───────────────────────────────────────────────────────────
class ServiceCard(QFrame):
    def __init__(self, key, title, desc):
        super().__init__()
        self.key = key
        self.setObjectName("ServiceCard")
        self.setFixedHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Top row: title & status dot
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.lbl_dot = QLabel("⚫")
        self.lbl_dot.setStyleSheet("color: #7d8590; font-size: 14px;")
        
        top_layout.addWidget(self.lbl_dot)
        top_layout.addWidget(self.lbl_title)
        top_layout.addStretch()
        
        # Bottom row: desc & extra controls
        bot_layout = QHBoxLayout()
        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        bot_layout.addWidget(self.lbl_desc)
        bot_layout.addStretch()
        
        self.lbl_status = QLabel("Idle")
        self.lbl_status.setStyleSheet("color: #7d8590; font-size: 12px; font-style: italic;")
        bot_layout.addWidget(self.lbl_status)
        
        layout.addLayout(top_layout)
        layout.addLayout(bot_layout)
        
    def set_status(self, state, text=None):
        if state == "running":
            self.lbl_dot.setStyleSheet("color: #d29922; font-size: 14px;")
            self.lbl_status.setText(text or "Starting...")
        elif state == "ok":
            self.lbl_dot.setStyleSheet("color: #3fb950; font-size: 14px;")
            self.lbl_status.setText(text or "Running")
        elif state == "error":
            self.lbl_dot.setStyleSheet("color: #f85149; font-size: 14px;")
            self.lbl_status.setText(text or "Error")
        else:
            self.lbl_dot.setStyleSheet("color: #7d8590; font-size: 14px;")
            self.lbl_status.setText(text or "Idle")

# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class LauncherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AOI Platform - Launcher")
        self.resize(900, 700)
        self.setStyleSheet(DARK_THEME_QSS)
        
        self.processes = {}
        self.cards = {}
        self.log_editors = {}
        
        # Track auto-start
        self.is_starting = False
        self.is_stopping = False

        self._build_ui()
        self._init_processes()
        
        # Auto-detect existing services
        QTimer.singleShot(1000, self.detect_services)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # Header
        header = QLabel("🔬 AOI System Control Center")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        main_layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Tab 1: Dashboard
        tab_dash = QWidget()
        dash_layout = QVBoxLayout(tab_dash)
        dash_layout.setContentsMargins(16, 16, 16, 16)
        
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, (key, title, desc) in enumerate(SERVICES_DEF):
            card = ServiceCard(key, title, desc)
            self.cards[key] = card
            grid.addWidget(card, i // 2, i % 2)
            
        dash_layout.addLayout(grid)
        dash_layout.addStretch()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Start All Services")
        self.btn_start.setObjectName("BtnStart")
        self.btn_start.setFixedHeight(45)
        self.btn_start.clicked.connect(self.start_all)
        
        self.btn_stop = QPushButton("⏹ Stop All Services")
        self.btn_stop.setObjectName("BtnStop")
        self.btn_stop.setFixedHeight(45)
        self.btn_stop.clicked.connect(self.stop_all)
        self.btn_stop.setEnabled(False)
        
        self.btn_ui = QPushButton("🌐 Open Operator Dashboard")
        self.btn_ui.setFixedHeight(45)
        self.btn_ui.clicked.connect(lambda: webbrowser.open("http://localhost:3001"))
        self.btn_ui.setEnabled(False)
        
        btn_layout.addWidget(self.btn_start, 2)
        btn_layout.addWidget(self.btn_stop, 2)
        btn_layout.addWidget(self.btn_ui, 1)
        dash_layout.addLayout(btn_layout)
        
        self.tabs.addTab(tab_dash, "Dashboard")
        
        # Tab 2: Logs
        self.tab_logs = QTabWidget()
        self._add_log_tab("General", "system")
        for key, title, _ in SERVICES_DEF:
            # Extract just the name after the emoji for the tab label
            name = title.split(" ", 1)[-1]
            self._add_log_tab(name, key)
            
        # Log controls
        log_ctrl_layout = QHBoxLayout()
        btn_clear = QPushButton("Clear Logs")
        btn_clear.clicked.connect(self._clear_logs)
        log_ctrl_layout.addStretch()
        log_ctrl_layout.addWidget(btn_clear)
        
        log_container = QWidget()
        log_container_layout = QVBoxLayout(log_container)
        log_container_layout.addWidget(self.tab_logs)
        log_container_layout.addLayout(log_ctrl_layout)
        self.tabs.addTab(log_container, "System Logs")
        
        # Tab 3: Settings
        tab_set = QWidget()
        set_layout = QVBoxLayout(tab_set)
        
        # Monitor Folder Setting
        form_layout = QGridLayout()
        form_layout.setSpacing(10)
        
        lbl_monitor = QLabel("Monitor Image Folder (IMAGE_WATCH_DIR):")
        self.txt_monitor_dir = QLineEdit()
        self.txt_monitor_dir.setPlaceholderText("Select folder to monitor incoming images...")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_monitor_dir)
        
        form_layout.addWidget(lbl_monitor, 0, 0)
        form_layout.addWidget(self.txt_monitor_dir, 0, 1)
        form_layout.addWidget(btn_browse, 0, 2)
        
        lbl_minio = QLabel("MinIO Endpoint:")
        self.txt_minio = QLineEdit()
        form_layout.addWidget(lbl_minio, 1, 0)
        form_layout.addWidget(self.txt_minio, 1, 1, 1, 2)
        
        set_layout.addLayout(form_layout)
        
        self.chk_auto_sync = QCheckBox("Enable Cloud Sync on Start")
        self.chk_auto_sync.setChecked(True)
        set_layout.addWidget(self.chk_auto_sync)
        
        btn_save_settings = QPushButton("💾 Save Settings")
        btn_save_settings.clicked.connect(self._save_settings)
        btn_save_settings.setFixedWidth(200)
        
        set_layout.addSpacing(20)
        set_layout.addWidget(btn_save_settings, alignment=Qt.AlignCenter)
        set_layout.addStretch()
        self.tabs.addTab(tab_set, "Settings")
        
        self._load_settings()

    def _load_settings(self):
        env_path = os.path.join(DB_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if line.startswith("IMAGE_WATCH_DIR="):
                        self.txt_monitor_dir.setText(line.split("=", 1)[1].strip())
                    elif line.startswith("MINIO_ENDPOINT="):
                        self.txt_minio.setText(line.split("=", 1)[1].strip())

    def _browse_monitor_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Monitor Directory")
        if d:
            self.txt_monitor_dir.setText(d)

    def _save_settings(self):
        env_path = os.path.join(DB_DIR, ".env")
        if not os.path.exists(env_path):
            QMessageBox.warning(self, "Error", ".env file not found!")
            return
            
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if line.startswith("IMAGE_WATCH_DIR="):
                new_lines.append(f"IMAGE_WATCH_DIR={self.txt_monitor_dir.text().strip()}\n")
            elif line.startswith("MINIO_ENDPOINT="):
                new_lines.append(f"MINIO_ENDPOINT={self.txt_minio.text().strip()}\n")
            else:
                new_lines.append(line)
                
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        QMessageBox.information(self, "Success", "Settings saved successfully to .env!\n\nPlease Stop and Restart services to apply changes.")

    def _add_log_tab(self, label, key):
        txt = QTextEdit()
        txt.setReadOnly(True)
        self.log_editors[key] = txt
        self.tab_logs.addTab(txt, label)

    def log_msg(self, msg, key="system"):
        txt = self.log_editors.get(key)
        if txt:
            txt.append(msg)
            scrollbar = txt.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        # Also copy important stuff to system log
        if key != "system":
            self.log_editors["system"].append(f"[{key.upper()}] {msg}")

    def _clear_logs(self):
        for txt in self.log_editors.values():
            txt.clear()

    # ─── PROCESS MANAGEMENT ───────────────────────────────────────────────────
    def _init_processes(self):
        # We will use QProcess for background services.
        pass

    def _create_process(self, key):
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(lambda k=key, p=proc: self._handle_stdout(k, p))
        proc.finished.connect(lambda exitCode, exitStatus, k=key: self._handle_finished(k, exitCode))
        return proc

    def _handle_stdout(self, key, proc):
        data = proc.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self.log_msg(line.strip(), key)

    def _handle_finished(self, key, exitCode):
        if key in self.cards:
            if self.is_stopping:
                self.cards[key].set_status("idle", "Stopped")
            else:
                self.cards[key].set_status("error", f"Exited ({exitCode})")
        
        if not self.is_stopping:
            self.log_msg(f"Process {key} exited unexpectedly with code {exitCode}", key)

    def detect_services(self):
        self.log_msg("Detecting running services...", "system")
        running_count = 0
        
        # Naive check by ports
        if port_open(5433):
            self.cards["docker"].set_status("ok", "Already running")
            running_count += 1
        if port_open(8000):
            self.cards["backend"].set_status("ok", "Already running")
            running_count += 1
        if port_open(3001):
            self.cards["ui"].set_status("ok", "Already running")
            running_count += 1
            
        if running_count > 0:
            self.log_msg(f"Detected {running_count} services already running.", "system")
            self.btn_start.setEnabled(False)
            self.btn_start.setText("🟢 System Running")
            self.btn_stop.setEnabled(True)
            self.btn_stop.setText("⏹ Stop All Services")
            if port_open(3001):
                self.btn_ui.setEnabled(True)

    def start_all(self):
        self.is_starting = True
        self.is_stopping = False
        
        # UI State: Starting
        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳ Starting Services...")
        self.btn_stop.setEnabled(False)
        self.btn_ui.setEnabled(False)
        
        self.log_msg("Starting all services...", "system")
        
        # 1. Docker
        self.cards["docker"].set_status("running")
        self.log_msg("Running docker-compose up -d...", "docker")
        proc_doc = self._create_process("docker")
        proc_doc.setWorkingDirectory(DB_DIR)
        proc_doc.start(DOCKER_EXE, ["compose", "up", "-d"])
        self.processes["docker"] = proc_doc
        
        # We use a timer to wait for docker to finish before starting others 
        # (in a real app we'd chain them, but here we'll just delay a bit for visual)
        QTimer.singleShot(2000, self.start_backend_and_scripts)

    def start_backend_and_scripts(self):
        self.cards["docker"].set_status("ok")
        
        # 2. FastAPI
        if not port_open(8000):
            self.cards["backend"].set_status("running")
            proc_be = self._create_process("backend")
            proc_be.setWorkingDirectory(DB_DIR)
            proc_be.start(PYTHON_EXE, ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"])
            self.processes["backend"] = proc_be
            self.cards["backend"].set_status("ok")
        
        # 3. Machine Control
        self.cards["machine"].set_status("running")
        proc_machine = self._create_process("machine")
        proc_machine.setWorkingDirectory(os.path.join(BASE_DIR, "machine_control"))
        shopfloor_url = os.environ.get("SHOPFLOOR_API_URL", "http://127.0.0.1:9090/ashx/WebAPI/Board/SerialTest/HandlerGetSerialInfo.ashx")
        proc_machine.start(PYTHON_EXE, ["pc_controller.py", "--mode", "semi-auto", "--api-mode", "real", "--api-endpoint", shopfloor_url])
        self.processes["machine"] = proc_machine
        self.cards["machine"].set_status("ok")
        
        # 3.5 Shopfloor Simulator (No Dashboard Card)
        proc_shopfloor = self._create_process("shopfloor")
        proc_shopfloor.setWorkingDirectory(os.path.join(BASE_DIR, "simulation"))
        proc_shopfloor.start(PYTHON_EXE, ["shopfloor_sim.py"])
        self.processes["shopfloor"] = proc_shopfloor
        
        # 4. Monitor
        self.cards["monitor"].set_status("running")
        proc_mon = self._create_process("monitor")
        proc_mon.setWorkingDirectory(DB_DIR)
        proc_mon.start(PYTHON_EXE, ["scripts/folder_monitor.py"])
        self.processes["monitor"] = proc_mon
        self.cards["monitor"].set_status("ok")
        
        # 4. Sync
        if self.chk_auto_sync.isChecked():
            self.cards["sync"].set_status("running")
            proc_sync = self._create_process("sync")
            proc_sync.setWorkingDirectory(DB_DIR)
            proc_sync.start(PYTHON_EXE, ["scripts/sync_to_server.py"])
            self.processes["sync"] = proc_sync
            self.cards["sync"].set_status("ok")
        else:
            self.cards["sync"].set_status("idle", "Disabled")

        # 5. UI
        if not port_open(3001):
            self.cards["ui"].set_status("running")
            proc_ui = self._create_process("ui")
            proc_ui.setWorkingDirectory(UI_DIR)
            proc_ui.start(NPM_EXE, ["run", "dev"])
            self.processes["ui"] = proc_ui
            self.cards["ui"].set_status("ok")
            
        self.log_msg("All services startup sequence triggered.", "system")
        
        # UI State: Running
        self.btn_start.setText("🟢 System Running")
        self.btn_stop.setEnabled(True)
        self.btn_ui.setEnabled(True)
        self.is_starting = False

    def stop_all(self, exit_after=False):
        reply = QMessageBox.question(self, "Confirm Stop", 
            "Are you sure you want to stop all services?\nThis will interrupt active connections to PLC and AI nodes.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.No:
            return

        self.is_stopping = True
        
        # UI State: Stopping
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("⏳ Stopping Services...")
        self.btn_start.setEnabled(False)
        self.btn_ui.setEnabled(False)
        
        self.log_msg("Stopping all services...", "system")
        
        # Terminate QProcesses
        for key, proc in self.processes.items():
            if key != "docker" and proc.state() != QProcess.NotRunning:
                if key in self.cards:
                    self.cards[key].set_status("running", "Stopping...")
                proc.terminate()
                if not proc.waitForFinished(5000):  # Wait up to 5s gracefully
                    proc.kill()
                if key in self.cards:
                    self.cards[key].set_status("idle", "Stopped")
        
        # Stop Docker without freezing UI completely
        self.cards["docker"].set_status("running", "Stopping...")
        self.log_msg("Running docker-compose down...", "docker")
        
        proc_doc = self._create_process("docker")
        proc_doc.setWorkingDirectory(DB_DIR)
        proc_doc.start(DOCKER_EXE, ["compose", "down"])
        
        # Wait asynchronously to avoid UI freeze
        while not proc_doc.waitForFinished(100):
            QApplication.processEvents()
            
        self.cards["docker"].set_status("idle", "Stopped")
        
        self.processes.clear()
        self.log_msg("All services stopped successfully.", "system")
        
        # UI State: Idle (Stopped)
        self.btn_stop.setText("⏹ Stop All Services")
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶ Start All Services")
        self.is_stopping = False
        
        if exit_after:
            QApplication.quit()

    def closeEvent(self, event):
        if self.processes and not self.is_stopping:
            reply = QMessageBox.question(self, "Confirm Exit", 
                "Services are still running in the background.\nDo you want to stop them and exit?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                event.ignore()
                self.stop_all(exit_after=True)
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherApp()
    window.show()
    sys.exit(app.exec())
