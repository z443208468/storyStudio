"""Real V2 production consumers with fictional signatures, HTTP and accounting.

The temporary verifier is not installed as a production trust root. Every
captured HTTP reply is SIMULATED; no complete Live acceptance is claimed.
"""
import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from functools import wraps
from contextlib import contextmanager
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests import test_cnw_early_e2e as early, test_p2_cost_guard as fees
from tools import cnw_live_authorization as auth, cnw_runner as runner
from tools import cnw_w10_policy as policy, cnw_recovery as recovery, cost_guard, cnw_live_provider
from tools.cnw_contract import ContractError


def verification_expiry_clock(terms):
    """Deterministic clock only; signatures and binding consumers stay real."""
    end = datetime.fromisoformat(terms["expires_at"])
    class VerificationClock(datetime):
        observations = []
        @classmethod
        def now(cls, tz=None):
            value = end - timedelta(seconds=1) if not cls.observations else end
            cls.observations.append(value.isoformat())
            return value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
    return VerificationClock


class LiveAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = early.EarlyCNWE2EGateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fees = fees.CampaignLimitTests()
        self.fees.setUp()
        self.addCleanup(self.fees.doCleanups)
        # The transport session owns project, ledger, pricing and slot paths
        # through this one live TemporaryDirectory, not unrelated global paths.
        owned = self.fixture.temp_root / "fictional-account"
        owned.mkdir()
        for attribute, name in (("config", "CONFIG"), ("pricing", "PRICING")):
            previous = getattr(self.fees, attribute)
            current = owned / previous.name
            current.write_bytes(previous.read_bytes())
            setattr(self.fees, attribute, current)
            binding = patch.object(cost_guard.accounting, name, current)
            binding.start(); self.addCleanup(binding.stop)
        self.fees.ledger = owned / "ledger.json"
        binding = patch.object(cost_guard.accounting, "LEDGER", self.fees.ledger)
        binding.start(); self.addCleanup(binding.stop)
        self.root = self.fixture.project
        self.contract = self.root / "contracts/ADAPT-HINGE-01.json"
        self.run_id = "SIGNED-ADAPT-RUN"
        self.run = self.root / "runs" / self.run_id
        self.keys = {"fictional-controller": os.urandom(32), "fictional-owner": os.urandom(32)}
        keys = self.keys
        class TestOnlyVerifier:
            def verify(self, signer, message, signature):
                return signer == "fictional-controller" and hmac.compare_digest(signature, hmac.digest(keys[signer], message, "sha256"))
            def verify_owner_authorization(self, signer, message, signature):
                return signer == "fictional-owner" and hmac.compare_digest(signature, hmac.digest(keys[signer], message, "sha256"))
        self.verifier = TestOnlyVerifier()
        self.trust = patch.object(policy, "_deployment_attestation_verifier", return_value=self.verifier)
        self.trust.start(); self.addCleanup(self.trust.stop)
        self.http = []
        def reply(url, **kwargs):
            self.http.append({"mode": "MOCK_ONLY", "simulation_status": "SIMULATED", "url": url, "body": kwargs["json"]})
            payload = {"id": "SIMULATED-HTTP-" + str(len(self.http)), "model": runner.MODEL,
                "simulation_status": "SIMULATED", "fixture_only": True,
                "choices": [{"finish_reason": "stop", "message": {"content": self.fixture._outputs()["plot"]}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
            return SimpleNamespace(status_code=200, json=lambda: payload)
        self.network = patch.object(runner.httpx, "post", side_effect=reply)
        self.network.start(); self.addCleanup(self.network.stop)
        self.key = patch.dict(os.environ, {"DEEPSEEK_API_KEY": "MOCK_ONLY_NOT_A_REAL_CREDENTIAL_0123456789"})
        self.key.start(); self.addCleanup(self.key.stop)
        self.sign()

    def signed(self, payload, signer, filename):
        path = self.root / "08_review" / filename
        signature = hmac.digest(self.keys[signer], policy._canonical_bytes(payload), "sha256")
        path.write_bytes(policy._canonical_bytes({"schema_version": "cnw_signed_controller_attestation_v1",
            "signer_id": signer, "payload": payload, "signature_base64": base64.b64encode(signature).decode()}))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    def sign(self, *, terms=None, request=None):
        request = request or auth.build_request(self.root, self.contract, run_id=self.run_id)
        now = datetime.now(timezone.utc)
        self.terms = terms or {"not_before": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(), "max_requests": 4,
            "max_input_tokens": 100000, "max_output_tokens": 8000,
            "limit_cny": "1.000000", "stages": ["plot"], "roles": {"plot": ["plot_agent"]}}
        controller = self.signed(request["controller_payload"], "fictional-controller", "controller-test-only.json")
        owner = self.signed({"purpose": "CNW_OWNER_LIVE_FEE_AUTHORIZATION", "decision": "AUTHORIZE",
            "bindings": request["bindings"], "identity_sha256": request["identity_sha256"],
            "implementation_sha256": request["implementation_sha256"],
            "provider": request["provider"], "cost_policy": request["cost_policy"], "terms": self.terms},
            "fictional-owner", "owner-test-only.json")
        path = auth.authorization_path(self.root, self.run_id)
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(policy._canonical_bytes({"schema_version": auth.SCHEMA, "controller": controller,
            "owner": owner, "terms": self.terms}))
        self.bundle = path
        return request

    def create(self):
        return runner.produce(SimpleNamespace(mode="live", unit="scene", work_id="ADAPT-HINGE-01",
            contract=str(self.contract), project_root=str(self.root), run_id=self.run_id, create_only=True))

    def test_signed_pre_run_and_real_existing_run_have_same_identity_without_provider(self):
        before = auth.build_request(self.root, self.contract, run_id=self.run_id)
        self.create()
        with patch.object(auth.cnw_project, "_compute_contract_preflight",
                wraps=auth.cnw_project._compute_contract_preflight) as compute:
            self.assertEqual(before, auth.build_request(self.root, self.contract, run_id=self.run_id))
        self.assertEqual(compute.call_count, 2)  # Real report's before/after checks.
        self.assertTrue(all(call.kwargs["existing_run"] is True for call in compute.call_args_list))
        grant = auth.require_run_authorization(self.run, stage="plot")
        self.assertEqual(grant["status"], "LIVE_AND_FEES_AUTHORIZED")
        self.assertEqual(runner.load_state(self.run)["provider_requests"], [])
        self.assertEqual(self.http, [])
        self.assertFalse(self.fees.ledger.exists())
        self.assertEqual(cnw_live_provider.verify_run_preflight(self.run)["run_id"], self.run_id)

    def test_existing_run_rejects_identity_and_provider_drift(self):
        self.create()
        state_path = self.run / "run_state.json"
        original = state_path.read_bytes()
        cases = {"run_id": "OTHER-RUN", "source_identity": {"source_id": "foreign"},
            "provider_config_sha256": "0" * 64, "workflow_template_sha256": "0" * 64}
        for field, value in cases.items():
            changed = json.loads(original)
            changed[field] = value
            try:
                state_path.write_bytes(policy._canonical_bytes(changed))
                with self.subTest(field=field), self.assertRaises(ContractError):
                    auth.build_request(self.root, self.contract, run_id=self.run_id)
            finally:
                state_path.write_bytes(original)
        with patch.object(runner, "MODEL", "foreign-model"), self.assertRaisesRegex(
                ContractError, "LIVE_AUTHORIZATION_PROVIDER_MISMATCH"):
            auth.build_request(self.root, self.contract, run_id=self.run_id)
        self.assertEqual(state_path.read_bytes(), original)
        self.assertEqual(self.http, [])
        self.assertFalse(self.fees.ledger.exists())

    def test_verification_expiry_rejects_chapter_before_slot_or_reservation(self):
        self.create()
        from tools import cnw_request_identity
        request = cnw_request_identity.expected_requests(self.run, stage="plot", role_id="plot_agent")[0]
        original = (self.run / "run_state.json").read_bytes()
        observations = []
        for entry in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
            clock = verification_expiry_clock(self.terms)
            with self.subTest(entry=entry.__name__), patch.object(auth, "datetime", clock), \
                    patch.object(cost_guard.accounting, "provider_slot",
                        side_effect=AssertionError("expired grant cannot open slot")), \
                    self.assertRaisesRegex(ContractError, "LIVE_GRANT_EXPIRED"):
                entry(self.run, **request)
            self.assertEqual(len(clock.observations), 2)
            observations.append({"entry": entry.__name__, "clock": clock.observations})
        self.assertEqual((self.run / "run_state.json").read_bytes(), original)
        self.assertEqual(self.http, [])
        self.assertFalse(self.fees.ledger.exists())
        target = os.environ.get("CNW_LIVE_GRANT_TEST_EVIDENCE")
        if target:
            Path(target + ".chapter_verification_expiry.json").write_text(json.dumps({
                "simulation_status": "SIMULATED", "real_provider_calls": 0,
                "observations": observations, "unchanged_run_state_sha256": hashlib.sha256(original).hexdigest(),
                "synthetic_reservations": 0, "actual_transport_calls": self.http}, indent=2), encoding="utf-8")

    def test_archived_simulated_receipt_cannot_escape_owned_context(self):
        self.create()
        state = runner.load_state(self.run)
        state["provider_attempts"] = [{"stage": "plot", "status": "INVALIDATED_AFTER_INPUT_CHANGE",
            "prior_receipt": {"stage": "plot", "mode": "MOCK_ONLY", "fixture_only": True,
                              "simulation_status": "SIMULATED"}}]
        runner.save_state(self.run, state)
        with self.assertRaisesRegex(ContractError, "LIVE_SIMULATED_HISTORY_FORBIDDEN"):
            auth.require_run_authorization(self.run, stage="plot")
        self.assertEqual(self.http, [])
        self.assertFalse(self.fees.ledger.exists())

    def test_disabled_auxiliary_cannot_use_signed_hook_scope(self):
        terms = self.full_terms()
        terms["stages"].append("support_hook")
        terms["roles"]["support_hook"] = ["nk_pov"]
        self.sign(terms=terms)
        self.create()
        runner._persist_stage(self.run, "scene_cards", "artifacts/scene_cards.md",
                              "## Scene 1\n### Required beats\n- Ada repairs the bell.\n")
        with self.assertRaisesRegex(ContractError, "LIVE_AUXILIARY_DISABLED"):
            auth.require_run_authorization(self.run, stage="support_hook")
        self.assertEqual(self.http, [])
        self.assertFalse(self.fees.ledger.exists())

    def test_enabled_auxiliary_grants_bind_parent_material_action_and_shared_fees(self):
        # Targeted authorization fixture: materialize only the prerequisites
        # needed to inspect each auxiliary boundary; this is not an E2E run.
        self.fixture.contract["integrations"] = {"nk": "ENABLED", "critics": "ENABLED"}
        self.contract.write_text(json.dumps(self.fixture.contract, ensure_ascii=False), encoding="utf-8")
        roles = {"plot": ["plot_agent"], "writing_brief": ["brief_agent"],
            "refine": ["refine"], "support_hook": ["nk_pov"],
            "critics_plot": ["critics_plot"], "critics_text": ["critics_text"]}
        terms = self.full_terms()
        terms.update(stages=list(roles), roles=roles)
        self.sign(terms=terms)
        with patch.object(runner, "_assert_support_components_available", return_value=None):
            self.create()
        runner._persist_stage(self.run, "plot", "artifacts/plot.md", "A fictional bell plan.\n")
        runner._persist_stage(self.run, "scene_cards", "artifacts/scene_cards.md",
                              "## Scene 1\n### Required beats\n- Ada repairs the bell.\n")
        runner._persist_stage(self.run, "prose", "artifacts/prose.md", "Ada repairs the bell. Then it rings.\n")
        runner._persist_stage(self.run, "adversarial_verify", "artifacts/verify.json",
                              json.dumps({"findings": [], "verdicts": {}}))
        runner._persist_stage(self.run, "completeness_critic", "artifacts/completeness.json",
                              json.dumps({"candidate_findings": [{"evidence": "Then it rings."}]}))
        from tools.cnw_nk_adapter import build_nk_payload
        state = runner.load_state(self.run)
        cards = runner._read_stage_text(self.run, state, "scene_cards")
        payload = build_nk_payload(self.fixture.contract, cards, runner._role_meta("cards", self.fixture.contract))
        runner._verify_current_nk_payload(self.run, payload)
        with self.assertRaisesRegex(ContractError, "NK_CURRENT_CARDS_MISMATCH"):
            runner._verify_current_nk_payload(self.run, {**payload, "fictional_tamper": True})
        for stage in ("support_hook", "critics_plot", "critics_text"):
            with self.subTest(stage=stage):
                self.assertEqual(auth.require_run_authorization(self.run, stage=stage)["status"],
                                 "LIVE_AND_FEES_AUTHORIZED")
        with cost_guard.accounting.locked_ledger():
            pass
        for stage in ("support_hook", "critics_plot", "critics_text"):
            account = cost_guard.for_run(self.run, stage=stage, model=runner.MODEL)
            receipt = account.command_reserve(SimpleNamespace(request_id="SIMULATED-" + stage,
                run_id=self.run_id, purpose="fictional auxiliary reserve",
                input_token_cap=100, output_token_cap=100), emit=False)
            self.assertEqual(receipt["status"], "RESERVED")
        rows = cost_guard.accounting.read_ledger_snapshot()["requests"]
        self.assertEqual({row["cost_context"]["stage"] for row in rows},
                         {"support_hook", "critics_plot", "critics_text"})
        self.assertEqual({row["cost_context"]["run_id"] for row in rows}, {self.run_id})
        self.assertEqual(self.http, [])

        plot_raw = (self.run / state["stages"]["plot"]["artifact"]["path"]).read_bytes()
        plot_sha = hashlib.sha256(plot_raw).hexdigest()
        plot_input = self.run / "artifacts/support" / ("critics-input-" + plot_sha + ".md")
        plot_input.parent.mkdir(parents=True, exist_ok=True)
        plot_input.write_bytes(plot_raw)
        self.assertEqual(auth.verify_auxiliary_native_input(self.run, stage="critics_plot",
            action="plan-critique", input_path=plot_input)["input_sha256"], plot_sha)
        with self.assertRaisesRegex(ContractError, "ACTION_MISMATCH"):
            auth.verify_auxiliary_native_input(self.run, stage="critics_plot",
                action="text-refine", input_path=plot_input)
        selection = runner._critics_excerpt_selection(self.run, runner.load_state(self.run))
        self.assertIsNotNone(selection)
        excerpt_raw = selection[0].encode("utf-8")
        excerpt_sha = hashlib.sha256(excerpt_raw).hexdigest()
        text_input = self.run / "artifacts/support" / ("critics-input-" + excerpt_sha + ".md")
        text_input.write_bytes(excerpt_raw)
        self.assertEqual(auth.verify_auxiliary_native_input(self.run, stage="critics_text",
            action="text-refine", input_path=text_input)["input_sha256"], excerpt_sha)
        text_input.write_bytes(b"foreign material\n")
        with self.assertRaisesRegex(ContractError, "CRITICS_INPUT_CHANGED"):
            auth.verify_auxiliary_native_input(self.run, stage="critics_text",
                action="text-refine", input_path=text_input)
        from tools import p2_06_critics_run as critics
        child = self.root / "runs" / "fictional-critics-child"
        child.mkdir()
        with self.assertRaisesRegex(ContractError, "CRITICS_INPUT_CHANGED"):
            critics.main(["--action", "text-refine", "--input", str(text_input),
                "--run-dir", str(child), "--ledger-run-id", self.run_id,
                "--parent-run-dir", str(self.run), "--parent-stage", "critics_text"])
        self.assertEqual(self.http, [])
        ledger_before = self.fees.ledger.read_bytes()
        quota = copy.deepcopy(terms)
        quota["max_requests"] = 3
        self.sign(terms=quota)
        account = cost_guard.for_run(self.run, stage="critics_text", model=runner.MODEL)
        with self.assertRaisesRegex(ContractError, "REQUEST_LIMIT_EXCEEDED"):
            account.command_reserve(SimpleNamespace(request_id="SIMULATED-fourth",
                run_id=self.run_id, purpose="fictional fourth hook reserve",
                input_token_cap=100, output_token_cap=100), emit=False)
        self.assertEqual(self.fees.ledger.read_bytes(), ledger_before)
        for changed in ("missing_parent", "wrong_role"):
            invalid = copy.deepcopy(terms)
            if changed == "missing_parent":
                invalid["stages"].remove("refine")
                invalid["roles"].pop("refine")
            else:
                invalid["roles"]["critics_text"] = ["foreign_hook"]
            self.sign(terms=invalid)
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    ContractError, "LIVE_GRANT_TERMS_INVALID"):
                auth.require_run_authorization(self.run, stage="critics_text")
        self.assertEqual(self.fees.ledger.read_bytes(), ledger_before)

    def test_actual_checked_plot_consumes_signed_b_and_records_original_accounting(self):
        self.create()
        with cost_guard.accounting.locked_ledger():
            pass  # Explicit temporary fictional ledger, never the real account.
        recovery.execute_checked(self.run, "plot")
        state = runner.load_state(self.run)
        artifact = state["stages"]["plot"]["artifact"]
        self.assertEqual(artifact["sha256"], hashlib.sha256((self.run / artifact["path"]).read_bytes()).hexdigest())
        self.assertEqual(len(self.http), 1)
        text = json.dumps(self.http[0]["body"]["messages"])
        self.assertIn("loose hinge", text)
        self.assertNotIn("A_ONLY_SECRET_CANARY", text)
        ledger = cost_guard.accounting.read_ledger_snapshot()
        self.assertEqual(len(ledger["requests"]), 1)
        row = ledger["requests"][0]
        self.assertEqual(row["status"], "SETTLED")
        self.assertEqual(row["cost_context"]["project_instance_id"], self.fixture.contract["project_instance_id"])
        self.assertIn("owner_grant_sha256", row["live_authorization"])
        first = (self.run / artifact["path"]).read_bytes()
        recovery.execute_checked(self.run, "plot")
        self.assertEqual(len(self.http), 1)
        self.assertEqual((self.run / artifact["path"]).read_bytes(), first)
        self.assertEqual(self.http[0]["simulation_status"], "SIMULATED")
        self.assertNotEqual(state.get("status"), "LIVE_EVIDENCE_VALIDATED")
        self.assertEqual(state["provider_requests"][0]["mode"], "MOCK_ONLY")
        with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
            runner.verify_live(SimpleNamespace(run_id=self.run_id, project_root=str(self.root)))
        forged = copy.deepcopy(state["provider_requests"][0])
        forged.update(mode="LIVE", fixture_only=False, simulation_status="LIVE")
        with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
            runner._receipt_content(self.run, forged)
        destination = os.environ.get("CNW_LIVE_GRANT_TEST_EVIDENCE")
        if destination:
            files = {}
            for relative in (artifact["path"], state["provider_requests"][0]["request_path"],
                             state["provider_requests"][0]["raw_response_path"]):
                raw = (self.run / relative).read_bytes()
                files[relative] = {"sha256": hashlib.sha256(raw).hexdigest(), "utf8": raw.decode("utf-8")}
            Path(destination).write_text(json.dumps({"mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
                "actual_run_state": state, "actual_http": self.http, "actual_files": files,
                "actual_synthetic_ledger": ledger}, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_forgery_wrong_roles_type_alias_expiry_and_source_change_reject_before_run(self):
        original = self.bundle.read_bytes()
        for field, value in (("max_requests", True), ("limit_cny", None),
                ("stages", ["plot", "plot"]), ("max_output_tokens", 0),
                ("expires_at", "2000-01-01T00:00:00+00:00")):
            changed = json.loads(original); changed["terms"][field] = value
            self.bundle.write_bytes(policy._canonical_bytes(changed))
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.create()
            self.assertFalse(self.run.exists())
        changed = json.loads(original); changed["owner"] = changed["controller"]
        self.bundle.write_bytes(policy._canonical_bytes(changed))
        with self.assertRaises(ContractError): self.create()
        self.bundle.write_bytes(original)
        owner = Path(json.loads(original)["owner"]["path"])
        forged = json.loads(owner.read_bytes()); forged["signature_base64"] = base64.b64encode(b"self-ACCEPT").decode()
        owner.write_bytes(policy._canonical_bytes(forged))
        changed = json.loads(original); changed["owner"]["sha256"] = hashlib.sha256(owner.read_bytes()).hexdigest()
        self.bundle.write_bytes(policy._canonical_bytes(changed))
        with self.assertRaisesRegex(ContractError, "SIGNATURE_INVALID"): self.create()
        self.sign()
        source = self.root / self.fixture.contract["story"]["source_file"]
        source.write_bytes(source.read_bytes() + b"changed source\n")
        with self.assertRaises(ContractError): self.create()
        self.assertEqual(self.http, [])

    def test_pending_unknown_budget_and_renewal_do_not_reset_spending(self):
        terms = copy.deepcopy(self.terms); terms.update(limit_cny="0.000300", max_input_tokens=100, max_output_tokens=100)
        self.sign(terms=terms); self.create()
        with cost_guard.accounting.locked_ledger(): pass
        account = cost_guard.for_run(self.run, stage="plot", model=runner.MODEL)
        def reserve(name):
            return account.command_reserve(SimpleNamespace(request_id=name, run_id=self.run_id,
                purpose="SIMULATED authorization accounting", input_token_cap=100, output_token_cap=100), emit=False)
        reserve("SIMULATED-A")
        account.command_settle(SimpleNamespace(request_id="SIMULATED-A", provider_request_id=None,
            returned_model=None, finish_reason=None, input_tokens=None, output_tokens=None), emit=False)
        original = self.fees.ledger.read_bytes()
        with self.assertRaisesRegex(ContractError, "BUDGET_EXCEEDED"): reserve("SIMULATED-B")
        self.assertEqual(self.fees.ledger.read_bytes(), original)
        # Fresh signatures/files do not reset the stable project/Run budget.
        self.sign(terms=terms)
        with self.assertRaisesRegex(ContractError, "BUDGET_EXCEEDED"): reserve("SIMULATED-C")
        self.assertEqual(self.fees.ledger.read_bytes(), original)
        self.assertEqual(cost_guard.accounting.read_ledger_snapshot()["requests"][0]["status"], "UNKNOWN_NOT_ZERO")

    def test_real_high_and_low_request_consumers_reject_changed_messages_role_or_tokens(self):
        self.create()
        with cost_guard.accounting.locked_ledger(): pass
        messages = runner.build_plot_request(self.root, self.fixture.contract)["messages"]
        before = self.fees.ledger.read_bytes()
        for entry in (runner.cnw_live_call, runner._cnw_live_call_in_slot):
            for role, output, actual, code in (("foreign_role", 100, messages, "ROLE_FORBIDDEN"),
                    ("plot_agent", 9000, messages, "TOKEN_LIMIT_EXCEEDED"),
                    ("plot_agent", 100, [{"role": "user", "content": "A_ONLY_SECRET_CANARY"}], "REQUEST_BINDING_MISMATCH")):
                with self.subTest(entry=entry.__name__, code=code), self.assertRaisesRegex(ContractError, code):
                    entry(self.run, stage="plot", role_id=role, messages=actual, output_cap=output)
        self.assertEqual(self.http, [])
        self.assertEqual(self.fees.ledger.read_bytes(), before)

    def test_unsigned_request_partial_write_recovers_without_overwriting_failed_attempt(self):
        from tools import cnw_native_pack as native
        original = native.tempfile.NamedTemporaryFile
        @contextmanager
        def partial(*args, **kwargs):
            with original(*args, **kwargs) as stream:
                class Writer:
                    def write(self, raw):
                        stream.write(raw[:3]); stream.flush()
                        raise OSError("SIMULATED partial request write")
                yield Writer()
        with patch.object(native.tempfile, "NamedTemporaryFile", partial), self.assertRaises(OSError):
            auth.publish_request(self.root, self.contract, run_id=self.run_id)
        directory = self.bundle.parent / "requests"
        self.assertEqual(list(directory.glob("*.json")), [])
        failed = {p: p.read_bytes() for p in (directory / ".native-write-attempts").iterdir()}
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(next(iter(failed.values()))), 3)
        published = auth.publish_request(self.root, self.contract, run_id=self.run_id)
        self.assertEqual(published, auth.publish_request(self.root, self.contract, run_id=self.run_id))
        self.assertIs(published["provider_call_authorized"], False)
        for path, raw in failed.items(): self.assertEqual(path.read_bytes(), raw)

    def test_grant_changed_after_reservation_blocks_http_and_preserves_original_charge(self):
        self.create()
        with cost_guard.accounting.locked_ledger(): pass
        original = cost_guard.RunAccount.command_reserve
        @wraps(original)
        def reserve_then_revoke(account, *args, **kwargs):
            result = original(account, *args, **kwargs)
            value = json.loads(self.bundle.read_bytes())
            value["terms"].update(not_before="2000-01-01T00:00:00+00:00", expires_at="2001-01-01T00:00:00+00:00")
            self.bundle.write_bytes(policy._canonical_bytes(value))
            return result
        messages = runner.build_plot_request(self.root, self.fixture.contract)["messages"]
        with patch.object(cost_guard.RunAccount, "command_reserve", reserve_then_revoke), self.assertRaisesRegex(ContractError, "LIVE_GRANT_EXPIRED"):
            runner.cnw_live_call(self.run, stage="plot", role_id="plot_agent", messages=messages, output_cap=4000)
        self.assertEqual(self.http, [])
        rows = cost_guard.accounting.read_ledger_snapshot()["requests"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "UNKNOWN_NOT_ZERO")
        self.assertIn("owner_grant_sha256", rows[0]["live_authorization"])

    def test_signature_for_other_implementation_cannot_create_run(self):
        request = auth.build_request(self.root, self.contract, run_id=self.run_id)
        changed = copy.deepcopy(request)
        changed["implementation_sha256"] = "0" * 64
        changed["controller_payload"]["implementation_sha256"] = "0" * 64
        self.sign(request=changed)
        with self.assertRaisesRegex(ContractError, "ATTESTATION_BINDING_INVALID"): self.create()
        self.assertFalse(self.run.exists())
        self.assertEqual(self.http, [])

    def full_terms(self):
        terms = copy.deepcopy(self.terms)
        roles = {"plot": ["plot_agent"], "scene_cards": ["scene_card_agent"], "writing_brief": ["brief_agent"],
            "prose": ["prose_agent_1", "prose_agent_2", "prose_agent_3"],
            "multi_lens_review": list(runner.LENS_IDS), "adversarial_verify": list(runner.VERIFIER_IDS),
            "completeness_critic": ["completeness"], "refine": ["refine"],
            "re_review": list(runner.LENS_IDS) + list(runner.VERIFIER_IDS)}
        terms.update(stages=list(roles), roles=roles, max_requests=80, limit_cny="10.000000")
        return terms

    def test_owned_context_rejects_duplicate_foreign_or_relabelled_history_and_account_paths(self):
        from tools.cnw_test_live_transport import _isolated_live_transport
        self.create()
        with cost_guard.accounting.locked_ledger(): pass
        recovery.execute_checked(self.run, "plot")
        rows = runner.load_state(self.run)["provider_requests"]
        with _isolated_live_transport(self.fixture.temp, data_home=self.fixture.data_home,
                projects=[self.root], runs=[self.run], transport=lambda *args, **kwargs: None) as session:
            session.history(self.run, rows)
            with self.assertRaisesRegex(ContractError, "RECEIPT_ID_DUPLICATE"):
                session.history(self.run, rows + rows)
            changed = copy.deepcopy(rows)
            changed[0]["ledger_settlement"]["cost_context"]["project_instance_id"] = "FOREIGN-INSTANCE"
            with self.assertRaisesRegex(ContractError, "COST_RECEIPT_BINDING_MISMATCH"):
                session.history(self.run, changed)
            changed = copy.deepcopy(rows); changed[0].update(mode="LIVE", fixture_only=False)
            with self.assertRaisesRegex(ContractError, "LIVE_TEST_RECEIPT_INVALID"):
                session.history(self.run, changed)
            with self.assertRaisesRegex(ContractError, "EXPIRED_OR_FOREIGN"):
                session.validate(self.root)
            with patch.object(cost_guard.accounting, "LEDGER", self.fixture.temp_root.parent / "outside-ledger-never-created.json"), \
                 self.assertRaisesRegex(ContractError, "LIVE_TEST_ACCOUNT_CHANGED"):
                session.validate(self.run)
        with self.assertRaisesRegex(ContractError, "EXPIRED_OR_FOREIGN"):
            session.validate(self.run)

    def test_signed_multistage_request_consumers_recovery_and_simulated_live_rejection(self):
        from tools.cnw_test_live_transport import _isolated_live_transport
        self.sign(terms=self.full_terms()); self.create()
        with cost_guard.accounting.locked_ledger(): pass
        self.fixture.rereview_messages = []
        outputs = self.fixture._outputs()
        actual = []
        def transport(run, *, url, body, request_id):
            stage = request_id.removeprefix("cnw-" + self.run_id + "-").rsplit("-", 1)[0]
            role, extra = None, None
            if stage in {"multi_lens_review", "re_review", "adversarial_verify"}:
                packet = json.loads(body["messages"][1]["content"])
                role = packet.get("lens_id") or packet.get("verifier_id")
                if "finding_id" in packet: extra = {"finding_id": packet["finding_id"]}
            content = self.fixture._response(stage, role, extra, outputs, body["messages"])
            actual.append({"stage": stage, "role_id": role, "messages": body["messages"],
                           "output_cap": body["max_tokens"], "mode": "MOCK_ONLY", "simulation_status": "SIMULATED"})
            payload = {"id": "SIMULATED-" + request_id, "model": runner.MODEL,
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
            return SimpleNamespace(status_code=200, json=lambda: payload)
        original = runner._persist_stage
        failed = []
        @wraps(original)
        def persist(*args, **kwargs):
            if args[1] == "scene_cards" and not failed:
                failed.append(True)
                raise RuntimeError("SIMULATED interruption after real receipt")
            return original(*args, **kwargs)
        with _isolated_live_transport(self.fixture.temp, data_home=self.fixture.data_home,
                projects=[self.root], runs=[self.run], transport=transport), \
             patch.object(runner.httpx, "post", side_effect=AssertionError("No HTTP fallback in simulation")), \
             patch.object(runner, "_persist_stage", persist):
            for stage in runner.CNW_STAGES:
                if stage == "scene_cards":
                    with self.assertRaisesRegex(RuntimeError, "interruption after real receipt"):
                        recovery.execute_checked(self.run, stage)
                    previous_count = len(actual)
                    recovery.execute_checked(self.run, stage)
                    self.assertEqual(len(actual), previous_count)
                else:
                    recovery.execute_checked(self.run, stage)
            state = runner.load_state(self.run)
            files = {}
            for stage in runner.CNW_STAGES:
                artifact = state["stages"][stage]["artifact"]
                raw = (self.run / artifact["path"]).read_bytes()
                self.assertTrue(raw)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact["sha256"])
                files[artifact["path"]] = {"sha256": artifact["sha256"], "utf8": raw.decode("utf-8")}
            self.assertEqual(sum(row["stage"] == "multi_lens_review" for row in actual), 5)
            self.assertEqual(sum(row["stage"] == "adversarial_verify" for row in actual), 3)
            self.assertTrue(all(row["mode"] == "MOCK_ONLY" and row["fixture_only"] is True for row in state["provider_requests"]))
            self.assertTrue(self.fixture.rereview_messages)
            for _, wire in self.fixture.rereview_messages:
                self.assertIn(outputs["refine"], json.loads(wire)[1]["content"])
            with self.assertRaisesRegex(ContractError, "MOCK_RECEIPT_CANNOT_PROVE_LIVE"):
                runner.verify_live(SimpleNamespace(run_id=self.run_id, project_root=str(self.root)))
            for receipt in state["provider_requests"]:
                for name in (receipt["request_path"], receipt["raw_response_path"]):
                    raw = (self.run / name).read_bytes()
                    files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "utf8": raw.decode("utf-8")}
            destination = os.environ.get("CNW_LIVE_GRANT_TEST_EVIDENCE")
            if destination:
                Path(destination + ".multistage.json").write_text(json.dumps({"mode": "MOCK_ONLY", "simulation_status": "SIMULATED",
                    "actual_requests": actual, "actual_run_state": state, "actual_files": files,
                    "actual_synthetic_ledger": cost_guard.accounting.read_ledger_snapshot()}, ensure_ascii=False, indent=2), encoding="utf-8")
        before = self.fees.ledger.read_bytes()
        with self.assertRaisesRegex(ContractError, "LIVE_SIMULATED_HISTORY_FORBIDDEN"):
            auth.require_run_authorization(self.run, stage="plot")
        self.assertEqual(self.fees.ledger.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
