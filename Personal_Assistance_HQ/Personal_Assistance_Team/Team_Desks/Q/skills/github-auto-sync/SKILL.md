---
name: github-auto-sync
description: Guideline for ensuring all modified dashboard or project files are committed and pushed to GitHub immediately after modification. Trigger proactively after editing any code or configuration file that belongs to a Git repository, ensuring the user can see updates on GitHub.
---

# GitHub Auto-Sync

This skill ensures that all changes made to the codebase or dashboards are committed and pushed to GitHub immediately so that the user (Keng) can see the updates on GitHub.

## Guidelines

- **Check for Git Repositories:** After making any changes, search the parent directories for a `.git` folder to identify if the files are part of a Git repository.
- **Auto-Commit and Push:**
  1. Check status with `git status`.
  2. If there are changes, stage them with `git add .` (or specific files).
  3. Commit with a clear, concise commit message (e.g. `git commit -m "Update Saturday posting slots to Reels / YT Shorts / TikTok"`).
  4. Push the changes to GitHub with `git push origin main` (or the active branch).
- **Verify Remote Status:** Make sure the push command completes successfully and without errors. If there are authentication issues or merge conflicts, report them clearly to the user.
