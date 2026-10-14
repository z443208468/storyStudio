"""Safe invocation builder for the existing, cost-guarded CritiCS bridge."""
from __future__ import annotations

import hashlib
import ast
import json
from dataclasses import replace
from pathlib import Path
import re

try:
    from .cnw_contract import ContractError, assert_output_within_root
    from . import critics_bridge
except ImportError:  # direct script execution
    from cnw_contract import ContractError, assert_output_within_root
    import critics_bridge

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
    if not plot.is_relative_to((ROOT / "workspace").resolve()) and not plot.is_relative_to((ROOT / "runs").resolve()):
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


def read_native_result(run_name: str | Path, *, action: str, input_path: Path,
                       critique_path: Path | None = None, parent_run_dir: Path | None = None,
                       parent_stage: str | None = None, ledger: dict | None = None) -> dict:
    """Read the native result and bind it to its original receipt and responses."""
    batch = _NativeReadBatch(parent_run_dir, parent_stage, ledger) if parent_run_dir is not None else None
    result = _read_native_result(run_name, action=action, input_path=input_path,
        critique_path=critique_path, parent_stage=parent_stage, batch=batch)
    if batch is not None:
        batch.finish()
    return result


class _NativeReadBatch:
    """One read's real account and file preimages; never a production permit."""
    def __init__(self, parent, stage, ledger):
        try:
            from .cost_guard import for_run, RunAccount
            from . import p2_cost_guard
            from .project_paths import _assert_no_reparse
        except ImportError:
            from cost_guard import for_run, RunAccount
            import p2_cost_guard
            from project_paths import _assert_no_reparse
        if not stage:
            raise ContractError("CRITICS_PARENT_RUN_BINDING_INVALID", str(parent))
        self.for_run, self.assert_path = for_run, _assert_no_reparse
        self.account = for_run(parent, stage=stage, model="deepseek-flash")
        if not isinstance(self.account, RunAccount):
            raise ContractError("CRITICS_PARENT_RUN_BINDING_INVALID", str(parent))
        self.parent = self.account.run
        self.ledger = ledger if ledger is not None else p2_cost_guard.read_ledger_snapshot()
        self.files = {}

    def snapshot(self, path):
        path = Path(path).absolute()
        self.assert_path(path, code="CRITICS_EVIDENCE_PATH_UNSAFE")
        raw = path.read_bytes()
        if path in self.files and self.files[path] != raw:
            raise ContractError("CRITICS_EVIDENCE_CHANGED", str(path))
        self.files[path] = raw
        return raw

    def attributed_account(self, stage):
        return replace(self.account, context=replace(self.account.context, stage=stage))

    def finish(self):
        current = self.for_run(self.parent, stage=self.account.context.stage, model="deepseek-flash")
        if current != self.account:
            raise ContractError("CRITICS_COST_CONTEXT_MISMATCH", self.parent.name)
        for path, raw in self.files.items():
            self.assert_path(path, code="CRITICS_EVIDENCE_PATH_UNSAFE")
            if path.read_bytes() != raw:
                raise ContractError("CRITICS_EVIDENCE_CHANGED", str(path))


def read_native_support_records(parent_run_dir, records, *, ledger=None):
    """Validate registered native references within one short lived read batch.

    Records are (hook name, hook evidence, original input snapshot path).
    Repeated references share one raw read, never authority or cross-call state.
    """
    records = list(records)
    if not records:
        return []
    batch = _NativeReadBatch(parent_run_dir, records[0][0], ledger)
    cache, results = {}, []
    for name, hook, input_path in records:
        if name not in {"critics_plot", "critics_text"}:
            raise ContractError("CRITICS_ACTION_INVALID", name)
        if not hook.get("run_dir"):
            raise ContractError("CRITICS_NATIVE_RUN_IDENTITY_MISSING", name)
        input_path = Path(input_path).absolute()
        batch.assert_path(input_path, code="CRITICS_EVIDENCE_PATH_UNSAFE")
        if not input_path.resolve(strict=True).is_relative_to(batch.parent):
            raise ContractError("CRITICS_INPUT_PARENT_RUN_MISMATCH", str(input_path))
        artifact_path = hook.get("input_artifact", {}).get("path")
        if (not artifact_path or assert_output_within_root(batch.parent, artifact_path).resolve(strict=True)
                != input_path.resolve(strict=True)):
            raise ContractError("CRITICS_INPUT_CHANGED", name)
        raw = batch.snapshot(input_path)
        actual_sha = hashlib.sha256(raw).hexdigest()
        if (actual_sha != hook.get("input_sha256")
                or actual_sha != hook.get("input_artifact", {}).get("sha256")):
            raise ContractError("CRITICS_INPUT_CHANGED", name)
        action = "plan-critique" if name == "critics_plot" else "text-refine"
        key = (str(hook["run_dir"]), name, action, str(Path(input_path).absolute()), actual_sha)
        if key not in cache:
            cache[key] = _read_native_result(hook["run_dir"], action=action,
                input_path=Path(input_path), parent_stage=name, batch=batch)
        result = cache[key]
        if hook.get("status") == "SUCCEEDED" and (
                hook.get("result") != result["result"]
                or hook.get("evidence_files") != result["evidence_files"]):
            raise ContractError("CRITICS_EVIDENCE_CHANGED", hook["run_dir"])
        results.append((name, hook, result))
    batch.finish()
    return results


def _read_native_result(run_name, *, action, input_path, critique_path=None,
                        parent_stage=None, batch=None):
    parent_run_dir = batch.parent if batch is not None else None
    input_path = Path(input_path).absolute()
    critique_path = Path(critique_path).absolute() if critique_path is not None else None
    supplied = Path(run_name)
    if batch is not None:
        if not supplied.is_absolute():
            raise ContractError("CRITICS_PARENT_RUN_BINDING_INVALID", str(supplied))
        batch.assert_path(supplied.absolute(), code="CRITICS_EVIDENCE_PATH_UNSAFE")
        directory = supplied.resolve(strict=True)
        if directory.parent != batch.parent.parent:
            raise ContractError("CRITICS_PARENT_RUN_BINDING_INVALID", str(batch.parent))
        run_id = directory.name
    elif supplied.is_absolute():
        directory = critics_bridge.project_path(str(supplied), directory=True)
        run_id = directory.name
        if parent_run_dir is None and critics_bridge._registered_project_for_path(directory):
            raise ContractError("CRITICS_PARENT_RUN_BINDING_REQUIRED", run_id)
    else:
        if Path(run_name).name != run_name or run_name in ("", ".", ".."):
            raise ContractError("CRITICS_RUN_ID_INVALID", str(run_name))
        run_id = str(run_name)
        directory = assert_output_within_root(ROOT / "runs", run_id)
    names = {"plan-critique": "critique.json", "text-refine": "text_refinement.json", "plan-revise": "modified_plot.md"}
    if action not in names:
        raise ContractError("CRITICS_ACTION_INVALID", action)
    output = assert_output_within_root(directory, names[action])
    receipt_path = assert_output_within_root(directory, "run_receipt.json")
    calls_path = assert_output_within_root(directory, "provider-calls.json")
    if batch is not None:
        batch.assert_path(input_path, code="CRITICS_EVIDENCE_PATH_UNSAFE")
        if not input_path.resolve(strict=True).is_relative_to(batch.parent):
            raise ContractError("CRITICS_INPUT_PARENT_RUN_MISMATCH", str(input_path))
        if critique_path is not None:
            batch.assert_path(critique_path, code="CRITICS_EVIDENCE_PATH_UNSAFE")
            if not critique_path.resolve(strict=True).is_relative_to(batch.parent.parent.parent):
                raise ContractError("CRITICS_INPUT_PARENT_RUN_MISMATCH", str(critique_path))
    receipt_raw = batch.snapshot(receipt_path) if batch is not None else receipt_path.read_bytes()
    receipt = json.loads(receipt_raw.decode("utf-8"))
    if receipt.get("action") != action:
        raise ContractError("CRITICS_RECEIPT_INVALID", "native receipt action mismatch")
    originals = {receipt_path: receipt_raw}
    originals.update({path: (batch.snapshot(path) if batch is not None else path.read_bytes())
                      for path in (output, calls_path, input_path)})
    if critique_path is not None:
        originals[critique_path] = batch.snapshot(critique_path) if batch is not None else critique_path.read_bytes()
    if batch is not None:
        parent = batch.parent
        if not input_path.resolve(strict=True).is_relative_to(parent):
            raise ContractError("CRITICS_INPUT_PARENT_RUN_MISMATCH", str(input_path))
        if critique_path is not None and not critique_path.resolve(strict=True).is_relative_to(parent.parent.parent):
            raise ContractError("CRITICS_INPUT_PARENT_RUN_MISMATCH", str(critique_path))
        account = batch.attributed_account(parent_stage)
        expected_context = account.context.record()
        binding = receipt.get("cost_binding")
        if (not expected_context or not isinstance(binding, dict)
                or binding.get("project_id") != expected_context["project_id"]
                or binding.get("project_instance_id") != expected_context["project_instance_id"]
                or binding.get("parent_run_id") != parent.name
                or binding.get("parent_run_path") != str(parent)
                or binding.get("stage") != parent_stage
                or binding.get("cost_context") != expected_context):
            raise ContractError("CRITICS_COST_CONTEXT_MISMATCH", run_id)
        calls_for_binding = json.loads(originals[calls_path].decode("utf-8"))
        ledger_rows = [row for row in batch.ledger["requests"]
                       if row.get("cost_context") == expected_context]
        for call in calls_for_binding:
            settlement = call.get("ledger_settlement") if isinstance(call, dict) else None
            if (not isinstance(settlement, dict)
                    or call.get("cost_context") != expected_context
                    or settlement.get("cost_context") != expected_context):
                raise ContractError("CRITICS_COST_RECEIPT_MISMATCH", run_id)
            account.verify_receipt({"request_id": call.get("local_request_id"),
                "provider_request_id": call.get("response", {}).get("id"),
                "model": call.get("response", {}).get("model"), "ledger_settlement": settlement},
                ledger={"requests": ledger_rows})
    elif receipt.get("cost_binding") is not None:
        raise ContractError("CRITICS_PARENT_RUN_BINDING_REQUIRED", run_id)
    verified = verify_plan_receipt(receipt, action=action, input_path=input_path, output_path=output)
    payload = originals[output].decode("utf-8") if action == "plan-revise" else json.loads(originals[output].decode("utf-8"))
    keys = ("structure", "ending", "original", "inspector") if action == "plan-critique" else ("voice", "image", "select")
    if action == "plan-revise":
        if not payload.strip() or critique_path is None:
            raise ContractError("CRITICS_NATIVE_OUTPUT_INVALID", action)
    elif not isinstance(payload, dict) or set(payload) != set(keys) or any(not isinstance(payload[key], str) or not payload[key].strip() for key in keys):
        raise ContractError("CRITICS_NATIVE_OUTPUT_INVALID", action)
    calls = json.loads(originals[calls_path].decode("utf-8"))
    if not isinstance(calls, list) or len(calls) != {"plan-critique": 5, "text-refine": 3, "plan-revise": 1}[action]:
        raise ContractError("CRITICS_PROVIDER_EVIDENCE_MISSING", run_name)
    contents, provider_ids = [], []
    for call in calls:
        if not isinstance(call, dict):
            raise ContractError("CRITICS_PROVIDER_EVIDENCE_INVALID", run_name)
        response = call.get("response", {})
        if not isinstance(response, dict):
            raise ContractError("CRITICS_PROVIDER_EVIDENCE_INVALID", run_name)
        choices = response.get("choices") or []
        if call.get("http_status") != 200 or response.get("model") != "deepseek-flash" or not isinstance(response.get("id"), str) or not response["id"] or not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict) or choices[0].get("finish_reason") != "stop":
            raise ContractError("CRITICS_PROVIDER_EVIDENCE_INVALID", run_name)
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
            raise ContractError("CRITICS_PROVIDER_EVIDENCE_INVALID", run_name)
        contents.append(message["content"])
        provider_ids.append(response["id"])
    if len(set(provider_ids)) != len(provider_ids):
        raise ContractError("CRITICS_PROVIDER_ID_DUPLICATED", run_name)
    simulated = [call.get("response", {}).get("simulation_status") == "SIMULATED"
                 or call.get("response", {}).get("fixture_only") is True for call in calls]
    markers = {}
    if any(simulated):
        if (not all(simulated) or receipt.get("mode") != "MOCK_ONLY"
                or receipt.get("simulation_status") != "SIMULATED" or receipt.get("fixture_only") is not True):
            raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", run_id)
        try:
            from .cnw_test_live_transport import current_session
        except ImportError:
            from cnw_test_live_transport import current_session
        session = current_session()
        if session is None or parent_run_dir is None:
            raise ContractError("MOCK_RECEIPT_CANNOT_PROVE_LIVE", run_id)
        session.validate(parent_run_dir)
        markers = {"mode": "MOCK_ONLY", "simulation_status": "SIMULATED", "fixture_only": True}
    elif receipt.get("mode") == "MOCK_ONLY" or receipt.get("fixture_only") is True:
        raise ContractError("CRITICS_SIMULATION_MARKERS_MISMATCH", run_id)
    ordered = ("structure", "ending", "original") if action == "plan-critique" else ("image", "voice", "select")
    offset = 1 if action == "plan-critique" else 0
    if action == "plan-revise":
        if payload != contents[0]:
            raise ContractError("CRITICS_RESULT_RESPONSE_MISMATCH", run_name)
    elif any(payload[key] != contents[index + offset] for index, key in enumerate(ordered)):
        raise ContractError("CRITICS_RESULT_RESPONSE_MISMATCH", run_name)
    prompts = []
    for call in calls:
        request = call.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("messages"), list):
            raise ContractError("CRITICS_REQUEST_EVIDENCE_INVALID", run_name)
        messages = request["messages"]
        if action in ("text-refine", "plan-revise") and (len(messages) != 1 or not isinstance(messages[0], dict) or messages[0].get("role") != "user"):
            raise ContractError("CRITICS_REQUEST_EVIDENCE_INVALID", run_name)
        users = [item.get("content") for item in messages if isinstance(item, dict) and item.get("role") == "user"]
        if not users or not isinstance(users[-1], str):
            raise ContractError("CRITICS_REQUEST_EVIDENCE_INVALID", run_name)
        prompts.append(users[-1])
    source = originals[input_path].decode("utf-8-sig")
    if action == "text-refine":
        templates = native_text_templates()
        expected = [templates["refine_prompt_image"].format(story=source),
                    templates["refine_prompt_voice"].format(story=source),
                    templates["choose_critic"].format(Image_refinement=payload["image"], Voice_refinement=payload["voice"])]
        if not native_prompt_dependencies_match(prompts, expected):
            raise ContractError("CRITICS_NATIVE_DEPENDENCY_MISMATCH", run_name)
    elif action == "plan-revise":
        critique = json.loads(originals[critique_path].decode("utf-8"))
        template = native_templates("storyline_template.py", {"applyQA"})["applyQA"]
        if not native_prompt_dependencies_match(prompts, [template.format(final_critic=critique, storyline=source)]):
            raise ContractError("CRITICS_NATIVE_DEPENDENCY_MISMATCH", run_name)
    else:
        # The pinned inspector returns the selected Question, not its full raw response.
        inspector = contents[4]
        start = inspector.lower().find("<answer>")
        if start >= 0:
            inspector = inspector[start + len("<answer>"):]
        pattern = r"(?ims)^\s*Question\s*:\s*(.*?)(?=^\s*(?:Why|Originality|Coherence|Interesting)\s*:|^\s*</?answer\b|\Z)"
        match = re.search(pattern, inspector)
        if not match or payload["inspector"] != match[1].strip():
            raise ContractError("CRITICS_RESULT_RESPONSE_MISMATCH", run_name)
        if any(source not in prompt for prompt in prompts):
            raise ContractError("CRITICS_NATIVE_DEPENDENCY_MISMATCH", run_name)
    files = [output, receipt_path, calls_path]
    if critique_path is not None:
        files.append(critique_path.resolve(strict=True))
    def evidence_path(path: Path) -> str:
        try:
            return path.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            return "external:" + path.as_posix()
    if any(path.read_bytes() != raw for path, raw in originals.items()):
        raise ContractError("CRITICS_EVIDENCE_CHANGED", run_id)
    return {"status": "SUCCEEDED", **markers, "action": action, "run_name": run_id,
            "run_dir": str(directory),
            "input_sha256": verified["input_sha256"].lower(), "result": payload,
            "provider_request_ids": provider_ids,
            "evidence_files": [{"path": evidence_path(path), "sha256": hashlib.sha256(originals[path]).hexdigest()} for path in files]}


def native_text_templates() -> dict[str, str]:
    """Read literal templates from the deployed pinned build without importing it."""
    return native_templates("story_template.py", {"refine_prompt_image", "refine_prompt_voice", "choose_critic"})


def native_conversation_template() -> str:
    """Read the deployed ConversationChain default; each native call starts empty."""
    path = ROOT / "runtime/envs/critics-api/Lib/site-packages/langchain/chains/conversation/prompt.py"
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "DEFAULT_TEMPLATE" for target in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and "{history}" in value and "{input}" in value:
                return value
    raise ContractError("CRITICS_NATIVE_TEMPLATES_MISSING", str(path))


def native_prompt_dependencies_match(prompts: list[str], expected: list[str]) -> bool:
    # Bare archived transport and the actual fresh ConversationChain transport
    # are each checked in full. Mixed or modified framing is never stripped.
    if prompts == expected:
        return True
    template = native_conversation_template()
    return prompts == [template.format(history="", input=prompt) for prompt in expected]


def native_templates(filename: str, wanted: set[str]) -> dict[str, str]:
    build = json.loads(PATCH_INDEX.read_text(encoding="utf-8"))["runtime_build_id"]
    path = ROOT / "runtime/patched/CritiCS" / build / "critics/setting/promptDesign" / filename
    values = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in wanted:
            values[node.targets[0].id] = ast.literal_eval(node.value)
    if set(values) != wanted:
        raise ContractError("CRITICS_NATIVE_TEMPLATES_MISSING", str(path))
    return values
