"""Local rollback checkpoint of Unity source assets before Codex runs."""
from pathlib import Path
from datetime import datetime, timezone
import uuid
import zipfile

def checkpoint(root):
    backup_dir = root / ".ai-office" / "checkpoints"
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6] + ".zip")
    temp = dest.with_suffix(".partial")
    count = 0
    try:
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as archive:
            for folder in ("Assets", "Packages", "ProjectSettings"):
                root_dir = root / folder
                if not root_dir.exists():
                    continue
                for path in root_dir.rglob("*"):
                    if path.is_symlink():
                        raise ValueError("Symlink requires manual backup review: " + str(path))
                    if path.is_file():
                        archive.write(path, path.relative_to(root).as_posix())
                        count += 1
        if not count:
            raise ValueError("Unity project contains no files to back up")
        temp.replace(dest)
        return dest
    except Exception:
        temp.unlink(missing_ok=True)
        raise
