"""Offline, identity-based health checks for optional reference/build assets."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import sys

REFERENCE_COMMIT = "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e"
REFERENCE_BLOBS = {
    "templates/config/workflow.template.yml": "146ea01a484cc0578cf290478b3941599ad7fb15",
    "templates/config/ai_roles.template.yml": "8ec31cb93cb0be1913579cc5cb05de45460988f8",
    "docs/THREE_LAYER_REVIEW.md": "d03488d15f1a7841f442119237aff6d6148020df",
    "docs/HOW_TO_ADAPT.md": "5cbd6de30a6acfb1334e414dd747a74b96f3c88a",
    "docs/GETTING_STARTED.md": "3496d75c56bf13c5b9e834fbe98df9c539cdfec3",
    "templates/CLAUDE.md": "d4bfb370aaf6aadbbbbd4915422e7ceac673d0d6",
    "templates/_workflows/01_first_import.md": "56148578d91d55e492a6913b4d73cbe529c34ecf",
    "templates/_workflows/02_incremental_update.md": "ae1c43eb249aa6fdbe7462bd6fd058222eb015fc",
    "templates/_workflows/03_revision.md": "cae774e2582b09bdeaa7e80e6a7831ab4053dce5",
    "templates/_workflows/04_canon_audit.md": "da2afada0be6b6e66892bc2c9625b7fd70a0c5f5",
    "templates/_workflows/05_handoff.md": "a0349689535741e6a8a47e19a421922c7a1d53c4",
    "templates/08_review/batch_review.template.md": "24ba804c4807e0e535eee07a00c46d58ff10fd5a",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    # These pinned method references are text files. Git's clean conversion
    # maps Windows CRLF checkouts back to the LF blob bytes.
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical:
        return ""
    header = f"blob {len(canonical)}\0".encode("ascii")
    return hashlib.sha1(header + canonical).hexdigest()


def _verify_reference_files(root: Path, expected_commit: str,
                            expected_blobs: dict[str, str]) -> str:
    reference_root = root / "runtime/reference/cnw_97ad71fe5e5e"
    manifest_path = reference_root / "CNW_LOCAL_REFERENCE_MANIFEST.json"
    if not manifest_path.is_file():
        return "RUNTIME_MISSING"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest["references"]
        if (manifest.get("project") != "MintoTsukino/claude-novel-workflow" or
                manifest.get("upstream_commit") != expected_commit or
                not isinstance(rows, list) or manifest.get("file_count") != len(rows)):
            return "PIN_MISMATCH"
        by_source = {row["source_path"]: row for row in rows if isinstance(row, dict)}
        if len(by_source) != len(rows):
            return "PIN_MISMATCH"
        for source_path, expected_blob in expected_blobs.items():
            row = by_source.get(source_path)
            if not row or row.get("upstream_git_blob") != expected_blob:
                return "PIN_MISMATCH"
            relative = Path(row["local_reference"])
            if relative.is_absolute() or ".." in relative.parts:
                return "PIN_MISMATCH"
            local = (root / relative).resolve(strict=True)
            if not local.is_relative_to(reference_root.resolve()):
                return "PIN_MISMATCH"
            if (local.stat().st_size != row.get("bytes") or
                    _sha(local) != str(row.get("sha256", "")).lower() or
                    _git_blob_sha(local) != expected_blob):
                return "PIN_MISMATCH"
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "PIN_MISMATCH"
    return "PINNED_REFERENCE_VERIFIED"


def verify_author_reference(repo_root: str | Path) -> str:
    return _verify_reference_files(Path(repo_root).resolve(), REFERENCE_COMMIT, REFERENCE_BLOBS)


def verify_optional_build(repo_root: str | Path, component: str) -> str:
    root = Path(repo_root).resolve()
    configs = {
        "critics": {
            "index": "patches/critics/PATCH_INDEX.json",
            "runtime_root": "runtime/patched/CritiCS",
            "prefix": "p2-02",
            "required_files": ("critics/plan/plan.py", "critics/text/text.py"),
            "extra_hashes": (),
        },
        "nk": {
            "index": "patches/nk/PATCH_INDEX.json",
            "runtime_root": "runtime/patched/NK",
            "prefix": "p2-03",
            "required_files": (),
            "extra_hashes": (("package_manifest", "package_manifest_sha256"),),
        },
    }
    config = configs.get(component)
    if config is None:
        return "IDENTITY_MISMATCH"
    index_path = root / config["index"]
    if not index_path.is_file():
        return "UNAVAILABLE"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        commit = str(index["source_commit"])
        patches, patch_hashes = index["ordered_patch_files"], index["patch_sha256"]
        lock_rel, lock_hash = index["dependency_lock"], str(index["dependency_lock_sha256"]).lower()
        build_id = str(index["runtime_build_id"])
        if (not commit or not isinstance(patches, list) or not patches or
                not isinstance(patch_hashes, list) or len(patches) != len(patch_hashes)):
            return "IDENTITY_MISMATCH"
        for relative, expected in zip(patches, patch_hashes):
            patch = (root / relative).resolve(strict=True)
            if not patch.is_relative_to(root) or _sha(patch) != str(expected).lower():
                return "IDENTITY_MISMATCH"
        lock = (root / lock_rel).resolve(strict=True)
        if not lock.is_relative_to(root) or _sha(lock) != lock_hash:
            return "IDENTITY_MISMATCH"
        identity_parts = [config["prefix"], commit[:8], str(patch_hashes[0]).lower()[:12], lock_hash[:12]]
        expected_id = "-".join(identity_parts)
        for field, expected_hash in config["extra_hashes"]:
            extra = (root / index[field]).resolve(strict=True)
            extra_hash = str(index[expected_hash]).lower()
            if not extra.is_relative_to(root) or _sha(extra) != extra_hash:
                return "IDENTITY_MISMATCH"
        runtime_path = str(index.get("runtime_path", f"{config['runtime_root']}/{build_id}")).replace("\\", "/")
        if build_id != expected_id or runtime_path != f"{config['runtime_root']}/{build_id}":
            return "IDENTITY_MISMATCH"
        build = (root / runtime_path).resolve(strict=True)
        if not build.is_relative_to((root / config["runtime_root"]).resolve(strict=True)):
            return "IDENTITY_MISMATCH"
        if any(not (build / relative).is_file() for relative in config["required_files"]):
            return "UNAVAILABLE"
        if component == "nk":
            package = (build / "package.json")
            if not package.is_file() or _sha(package) != str(index["package_manifest_sha256"]).lower():
                return "IDENTITY_MISMATCH"
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "IDENTITY_MISMATCH"
    return "AVAILABLE_PINNED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    result = {
        "author_reference": verify_author_reference(root),
        "optional_critics": verify_optional_build(root, "critics"),
        "optional_nk": verify_optional_build(root, "nk"),
        "provider_call": "none",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
