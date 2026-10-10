"""Map a CNW scene contract into the existing NK perspective route."""
from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    from .cnw_contract import ContractError
except ImportError:  # direct script execution
    from cnw_contract import ContractError


def _card_beat_descriptions(cards_markdown: str, fallback_beats: list[dict]) -> list[dict]:
    """Extract ordered, observable events from the accepted Scene Cards.

    The NK event sequence must come from the cards that were actually written,
    not from the contract goal text alone.
    """
    events: list[dict] = []
    current_scene = None
    in_beats = False
    for raw_line in cards_markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## Scene"):
            current_scene = line.lstrip("# ").strip()
            in_beats = False
        elif line.startswith("### Required beats"):
            in_beats = True
        elif in_beats and line.startswith("###"):
            in_beats = False
        elif in_beats and line.lstrip().startswith(("-", "*")):
            text = line.lstrip("-* ").strip()
            if text:
                events.append({"label": (current_scene or "SCENE") + f"-{len(events) + 1:02d}", "description": text})
    if events:
        return events
    return [{"label": beat["beat_id"], "description": beat.get("goal", "")} for beat in fallback_beats]


def build_nk_payload(contract: dict[str, Any], accepted_cards_markdown: str, accepted_cards_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    story = contract["story"]
    unit = contract["unit"]
    beats = story.get("required_beats", [])
    if not beats:
        raise ContractError("NK_EVENT_SEQUENCE_MISSING", "Scene Card has no ordered events")
    if not isinstance(accepted_cards_markdown, str) or not accepted_cards_markdown.strip():
        raise ContractError("NK_CARDS_REQUIRED", "accepted Scene Cards text is required")
    events = _card_beat_descriptions(accepted_cards_markdown, beats)
    snapshots = []
    for name in story.get("characters_in_scene", []):
        traits = story.get("nk_character_traits", {}).get(name, {})
        snapshots.append({
            "name": name,
            "traits": {
                "physiology": traits.get("physiology", []),
                "psychology": traits.get("psychology", []),
                "sociology": traits.get("sociology", []),
            },
        })
    payload = {
        "eventSequence": events,
        "perspectives": [{
            "id": f"{unit['id']}-pov-01",
            "narrator": unit["pov"],
            "eventLabel": (events[0]["label"] if events else unit["id"]),
            "eventObjective": (
                f"POV={unit['pov']}. Scene scope: {story['role_in_story']} "
                "Reflect only on the narrator's own experience and directly observable or heard events. "
                "Do not infer other characters' unspoken motives or use protected future information."
            ),
            "characterSnapshots": snapshots,
        }],
        "customPrompt": "只输出简短、可执行的 POV 边界反思；限于当前事件中的亲历、亲闻和可观察事实。不得把 reflection 当正文、补写秘密或推断旁人内心。",
    }
    return payload


def map_reflection_to_brief(brief: str, response: dict[str, Any], provider_receipt: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    perspectives = response.get("perspectives")
    if not isinstance(perspectives, list) or len(perspectives) != 1 or not isinstance(perspectives[0], dict):
        raise ContractError("NK_RESPONSE_INVALID", "expected one validated perspective")
    reflection = perspectives[0].get("reflection")
    if not isinstance(reflection, str) or not reflection.strip():
        raise ContractError("NK_RESPONSE_INVALID", "reflection is empty")
    response_hash = hashlib.sha256(json.dumps(response, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    status = provider_receipt.get("status")
    if status == "LIVE_ACCEPTED":
        required = ("request_id", "provider_request_id", "model", "finish_reason", "usage", "http_status", "validated_response_sha256", "raw_response_sha256")
        missing = [key for key in required if provider_receipt.get(key) in (None, "", {})]
        if missing or provider_receipt.get("model") != "deepseek-flash" or provider_receipt.get("finish_reason") != "stop" or provider_receipt.get("http_status") != 200:
            raise ContractError("NK_PROVIDER_RECEIPT_INVALID", ", ".join(missing) or "model/status mismatch")
        usage = provider_receipt.get("usage")
        if not isinstance(usage, dict) or not all(isinstance(usage.get(key), int) for key in ("prompt_tokens", "completion_tokens")):
            raise ContractError("NK_PROVIDER_RECEIPT_INVALID", "usage must contain prompt_tokens and completion_tokens")
        if provider_receipt["validated_response_sha256"].lower() != response_hash:
            raise ContractError("NK_PROVIDER_RESPONSE_HASH_MISMATCH", "receipt does not bind validated NK response")
    elif status == "FIXTURE_ONLY":
        if provider_receipt.get("provider_request_id"):
            raise ContractError("NK_FIXTURE_HAS_PROVIDER_ID", "offline fixture cannot claim a live provider ID")
    else:
        raise ContractError("NK_PROVIDER_RECEIPT_REQUIRED", "mapping requires LIVE_ACCEPTED evidence or an explicit offline fixture")
    section = (
        "\n\n## NK Perspective Reflection (support only)\n\n"
        f"- response_sha256: `{response_hash}`\n"
        f"- source_status: `{status}`\n"
        f"- provider_request_id: `{provider_receipt.get('provider_request_id') or 'FIXTURE_ONLY'}`\n"
        "- scope: POV-boundary reminder only; not canon and not prose\n\n"
        f"> {reflection.strip()}\n"
    )
    mapping = {
        "response_sha256": response_hash,
        "reflection_sha256": hashlib.sha256(reflection.strip().encode("utf-8")).hexdigest(),
        "brief_section": "NK Perspective Reflection (support only)",
        "source_status": status,
        "provider_request_id": provider_receipt.get("provider_request_id"),
    }
    return brief.rstrip() + section, mapping
