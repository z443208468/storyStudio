"""Offline contract checks for the CritiCS adapter; no provider request is made."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PATCH_INDEX = json.loads((ROOT / "patches" / "critics" / "PATCH_INDEX.json").read_text(encoding="utf-8"))
BUILD = ROOT / "runtime" / "patched" / "CritiCS" / PATCH_INDEX["runtime_build_id"]
PYTHON = sys.executable
sys.path.insert(0, str(BUILD))
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("DEEPSEEK_API_KEY", None)

from critics.plan import plan as plan_module
from critics.text import text as text_module
from critics.setting.chatsetting import gptsetting
from critics.setting.util import get_assistant_response


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


class Memory:
    def __init__(self):
        self.chat_memory = self
        self.messages = []

    def dict(self):
        return {"messages": self.messages}


class FakeConversation:
    def __init__(self, response: str, prompts: list[str]):
        self.response = response
        self.prompts = prompts
        self.memory = Memory()

    def predict(self, *, input: str):
        self.prompts.append(input)
        self.memory.messages = [{"content": input}, {"content": self.response}]
        return self.response


fixture_path = ROOT / "tools" / "fixtures" / "critics_offline_responses.json"
fixture_bytes = fixture_path.read_bytes()
responses = json.loads(fixture_bytes.decode("utf-8-sig"))["responses"]
require(len(responses) == 9, "EXPECTED_NINE_FIXED_ROLE_RESPONSES")
prompts: list[str] = []
call_index = 0

def fake_chatsettubg(**kwargs):
    global call_index
    response = responses[call_index]
    call_index += 1
    return {"memory": None, "conversation": FakeConversation(response, prompts)}

plan_module.chatsettubg = fake_chatsettubg
text_module.chatsettubg = fake_chatsettubg
plot = "SYNTHETIC_PLOT_MARKER: a traveler chooses which lantern to repair."
excerpt = "VOICE_INPUT_MARKER: the traveler lifted a blue lantern from the table."
with tempfile.TemporaryDirectory(dir=ROOT / "runtime" / "tmp", prefix="critics-offline-") as temp:
    os.chdir(temp)
    critique = plan_module.Critic(plot).three_critic()
    revised = plan_module.modifiedStoryline(plot, critique)
    refined = text_module.Refinement(excerpt).Two_refinement()
    os.chdir(str(ROOT))  # Release the temporary working directory before cleanup on Windows.

require(call_index == 9, "EXPECTED_ORIGINAL_5_PLUS_1_PLUS_3_CALL_SEQUENCE")
require(len(prompts) == 9, "EXPECTED_NINE_CAPTURED_PROMPTS")
require(all("SYNTHETIC_PLOT_MARKER" in prompt for prompt in prompts[:6]), "PLOT_NOT_PASSED_THROUGH_ALL_PLAN_CALLS")
require("Can the opening action reveal the plot's central choice?" in prompts[5], "LEADER_SELECTION_NOT_PASSED_TO_REVISE")
require(all("VOICE_INPUT_MARKER" in prompts[index] for index in (6, 7)), "IMAGE_OR_VOICE_PROMPT_MISSING_REAL_INPUT")
require("IMAGE_RESULT" in prompts[8] and "VOICE_RESULT" in prompts[8], "LEADER_DID_NOT_RECEIVE_BOTH_CRITIQUE_RESULTS")
require(critique["inspector"] == "Can the opening action reveal the plot's central choice?", "LEADER_QUESTION_NOT_PARSED")
require(refined["select"].startswith("LEADER_CHOICE"), "TEXT_LEADER_RESULT_NOT_RETURNED")
empty_response = FakeConversation("", [])
empty_response.memory.messages = [{"content": ""}]
try:
    get_assistant_response(empty_response)
except ValueError as error:
    require(str(error) == "EMPTY_OR_NON_TEXT_MODEL_RESPONSE", "EMPTY_RESPONSE_NOT_REJECTED")
else:
    raise AssertionError("EMPTY_MODEL_RESPONSE_WAS_ACCEPTED")
try:
    plan_module.Critic(plot).split_personas("Expert 1.\nAge 42\nExpert 2.\nExpert 3.\nLeader.")
except ValueError as error:
    require(str(error).startswith("PERSONA_"), "PERSONA_PARSE_ERROR_NOT_EXPLICIT")
else:
    raise AssertionError("MALFORMED_PERSONA_WAS_ACCEPTED")

bad_prompts: list[str] = []
def bad_chatsettubg(**kwargs):
    return {"conversation": FakeConversation("No selected question was returned.", bad_prompts)}
plan_module.chatsettubg = bad_chatsettubg
try:
    plan_module.Critic(plot).inspector_gpt(
        persona_type="Leader",
        first_critique="<question>\nQuestion :\nfirst?\nWhy: reason\n<question/>",
        second_critique="<question>\nQuestion :\nsecond?\nWhy: reason\n<question/>",
        third_critique="<question>\nQuestion :\nthird?\nWhy: reason\n<question/>",
    )
except ValueError as error:
    require(str(error) == "INSPECTOR_QUESTION_PARSE_FAILED", "LEADER_PARSE_ERROR_NOT_EXPLICIT")
else:
    raise AssertionError("MALFORMED_LEADER_OUTPUT_WAS_ACCEPTED")
plan_module.chatsettubg = fake_chatsettubg

# Check the actual adapter constructor contract without allowing network access.
constructed = {}
class FakeModel:
    def __init__(self, **kwargs):
        constructed.update(kwargs)
class FakeChain:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.memory = Memory()
        self.predict = lambda **call: "unused"

original_model, original_chain = gptsetting.ChatOpenAI, gptsetting.ConversationChain
gptsetting.ChatOpenAI, gptsetting.ConversationChain = FakeModel, FakeChain
os.environ["DEEPSEEK_API_KEY"] = "offline-placeholder-never-sent"
try:
    gptsetting.chatsettubg(stop=["<question/>"])
finally:
    os.environ.pop("DEEPSEEK_API_KEY", None)
    gptsetting.ChatOpenAI, gptsetting.ConversationChain = original_model, original_chain
require(constructed.get("model") == "deepseek-flash", "MODEL_NOT_EXPLICIT_FLASH")
require(constructed.get("base_url") == "https://api.deepseek.com/v1", "HOST_NOT_OFFICIAL")
require(constructed.get("max_retries") == 0, "SDK_RETRIES_NOT_DISABLED")
require(constructed.get("extra_body") == {"thinking": {"type": "disabled"}}, "THINKING_MODE_NOT_EXPLICIT")
require(constructed.get("stop") == ["<question/>"] and constructed.get("timeout") == 180, "CALL_OPTIONS_NOT_PRESERVED")
for kwargs in ({"model_name": "gpt-4"}, {"completion": "completion_mode"}):
    try:
        gptsetting.chatsettubg(**kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError("LEGACY_OR_NON_FLASH_ROUTE_DID_NOT_FAIL_CLOSED")

bridge_spec = importlib.util.spec_from_file_location("critics_bridge", ROOT / "tools" / "critics_bridge.py")
bridge = importlib.util.module_from_spec(bridge_spec)
bridge_spec.loader.exec_module(bridge)
try:
    bridge.project_path(str(ROOT.parent / "outside.txt"))
except ValueError as error:
    require(str(error) == "PATH_OUTSIDE_PROJECT_ROOT", "UNEXPECTED_PATH_GUARD_ERROR")
else:
    raise AssertionError("OUTSIDE_PROJECT_PATH_ACCEPTED")
try:
    bridge.project_path(".env")
except ValueError as error:
    require(str(error) == "INPUT_MUST_BE_UNDER_CANGQI_WORKSPACE_OR_RUNS", "SENSITIVE_INPUT_SCOPE_NOT_ENFORCED")
else:
    raise AssertionError("SENSITIVE_CONFIG_PATH_ACCEPTED_AS_STORY_INPUT")
symlink_output_case_executed = False
with tempfile.TemporaryDirectory(dir=ROOT / "runtime" / "tmp", prefix="critics-path-guard-") as guard_root:
    guard_root = Path(guard_root)
    runs = guard_root / "runs"
    runs.mkdir()
    bridge.ROOT = guard_root
    existing = runs / "existing"
    existing.mkdir()
    try:
        bridge.create_run_directory(str(existing))
    except ValueError as error:
        require(str(error) == "RUN_DIR_MUST_BE_NEW", "EXISTING_RUN_DIR_ACCEPTED")
    else:
        raise AssertionError("EXISTING_RUN_DIR_ACCEPTED")
    fresh = bridge.create_run_directory(str(runs / "fresh"))
    outside = guard_root / "outside.txt"
    (fresh / "critique.json").symlink_to(outside)
    require((fresh / "critique.json").is_symlink(), "SYMLINK_FIXTURE_NOT_CREATED")
    symlink_output_case_executed = True
    try:
        bridge.write_json(fresh / "critique.json", {"safe": False}, fresh)
    except ValueError as error:
        require(str(error) == "OUTPUT_PATH_NOT_FRESH_INSIDE_RUN_DIR", "SYMLINK_OUTPUT_NOT_REJECTED")
    else:
        raise AssertionError("SYMLINK_OUTPUT_NOT_REJECTED")
    require(not outside.exists(), "SYMLINK_TARGET_WAS_WRITTEN")
    bridge.ROOT = ROOT

try:
    bridge.configure_provider()
except RuntimeError as error:
    require(str(error) == "DEEPSEEK_API_KEY_REQUIRED", "MISSING_KEY_DID_NOT_FAIL_CLOSED")
else:
    raise AssertionError("MISSING_KEY_WAS_ACCEPTED")
os.environ["DEEPSEEK_API_KEY"] = "offline-placeholder-never-sent"
bridge.configure_provider()
os.environ.pop("DEEPSEEK_API_KEY", None)
require(os.environ.get("LANGCHAIN_TRACING_V2") == "false" and os.environ.get("LANGSMITH_TRACING") == "false", "TRACING_NOT_DISABLED")

record = {
    "status": "PASS",
    "python": sys.version.split()[0],
    "fixed_response_fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest().upper(),
    "calls": [
        {"sequence": i + 1, "prompt_sha256": sha(prompt), "prompt_length": len(prompt)}
        for i, prompt in enumerate(prompts)
    ],
    "checks": {
        "original_five_plan_roles": True,
        "leader_selection_reaches_modified_storyline": True,
        "image_and_voice_receive_original_excerpt": True,
        "text_leader_receives_both_role_results": True,
        "all_model_construction_is_explicit_flash": True,
        "legacy_routes_fail_closed": True,
        "project_path_boundary_enforced": True,
    "fresh_run_directory_and_symlink_outputs_rejected": True,
    "symlink_output_case_executed": symlink_output_case_executed,
        "sensitive_config_input_rejected": True,
        "malformed_persona_and_leader_fail_closed": True,
        "empty_model_response_fails_closed": True,
        "missing_key_fails_closed": True,
        "tracing_disabled_for_production_runs": True,
        "provider_calls": 0,
    },
    "outputs": {
        "critic_keys": sorted(critique),
        "modified_plot_sha256": sha(revised),
        "text_refinement_keys": sorted(refined),
        "leader_result_sha256": sha(refined["select"]),
    },
}
out = ROOT / "evidence" / "critics" / "offline-check.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, ensure_ascii=False, indent=2))
