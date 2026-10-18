"""Safe independent Unity workspaces and conflict-aware integration without Git."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import zipfile
import uuid
from pathlib import Path

from office_core import office_dir, prepare, atomic_json
from safety import checkpoint

SOURCE_DIRS = ("Assets", "Packages", "ProjectSettings")
_merge_lock = threading.RLock()


def digest(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(root: Path):
    result = {}
    for folder in SOURCE_DIRS:
        source = root / folder
        if not source.exists():
            continue
        if source.is_symlink():
            raise ValueError("Symbolic link is not supported: " + str(source))
        for path in source.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symbolic link is not supported: " + str(path))
            if path.is_file():
                result[path.relative_to(root).as_posix()] = digest(path)
    return result


def workspace_for(root: Path, task_id: str):
    return office_dir(root) / "workspaces" / task_id / "project"


def provision(root: Path, task_id: str, gdd: str):
    """Create one isolated snapshot per task. Never hand Codex the live project."""
    root = Path(root)
    folder = workspace_for(root, task_id)
    if folder.parent.exists():
        # Preserve failed and interrupted work when a user explicitly retries.
        archive = folder.parent.with_name(task_id + "-previous-" + uuid.uuid4().hex[:8])
        folder.parent.rename(archive)
    folder.mkdir(parents=True)
    baseline = inventory(root)
    for section in SOURCE_DIRS:
        source = root / section
        if source.exists():
            shutil.copytree(source, folder / section, symlinks=False, copy_function=shutil.copy2)
    gdd_path = folder / ".ai-office" / "gdd" / "approved.md"
    gdd_path.parent.mkdir(parents=True)
    gdd_path.write_text(gdd, encoding="utf-8")
    atomic_json(folder.parent / "baseline.json", baseline)
    return folder


def compute_changes(root: Path, task_id: str):
    workspace = workspace_for(root, task_id)
    baseline = json.loads((workspace.parent / "baseline.json").read_text(encoding="utf-8"))
    after = inventory(workspace)
    changed = []
    for path in sorted(set(baseline) | set(after)):
        before, new = baseline.get(path), after.get(path)
        if before == new:
            continue
        kind = "delete" if new is None else ("add" if before is None else "modify")
        changed.append({"path": path, "action": kind, "before": before, "after": new})
    return changed


def inspect_conflicts(root: Path, changes):
    issues = []
    for change in changes:
        rel = change["path"]
        if Path(rel).is_absolute() or ".." in Path(rel).parts or rel.split("/", 1)[0] not in SOURCE_DIRS:
            issues.append(rel + ": invalid path")
            continue
        live_path = Path(root) / rel
        if any(parent.is_symlink() for parent in (live_path, *list(live_path.parents)[:-1])):
            issues.append(rel + ": symlink")
            continue
        if digest(live_path) != change["before"] and digest(live_path) != change["after"]:
            issues.append(rel + ": modified by another agent or Unity")
        if change["action"] == "delete":
            issues.append(rel + ": deletion requires explicit review")
    return issues


def integrate(root: Path, task_id: str, changes, *, allow_deletions=False):
    """Verify fingerprints, then create a checkpoint and apply; conflicts never overwrite."""
    root = Path(root)
    with _merge_lock:
        conflicts = inspect_conflicts(root, changes)
        if allow_deletions:
            conflicts = [x for x in conflicts if not x.endswith(": deletion requires explicit review")]
        if conflicts:
            return None, conflicts
        workspace = workspace_for(root, task_id)
        # Preflight every source before changing any production file.
        for change in changes:
            if change["action"] != "delete":
                source = workspace / change["path"]
                if not source.is_file() or source.is_symlink() or digest(source) != change["after"]:
                    raise ValueError("Workspace changed after review: " + change["path"])
        backup = checkpoint(root) if changes else None
        try:
            for change in changes:
                relative = change["path"]
                source = workspace / relative
                target = root / relative
                if change["action"] == "delete":
                    if target.is_dir() or target.is_symlink():
                        raise ValueError("Invalid deletion path: " + relative)
                    target.unlink(missing_ok=True)
                else:
                    if not source.is_file() or source.is_symlink() or digest(source) != change["after"]:
                        raise ValueError("Workspace changed after review: " + relative)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temp = target.with_name(target.name + ".gamedev-office-tmp")
                    try:
                        shutil.copy2(source, temp)
                        os.replace(temp, target)
                    finally:
                        temp.unlink(missing_ok=True)
        except Exception as exc:
            if backup:
                try:
                    restore_changed(root, backup, changes)
                except Exception as rollback_exc:
                    raise RuntimeError("Integration failed; restore manually from " +
                                       str(backup) + ": " + str(rollback_exc)) from exc
            raise
        return backup, []


def file_preview(root: Path, task_id: str, changes, max_lines=160):
    lines = []
    for change in changes:
        lines.append(change["action"].upper() + "  " + change["path"])
        if change["action"] == "delete":
            continue
        target = workspace_for(root, task_id) / change["path"]
        if target.suffix.lower() not in (".cs", ".json", ".md", ".shader", ".uxml", ".uss"):
            continue
        try:
            snippet = target.read_text(encoding="utf-8")
            lines.append("\n".join(snippet.splitlines()[:max_lines]))
        except (OSError, UnicodeError):
            pass
        lines.append("---")
    return "\n".join(lines)[:40000]


def restore_changed(root: Path, archive: Path, changes):
    """Restore only paths touched by a merge from an earlier checkpoint."""
    with zipfile.ZipFile(archive, "r") as backup:
        existing = set(backup.namelist())
        for item in changes:
            relative = item["path"]
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts or relative.split("/", 1)[0] not in SOURCE_DIRS:
                raise ValueError("Unsafe backup file path: " + relative)
            target = Path(root) / relative
            if any(parent.is_symlink() for parent in (target, *list(target.parents)[:-1])):
                raise ValueError("Symlink during restore: " + relative)
            if relative in existing:
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.with_name(target.name + ".gamedev-office-restore")
                try:
                    with backup.open(relative) as source, temp.open("wb") as output:
                        shutil.copyfileobj(source, output)
                    os.replace(temp, target)
                finally:
                    temp.unlink(missing_ok=True)
            else:
                target.unlink(missing_ok=True)


def undo_merge(root: Path, task):
    """Undo one applied task only while its touched files still match the agent version."""
    if task["status"] != "merged" or not task.get("checkpoint"):
        raise ValueError("Only applied tasks with a checkpoint can be restored.")
    with _merge_lock:
        for item in task.get("changes", []):
            if digest(Path(root) / item["path"]) != item["after"]:
                raise ValueError("Current project has newer changes in " + item["path"] +
                                 "; undo would destroy them.")
        backup_of_current = checkpoint(Path(root))
        try:
            restore_changed(Path(root), Path(task["checkpoint"]), task["changes"])
        except Exception:
            restore_changed(Path(root), backup_of_current, task["changes"])
            raise
        return backup_of_current
