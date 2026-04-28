import os
import re
import sys
import argparse

# --- Configuration ---
# Patterns to look for (Regex)
SENSITIVE_PATTERNS = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Key": r"[0-9a-zA-Z/+]{40}",
    "Generic API Key": r"api_key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{20,}['\"]",
    "Hardcoded Password": r"password\s*[:=]\s*['\"][a-zA-Z0-9@#$%^&+=]{8,}['\"]",
    "Private Key Block": r"-----BEGIN RSA PRIVATE KEY-----",
    "Env Var in Code": r"os\.getenv\(['\"]([A-Z_]+)['\"]\)" # Not strict error, but good for audit
}

# OWASP-ish checks (Basic Static Analysis)
OWASP_CHECKS = {
    "SQL Injection": {
        "pattern": r"(execute|cursor\.execute)\s*\(\s*f['\"]",
        "desc": "Possible SQL Injection: Usage of f-string in SQL execution. Use parameterized queries."
    },
    "Debug Mode": {
        "pattern": r"debug\s*=\s*True",
        "desc": "Debug mode enabled. Ensure this is not for production."
    },
    "Hardcoded IP": {
        "pattern": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "desc": "Hardcoded IP address found. Use hostnames or config."
    }
}

IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode", "brain", "postgres_data", "mongo_data"}
IGNORE_EXTENSIONS = {".png",".jpg",".jpeg",".webp",".pyc",".exe",".dll",".so",".dylib", ".md", ".json",".txt"}

def scan_file(filepath):
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.splitlines()

            for i, line in enumerate(lines):
                # Check for Secrets
                for name, pattern in SENSITIVE_PATTERNS.items():
                    # Naively check regex. 
                    # For strict keys (AWS), the regex is specific.
                    # For generic ones, we try to avoid false positives by checking variable naming context
                    if "Secret" in name or "Key" in name:
                         # Skip if it looks like an env var usage e.g. os.getenv("API_KEY")
                         if "getenv" in line or "environ" in line:
                             continue
                    
                    if re.search(pattern, line):
                        # Mask the match for display
                        issues.append(f"[SECRET] {name} found on line {i+1}")

                # Check OWASP patterns
                for name, check in OWASP_CHECKS.items():
                    if re.search(check["pattern"], line, re.IGNORECASE):
                         issues.append(f"[OWASP] {name}: {check['desc']} (Line {i+1})")
                         
    except Exception as e:
        print(f"⚠️ Could not read {filepath}: {e}")
        
    return issues

def main():
    parser = argparse.ArgumentParser(description="Security Scan for Secure Commit Skill")
    parser.add_argument("path", help="Path to scan (file or directory)", nargs="?", default=".")
    args = parser.parse_args()

    target_path = os.path.abspath(args.path)
    print(f"🔍 Starting Security Scan on: {target_path}")
    
    total_issues = 0
    files_scanned = 0
    
    # Walk directory
    if os.path.isdir(target_path):
        for root, dirs, files in os.walk(target_path):
            # Filter directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
            
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in IGNORE_EXTENSIONS:
                    continue
                
                filepath = os.path.join(root, file)
                issues = scan_file(filepath)
                files_scanned += 1
                
                if issues:
                    print(f"\n❌ {os.path.relpath(filepath, target_path)}")
                    for issue in issues:
                        print(f"   - {issue}")
                    total_issues += len(issues)
    else:
        # Single file
        issues = scan_file(target_path)
        if issues:
             print(f"\n❌ {os.path.basename(target_path)}")
             for issue in issues:
                 print(f"   - {issue}")
             total_issues += len(issues)

    print("\n" + "="*40)
    print(f"📊 Scan Complete: {files_scanned} files scanned.")
    if total_issues > 0:
        print(f"🛑 Found {total_issues} potential security issues.")
        print("RECOMMENDATION: Review and fix before committing.")
        sys.exit(1) # Return error code to stop workflow
    else:
        print(f"✅ No obvious issues found. Ready to commit.")
        sys.exit(0)

if __name__ == "__main__":
    main()
