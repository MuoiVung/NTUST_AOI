"""
NTUST AOI System Launcher
One-click startup: Docker → DB Services → FastAPI Backend → Vite UI → Browser
On re-open: auto-detects which services are already running.
"""

import tkinter as tk
from tkinter import scrolledtext
import subprocess, threading, time, os, sys, webbrowser, socket, shutil

# ─── PLATFORM CONFIG ──────────────────────────────────────────────────────────
IS_WINDOWS = sys.platform == "win32"
CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0

# ─── PATH CONFIG ──────────────────────────────────────────────────────────────
# When bundled by PyInstaller, __file__ points to a temp extraction folder.
# Use sys.executable (the .exe path) when frozen. Also handle the case where
# the .exe is deployed to Desktop while the project is in Desktop\ntust_aoi\.
if getattr(sys, "frozen", False):
    _exe_dir = os.path.dirname(sys.executable)
    # If the exe is in the parent of the project (e.g. Desktop\), look one level down
    _project_subdir = os.path.join(_exe_dir, "ntust_aoi")
    if os.path.isdir(_project_subdir) and os.path.isdir(os.path.join(_project_subdir, "ntust_aoi_pcb_db")):
        BASE_DIR = _project_subdir
    else:
        BASE_DIR = _exe_dir
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_DIR = os.path.join(BASE_DIR, "ntust_aoi_pcb_db")
UI_DIR = os.path.join(BASE_DIR, "NTUST-AOI-UI")

# Auto-detect Python: prefer the running interpreter, then PATH, then a known fallback.
PYTHON_EXE = (
    sys.executable
    or shutil.which("python")
    or shutil.which("python3")
    or (r"C:\Users\OMNI-3125HTT-ADN\AppData\Local\Programs\Python\Python311\python.exe" if IS_WINDOWS else "python3")
)
# Auto-detect npm from PATH, fallback to a known Windows location.
NPM_EXE = (
    shutil.which("npm")
    or (r"C:\Program Files\nodejs\npm.cmd" if IS_WINDOWS else "npm")
)
DOCKER_DESKTOP = r"C:\Program Files\Docker\Docker\Docker Desktop.exe" if IS_WINDOWS else "/Applications/Docker.app"

FOLDER_MONITOR_PY = os.path.join(DB_DIR, "scripts", "folder_monitor.py")

BACKEND_PORT   = 8000
UI_PORT        = 3001
UI_URL         = f"http://localhost:{UI_PORT}"

# ─── THEME ────────────────────────────────────────────────────────────────────
BG           = "#0d1117"
PANEL_BG     = "#161b22"
CARD_BG      = "#1c2128"
BORDER       = "#30363d"
TEXT_MAIN    = "#e6edf3"
TEXT_DIM     = "#7d8590"
TEXT_SUB     = "#8b949e"
GREEN        = "#3fb950"
GREEN_DIM    = "#1a4a34"
RED          = "#f85149"
RED_DIM      = "#4a1a1a"
YELLOW       = "#d29922"
BLUE         = "#388bfd"
BLUE_DIM     = "#1a2a4a"
PURPLE       = "#bc8cff"

# Service definitions: (key, icon, label, check_fn)
# check_fn returns True if already running
def docker_ok():
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=4,
                           creationflags=CREATION_FLAGS)
        return r.returncode == 0
    except Exception:
        return False

def port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False

def wait_port(port, timeout=90, interval=2):
    t = time.time()
    while time.time() - t < timeout:
        if port_open(port): return True
        time.sleep(interval)
    return False

def monitor_ok():
    """Checks if folder_monitor.py is running by scanning the process list."""
    try:
        if IS_WINDOWS:
            cmd = ['wmic', 'process', 'where', "name='python.exe'", 'get', 'commandline']
            r = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS)
            if r.returncode == 0 and r.stdout:
                return "folder_monitor.py" in r.stdout
        else:
            r = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout:
                return "folder_monitor.py" in r.stdout
        return False
    except:
        return False

def sync_ok():
    """Checks if sync_to_server.py is running."""
    try:
        if IS_WINDOWS:
            cmd = ['wmic', 'process', 'where', "name='python.exe'", 'get', 'commandline']
            r = subprocess.run(cmd, capture_output=True, text=True, creationflags=CREATION_FLAGS)
            if r.returncode == 0 and r.stdout:
                return "sync_to_server.py" in r.stdout
        else:
            r = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout:
                return "sync_to_server.py" in r.stdout
        return False
    except:
        return False

SERVICES = [
    ("docker",   "🐳", "Docker Daemon",     lambda: docker_ok()),
    ("db",       "🗄️", "Database & Nginx",  lambda: port_open(5433)),
    ("backend",  "⚡", "FastAPI Backend",    lambda: port_open(BACKEND_PORT)),
    ("monitor",  "📂", "Folder Monitor",    lambda: monitor_ok()),
    ("sync",     "☁️", "Cloud Sync (MinIO)", lambda: sync_ok()),
    ("ui",       "🎨", "Vite UI Server",     lambda: port_open(UI_PORT)),
    ("browser",  "🌐", "Open Browser",       lambda: False),
]

STATE_COLORS = {
    "idle":     TEXT_DIM,
    "running":  YELLOW,
    "ok":       GREEN,
    "error":    RED,
    "stopping": YELLOW,
}
STATE_TEXTS = {
    "idle":     "Idle",
    "running":  "Starting…",
    "ok":       "✔  Running",
    "error":    "✘  Failed",
    "stopping": "Stopping…",
}


class LauncherApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("NTUST AOI — Launcher")
        self.geometry("780x800")
        self.minsize(780, 680)
        self.resizable(True, True)
        self.configure(bg=BG)

        self._proc_backend = None
        self._proc_ui      = None
        self._proc_monitor = None
        self._dots  = {}
        self._texts = {}
        self._sync_enabled = tk.BooleanVar(value=True)

        self._build_ui()

        # Auto-detect on startup
        threading.Thread(target=self._detect_services, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # UI LAYOUT
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=PANEL_BG, pady=20)
        hdr.pack(fill="x")

        tk.Label(hdr, text="🔬  NTUST AOI Platform",
                 font=("Segoe UI", 22, "bold"), fg=TEXT_MAIN, bg=PANEL_BG
                 ).pack()
        tk.Label(hdr, text="Automated Optical Inspection — System Launcher",
                 font=("Segoe UI", 10), fg=TEXT_DIM, bg=PANEL_BG
                 ).pack(pady=(3, 0))

        # Auto Adjust Button in Header
        self._btn_fit = tk.Button(
            hdr, text="⛶  Auto Fit", font=("Segoe UI", 8, "bold"),
            bg=BORDER, fg=TEXT_DIM, relief="flat", padx=8, pady=2,
            activebackground=CARD_BG, activeforeground=TEXT_MAIN,
            cursor="hand2", command=self._auto_size
        )
        self._btn_fit.place(relx=0.98, rely=0.1, anchor="ne")

        # ── Service cards ────────────────────────────────────────────────────
        cards = tk.Frame(self, bg=BG, padx=24, pady=6)
        cards.pack(fill="x")

        tk.Label(cards, text="Service Status",
                 font=("Segoe UI", 9, "bold"), fg=TEXT_DIM, bg=BG, anchor="w"
                 ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # Setup 2 columns
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        for idx, (key, icon, label, _) in enumerate(SERVICES):
            card = tk.Frame(cards, bg=CARD_BG, pady=6, padx=14,
                            highlightbackground=BORDER, highlightthickness=1)
            
            # Grid placement (2 columns)
            r = (idx // 2) + 1
            c = idx % 2
            
            # If it's the last service and odd count, let it span 2 columns
            if idx == len(SERVICES) - 1 and len(SERVICES) % 2 != 0:
                card.grid(row=r, column=c, columnspan=2, sticky="ew", padx=3, pady=3)
            else:
                card.grid(row=r, column=c, sticky="ew", padx=3, pady=3)

            dot = tk.Label(card, text="●", font=("Segoe UI", 14),
                           fg=TEXT_DIM, bg=CARD_BG)
            dot.pack(side="left", padx=(0, 8))

            icon_lbl = tk.Label(card, text=icon, font=("Segoe UI", 12),
                                fg=TEXT_MAIN, bg=CARD_BG, width=3)
            icon_lbl.pack(side="left")

            tk.Label(card, text=label, font=("Segoe UI", 10, "bold"),
                     fg=TEXT_MAIN, bg=CARD_BG, anchor="w").pack(side="left", padx=4)

            state_lbl = tk.Label(card, text="Checking…",
                                 font=("Segoe UI", 9, "italic"),
                                 fg=TEXT_DIM, bg=CARD_BG)
            state_lbl.pack(side="right", padx=6)

            # Add Master Toggle for Sync service
            if key == "sync":
                chk = tk.Checkbutton(
                    card, text="Enabled", variable=self._sync_enabled,
                    bg=CARD_BG, fg=TEXT_DIM, activebackground=CARD_BG,
                    activeforeground=TEXT_MAIN, selectcolor=BG,
                    font=("Segoe UI", 8), cursor="hand2",
                    command=self._on_sync_toggle
                )
                chk.pack(side="right", padx=6)

            self._dots[key]  = dot
            self._texts[key] = state_lbl

        # ── Button bar (Pack early at bottom to ensure visibility) ──────────
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(side="bottom", fill="x")

        bar = tk.Frame(self, bg=PANEL_BG, pady=18, padx=24)
        bar.pack(side="bottom", fill="x")

        # START button
        self._btn_start = self._make_btn(
            bar, "▶   Start All Services",
            bg=BLUE, fg="white", abg="#2563eb",
            padx=32, pady=14, font_size=13,
            cmd=self._on_start
        )
        self._btn_start.pack(side="left")

        # OPEN UI button
        self._btn_open = self._make_btn(
            bar, "🌐   Open UI",
            bg=CARD_BG, fg=TEXT_DIM, abg=BORDER,
            padx=24, pady=14, font_size=12,
            cmd=lambda: webbrowser.open(UI_URL),
            state="disabled"
        )
        self._btn_open.pack(side="left", padx=10)

        # CLOSE SERVICES button
        self._btn_close = self._make_btn(
            bar, "⏹   Close Services",
            bg=RED_DIM, fg=RED, abg="#5a1a1a",
            padx=24, pady=14, font_size=12,
            cmd=self._on_close_services,
            state="disabled"
        )
        self._btn_close.pack(side="left")

        # Status label on right
        self._status_lbl = tk.Label(
            bar, text="", font=("Segoe UI", 10, "italic"),
            fg=TEXT_DIM, bg=PANEL_BG
        )
        self._status_lbl.pack(side="right")

        # ── Log (Takes remaining space) ─────────────────────────────────────
        log_outer = tk.Frame(self, bg=BG, padx=24)
        log_outer.pack(fill="both", expand=True, pady=(0, 4))

        tk.Label(log_outer, text="Output Log",
                 font=("Segoe UI", 9, "bold"), fg=TEXT_DIM, bg=BG, anchor="w"
                 ).pack(fill="x", pady=(0, 4))

        self._log = scrolledtext.ScrolledText(
            log_outer, height=14, font=("Consolas", 9),
            bg="#090d12", fg="#8b949e", insertbackground=TEXT_MAIN,
            borderwidth=0, highlightthickness=1,
            highlightbackground=BORDER, relief="flat", state="disabled"
        )
        self._log.pack(fill="both", expand=True)
        self._log.tag_config("ok",   foreground=GREEN)
        self._log.tag_config("err",  foreground=RED)
        self._log.tag_config("info", foreground=BLUE)
        self._log.tag_config("warn", foreground=YELLOW)

    def _make_btn(self, parent, text, bg, fg, abg,
                  padx, pady, font_size, cmd, state="normal"):
        btn = tk.Button(
            parent, text=text,
            font=("Segoe UI", font_size, "bold"),
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            relief="flat", padx=padx, pady=pady,
            cursor="hand2", command=cmd, state=state,
            bd=0, highlightthickness=0
        )
        return btn

    # ──────────────────────────────────────────────────────────────────────────
    # LOG HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _log_write(self, msg, tag=""):
        def _do():
            self._log.configure(state="normal")
            ts = time.strftime("%H:%M:%S")
            self._log.insert("end", f"[{ts}] {msg}\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _set_service(self, key, state):
        color = STATE_COLORS.get(state, TEXT_DIM)
        text  = STATE_TEXTS.get(state, "")
        def _do():
            if key in self._dots:  self._dots[key].config(fg=color)
            if key in self._texts: self._texts[key].config(fg=color, text=text)
        self.after(0, _do)

    def _set_status(self, msg, color=None):
        self.after(0, lambda: self._status_lbl.config(
            text=msg, fg=color or TEXT_DIM))

    # ──────────────────────────────────────────────────────────────────────────
    # AUTO-DETECT on startup
    # ──────────────────────────────────────────────────────────────────────────

    def _detect_services(self):
        """Check which services are already running and update UI accordingly."""
        self._log_write("Checking existing services…", "info")
        self._set_status("Detecting services…")

        all_checks = [
            ("docker",  "Docker Daemon",   docker_ok,             None),
            ("db",      "Database",        lambda: port_open(5433), 5433),
            ("backend", "FastAPI Backend", lambda: port_open(BACKEND_PORT), BACKEND_PORT),
            ("monitor", "Folder Monitor",  monitor_ok,            None),
            ("ui",      "Vite UI",         lambda: port_open(UI_PORT), UI_PORT),
        ]

        any_running = False
        all_running = True

        for key, name, check_fn, _ in all_checks:
            is_up = check_fn()
            if is_up:
                self._set_service(key, "ok")
                self._log_write(f"  {name}: already running ✓", "ok")
                any_running = True
            else:
                self._set_service(key, "idle")
                self._log_write(f"  {name}: not running", "warn")
                all_running = False

        # Browser is never "pre-detected"
        self._set_service("browser", "idle")

        if all_running:
            self._log_write("All services already running! Ready to use.", "ok")
            self._set_status("✅  All services running", GREEN)
            self.after(0, self._activate_running_state)
        elif any_running:
            self._log_write("Some services running. You can start missing ones or close all.", "warn")
            self._set_status("⚠️  Partial services detected", YELLOW)
            self.after(0, lambda: self._btn_close.config(state="normal"))
            self.after(0, lambda: self._btn_start.config(text="▶   Start Missing Services"))
            if port_open(UI_PORT):
                self.after(0, lambda: self._btn_open.config(state="normal", fg=GREEN))
        else:
            self._log_write("No services running. Click 'Start All Services'.", "info")
            self._set_status("Ready to start", TEXT_DIM)

    def _activate_running_state(self):
        """All services are running — update buttons accordingly."""
        self._btn_start.config(text="✓  All Running", bg=GREEN, state="disabled")
        self._btn_open.config(state="normal", fg=GREEN, bg=CARD_BG)
        self._btn_close.config(state="normal")
        self._set_service("browser", "ok")

    # ──────────────────────────────────────────────────────────────────────────
    # START ALL
    # ──────────────────────────────────────────────────────────────────────────

    def _on_start(self):
        self._btn_start.config(state="disabled", text="Starting…", bg=YELLOW)
        self._btn_close.config(state="disabled")
        threading.Thread(target=self._run_all, daemon=True).start()

    def _run_all(self):
        self._log_write("\n=== Starting NTUST AOI Services ===", "info")

        # 1. Docker
        self._set_service("docker", "running")
        self._set_status("Checking Docker…")

        if not docker_ok():
            self._log_write("Docker not running — launching Docker Desktop…", "warn")
            try:
                if IS_WINDOWS:
                    subprocess.Popen([DOCKER_DESKTOP], creationflags=CREATION_FLAGS)
                else:
                    subprocess.Popen(["open", "-a", "Docker"])
            except FileNotFoundError:
                self._log_write("Docker Desktop not found. Please start it manually.", "err")
            self._log_write("Waiting for Docker daemon (up to 120s)…", "warn")
            deadline = time.time() + 120
            ok = False
            while time.time() < deadline:
                if docker_ok():
                    ok = True; break
                time.sleep(3)
            if not ok:
                self._log_write("ERROR: Docker did not start in time.", "err")
                self._set_service("docker", "error")
                self._on_fail(); return

        self._set_service("docker", "ok")
        self._log_write("Docker daemon ready ✓", "ok")

        # 2. DB
        self._set_service("db", "running")
        self._set_status("Starting DB services…")
        self._log_write("docker compose up -d …", "info")

        if not port_open(5433):
            self._log_write("Launching docker containers…", "info")
            try:
                ret = subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    cwd=DB_DIR,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=CREATION_FLAGS,
                    timeout=60
                )
                if ret.returncode != 0:
                    self._log_write("docker compose up returned non-zero. Checking port anyway…", "warn")
            except subprocess.TimeoutExpired:
                self._log_write("docker compose up timed out (60s) — checking if port opened anyway…", "warn")
            except Exception as e:
                self._log_write(f"docker compose up error: {e}", "err")
                self._set_service("db", "error")
                self._on_fail(); return
            self._log_write("Waiting for PostgreSQL (port 5433)…", "info")
            if not wait_port(5433, timeout=60):
                self._log_write("ERROR: PostgreSQL did not become ready.", "err")
                self._set_service("db", "error")
                self._on_fail(); return
        else:
            self._log_write("Database was already running ✓", "ok")

        self._set_service("db", "ok")
        self._log_write("Database & Nginx ready ✓", "ok")

        # 3. FastAPI
        self._set_service("backend", "running")
        self._set_status("Starting API server…")

        if not port_open(BACKEND_PORT):
            self._log_write("Starting FastAPI backend on port 8000…", "info")
            self._proc_backend = subprocess.Popen(
                [PYTHON_EXE, "-c",
                 "import uvicorn; uvicorn.run('api.main:app', host='0.0.0.0', port=8000)"],
                cwd=DB_DIR,
                creationflags=CREATION_FLAGS
            )
            if not wait_port(BACKEND_PORT, timeout=30):
                self._log_write("ERROR: FastAPI backend did not start.", "err")
                self._set_service("backend", "error")
                self._on_fail(); return
        else:
            self._log_write("FastAPI was already running ✓", "ok")

        self._set_service("backend", "ok")
        self._log_write("FastAPI backend ready at http://localhost:8000 ✓", "ok")

        # 3.5 Folder Monitor
        self._set_service("monitor", "running")
        self._set_status("Starting Folder Monitor…")
        if not monitor_ok():
            self._proc_monitor = subprocess.Popen(
                [PYTHON_EXE, FOLDER_MONITOR_PY],
                cwd=DB_DIR,
                creationflags=CREATION_FLAGS
            )
            time.sleep(1)
        self._set_service("monitor", "ok")

        # 3.6 Cloud Sync
        if self._sync_enabled.get():
            self._set_service("sync", "running")
            self._set_status("Starting Cloud Sync…")
            if not sync_ok():
                sync_script = os.path.join(DB_DIR, "scripts", "sync_to_server.py")
                self._proc_sync = subprocess.Popen(
                    [PYTHON_EXE, sync_script],
                    cwd=DB_DIR,
                    creationflags=CREATION_FLAGS
                )
                time.sleep(1)
            self._set_service("sync", "ok")
        else:
            self._set_service("sync", "idle")
            self._log_write("Cloud Sync is disabled by user — skipping.", "warn")

        # 4. Vite UI
        self._set_service("ui", "running")
        self._set_status("Starting UI server…")

        if not port_open(UI_PORT):
            self._log_write(f"Starting Vite UI on port {UI_PORT}…", "info")
            self._proc_ui = subprocess.Popen(
                [NPM_EXE, "run", "dev"],
                cwd=UI_DIR,
                creationflags=CREATION_FLAGS
            )
            if not wait_port(UI_PORT, timeout=60):
                self._log_write("ERROR: Vite UI server did not start.", "err")
                self._set_service("ui", "error")
                self._on_fail(); return
        else:
            self._log_write("Vite UI was already running ✓", "ok")

        self._set_service("ui", "ok")
        self._log_write(f"UI server ready at {UI_URL} ✓", "ok")

        # 5. Browser
        self._set_service("browser", "running")
        self._set_status("Opening browser…")
        time.sleep(1)
        webbrowser.open(UI_URL)
        self._set_service("browser", "ok")
        self._log_write(f"Browser opened at {UI_URL} ✓", "ok")

        # Done
        self._log_write("\n" + "─" * 52, "ok")
        self._log_write("  ✅  All systems running!", "ok")
        self._log_write(f"  🌐  {UI_URL}", "ok")
        self._log_write("─" * 52, "ok")
        self._set_status("✅  All systems running!", GREEN)
        self.after(0, self._activate_running_state)

    def _on_fail(self):
        self._set_status("Startup failed — check log", RED)
        self.after(0, lambda: self._btn_start.config(
            text="▶   Retry", bg=RED, state="normal"))
        self.after(0, lambda: self._btn_close.config(state="normal"))

    # ──────────────────────────────────────────────────────────────────────────
    # CLOSE ALL SERVICES
    # ──────────────────────────────────────────────────────────────────────────

    def _on_close_services(self):
        self._btn_close.config(state="disabled", text="Stopping…")
        self._btn_start.config(state="disabled")
        self._btn_open.config(state="disabled")
        threading.Thread(target=self._shutdown_all, daemon=True).start()

    def _shutdown_all(self):
        self._log_write("\n=== Shutting down all services ===", "warn")
        self._set_status("Stopping services…", YELLOW)

        # Kill Vite
        if self._proc_ui and self._proc_ui.poll() is None:
            self._log_write("Stopping Vite UI…", "warn")
            self._set_service("ui", "stopping")
            if IS_WINDOWS:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._proc_ui.pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=CREATION_FLAGS, timeout=3)
                except Exception:
                    pass
            else:
                self._proc_ui.terminate()
                try:    self._proc_ui.wait(timeout=3)
                except: self._proc_ui.kill()
        self._set_service("ui", "idle")
        self._log_write("Vite UI stopped ✓", "ok")

        # Kill FastAPI
        if self._proc_backend and self._proc_backend.poll() is None:
            self._log_write("Stopping FastAPI…", "warn")
            self._set_service("backend", "stopping")
            if IS_WINDOWS:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(self._proc_backend.pid)], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=CREATION_FLAGS, timeout=3)
                except Exception:
                    pass
            else:
                self._proc_backend.terminate()
                try:    self._proc_backend.wait(timeout=3)
                except: self._proc_backend.kill()
        self._set_service("backend", "idle")
        self._log_write("FastAPI stopped ✓", "ok")

        # Kill Monitor
        if monitor_ok():
            self._log_write("Stopping Folder Monitor…", "warn")
            self._set_service("monitor", "stopping")
            if IS_WINDOWS:
                try:
                    subprocess.run(['wmic', 'process', 'where', "commandline like '%folder_monitor.py%'", 'call', 'terminate'], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=CREATION_FLAGS, timeout=3)
                except Exception:
                    pass
                try:
                    subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq python.exe", "/FI", "WINDOWTITLE eq *folder_monitor*"], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=CREATION_FLAGS, timeout=3)
                except Exception:
                    pass
            else:
                try:
                    subprocess.run(['pkill', '-f', 'folder_monitor.py'], timeout=3)
                except Exception:
                    pass

            if self._proc_monitor:
                try: self._proc_monitor.terminate(); self._proc_monitor.kill()
                except: pass
        self._set_service("monitor", "idle")
        self._log_write("Folder Monitor stopped ✓", "ok")

        # Kill Sync
        if sync_ok():
            self._log_write("Stopping Cloud Sync…", "warn")
            self._set_service("sync", "stopping")
            if IS_WINDOWS:
                try:
                    subprocess.run(['wmic', 'process', 'where', "commandline like '%sync_to_server.py%'", 'call', 'terminate'], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=CREATION_FLAGS, timeout=3)
                except Exception:
                    pass
            else:
                try:
                    subprocess.run(['pkill', '-f', 'sync_to_server.py'], timeout=3)
                except Exception:
                    pass

            if hasattr(self, '_proc_sync') and self._proc_sync:
                try: self._proc_sync.terminate(); self._proc_sync.kill()
                except: pass
        self._set_service("sync", "idle")
        self._log_write("Cloud Sync stopped ✓", "ok")

        # docker compose down
        self._log_write("Running docker compose down…", "warn")
        self._set_service("db", "stopping")
        try:
            ret = subprocess.run(
                ["docker", "compose", "down"],
                cwd=DB_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                creationflags=CREATION_FLAGS, timeout=15
            )
            if ret.returncode == 0:
                self._log_write("Docker services stopped ✓", "ok")
            else:
                self._log_write(f"docker compose down: {ret.stderr.strip()}", "err")
        except subprocess.TimeoutExpired:
            self._log_write("Docker compose down timed out (took > 15s) — forcing closure.", "warn")
        except Exception as e:
            self._log_write(f"Docker compose down failed: {str(e)}", "err")

        self._set_service("db", "idle")
        self._set_service("docker", "idle")
        self._set_service("browser", "idle")

        self._log_write("All services stopped. Closing…", "ok")
        self._set_status("Done. Closing…", GREEN)
        time.sleep(1.5)
        self.after(0, self.destroy)

    # ──────────────────────────────────────────────────────────────────────────
    # ─── WINDOW HELPERS ────────────────────────────────────────────────────────
    def _auto_size(self):
        """Fit window to content or center it."""
        try:
            # Try to expand to full height if it's currently small
            if self.winfo_height() < 800:
                self.geometry("740x850")
            else:
                self.geometry("740x720")
            self.update_idletasks()
        except Exception:
            pass

    def _on_sync_toggle(self):
        """Called when the 'Enabled' checkbox for Cloud Sync is clicked."""
        is_enabled = self._sync_enabled.get()
        if not is_enabled:
            self._log_write("Cloud Sync disabled by user.", "warn")
            # If it's running, stop it
            if sync_ok():
                self._shutdown_sync_only()
        else:
            self._log_write("Cloud Sync enabled.", "info")

    def _shutdown_sync_only(self):
        self._log_write("Stopping Cloud Sync service...", "warn")
        if IS_WINDOWS:
            subprocess.run(['wmic', 'process', 'where', "commandline like '%sync_to_server.py%'", 'call', 'terminate'], 
                           creationflags=CREATION_FLAGS)
        else:
            subprocess.run(['pkill', '-f', 'sync_to_server.py'])
        self._set_service("sync", "idle")

    def on_close(self):
        self.destroy()


if __name__ == "__main__":
    try:
        app = LauncherApp()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except Exception as e:
        if IS_WINDOWS:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Launcher Error:\n{str(e)}", "Startup Error", 0x10)
        else:
            print(f"Launcher Error: {e}")
