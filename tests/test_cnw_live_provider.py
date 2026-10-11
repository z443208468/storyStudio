from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

import httpx

from tools import cnw_live_provider, cnw_w10_policy, p2_cost_guard

ROOT = Path(__file__).resolve().parents[1]


class LiveProviderTransportTests(unittest.TestCase):
    @staticmethod
    def input_hash(messages):
        raw = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def setUp(self):
        self.run_id = f"W10-TRANSPORT-TEST-{uuid.uuid4().hex[:8]}"
        self.run = ROOT / "runs" / self.run_id
        self.run.mkdir(parents=True)
        contract_sha = cnw_w10_policy.CONTRACT_SHA256
        (self.run / "run_state.json").write_text(json.dumps({
            "schema_version": "cnw_run_state_v1", "run_id": self.run_id, "mode": "live", "unit_kind": "scene",
            "fixture_only": False, "contract_sha256": contract_sha, "provider_requests": [],
            "w10_contract_preflight": {"status": "ACCEPTED", "scope": "W10_SINGLE_SCENE",
                "contract_sha256": contract_sha, "source_script_sha256": cnw_w10_policy.SOURCE_SCRIPT_SHA256,
                "evidence_sha256": cnw_w10_policy.PREFLIGHT_EVIDENCE_SHA256,
                "controller_acceptance_ref": cnw_w10_policy.PREFLIGHT_REF,
                "provider_call_authorized": True},
            "stages": {"lens5": {"status": "READY_FOR_EXECUTION"},
                       "verifier3": {"status": "READY_FOR_EXECUTION"},
                       "plot": {"status": "READY_FOR_EXECUTION"}},
        }), encoding="utf-8")
        self.ledger_dir = ROOT / "tests" / "_isolated_workspace"
        self.ledger_dir.mkdir(exist_ok=True)
        self.ledger = self.ledger_dir / f"{self.run_id}-ledger.json"
        self.ledger.write_text(json.dumps({"requests": [], "limit": "10"}), encoding="utf-8")
        self.old_ledger = p2_cost_guard.LEDGER
        p2_cost_guard.LEDGER = self.ledger

    def tearDown(self):
        p2_cost_guard.LEDGER = self.old_ledger
        shutil.rmtree(self.run, ignore_errors=True)
        self.ledger.unlink(missing_ok=True)
        self.ledger.with_suffix(".lock").unlink(missing_ok=True)

    def transport(self, content="A complete stage result.", usage=None):
        def send(url, body, request_id, key):
            self.assertEqual(url, cnw_live_provider.API_URL)
            self.assertNotIn("api_key", body)
            self.assertEqual(key, "test-secret-never-sent-by-mock")
            payload = {"id": f"provider-{request_id}", "model": cnw_live_provider.MODEL,
                "choices": [{"message": {"content": content, "reasoning_content": "private chain"}, "finish_reason": "stop"}],
                "usage": usage or {"prompt_tokens": 123, "completion_tokens": 41}}
            return httpx.Response(200, json=payload, request=httpx.Request("POST", url))
        return send

    def test_one_call_is_raw_hash_bound_and_cost_settled_without_key_artifacts(self):
        secret = "test-secret-never-sent-by-mock"
        source = "frozen prompt"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": secret}):
            content, receipt = cnw_live_provider.complete(
                self.run, stage="lens5", role_id="canon",
                messages=[{"role": "user", "content": source}],
                input_sha256=self.input_hash([{"role": "user", "content": source}]),
                input_token_cap=500, output_token_cap=250, transport=self.transport())
        self.assertEqual(content, "A complete stage result.")
        self.assertEqual(receipt["lens_id"], "canon")
        self.assertEqual(receipt["mode"], "MOCK_ONLY")
        self.assertTrue(receipt["fixture_only"])
        self.assertEqual(receipt["ledger_settlement"]["status"], "SETTLED")
        raw = self.run / receipt["raw_response_path"]
        self.assertEqual(hashlib.sha256(raw.read_bytes()).hexdigest(), receipt["raw_response_sha256"])
        request_file = raw.parent / "request.json"
        self.assertNotIn(secret, request_file.read_text(encoding="utf-8"))
        self.assertNotIn(secret, raw.read_text(encoding="utf-8"))
        self.assertNotIn("private chain", raw.read_text(encoding="utf-8"))
        rows = json.loads(self.ledger.read_text(encoding="utf-8"))["requests"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "SETTLED")
        self.assertEqual(rows[0]["usage"], {"input_tokens": 123, "output_tokens": 41})
        state = json.loads((self.run / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(len(state["provider_requests"]), 1)
        self.assertEqual(state["provider_requests"][0]["request_id"], receipt["request_id"])

    def test_transport_timeout_is_settled_unknown_not_zero_and_not_retried(self):
        calls = []
        def timeout(*_args):
            calls.append(1)
            raise TimeoutError("offline mock")
        source = "frozen prompt"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret-never-sent-by-mock"}):
            with self.assertRaisesRegex(Exception, "LIVE_PROVIDER_OUTCOME_UNKNOWN"):
                cnw_live_provider.complete(self.run, stage="verifier3", role_id="verifier_1",
                    messages=[{"role": "user", "content": source}],
                    input_sha256=self.input_hash([{"role": "user", "content": source}]),
                    input_token_cap=500, output_token_cap=250, transport=timeout)
        self.assertEqual(len(calls), 1)
        rows = json.loads(self.ledger.read_text(encoding="utf-8"))["requests"]
        self.assertEqual(rows[0]["status"], "UNKNOWN_NOT_ZERO")
        state = json.loads((self.run / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["provider_attempts"][0]["status"], "OUTCOME_UNKNOWN")
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret-never-sent-by-mock"}):
            with self.assertRaisesRegex(Exception, "LIVE_STAGE_RETRY_REQUIRES_CONTROLLER_REVIEW"):
                cnw_live_provider.complete(self.run, stage="verifier3", role_id="verifier_1",
                    messages=[{"role": "user", "content": source}],
                    input_sha256=self.input_hash([{"role": "user", "content": source}]),
                    input_token_cap=500, output_token_cap=250, transport=timeout)
        self.assertEqual(len(calls), 1)

    def test_usage_above_reserved_token_caps_is_charged_and_blocks_acceptance(self):
        source = "frozen plot packet"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret-never-sent-by-mock"}):
            with self.assertRaisesRegex(Exception, "LIVE_PROVIDER_BUDGET_EXCEEDED"):
                cnw_live_provider.complete(
                    self.run, stage="plot", messages=[{"role": "user", "content": source}],
                    input_sha256=self.input_hash([{"role": "user", "content": source}]),
                    input_token_cap=100, output_token_cap=25,
                    transport=self.transport(usage={"prompt_tokens": 123, "completion_tokens": 41}))
        rows = json.loads(self.ledger.read_text(encoding="utf-8"))["requests"]
        self.assertEqual(rows[0]["status"], "SETTLED_OVER_BUDGET")
        self.assertEqual(rows[0]["usage"], {"input_tokens": 123, "output_tokens": 41})
        self.assertGreater(float(rows[0]["estimated_actual_cny"]), 0)
        self.assertEqual(rows[0]["budget_exceeded"]["token_caps"], True)
        state = json.loads((self.run / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["provider_attempts"][0]["status"], "SETTLED_OVER_BUDGET")
        self.assertEqual(state["provider_requests"], [])
    def test_validated_provider_output_closes_only_its_ready_stage(self):
        secret = "test-secret-never-sent-by-mock"
        source = "frozen plot packet"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": secret}):
            content, _ = cnw_live_provider.complete(
                self.run, stage="plot", messages=[{"role": "user", "content": source}],
                input_sha256=self.input_hash([{"role": "user", "content": source}]),
                input_token_cap=500, output_token_cap=250, transport=self.transport())
        with self.assertRaisesRegex(Exception, "LIVE_MOCK_PROVIDER_ACCEPTANCE_FORBIDDEN"):
            cnw_live_provider.accept_validated_stage(self.run, stage="plot", content=content,
                validation={"status": "ROLE_OUTPUT_VALID"})
        state = json.loads((self.run / "run_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["stages"]["plot"]["status"], "READY_FOR_EXECUTION")
        self.assertNotIn("artifact", state["stages"]["plot"])

    def test_stage_acceptance_cannot_replace_receipted_provider_output(self):
        source = "frozen plot packet"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret-never-sent-by-mock"}):
            cnw_live_provider.complete(
                self.run, stage="plot", messages=[{"role": "user", "content": source}],
                input_sha256=self.input_hash([{"role": "user", "content": source}]),
                input_token_cap=500, output_token_cap=250, transport=self.transport())
        with self.assertRaisesRegex(Exception, "LIVE_MOCK_PROVIDER_ACCEPTANCE_FORBIDDEN"):
            cnw_live_provider.accept_validated_stage(self.run, stage="plot", content="changed output",
                validation={"status": "ROLE_OUTPUT_VALID"})

    def test_request_hash_must_bind_the_serialized_messages(self):
        source = "frozen plot packet"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret-never-sent-by-mock"}):
            with self.assertRaisesRegex(Exception, "LIVE_REQUEST_INVALID"):
                cnw_live_provider.complete(
                    self.run, stage="plot", messages=[{"role": "user", "content": source}],
                    input_sha256=hashlib.sha256(source.encode()).hexdigest(),
                    input_token_cap=500, output_token_cap=250, transport=self.transport())

    def test_explicitly_disabled_provider_call_is_blocked_before_reservation(self):
        state_path = self.run / "run_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["w10_contract_preflight"]["provider_call_authorized"] = False
        state_path.write_text(json.dumps(state), encoding="utf-8")
        ledger_before = self.ledger.read_bytes()
        source = "frozen plot packet"
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(Exception, "LIVE_STAGE_NOT_AUTHORIZED_OR_READY"):
                cnw_live_provider.complete(self.run, stage="plot",
                    messages=[{"role": "user", "content": source}],
                    input_sha256=self.input_hash([{"role": "user", "content": source}]),
                    input_token_cap=500, output_token_cap=250,
                    transport=self.transport())
        self.assertEqual(self.ledger.read_bytes(), ledger_before)
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8"))[
            "w10_contract_preflight"]["provider_call_authorized"], False)


if __name__ == "__main__":
    unittest.main()
