"""Thin project bridge around the unmodified CritiCS method sequence."""
from __future__ import annotations

import argparse
from typing import NamedTuple
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATCH_INDEX = json.loads((ROOT / "patches" / "critics" / "PATCH_INDEX.json").read_text(encoding="utf-8"))
BUILD = ROOT / "runtime" / "patched" / "CritiCS" / PATCH_INDEX["runtime_build_id"]
CONFIG = ROOT / "config" / "production.example.json"


class _RegisteredNativeInvocation(NamedTuple):
    account: object
    parent_run_dir: Path
    run_dir: Path
    input_path: Path
    critique_path: Path | None
    action: str
    input_sha256: str
    critique_sha256: str | None
    accounted_send: object


def _verify_registered_invocation(source: Path, critique: Path | None,
                                 run_dir: Path, action: str, invocation) -> None:
    owner = _registered_project_for_path(run_dir)
    source_owner = _registered_project_for_path(source)
    critique_owner = _registered_project_for_path(critique) if critique else None
    if not (owner or source_owner or critique_owner):
        if invocation is not None:
            raise ValueError("CRITICS_REGISTERED_INVOCATION_INVALID")
        return
    if not isinstance(invocation, _RegisteredNativeInvocation):
        raise ValueError("CRITICS_REGISTERED_INVOCATION_REQUIRED")
    import httpx
    try:
        from . import cost_guard
    except ImportError:
        import cost_guard
    parent = invocation.parent_run_dir
    stage = "critics_text" if action == "text-refine" else "critics_plot"
    account = invocation.account
    if (not owner or source_owner != owner or (critique and critique_owner != owner)
            or not isinstance(account, cost_guard.RunAccount)
            or _registered_project_for_path(parent) != owner
            or run_dir.parent != parent.parent or not source.is_relative_to(parent)
            or invocation.run_dir != run_dir or invocation.input_path != source
            or invocation.critique_path != critique or invocation.action != action
            or account.run != parent or account.context.run_id != parent.name
            or account.context.stage != stage
            or account.context != cost_guard.for_run(parent, stage=stage, model="deepseek-flash").context
            or invocation.accounted_send is not httpx.Client.send
            or invocation.input_sha256 != sha256_file(source)
            or invocation.critique_sha256 != (sha256_file(critique) if critique else None)):
        raise ValueError("CRITICS_REGISTERED_INVOCATION_INVALID")


def project_path(value: str, *, directory: bool = False) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve(strict=False)
    repo_roots = ((ROOT / "workspace").resolve(), (ROOT / "runs").resolve())
    repo_content_allowed = any(resolved.is_relative_to(base) for base in repo_roots)
    data_home_project = _registered_project_for_path(resolved)
    if directory:
        in_repo_runs = resolved.is_relative_to((ROOT / "runs").resolve())
        in_project_runs = bool(data_home_project and
                               resolved.is_relative_to((data_home_project / "runs").resolve()))
        if not (in_repo_runs or in_project_runs):
            raise ValueError("RUN_DIR_MUST_BE_UNDER_REGISTERED_RUNS")
    elif not (repo_content_allowed or data_home_project):
        raise ValueError("INPUT_MUST_BE_UNDER_PRIVATE_WORKSPACE_OR_REGISTERED_PROJECT")
    if resolved == ROOT.resolve():
        raise ValueError("PROJECT_ROOT_IS_NOT_A_FILE")
    return resolved


def _registered_project_for_path(path: Path) -> Path | None:
    """Return the registered DataHome project containing path, if any."""
    try:
        from project_paths import resolve_project
    except ImportError:
        try:
            from .project_paths import resolve_project
        except ImportError:
            return None
    for ancestor in (path, *path.parents):
        if ancestor.parent.name != "projects":
            continue
        try:
            registration = resolve_project(ancestor, data_home=ancestor.parent.parent)
        except Exception:
            continue
        if registration.get("project_root") == str(ancestor.resolve(strict=True)):
            return ancestor.resolve(strict=True)
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def create_run_directory(value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    candidate = candidate.absolute().resolve(strict=False)
    runs = candidate.parent
    if runs == ROOT / "runs":
        if runs.is_symlink() or not runs.is_dir():
            raise ValueError("RUNS_ROOT_INVALID")
    else:
        project = _registered_project_for_path(runs)
        if (runs.name != "runs" or project is None or
                runs.resolve(strict=False) != (project / "runs").resolve(strict=False)):
            raise ValueError("RUNS_ROOT_NOT_REGISTERED")
        if runs.is_symlink() or not runs.is_dir():
            raise ValueError("RUNS_ROOT_INVALID")
    if candidate.name in ("", ".", ".."):
        raise ValueError("RUN_DIR_MUST_BE_NEW_DIRECT_CHILD")
    if candidate.is_symlink() or candidate.exists():
        raise ValueError("RUN_DIR_MUST_BE_NEW")
    candidate.mkdir(exist_ok=False)
    return candidate.resolve(strict=True)


def write_text(path: Path, content: str, run_dir: Path):
    if path.parent != run_dir or path.exists() or path.is_symlink():
        raise ValueError("OUTPUT_PATH_NOT_FRESH_INSIDE_RUN_DIR")
    path.relative_to(run_dir)
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(content)


def write_json(path: Path, payload, run_dir: Path):
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", run_dir)


def configure_provider():
    cfg = read_json(CONFIG)["provider"]
    required = {"model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1"}
    for key, expected in required.items():
        if cfg.get(key) != expected:
            raise ValueError(f"PROVIDER_CONFIG_INVALID:{key}")
    for env_name, key in (("STORYSTUDIO_MODEL", "model"), ("STORYSTUDIO_BASE_URL", "base_url")):
        present = os.environ.get(env_name)
        if present and present != cfg[key]:
            raise ValueError(f"PROVIDER_ENV_OVERRIDE_REJECTED:{env_name}")
        os.environ[env_name] = cfg[key]
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY_REQUIRED")
    # This run writes prompts/responses only to the private run directory.
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"


def main(argv=None, *, _registered_invocation=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("plan-critique")
    p.add_argument("--plot", required=True)
    p.add_argument("--run-dir", required=True)
    p = sub.add_parser("plan-revise")
    p.add_argument("--plot", required=True)
    p.add_argument("--critique", required=True)
    p.add_argument("--run-dir", required=True)
    p = sub.add_parser("text-refine")
    p.add_argument("--excerpt", required=True)
    p.add_argument("--run-dir", required=True)
    args = parser.parse_args(argv)

    input_arg = getattr(args, "plot", None) or getattr(args, "excerpt", None)
    source = project_path(input_arg)
    if not source.is_file():
        raise FileNotFoundError("INPUT_FILE_NOT_FOUND")
    critique_path = project_path(args.critique) if args.action == "plan-revise" else None
    if critique_path is not None and not critique_path.is_file():
        raise FileNotFoundError("CRITIQUE_FILE_NOT_FOUND")
    requested_run = project_path(args.run_dir, directory=True)
    _verify_registered_invocation(source, critique_path, requested_run, args.action, _registered_invocation)
    if not BUILD.is_dir():
        raise FileNotFoundError("CRITICS_BUILD_NOT_FOUND")
    run_dir = create_run_directory(args.run_dir)

    configure_provider()
    sys.path.insert(0, str(BUILD))
    os.chdir(run_dir)
    text = source.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError("INPUT_EMPTY")

    if args.action == "plan-critique":
        from critics.plan.plan import Critic
        result = Critic(text).three_critic()
        output_path = run_dir / "critique.json"
        write_json(output_path, result, run_dir)
    elif args.action == "plan-revise":
        from critics.plan.plan import modifiedStoryline
        critique = read_json(critique_path)
        result = modifiedStoryline(text, critique)
        output_path = run_dir / "modified_plot.md"
        write_text(output_path, str(result), run_dir)
    else:
        from critics.text.text import Refinement
        result = Refinement(text).Two_refinement()
        output_path = run_dir / "text_refinement.json"
        write_json(output_path, result, run_dir)

    if not output_path.is_file() or not output_path.stat().st_size:
        raise RuntimeError("CRITICS_OUTPUT_NOT_WRITTEN")
    write_json(run_dir / "run_receipt.json", {
        "action": args.action,
        "input_sha256": sha256_file(source),
        "output_sha256": sha256_file(output_path),
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com/v1",
        "build": str(BUILD.relative_to(ROOT)).replace("\\", "/"),
        "status": "SUCCEEDED",
    }, run_dir)
    print(json.dumps({"status": "SUCCEEDED", "output": str(output_path), "receipt": str(run_dir / "run_receipt.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"CRITICS_BRIDGE_FAILED:{type(error).__name__}:{error}", file=sys.stderr)
        raise SystemExit(2)
