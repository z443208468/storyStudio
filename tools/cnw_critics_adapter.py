"""Safe invocation builder for the existing, cost-guarded CritiCS bridge."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

try:
    from .cnw_contract import ContractError
except ImportError:  # direct script execution
    from cnw_contract import ContractError

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "p2_06_critics_run.py"
PATCH_INDEX = ROOT / "patches" / "critics" / "PATCH_INDEX.json"


def build_plan_critique_command(python: str | Path, plot_path: str | Path, run_name: str) -> list[str]:
    if Path(run_name).name != run_name or run_name in ("", ".", ".."):
        raise ContractError("CRITICS_RUN_ID_INVALID", run_name)
    plot = Path(plot_path)
    if not plot.is_absolute():
        plot = ROOT / plot
    plot = plot.resolve(strict=True)
    if not plot.is_relative_to((ROOT / "workspace" / "cangqi").resolve()) and not plot.is_relative_to((ROOT / "runs").resolve()):
        raise ContractError("CRITICS_INPUT_PATH_UNSAFE", "plot must be in the private project or run directory")
    if not plot.is_file():
        raise ContractError("CRITICS_PLOT_MISSING", str(plot))
    return [str(python), str(RUNNER), "--action", "plan-critique", "--input", str(plot), "--run-name", run_name]


def build_plan_revise_command(python: str | Path, plot_path: str | Path, critique_path: str | Path, run_name: str) -> list[str]:
    command = build_plan_critique_command(python, plot_path, run_name)
    command[command.index("plan-critique")] = "plan-revise"
    critique = Path(critique_path)
    if not critique.is_absolute():
        critique = ROOT / critique
    critique = critique.resolve(strict=True)
    if not critique.is_relative_to((ROOT / "runs").resolve()) or not critique.is_file():
        raise ContractError("CRITICS_INPUT_PATH_UNSAFE", "critique must be a private run output")
    command.extend(["--critique", str(critique)])
    return command


def verify_plan_receipt(receipt: dict, *, action: str, input_path: str | Path, output_path: str | Path) -> dict:
    if receipt.get("action") != action or receipt.get("status") != "SUCCEEDED" or receipt.get("model") != "deepseek-flash":
        raise ContractError("CRITICS_RECEIPT_INVALID", "action/status/model mismatch")
    source = Path(input_path).resolve(strict=True)
    output = Path(output_path).resolve(strict=True)
    expected = hashlib.sha256(source.read_bytes()).hexdigest().upper()
    actual = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    if receipt.get("input_sha256") != expected or receipt.get("output_sha256") != actual:
        raise ContractError("CRITICS_RECEIPT_HASH_MISMATCH", "receipt does not bind actual input/output")
    build_id = json.loads(PATCH_INDEX.read_text(encoding="utf-8"))["runtime_build_id"]
    expected_build = f"runtime/patched/CritiCS/{build_id}"
    if receipt.get("build", "").replace("\\", "/") != expected_build or receipt.get("base_url") != "https://api.deepseek.com/v1":
        raise ContractError("CRITICS_RECEIPT_METHOD_MISMATCH", "receipt does not bind the pinned patched build and provider endpoint")
    return {"action": action, "input_sha256": expected, "output_sha256": actual, "build": expected_build, "status": "FOUND_AND_HASH_VERIFIED"}
