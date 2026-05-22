---
name: secure_commit
description: A skill to securely commit code to GitHub by performing automated security audits and credential scanning before checking in.
---

# Secure Commit Skill

This skill allows you to safely commit code by first auditing it for credentials, secrets, and OWASP vulnerabilities.

## Workflow

Always follow these steps when asked to "securely commit" or "commit with audit":

1.  **Run Security Scan**
    Execute the python security scanner included in this skill on the current workspace.
    ```bash
    python .agent/skills/secure_commit/scripts/security_scan.py .
    ```

2.  **Analyze Results**
    *   **If Scan Fails (Exit Code 1)**:
        *   Read the output to identify the file and line number of the issue.
        *   **STOP**. Do not proceed with the commit.
        *   Notify the user about the specific security issues found (e.g., "Found hardcoded API key in config.py").
        *   Ask the user if they want to fix it or override (only if it's a false positive).
    *   **If Scan Passes (Exit Code 0)**:
        *   Proceed to step 3.

3.  **Review Changes**
    *   Run `git status` and `git diff --cached` (if code is staged) or `git diff` to see what will be added.
    *   Ensure no `.env` files or local config files are being tracked (check `.gitignore`).

4.  **Perform Commit**
    *   Stage the files: `git add .` (or specific files).
    *   Commit with the user's message: `git commit -m "message"`
    *   Push to the branch: `git push origin <branch_name>`

## Usage Example

> User: "Please build and commit these changes."

**Agent Action:**
1.  Run `python .agent/skills/secure_commit/scripts/security_scan.py .`
2.  If passed:
    ```bash
    git add .
    git commit -m "feat: implemented X"
    git push origin feature/x
    ```
