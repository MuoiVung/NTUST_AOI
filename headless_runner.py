import os
import subprocess
import sys
import time

PID_FILE = "headless_runner.pids"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def start_all():

    
    print("[RUNNER] Starting FastAPI Backend (Port 8000)...")
    proc_api = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"], cwd=os.path.join(BASE_DIR, "ntust_aoi_pcb_db"))
    
    print("[RUNNER] Starting Vite Frontend (Port 3001)...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    proc_ui = subprocess.Popen([npm_cmd, "run", "dev"], cwd=os.path.join(BASE_DIR, "NTUST-AOI-UI"), shell=sys.platform=="win32")
    
    print("[RUNNER] Starting PLC Simulator (Port 15000)...")
    proc_plc = subprocess.Popen([sys.executable, "plc_sim.py"], cwd=os.path.join(BASE_DIR, "simulation"))
    
    print("[RUNNER] Starting Shopfloor Simulator (Port 9090)...")
    proc_shop = subprocess.Popen([sys.executable, "-m", "uvicorn", "shopfloor_sim:app", "--host", "127.0.0.1", "--port", "9090"], cwd=os.path.join(BASE_DIR, "simulation"))
    
    print("[RUNNER] Waiting 3 seconds for services to initialize...")
    time.sleep(3)
    
    print("[RUNNER] Starting PC Controller (Machine Logic)...")
    shopfloor_url = os.environ.get("SHOPFLOOR_API_URL", "http://127.0.0.1:9090/api/v1/shopfloor/info")
    proc_pc = subprocess.Popen([sys.executable, "pc_controller.py", "--mode", "semi-auto", "--api-mode", "real", "--api-endpoint", shopfloor_url], cwd=os.path.join(BASE_DIR, "machine_control"))

    pids = [proc_api.pid, proc_ui.pid, proc_plc.pid, proc_shop.pid, proc_pc.pid]
    with open(PID_FILE, "w") as f:
        for pid in pids:
            f.write(f"{pid}\n")
    print(f"[RUNNER] All services started! PIDs saved to {PID_FILE}")
    print("[RUNNER] You can now run automated integration tests or use the browser_subagent.")
    print("[RUNNER] To stop, run: python headless_runner.py stop")

def stop_all():
    if os.path.exists(PID_FILE):
        print("[RUNNER] Stopping Python & Node processes from PID file...")
        with open(PID_FILE, "r") as f:
            for line in f:
                pid = line.strip()
                if pid:
                    try:
                        if sys.platform == "win32":
                            subprocess.run(["taskkill", "/F", "/T", "/PID", pid], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                        else:
                            subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
                    except:
                        pass
        os.remove(PID_FILE)
    
    print("[RUNNER] Running fallback termination to ensure clean state...")
    if sys.platform == "win32":
        try:
            for port in [8000, 3001, 9090, 15000, 16000]:
                try:
                    out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
                    for line in out.strip().split('\n'):
                        if "LISTENING" in line:
                            pid = line.strip().split()[-1]
                            subprocess.run(["taskkill", "/F", "/T", "/PID", pid], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    pass
        except Exception:
            pass
    else:
        subprocess.run("pkill -f 'uvicorn'", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f 'vite'", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f 'plc_sim.py'", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f 'pc_controller.py'", shell=True, stderr=subprocess.DEVNULL)


    print("[RUNNER] All services completely stopped and cleaned up!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python headless_runner.py [start|stop]")
        sys.exit(1)
    
    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_all()
    elif cmd == "stop":
        stop_all()
    else:
        print("Unknown command. Use 'start' or 'stop'.")
