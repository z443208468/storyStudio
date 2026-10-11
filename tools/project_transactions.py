"""Shared serialization primitive for project-authoritative writes."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

try:
    from .cnw_contract import ContractError
except ImportError:
    from cnw_contract import ContractError

PROJECT_WRITE_LOCK = ".story-studio-project-write.lock"


@contextmanager
def project_write_lock(project_root: str | Path):
    """Serialize mutations against one project root using the runner lock API."""
    root = Path(project_root)
    if root.is_symlink():
        raise ContractError("PROJECT_WRITE_ROOT_SYMLINK_REJECTED", str(root))
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    try:
        from . import cnw_runner
    except ImportError:
        import cnw_runner
    with cnw_runner.locked_run(root, lock_name=PROJECT_WRITE_LOCK):
        yield
