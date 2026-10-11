"""Explicit DataHome and project-instance resolution for the generic app.

This is a small, offline-only resolver. It does not touch legacy workspaces,
load project manuscripts, or call a provider. CNW production entry points are
not redirected by this module during the R5 shadow stage.
"""
from __future__ import annotations

import json
import os
import re
import csv
import io
import shutil
import stat
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping


class PathResolutionError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
POINTER_SCHEMA = "story_studio_setup_v1"
IDENTITY_SCHEMA = "story_studio_project_identity_v1"
REGISTRY_SCHEMA = "story_studio_project_registry_v1"
DATA_HOME_SCHEMA = "story_studio_data_home_identity_v1"
_REPARSE_POINT = 0x400
APP_ROOT = Path(__file__).resolve().parents[1]


def setup_pointer_path(env: Mapping[str, str] | None = None) -> Path:
    """Return the one machine-user pointer location; never a data-root default."""
    env = os.environ if env is None else env
    if os.name == "nt":
        base = env.get("LOCALAPPDATA")
        if not base:
            raise PathResolutionError("SETUP_POINTER_LOCATION_UNAVAILABLE", "LOCALAPPDATA is not set")
        return Path(base) / "StoryStudio" / "setup.json"
    base = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "StoryStudio" / "setup.json"


def _absolute_without_traversal(raw: str | os.PathLike[str], *, code: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        raise PathResolutionError(code, "an explicit absolute path is required")
    if ".." in path.parts:
        raise PathResolutionError(code, "parent traversal is not allowed")
    return path


def _assert_no_reparse(path: Path, *, code: str) -> None:
    """Inspect every existing component without relying on Path.is_junction()."""
    path = _absolute_without_traversal(path, code=code)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            # Descendants cannot exist after the first missing component.
            return
        except OSError as exc:
            raise PathResolutionError(code, f"cannot inspect path component: {current}") from exc
        attributes = getattr(info, "st_file_attributes", 0)
        if stat.S_ISLNK(info.st_mode) or attributes & _REPARSE_POINT:
            raise PathResolutionError(code, f"symbolic link or reparse point is not allowed: {current}")


def _canonical_existing_or_missing(path: Path, *, code: str) -> Path:
    _assert_no_reparse(path, code=code)
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise PathResolutionError(code, "path cannot be canonicalized") from exc


def _windows_private_acl(path: Path, *, create: bool, require_independent: bool = True) -> None:
    icacls = shutil.which("icacls.exe") or shutil.which("icacls")
    whoami = shutil.which("whoami.exe") or shutil.which("whoami")
    if not icacls or not whoami:
        raise PathResolutionError("DATA_HOME_PERMISSION_CHECK_UNAVAILABLE", "icacls and whoami are required to verify Windows DataHome ACLs")
    try:
        user_result = subprocess.run([whoami, "/user", "/fo", "csv", "/nh"], capture_output=True, text=True, timeout=10, check=False)
        user_row = next(csv.reader(io.StringIO(user_result.stdout))) if user_result.returncode == 0 else []
        user_sid = user_row[-1] if len(user_row) >= 2 else ""
        if not user_sid.startswith("S-"):
            raise ValueError("current Windows user SID unavailable")
        if create:
            grants = [f"*{user_sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F"]
            changed = subprocess.run([icacls, str(path), "/inheritance:r", "/grant:r", *grants], capture_output=True, text=True, timeout=10, check=False)
            if changed.returncode != 0:
                raise ValueError("icacls could not protect the new DataHome")
        result = subprocess.run([icacls, str(path)], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PathResolutionError("DATA_HOME_PERMISSION_CHECK_UNAVAILABLE", "Windows ACL inspection failed") from exc
    if result.returncode != 0 or user_result.returncode != 0:
        raise PathResolutionError("DATA_HOME_PERMISSION_CHECK_UNAVAILABLE", "Windows ACL inspection failed")
    allowed = {user_sid.casefold(), user_row[0].casefold(), "s-1-5-18", "s-1-5-32-544",
               "nt authority\\system", "builtin\\administrators", "owner rights", "s-1-3-4"}
    entries = []
    for line in result.stdout.splitlines():
        match = re.search(r"((?:\([^)]*\))+)$", line.strip())
        if match:
            head = line.strip()[:match.start()].rstrip()
            if path.name.casefold() in head.casefold():
                boundary = head.casefold().rfind(path.name.casefold()) + len(path.name)
                principal = head[boundary:].strip().rstrip(":")
            else:
                principal = head.rstrip(":").strip()
            if not principal:
                raise PathResolutionError("DATA_HOME_PERMISSION_CHECK_UNAVAILABLE", "Windows ACL output could not be parsed")
            entries.append((principal.casefold(), match.group(1)))
    if not entries or (require_independent and any("(I)" in flags for _, flags in entries)):
        raise PathResolutionError("DATA_HOME_ACL_NOT_INDEPENDENT", "DataHome ACL inherits access from its parent")
    for principal, flags in entries:
        normalized = principal.removeprefix("*")
        if normalized not in allowed:
            raise PathResolutionError("DATA_HOME_ACL_TOO_BROAD", "DataHome grants access to a principal outside the current user, Administrators, or SYSTEM")
        if "(DENY)" in flags.upper():
            continue


def _assert_private_permissions(path: Path, *, require_independent_acl: bool = True) -> None:
    if os.name == "nt":
        _windows_private_acl(path, create=False, require_independent=require_independent_acl)
        return
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise PathResolutionError("DATA_HOME_ACL_TOO_BROAD", "DataHome must not grant group or other access")


def _ensure_private_directory(path: Path, *, root: Path, code: str) -> Path:
    """Create or validate every DataHome child directory before writing beneath it."""
    root = root.resolve(strict=True)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise PathResolutionError(code, "private directory must remain inside DataHome") from exc
    current = root
    for part in relative.parts:
        current = current / part
        _assert_no_reparse(current, code=code)
        try:
            current.mkdir()
        except FileExistsError:
            if not current.is_dir():
                raise PathResolutionError(code, "a required private directory path is not a directory")
            _assert_private_permissions(current, require_independent_acl=False)
        except OSError as exc:
            if not current.is_dir():
                raise PathResolutionError(code, "cannot create a required private directory") from exc
            _assert_private_permissions(current, require_independent_acl=False)
        else:
            if os.name == "nt":
                _windows_private_acl(current, create=True)
            else:
                current.chmod(0o700)
            _assert_private_permissions(current, require_independent_acl=False)
        _assert_no_reparse(current, code=code)
    return current


def _write_json_new(path: Path, value: dict) -> None:
    """Create one immutable registration record without replacing an existing file."""
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PathResolutionError("PROJECT_INSTANCE_COLLISION", f"registration already exists: {path.name}") from exc


def _replace_json(path: Path, value: dict) -> None:
    """Atomically replace the small setup pointer on its own volume."""
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=".setup-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _prepare_data_home(raw: str | os.PathLike[str]) -> Path:
    chosen = _absolute_without_traversal(raw, code="DATA_HOME_INVALID")
    if chosen == APP_ROOT or chosen.is_relative_to(APP_ROOT):
        raise PathResolutionError("DATA_HOME_INSIDE_APP_ROOT", "private DataHome must be outside the application source tree")
    _assert_no_reparse(chosen, code="DATA_HOME_REPARSE_POINT")
    created = False
    try:
        if not chosen.exists():
            chosen.mkdir(parents=True)
            created = True
    except OSError as exc:
        if not chosen.is_dir():
            raise PathResolutionError("DATA_HOME_NOT_WRITABLE", "cannot create the explicitly selected DataHome") from exc
    _assert_no_reparse(chosen, code="DATA_HOME_REPARSE_POINT")
    canonical = chosen.resolve(strict=True)
    if not canonical.is_dir():
        raise PathResolutionError("DATA_HOME_INVALID", "selected path is not a directory")
    if created and os.name == "nt":
        _windows_private_acl(canonical, create=True)
    elif created:
        canonical.chmod(0o700)
    _assert_private_permissions(canonical)
    probe = canonical / f".storystudio-write-check-{uuid.uuid4().hex}"
    try:
        with probe.open("xb") as stream:
            stream.write(b"ok")
            stream.flush()
            os.fsync(stream.fileno())
        probe.unlink()
    except OSError as exc:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass
        raise PathResolutionError("DATA_HOME_NOT_WRITABLE", "selected DataHome failed its write check") from exc
    try:
        shutil.disk_usage(canonical)
    except OSError as exc:
        raise PathResolutionError("DATA_HOME_CAPACITY_UNKNOWN", "cannot inspect selected DataHome volume") from exc
    return canonical


def setup_data_home(
    data_home: str | os.PathLike[str],
    *,
    pointer_path: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    """Persist an explicitly selected private root in the machine-user pointer."""
    chosen = _prepare_data_home(data_home)
    pointer = Path(pointer_path) if pointer_path is not None else setup_pointer_path(env)
    pointer = _absolute_without_traversal(pointer, code="SETUP_POINTER_INVALID")
    if pointer == APP_ROOT or pointer.is_relative_to(APP_ROOT):
        raise PathResolutionError("SETUP_POINTER_INSIDE_APP_ROOT", "the setup pointer must be outside the application source tree")
    _assert_no_reparse(pointer.parent, code="SETUP_POINTER_INVALID")
    _assert_no_reparse(pointer, code="SETUP_POINTER_INVALID")
    try:
        pointer.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PathResolutionError("SETUP_POINTER_NOT_WRITABLE", "cannot create user configuration directory") from exc
    _assert_no_reparse(pointer.parent, code="SETUP_POINTER_INVALID")
    payload = {"schema_version": POINTER_SCHEMA, "data_home": str(chosen)}
    if pointer.exists():
        try:
            existing = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PathResolutionError("SETUP_POINTER_INVALID", "existing setup pointer is unreadable or malformed") from exc
        if not isinstance(existing, dict) or existing.get("schema_version") != POINTER_SCHEMA:
            raise PathResolutionError("SETUP_POINTER_INVALID", "existing setup pointer has an unsupported schema")
        _replace_json(pointer, payload)
    else:
        try:
            with pointer.open("xb") as stream:
                stream.write((json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8"))
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise PathResolutionError("SETUP_POINTER_RACE", "setup pointer was created concurrently; resolve again") from exc
        except OSError as exc:
            raise PathResolutionError("SETUP_POINTER_NOT_WRITABLE", "cannot persist setup pointer") from exc
    _assert_no_reparse(pointer, code="SETUP_POINTER_INVALID")
    return chosen


def resolve_data_home(
    *,
    explicit: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    pointer_path: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve explicit argument, environment override, then persisted selection."""
    env = os.environ if env is None else env
    selected = explicit if explicit is not None else env.get("STORYSTUDIO_DATA_HOME")
    if selected is not None:
        chosen = _absolute_without_traversal(selected, code="DATA_HOME_INVALID")
        _assert_no_reparse(chosen, code="DATA_HOME_REPARSE_POINT")
        try:
            canonical = chosen.resolve(strict=True)
        except OSError as exc:
            raise PathResolutionError("DATA_HOME_UNAVAILABLE", "explicit DataHome does not exist or cannot be resolved") from exc
        if not canonical.is_dir():
            raise PathResolutionError("DATA_HOME_INVALID", "selected path is not a directory")
        if canonical == APP_ROOT or canonical.is_relative_to(APP_ROOT):
            raise PathResolutionError("DATA_HOME_INSIDE_APP_ROOT", "private DataHome must be outside the application source tree")
        _assert_private_permissions(canonical)
        return canonical
    pointer = Path(pointer_path) if pointer_path is not None else setup_pointer_path(env)
    pointer = _absolute_without_traversal(pointer, code="SETUP_POINTER_INVALID")
    if pointer == APP_ROOT or pointer.is_relative_to(APP_ROOT):
        raise PathResolutionError("SETUP_POINTER_INVALID", "setup pointer cannot be stored inside the application source tree")
    _assert_no_reparse(pointer, code="SETUP_POINTER_INVALID")
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PathResolutionError("DATA_HOME_REQUIRED", "select a DataHome with setup --data-home before project writes") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PathResolutionError("SETUP_POINTER_INVALID", "setup pointer is unreadable or malformed") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != POINTER_SCHEMA or not isinstance(payload.get("data_home"), str):
        raise PathResolutionError("SETUP_POINTER_INVALID", "setup pointer schema or selected path is invalid")
    chosen = _absolute_without_traversal(payload["data_home"], code="SETUP_POINTER_INVALID")
    _assert_no_reparse(chosen, code="DATA_HOME_REPARSE_POINT")
    try:
        canonical = chosen.resolve(strict=True)
    except OSError as exc:
        raise PathResolutionError("SETUP_POINTER_INVALID", "persisted DataHome is unavailable") from exc
    if not canonical.is_dir():
        raise PathResolutionError("SETUP_POINTER_INVALID", "persisted DataHome is not a directory")
    if canonical == APP_ROOT or canonical.is_relative_to(APP_ROOT):
        raise PathResolutionError("SETUP_POINTER_INVALID", "persisted DataHome points inside the application source tree")
    _assert_private_permissions(canonical)
    return canonical


def _registry_root(data_home: Path) -> Path:
    return data_home / "shared" / "project_instances"


def _data_home_identity(data_home: Path, *, create: bool) -> str:
    marker = data_home / "shared" / "data_home_identity.json"
    _assert_no_reparse(marker.parent, code="DATA_HOME_REPARSE_POINT")
    _assert_no_reparse(marker, code="DATA_HOME_REPARSE_POINT")
    if marker.exists():
        _assert_private_permissions(marker, require_independent_acl=False)
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PathResolutionError("DATA_HOME_IDENTITY_INVALID", "DataHome identity is unreadable or malformed") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != DATA_HOME_SCHEMA or not isinstance(payload.get("data_home_id"), str):
            raise PathResolutionError("DATA_HOME_IDENTITY_INVALID", "DataHome identity schema is invalid")
        return payload["data_home_id"]
    if not create:
        raise PathResolutionError("DATA_HOME_IDENTITY_MISSING", "DataHome has not been registered")
    data_home_id = str(uuid.uuid4())
    _write_json_new(marker, {"schema_version": DATA_HOME_SCHEMA, "data_home_id": data_home_id,
                             "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return data_home_id


@contextmanager
def _registry_lock(registry_root: Path):
    """Fail closed on concurrent/stale registry writes; recovery is explicit."""
    lock_path = registry_root / ".registration.lock"
    _assert_no_reparse(registry_root, code="PROJECT_REGISTRY_UNSAFE")
    try:
        with lock_path.open("x", encoding="ascii") as stream:
            stream.write(f"pid={os.getpid()}\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PathResolutionError("PROJECT_REGISTRY_BUSY", "another or interrupted registration owns the registry lock") from exc
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def create_project(
    *,
    project_id: str,
    display_name: str = "",
    data_home: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    pointer_path: str | os.PathLike[str] | None = None,
) -> dict:
    """Register one new instance under an explicit/persisted DataHome.

    Creating a new instance is also the identity boundary for fork/clone-as-new:
    project content approval is a caller responsibility; old run/acceptance and
    cost records are not copied by this function.
    """
    if not PROJECT_ID.fullmatch(project_id):
        raise PathResolutionError("PROJECT_ID_INVALID", "project_id must be a short safe display label")
    root = resolve_data_home(explicit=data_home, env=env, pointer_path=pointer_path)
    projects_root = root / "projects"
    registry_root = _registry_root(root)
    _assert_no_reparse(root, code="DATA_HOME_REPARSE_POINT")
    _ensure_private_directory(projects_root, root=root, code="PROJECT_PATH_UNSAFE")
    _ensure_private_directory(registry_root, root=root, code="PROJECT_REGISTRY_UNSAFE")

    with _registry_lock(registry_root):
        _assert_no_reparse(root, code="DATA_HOME_REPARSE_POINT")
        _assert_private_permissions(projects_root, require_independent_acl=False)
        _assert_private_permissions(registry_root, require_independent_acl=False)
        _assert_no_reparse(projects_root, code="PROJECT_PATH_UNSAFE")
        _assert_no_reparse(registry_root, code="PROJECT_REGISTRY_UNSAFE")
        data_home_id = _data_home_identity(root, create=True)
        instance_id = str(uuid.uuid4())
        project_root = projects_root / instance_id
        _ensure_private_directory(project_root, root=root, code="PROJECT_PATH_UNSAFE")
        identity_path = project_root / "project_identity.json"
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        identity = {
            "schema_version": IDENTITY_SCHEMA,
            "project_instance_id": instance_id,
            "project_id": project_id,
            "display_name": display_name,
            "data_home_id": data_home_id,
            "registered_project_root": str(project_root.resolve(strict=True)),
            "created_at": now,
            "status": "ACTIVE",
        }
        registry = {
            "schema_version": REGISTRY_SCHEMA,
            "project_instance_id": instance_id,
            "project_root": identity["registered_project_root"],
            "status": "ACTIVE",
        }
        try:
            _write_json_new(identity_path, identity)
            _write_json_new(registry_root / f"{instance_id}.json", registry)
        except Exception:
            # A failed pair is retained as an explicit incomplete registration for
            # doctor/recovery; it is never silently re-used or rewritten.
            raise
    return {"project_instance_id": instance_id, "project_id": project_id, "project_root": str(project_root), "status": "PROJECT_READY"}


def resolve_project(
    project_root: str | os.PathLike[str] | None,
    *,
    data_home: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    pointer_path: str | os.PathLike[str] | None = None,
) -> dict:
    """Validate an explicit project root against its immutable registry record."""
    if project_root is None:
        env = os.environ if env is None else env
        project_root = env.get("STORYSTUDIO_PROJECT_ROOT")
    if project_root is None:
        raise PathResolutionError("PROJECT_REQUIRED", "select a registered project root")
    root = resolve_data_home(explicit=data_home, env=env, pointer_path=pointer_path)
    candidate = _absolute_without_traversal(project_root, code="PROJECT_PATH_UNSAFE")
    _assert_no_reparse(candidate, code="PROJECT_PATH_UNSAFE")
    try:
        canonical = candidate.resolve(strict=True)
    except OSError as exc:
        raise PathResolutionError("PROJECT_REQUIRED", "project root is unavailable") from exc
    projects_root_path = root / "projects"
    _assert_no_reparse(projects_root_path, code="PROJECT_PATH_UNSAFE")
    _assert_no_reparse(_registry_root(root), code="PROJECT_REGISTRY_UNSAFE")
    _assert_no_reparse(root / "shared", code="PROJECT_REGISTRY_UNSAFE")
    _assert_private_permissions(root / "shared", require_independent_acl=False)
    projects_root = projects_root_path.resolve(strict=True)
    _assert_private_permissions(projects_root, require_independent_acl=False)
    _assert_private_permissions(_registry_root(root), require_independent_acl=False)
    if canonical.parent != projects_root:
        raise PathResolutionError("PROJECT_PATH_OUTSIDE_DATA_HOME", "registered writable projects must be immediate DataHome children")
    _assert_private_permissions(canonical, require_independent_acl=False)
    identity_path = canonical / "project_identity.json"
    _assert_private_permissions(identity_path, require_independent_acl=False)
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PathResolutionError("PROJECT_IDENTITY_INVALID", "project identity is missing or malformed") from exc
    if not isinstance(identity, dict) or identity.get("schema_version") != IDENTITY_SCHEMA:
        raise PathResolutionError("PROJECT_IDENTITY_INVALID", "unsupported project identity schema")
    instance_id = identity.get("project_instance_id")
    if not isinstance(instance_id, str):
        raise PathResolutionError("PROJECT_IDENTITY_INVALID", "project instance identity is absent")
    try:
        canonical_instance_id = str(uuid.UUID(instance_id))
    except (ValueError, AttributeError) as exc:
        raise PathResolutionError("PROJECT_IDENTITY_INVALID", "project instance identity must be a canonical UUID") from exc
    if canonical_instance_id != instance_id:
        raise PathResolutionError("PROJECT_IDENTITY_INVALID", "project instance identity must be a canonical lowercase UUID")
    registry_path = _registry_root(root) / f"{instance_id}.json"
    _assert_no_reparse(registry_path, code="PROJECT_REGISTRY_UNSAFE")
    _assert_private_permissions(registry_path, require_independent_acl=False)
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PathResolutionError("PROJECT_REGISTRATION_INCOMPLETE", "registry record is missing or malformed") from exc
    expected = str(canonical)
    if (not isinstance(registry, dict) or
            registry.get("schema_version") != REGISTRY_SCHEMA or
            identity.get("registered_project_root") != expected or
            registry.get("project_instance_id") != instance_id or
            registry.get("project_root") != expected or
            registry.get("status") != "ACTIVE" or
            identity.get("status") != "ACTIVE"):
        raise PathResolutionError("PROJECT_INSTANCE_COLLISION", "identity is not active at this unique registered root")
    if identity.get("data_home_id") != _data_home_identity(root, create=False):
        raise PathResolutionError("PROJECT_DATA_HOME_MISMATCH", "project is registered to a different DataHome")
    _assert_private_permissions(root / "shared" / "data_home_identity.json", require_independent_acl=False)
    return {"status": "PROJECT_READY", "project_instance_id": instance_id, "project_id": identity.get("project_id"), "project_root": str(canonical)}
