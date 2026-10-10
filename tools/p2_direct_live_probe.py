"""Run one harmless, bounded DeepSeek Flash chat request and record private evidence."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "p2-04-live-20261010"
OUTPUT = ROOT / "runs" / RUN_ID
if OUTPUT.exists():
    raise SystemExit("LIVE_RUN_ALREADY_EXISTS")
if not os.environ.get("DEEPSEEK_API_KEY"):
    raise SystemExit("DEEPSEEK_API_KEY_REQUIRED")

spec = importlib.util.spec_from_file_location("p2_cost_guard", ROOT / "tools" / "p2_cost_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

from openai import OpenAI

request_id = "direct-" + uuid.uuid4().hex
cap_in, cap_out = 2048, 128


class Args:
    pass


reserve = Args()
reserve.request_id = request_id
reserve.run_id = RUN_ID
reserve.purpose = "harmless plain-text provider connectivity check"
reserve.input_token_cap = cap_in
reserve.output_token_cap = cap_out
guard.command_reserve(reserve)

OUTPUT.mkdir(parents=True, exist_ok=False)
prompt = "Reply exactly with: P2 live path ready."
try:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com/v1",
        max_retries=0,
        timeout=45,
    )
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=cap_out,
        extra_body={"thinking": {"type": "disabled"}},
    )
    choice = response.choices[0]
    content = choice.message.content or ""
    usage = response.usage
    if response.model != "deepseek-flash" or choice.finish_reason != "stop" or not content.strip():
        raise RuntimeError("DIRECT_PROVIDER_RESULT_INVALID")
    input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    output_tokens = getattr(usage, "completion_tokens", None) if usage else None
    settle = Args()
    settle.request_id = request_id
    settle.provider_request_id = response.id
    settle.returned_model = response.model
    settle.finish_reason = choice.finish_reason
    settle.input_tokens = input_tokens
    settle.output_tokens = output_tokens
    guard.command_settle(settle)
    raw = {
        "request": {"model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1", "prompt": prompt},
        "response": response.model_dump(mode="json"),
    }
    (OUTPUT / "direct-response.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "SUCCEEDED",
        "run_id": RUN_ID,
        "provider_request_id": response.id,
        "requested_model": "deepseek-flash",
        "returned_model": response.model,
        "finish_reason": choice.finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "response_chars": len(content),
        "evidence": str(OUTPUT / "direct-response.json"),
    }))
except Exception as error:
    settle = Args()
    settle.request_id = request_id
    settle.provider_request_id = None
    settle.returned_model = None
    settle.finish_reason = None
    settle.input_tokens = None
    settle.output_tokens = None
    guard.command_settle(settle)
    (OUTPUT / "direct-response-error.json").write_text(
        json.dumps({"status": "FAILED_OR_UNKNOWN", "request_id": request_id, "error_type": type(error).__name__}, indent=2) + "\n",
        encoding="utf-8",
    )
    raise
