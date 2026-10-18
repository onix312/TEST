# Automation instructions for onix312/TEST

This repository is **GameDev AI Office**, a local Python/PySide6 desktop tool that orchestrates Codex jobs for a **separate** Unity project. Do not confuse it with game source code.

## Do Not Feed the Cargo

The approved 100 decisions are in `docs/gdd/DECISIONS-001-100.md`. The other GDD documents interpret them; `docs/ROADMAP-UNITY-CODEX.md` describes the proposed implementation sequence.

- Never invent an approval or revise an approved mechanic without explicit user sign-off.
- Big alpha scope GDD-099 is mandatory; internal scaffolding/prototypes do not replace it.
- No open pickup, manual gearbox, always-online time progression, magically revealing maps or AI-only core delivery crews.
- For every task cite GDD IDs; isolate file changes and add tests where meaningful.
- `main` must remain buildable; do not auto-merge or delete others' changes.
- Do not modify a user's Unity project from this repository unless they have explicitly connected that local project in the app.
- GameDev AI Office only directly writes to Unity `Assets/`, `Packages/`, `ProjectSettings/` in *isolated task workspaces*, with conflict detection and checkpoints.
- QA is factual. Codex process success is not the same as passing Unity compilation or PlayMode tests.
- Python checks: `python -m unittest discover -s tests -v`; Qt offscreen UI smoke when PySide6 is available.
- Read the nearest README and run git status before editing; preserve unrelated changes.

## Constraints

No account creation, payments, software installation, public game deployment or large destructive action without appropriate user authorization. External model API is separately billed; never hardcode tokens, credentials or misleading nonexistent model access.
