"""Portable output names and atomic writes for generated artifacts."""
import os
from pathlib import Path
import re
import tempfile


def name_problem(name: str) -> str | None:
    if (not name or len(name) > 100 or name != name.strip()
            or name.endswith('.') or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)):
        return 'map name must be a portable filename (1-100 characters, no path separators)'
    if name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                                      *(f'COM{i}' for i in range(1, 10)),
                                      *(f'LPT{i}' for i in range(1, 10))}:
        return 'map name is reserved on Windows'
    return None


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as f:
            temp = Path(f.name)
            f.write(data)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
