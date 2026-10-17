# GameDev AI Office (Unity + Codex)

Windows desktop prototype for local Unity development. Existing ChatGPT conversation remains the Game Designer; import approved GDD manually (.md/.txt).

## Windows installation

1. Install Unity Editor and Codex CLI; sign in via `codex login`.
2. From GitHub Actions → **Windows build**, download the `GameDevAIOffice-Windows` artifact for a successful run of the feature branch, extract the folder and run `GameDevAIOffice.exe`. Alternatively install Python 3.11 and run `start.bat` from the source.
3. Choose a Unity project's root directory (Assets and ProjectSettings), set Unity.exe, and import approved GDD.
4. Add Codex tasks. They run sequentially without a Git repository; a zip checkpoint of Assets, Packages and ProjectSettings is created before each task.

## Limitations

This is **not a finished out-of-box game studio**. There is no automatic access to your existing ChatGPT chat, multi-agent collaboration, Pixel Office, or automatic recovery/merge. Unity and Codex require separate installation. Windows CI must pass before considering the EXE usable. Restore backup archives manually with Unity closed.

Source files and CI workflow are in branch `feature/gamedev-ai-office` and PR #1.
