import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, cwd=None, shell=False):
    subprocess.run(cmd, cwd=cwd or BASE_DIR, shell=shell, check=True)

def cmd_setup():
    print("==> Installing Python dependencies...")
    run_cmd([sys.executable, "-m", "pip", "install", "-r", "ntust_aoi_pcb_db/requirements.txt"])
    print("==> Installing Node dependencies...")
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    run_cmd([npm_cmd, "install"], cwd=os.path.join(BASE_DIR, "NTUST-AOI-UI"))
    print("Done. Activate environment: conda activate aoi_env")

def cmd_start():
    run_cmd([sys.executable, "headless_runner.py", "start"])

def cmd_stop():
    run_cmd([sys.executable, "headless_runner.py", "stop"])

def cmd_restart():
    cmd_stop()
    cmd_start()

def cmd_test():
    print("==> Running E2E integration test...")
    run_cmd([sys.executable, "test_sn5434.py"])

def cmd_git_check():
    print("==> Current branch:")
    try:
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        print(f"  {branch}")
        if branch == "main":
            print("  ⚠️  WARNING: You are on 'main'! Create a feature branch before making changes.")
            print("  Run: git checkout -b feat/<description>")
    except Exception:
        print("  unknown")
    
    print("\n==> Recent commits:")
    subprocess.run(["git", "--no-pager", "log", "--oneline", "-5"])
    
    print("\n==> Working tree status:")
    subprocess.run(["git", "--no-pager", "status", "--short"])
    
    print("\n==> Conflict markers (unresolved merges):")
    try:
        conflicts = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=U"], text=True).strip()
        if conflicts:
            print("  ⛔ CONFLICTS DETECTED — human must resolve:")
            for line in conflicts.split('\n'):
                print(f"    {line}")
            subprocess.run(["git", "--no-pager", "diff", "--diff-filter=U"])
        else:
            print("  None found.")
    except Exception:
        print("  None found.")

def cmd_update_docs():
    print("==> Files changed since last commit:")
    subprocess.run(["git", "--no-pager", "diff", "--name-only", "HEAD"])
    print("\n==> Documentation to update:")
    try:
        changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], text=True)
        if "machine_control/" in changed:
            print("  → machine_control/README.md\n  → machine_control/ARCHITECTURE.md")
        if "ntust_aoi_pcb_db/api/" in changed:
            print("  → ntust_aoi_pcb_db/README.md\n  → ntust_aoi_pcb_db/ARCHITECTURE.md")
        if "ntust_aoi_pcb_db/sql/" in changed:
            print("  → ntust_aoi_pcb_db/ARCHITECTURE.md\n  → docs/reference/DATABASE_SCHEMA.md")
        if "NTUST-AOI-UI/" in changed:
            print("  → NTUST-AOI-UI/README.md\n  → NTUST-AOI-UI/ARCHITECTURE.md")
        if "simulation/" in changed:
            print("  → simulation/README.md\n  → simulation/ARCHITECTURE.md")
        if "tasks.py" in changed:
            print("  → README.md (tasks.py command reference table)")
    except Exception:
        pass
    print("  → .agents/PROGRESS.md (always — if a new feature or fix was added)")
    print("\n  NOTE: docs/system architect overall/ is HUMAN-ONLY. Never edit with AI.")

TASKS = {
    "setup": cmd_setup,
    "install": cmd_setup,
    "start": cmd_start,
    "stop": cmd_stop,
    "restart": cmd_restart,
    "test": cmd_test,
    "git-check": cmd_git_check,
    "update-docs": cmd_update_docs,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in TASKS:
        print("Available tasks:")
        for task in TASKS.keys():
            print(f"  {task}")
        sys.exit(1)
    
    TASKS[sys.argv[1]]()
