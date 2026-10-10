#!/usr/bin/env python3
"""Byte-for-byte local CNW source-reference capture from an existing pinned submodule.

Does NOT download, update, checkout, modify or remove upstream files. It copies the
original open-source docs/templates and a small set of local-only reference materials
into gitignored runtime/reference/, records Git blob IDs and SHA-256, and fails if
existing snapshots differ. Requires git and Python stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PIN = "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e"
PREFIXES = ("docs/", "templates/")
ROOT_FILES = {"README.md", "LICENSE", "CLAUDE.md"}
LOCAL_ONLY_EXAMPLES = {
    "example_project/00_meta/episode_production_manual.md",
    "example_project/00_meta/manuscript_review_rubric.md",
    "example_project/00_meta/sprint_goal_arc02_production.md",
    "example_project/05_scene_cards/ep001_scene_cards.md",
    "example_project/06_plot/ep002_plot.md",
    "example_project/07_draft/ep001_writing_brief.md",
    "example_project/08_review/ep002-ep006_batch_review.md",
}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"GIT_FAILED:{' '.join(args)}: {result.stderr.strip()[:500]}"
        )
    return result.stdout.strip()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if is_junction and is_junction():
        return True
    if os.name == "nt":
        try:
            # Python < 3.12 has no Path.is_junction(); Windows marks both
            # symlinks and junctions with FILE_ATTRIBUTE_REPARSE_POINT.
            return bool(path.lstat().st_file_attributes & 0x400)
        except (AttributeError, OSError):
            return False
    return False


def ensure_no_redirect(root: Path, path: Path) -> None:
    """Reject symlink/junction ancestors before creating or writing a target."""
    root = root.resolve(strict=True)
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
    except ValueError as err:
        raise RuntimeError(f"OUTPUT_PATH_ESCAPE:{path}") from err
    current = root
    for part in relative.parts:
        current = current / part
        if is_link_or_junction(current):
            raise RuntimeError(f"OUTPUT_PATH_REDIRECT:{current}")
        if current.exists() and not current.is_dir() and current != absolute:
            raise RuntimeError(f"OUTPUT_PARENT_NOT_DIRECTORY:{current}")
    resolved = absolute.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as err:
        raise RuntimeError(f"OUTPUT_PATH_ESCAPE:{path}") from err


def assert_git_ignored(root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--quiet", "--", relative],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"REFERENCE_OUTPUT_NOT_IGNORED:{relative}")


def capture(root: Path) -> dict:
    root = root.resolve(strict=True)
    source = root / "third_party" / "claude-novel-workflow"
    if not (source / ".git").exists():
        raise RuntimeError(
            "PINNED_SUBMODULE_NOT_INITIALIZED: use the already-approved I00 checkout; "
            "ask Writer to initialize only this existing submodule if absent"
        )
    observed = git(source, "rev-parse", "HEAD")
    if observed != PIN:
        raise RuntimeError(f"UPSTREAM_COMMIT_MISMATCH expected={PIN} actual={observed}")
    # Only check tracked modifications. Preserve and report WIP instead of clearing it.
    tracked_dirty = git(source, "diff", "--name-only", "HEAD")
    if tracked_dirty:
        raise RuntimeError(f"UPSTREAM_TRACKED_WIP_PRESENT:{tracked_dirty[:500]}")

    reference_root = root / "runtime" / "reference"
    output = reference_root / ("cnw_" + PIN[:12])
    for directory in (root / "runtime", reference_root, output):
        ensure_no_redirect(root, directory)
        if not directory.exists():
            directory.mkdir()
        ensure_no_redirect(root, directory)
    assert_git_ignored(root, output / "CNW_LOCAL_REFERENCE_MANIFEST.json")

    allpaths = git(source, "ls-tree", "-r", "--name-only", PIN).splitlines()
    selected = sorted(
        p for p in allpaths
        if p.startswith(PREFIXES) or p in ROOT_FILES or p in LOCAL_ONLY_EXAMPLES
    )
    if len(selected) < 45:
        raise RuntimeError(f"UPSTREAM_REFERENCE_INVENTORY_TOO_SMALL:{len(selected)}")

    records: list[dict] = []
    for relative in selected:
        if relative.startswith("/") or "\\" in relative or ".." in Path(relative).parts:
            raise RuntimeError(f"UNSAFE_UPSTREAM_PATH:{relative}")
        src = source / relative
        dst = output / relative
        ensure_no_redirect(output, dst.parent)
        if dst.exists() or is_link_or_junction(dst):
            ensure_no_redirect(output, dst)
        if not src.is_file() or src.is_symlink():
            raise RuntimeError(f"UPSTREAM_SOURCE_MISSING_OR_SYMLINK:{relative}")
        commit_blob = git(source, "rev-parse", f"{PIN}:{relative}")
        actual_blob = git(source, "hash-object", "--", relative)
        if commit_blob != actual_blob:
            raise RuntimeError(f"UPSTREAM_SOURCE_BYTES_CHANGED:{relative}")
        before = sha256(src)
        if dst.exists():
            if not dst.is_file() or dst.is_symlink() or sha256(dst) != before:
                raise RuntimeError(f"EXISTING_REFERENCE_COLLISION:{relative}")
        else:
            # Create each missing directory only after its full ancestor chain
            # has been checked. Recheck after creation before writing bytes.
            missing: list[Path] = []
            parent = dst.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for directory in reversed(missing):
                ensure_no_redirect(output, directory)
                directory.mkdir()
                ensure_no_redirect(output, directory)
            shutil.copyfile(src, dst)
        if sha256(dst) != before:
            raise RuntimeError(f"REFERENCE_COPY_MISMATCH:{relative}")
        records.append({
            "source_path": relative,
            "upstream_git_blob": commit_blob,
            "sha256": before,
            "bytes": src.stat().st_size,
            "local_reference": (Path("runtime") / "reference" / ("cnw_" + PIN[:12]) / relative).as_posix(),
        })

    manifest = {
        "project": "MintoTsukino/claude-novel-workflow",
        "upstream_commit": PIN,
        "copied_from": "existing pinned third_party/claude-novel-workflow checkout",
        "scope": "docs and generic templates + selected local-only operational examples",
        "file_count": len(records),
        "references": records,
        "warning": "Do not commit local-only example story materials or user manuscripts to a public repository. Use the templates as methods, not the example novel's canon.",
    }
    encoded = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    manifest_path = output / "CNW_LOCAL_REFERENCE_MANIFEST.json"
    if manifest_path.exists() and manifest_path.read_bytes() != encoded:
        raise RuntimeError("EXISTING_REFERENCE_MANIFEST_COLLISION")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if not manifest_path.exists():
        manifest_path.write_bytes(encoded)
    return {
        "status": "REFERENCE_CAPTURE_VERIFIED",
        "source_commit": PIN,
        "files": len(records),
        "reference_root": str(output),
        "manifest_sha256": sha256(manifest_path),
        "manifest": str(manifest_path),
        "no_supplier_calls": True,
        "upstream_modified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = capture(args.repo_root)
    except Exception as err:
        print(json.dumps({"status": "BLOCKED", "error": str(err)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
