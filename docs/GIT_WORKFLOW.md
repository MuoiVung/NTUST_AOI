# Git Workflow — NTUST AOI

> **When to read:** Any session where you create, modify, or delete any file.
> **Source:** AOI factory floor — a bad merge to `main` can cause PLC halt or data loss.
> **Expiry:** Remove this doc if CI enforces branch protection rules automatically.

---

## Session Start Checklist

Run these before touching any file:

```bash
git pull origin main      # Always start from latest main
python tasks.py git-check # Verify branch, status, check for conflict markers
```

If `git-check` warns you are on `main`: stop and create a branch first.

---

## Branch Naming Convention

```
feat/<short-description>      # New feature or capability
fix/<short-description>       # Bug fix
docs/<short-description>      # Documentation only changes
refactor/<short-description>  # Code restructure, no behaviour change
```

Examples:
```bash
git checkout -b feat/ai-inference-endpoint
git checkout -b fix/plc-ack-timeout
git checkout -b docs/update-db-schema
git checkout -b refactor/camera-tcp-client
```

---

## Branch Lifecycle

```
1. git pull origin main
2. git checkout -b <type>/<description>
3. Make changes, run `python tasks.py update-docs`
4. git add . && git commit -m "<type>: <description>"
5. git push origin <branch>
6. Open PR / merge request for review
7. After merge: git checkout main && git branch -d <branch>
```

---

## Merge Conflict Protocol

### Detect conflicts
```bash
git status                        # Shows files with conflicts (both modified)
git diff --diff-filter=U          # Shows full conflict diff
```

### Required steps when conflicts exist

1. **STOP.** Do not proceed with the merge.
2. **Display** the full conflict diff — show all `<<<<<<<`, `=======`, `>>>>>>>` markers.
3. **Surface to human.** Paste the conflict output and wait for explicit resolution instructions.
4. **Never auto-resolve.** Do not pick one side automatically (`--ours` / `--theirs`)
   without human approval.
5. After human resolves: `git add <resolved-files>` → `git commit`

### Why this matters

A conflict in `pc_controller.py`, `shared_protocol.py`, or `sql/init.sql` that is
auto-resolved incorrectly can cause:
- PLC halt (missing ACK due to wrong event code)
- DB schema mismatch (dropped columns, missing triggers)
- Silent data corruption in production runs

---

## Forbidden Actions

| Action | Why |
|---|---|
| `git commit` directly to `main` | No review, no traceability |
| `git push --force` to `main` | Destroys history, affects all team members |
| Auto-resolving conflicts | Risk of PLC halt or data loss |
| Working on a stale checkout | Race conditions, stale assumptions |
