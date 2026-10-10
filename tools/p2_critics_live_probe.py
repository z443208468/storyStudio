"""Run one bounded-input live ConversationChain call through CritiCS chatsettubg."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid
import httpx

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "p2-04-live-20261010"
OUTPUT = ROOT / "runs" / RUN_ID
if not OUTPUT.is_dir():
    raise SystemExit("LIVE_RUN_DIRECTORY_MISSING")
if not os.environ.get("DEEPSEEK_API_KEY"):
    raise SystemExit("DEEPSEEK_API_KEY_REQUIRED")

spec = importlib.util.spec_from_file_location("p2_cost_guard", ROOT / "tools" / "p2_cost_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
index = json.loads((ROOT / "patches" / "critics" / "PATCH_INDEX.json").read_text(encoding="utf-8"))
build = ROOT / "runtime" / "patched" / "CritiCS" / index["runtime_build_id"]
sys.path.insert(0, str(build))

from langchain_core.callbacks import BaseCallbackHandler
from critics.setting.chatsetting.gptsetting import chatsettubg

request_id = "critics-" + uuid.uuid4().hex
cap_in, cap_out = 10000, 8192


class Args:
    pass


reserve = Args()
reserve.request_id = request_id
reserve.run_id = RUN_ID
reserve.purpose = "single short CritiCS chatsettubg ConversationChain live call"
reserve.input_token_cap = cap_in
reserve.output_token_cap = cap_out
guard.command_reserve(reserve)


class Capture(BaseCallbackHandler):
    llm_result = None

    def on_llm_end(self, response, **kwargs):
        self.llm_result = response


prompt = "Reply exactly with: CritiCS live path ready."
transport_record = {}
original_send = httpx.Client.send


def capture_provider_response(client, request, *args, **kwargs):
    response = original_send(client, request, *args, **kwargs)
    if request.url.host == "api.deepseek.com" and request.url.path == "/v1/chat/completions":
        response.read()
        payload = response.json()
        choices = payload.get("choices") or []
        choice = choices[0] if choices else {}
        usage_payload = payload.get("usage") or {}
        transport_record.update({
            "host": "https://api.deepseek.com/v1",
            "status": response.status_code,
            "provider_request_id": payload.get("id"),
            "returned_model": payload.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "usage": {
                "input_tokens": usage_payload.get("prompt_tokens"),
                "output_tokens": usage_payload.get("completion_tokens"),
            },
        })
        (OUTPUT / "critics-provider-response.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return response


httpx.Client.send = capture_provider_response
try:
    configured = chatsettubg()
    capture = Capture()
    result = configured["conversation"].invoke({"input": prompt}, config={"callbacks": [capture]})
    messages = configured["memory"].chat_memory.messages
    assistant = messages[-1] if messages else None
    text = str(result.get("response", ""))
    metadata = getattr(assistant, "response_metadata", {}) or {}
    usage = metadata.get("token_usage") or {}
    usage_meta = getattr(assistant, "usage_metadata", None) or {}
    input_tokens = usage.get("prompt_tokens", usage_meta.get("input_tokens"))
    output_tokens = usage.get("completion_tokens", usage_meta.get("output_tokens"))
    finish_reason = metadata.get("finish_reason")
    provider_id = transport_record.get("provider_request_id") or metadata.get("id")
    returned_model = transport_record.get("returned_model") or metadata.get("model_name") or metadata.get("model")
    input_tokens = transport_record.get("usage", {}).get("input_tokens", input_tokens)
    output_tokens = transport_record.get("usage", {}).get("output_tokens", output_tokens)
    finish_reason = transport_record.get("finish_reason") or finish_reason
    if capture.llm_result is not None:
        llm_output = capture.llm_result.llm_output or {}
        callback_usage = llm_output.get("token_usage") or {}
        input_tokens = input_tokens if input_tokens is not None else callback_usage.get("prompt_tokens")
        output_tokens = output_tokens if output_tokens is not None else callback_usage.get("completion_tokens")
        returned_model = returned_model or llm_output.get("model_name")
        generations = capture.llm_result.generations or []
        generation = generations[0][0] if generations and generations[0] else None
        generation_info = getattr(generation, "generation_info", {}) or {}
        finish_reason = finish_reason or generation_info.get("finish_reason")
        provider_id = provider_id or generation_info.get("id")

    if (transport_record.get("status") != 200 or not provider_id
            or returned_model != "deepseek-flash" or finish_reason != "stop"
            or input_tokens is None or output_tokens is None):
        raise RuntimeError("CRITICS_PROVIDER_RESULT_METADATA_INVALID")

    settle = Args()
    settle.request_id = request_id
    settle.provider_request_id = provider_id
    settle.returned_model = returned_model
    settle.finish_reason = finish_reason
    settle.input_tokens = input_tokens
    settle.output_tokens = output_tokens
    guard.command_settle(settle)

    evidence = {
        "request": {"model": "deepseek-flash", "base_url": "https://api.deepseek.com/v1", "prompt": prompt},
        "response": {
            "output": text,
            "memory_message_count": len(messages),
            "provider_request_id": provider_id,
            "returned_model": returned_model,
            "finish_reason": finish_reason,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
            "response_metadata": metadata,
            "transport": transport_record,
        },
    }
    (OUTPUT / "critics-conversation-response.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    if not text.strip() or len(messages) < 2:
        raise RuntimeError("CRITICS_CONVERSATION_MEMORY_OR_OUTPUT_MISSING")
    print(json.dumps({
        "status": "SUCCEEDED",
        "run_id": RUN_ID,
        "provider_request_id": provider_id,
        "requested_model": "deepseek-flash",
        "returned_model": returned_model,
        "finish_reason": finish_reason,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "memory_message_count": len(messages),
        "response_chars": len(text),
        "evidence": str(OUTPUT / "critics-conversation-response.json"),
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
    (OUTPUT / "critics-conversation-error.json").write_text(
        json.dumps({"status": "FAILED_OR_UNKNOWN", "request_id": request_id, "error_type": type(error).__name__}, indent=2) + "\n",
        encoding="utf-8",
    )
    raise
finally:
    httpx.Client.send = original_send
