"""Thin project bridge around the unmodified CritiCS method sequence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PATCH_INDEX = json.loads((ROOT / "patches" / "critics" / "PATCH_INDEX.json").read_text(encoding="utf-8"))
BUILD = ROOT / "runtime" / "patched" / "CritiCS" / PATCH_INDEX["runtime_build_id"]
CONFIG = ROOT / "config" / "production.example.json"


def project_path(value: str, *, directory: bool = False) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("PATH_OUTSIDE_PROJECT_ROOT") from exc
    if directory and not resolved.is_relative_to((ROOT / "runs").resolve()):
        raise ValueError("RUN_DIR_MUST_BE_UNDER_RUNS")
    if not directory:
        allowed = ((ROOT / "workspace" / "cangqi").resolve(), (ROOT / "runs").resolve())
        if not any(resolved.is_relative_to(base) for base in allowed):
            raise ValueError("INPUT_MUST_BE_UNDER_CANGQI_WORKSPACE_OR_RUNS")
    if resolved == ROOT.resolve():
        raise ValueError("PROJECT_ROOT_IS_NOT_A_FILE")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def create_run_directory(value: str) -> Path:
    runs = ROOT / "runs"
    if runs.is_symlink() or not runs.is_dir():
        raise ValueError("RUNS_ROOT_INVALID")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        relative = candidate.relative_to(runs)
    except ValueError as exc:
        raise ValueError("RUN_DIR_MUST_BE_UNDER_RUNS") from exc
    if len(relative.parts) != 1 or relative.parts[0] in (".", ".."):
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


def main(argv=None) -> int:
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

    if not BUILD.is_dir():
        raise FileNotFoundError("CRITICS_BUILD_NOT_FOUND")
    input_arg = getattr(args, "plot", None) or getattr(args, "excerpt", None)
    source = project_path(input_arg)
    if not source.is_file():
        raise FileNotFoundError("INPUT_FILE_NOT_FOUND")
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
        critique_path = project_path(args.critique)
        if not critique_path.is_file():
            raise FileNotFoundError("CRITIQUE_FILE_NOT_FOUND")
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
