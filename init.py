import os
import sys
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    print(f"==> Working directory: {ROOT_DIR}")
    
    print("==> Syncing dependencies")
    subprocess.run([sys.executable, "tasks.py", "setup"], cwd=ROOT_DIR, check=True)
    
    print("==> Running baseline verification")
    # In NTUST_AOI, 'test' requires the system to be running first.
    # Therefore, we might not want to run 'test' directly here without starting.
    # Alternatively, we could just run a linter or 'git-check' as a quick verification.
    subprocess.run([sys.executable, "tasks.py", "git-check"], cwd=ROOT_DIR, check=True)
    
    print("==> Startup command")
    print("    python tasks.py start")
    print("")
    
    if os.environ.get("RUN_START_COMMAND") == "1":
        print("==> Starting the app")
        subprocess.run([sys.executable, "tasks.py", "start"], cwd=ROOT_DIR, check=True)
    else:
        print("Set RUN_START_COMMAND=1 if you want init.py to launch the app directly.")

if __name__ == "__main__":
    main()
