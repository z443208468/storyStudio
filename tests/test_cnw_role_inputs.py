"""Offline checks for the public templates' supplementary role inputs."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

from tools import cnw_roles as roles
from tools import cnw_runner as runner
from tools.cnw_contract import ContractError


class RoleInputTests(unittest.TestCase):
    def _native_nk_case(self, mode):
        import socket
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            build = root / "runtime/patched/NK/mock"
            (build / "node_modules/next/dist/bin").mkdir(parents=True)
            (build / "node_modules/next/dist/bin/next").write_text("MOCK", encoding="utf-8")
            index = root / "patches/nk/PATCH_INDEX.json"
            index.parent.mkdir(parents=True)
            index.write_text(json.dumps({"runtime_build_id": "mock"}), encoding="utf-8")
            process = Mock(pid=1234)
            process.poll.return_value = 1 if mode == "exited" else None
            def stop():
                process.poll.return_value = 0
            process.terminate.side_effect = stop
            process.kill.side_effect = stop
            guard = SimpleNamespace(command_reserve=Mock(return_value={"status": "RESERVED"}),
                command_settle=Mock(return_value={"status": "SETTLED"}),
                load_config=lambda: ({}, {}), estimate=lambda *args: Decimal("0.001"))
            launch = {}
            def start(command, **kwargs):
                launch.update(command=command, env=kwargs["env"])
                return process
            def request(url, **kwargs):
                self.assertIn(str(launch["command"][-1]), url)
                if mode != "missing":
                    Path(launch["env"]["STORYSTUDIO_NK_LIVE_CAPTURE"]).write_text(json.dumps({
                        "request_id": launch["env"]["STORYSTUDIO_NK_LIVE_REQUEST_ID"],
                        "response": {"id": "MOCK", "model": runner.MODEL,
                            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                            "choices": [{"finish_reason": "stop", "message": {"content": "MOCK reflection"}}]}}), encoding="utf-8")
                return SimpleNamespace(status_code=200, json=lambda: {"perspectives": [{"reflection": "MOCK reflection"}]})
            listener = Mock()
            listener.getsockname.return_value = ("127.0.0.1", 49123)
            context = Mock()
            context.__enter__ = Mock(return_value=listener)
            context.__exit__ = Mock(return_value=False)
            with patch.object(runner, "ROOT", root), patch.object(runner, "_p2_guard", return_value=guard), \
                    patch.dict(runner.os.environ, {"DEEPSEEK_API_KEY": "MOCK_SECRET"}), \
                    patch("shutil.which", return_value="node.exe"), patch("socket.socket", return_value=context), \
                    patch("subprocess.Popen", side_effect=start), \
                    patch.object(runner.httpx, "get") as health, patch.object(runner.httpx, "post", side_effect=request) as post:
                if mode == "success":
                    result = runner._invoke_nk_service(run, {"MOCK": "private source"})
                    self.assertEqual(runner._receipt_content(run, result["receipt"]), "MOCK reflection")
                    self.assertEqual(guard.command_settle.call_args.args[0].input_tokens, 10)
                else:
                    with self.assertRaisesRegex(ContractError, "NK_SERVER_EXITED" if mode == "exited" else "NK_PROVIDER_CAPTURE_MISSING_OR_INVALID"):
                        runner._invoke_nk_service(run, {"MOCK": "private source"})
                    self.assertIsNone(guard.command_settle.call_args.args[0].input_tokens)
                guard.command_settle.assert_called_once()
                self.assertEqual(launch["command"], ["node.exe", str(build / "node_modules/next/dist/bin/next"),
                    "start", "--hostname", "127.0.0.1", "--port", "49123"])
                if mode == "exited":
                    health.assert_not_called()
                    post.assert_not_called()
                else:
                    process.terminate.assert_called_once()
                manifest = json.loads(next(run.glob("nk-service*.json")).read_text())
                self.assertEqual(manifest["status"], "STOPPED")
                self.assertNotIn("MOCK_SECRET", json.dumps(manifest))

    def test_native_nk_owns_port_process_and_receipt(self):
        self._native_nk_case("success")

    def test_native_nk_does_not_use_health_after_child_exits(self):
        self._native_nk_case("exited")

    def test_native_nk_missing_capture_retains_reservation(self):
        self._native_nk_case("missing")

    def test_unchanged_nk_input_reuses_verified_reflection(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "cards.md").write_text("MOCK cards", encoding="utf-8")
            (run / "reflection.md").write_text("MOCK unchanged reflection", encoding="utf-8")
            payload = {"fixture": "same input"}
            receipt = {"request_id": "MOCK-NK", "role_id": "nk_pov", "status": "SUCCEEDED",
                       "input_sha256": runner.sha(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())}
            state = {"provider_requests": [receipt], "stages": {"scene_cards": {
                "artifact": {"path": "cards.md", "sha256": runner.sha((run / "cards.md").read_bytes())}}},
                "support_hooks": {"nk_pov": {"status": "MATERIALIZED", "request_id": "MOCK-NK",
                    "artifact": {"path": "reflection.md", "sha256": runner.sha((run / "reflection.md").read_bytes())},
                    "mapping": {"source_status": "LIVE_ACCEPTED"}}}}
            with patch.object(runner, "_run_dir_base", return_value=run), \
                    patch.object(runner, "_role_meta", return_value={}), \
                    patch("tools.cnw_nk_adapter.build_nk_payload", return_value=payload), \
                    patch.object(runner, "_receipt_content", return_value="MOCK raw") as verify, \
                    patch.object(runner, "_invoke_nk_service", side_effect=ContractError("MOCK_NEW_INPUT", "offline")) as service:
                result = runner._nk_pov(run, state, {})
                self.assertEqual(result["provider_call"], "reused")
                verify.assert_called_once_with(run, receipt)
                service.assert_not_called()
                receipt["input_sha256"] = "changed input"
                with self.assertRaisesRegex(ContractError, "MOCK_NEW_INPUT"):
                    runner._nk_pov(run, state, {})
                service.assert_called_once()

    def test_private_request_snapshot_matches_dispatch_and_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "run_state.json").write_text(json.dumps({"run_id": run.name, "stages": {},
                "provider_requests": [], "schema_version": "TEST_FIXTURE_ONLY"}), encoding="utf-8")
            guard = SimpleNamespace(provider_slot=nullcontext,
                command_reserve=lambda args, **kwargs: {"status": "RESERVED"},
                command_settle=lambda args, **kwargs: {"status": "SETTLED"},
                load_config=lambda: ({}, {}), estimate=lambda *args: Decimal("0.001"))
            response = Mock(status_code=200)
            response.json.return_value = {"id": "MOCK_RESPONSE", "model": runner.MODEL,
                "choices": [{"finish_reason": "stop", "message": {"content": "MOCK brief"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10}}
            messages = [{"role": "user", "content": "MOCK private sources"}]
            with patch.object(runner, "_p2_guard", return_value=guard), \
                    patch.dict(runner.os.environ, {"DEEPSEEK_API_KEY": "MOCK_ONLY_NOT_A_REAL_KEY_12345"}), \
                    patch.object(runner.httpx, "post", return_value=response) as post:
                first = runner.cnw_live_call(run, stage="writing_brief", role_id="brief_agent", messages=messages, output_cap=100)
                snapshot = run / first[1]["request_path"]
                self.assertEqual(json.loads(snapshot.read_text(encoding="utf-8")), post.call_args.kwargs["json"])
                self.assertNotIn("MOCK_ONLY_NOT_A_REAL_KEY", snapshot.read_text(encoding="utf-8"))
                self.assertEqual(first, runner.cnw_live_call(run, stage="writing_brief", role_id="brief_agent", messages=messages, output_cap=100))
                snapshot.write_text("{}", encoding="utf-8")
                with self.assertRaisesRegex(ContractError, "LIVE_REQUEST_HASH_MISMATCH"):
                    runner.cnw_live_call(run, stage="writing_brief", role_id="brief_agent", messages=messages, output_cap=100)
                self.assertEqual(post.call_count, 1)

    def test_brief_reads_supplementary_canon_and_template_instructions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            keys = roles.AUTHOR_ROLE_READS["brief"] + roles.AUTHOR_TEMPLATE_READS["brief"]
            for key in keys:
                path = root / key.replace("<work_id>", "ep007")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"SOURCE:{key}", encoding="utf-8")
            materials = roles.read_actual_texts(root, "brief", "ep007")
            self.assertEqual(set(materials), set(keys))
            contract = {"project_id": "FICT", "unit": {"id": "ep007"}, "story": {"required_beats": []}}
            messages = roles.build_author_role_messages("brief", contract, materials)
            request = json.loads(messages[1]["content"])
            self.assertEqual(request["materials"], materials)
            for source in roles.AUTHOR_TEMPLATE_READ_SOURCES["brief"]:
                self.assertIn(f"pinned_author_supplementary_reading: {source}", messages[0]["content"])
            self.assertIn("Brief agent", messages[0]["content"])
            before = roles.sha256_bytes(json.dumps(messages, sort_keys=True).encode())
            (root / "90_canon/timeline.md").write_text("Changed story-time", encoding="utf-8")
            after_messages = roles.build_author_role_messages("brief", contract,
                                                              roles.read_actual_texts(root, "brief", "ep007"))
            self.assertNotEqual(before, roles.sha256_bytes(json.dumps(after_messages, sort_keys=True).encode()))

    def test_speakers_come_from_brief_not_on_screen_cast_in_both_paths(self):
        contract = {"unit": {"id": "FICT", "language": "zh", "pov": "Alice", "target_visible_chars": 20,
                             "min_visible_chars": 10, "max_visible_chars": 30},
                    "story": {"characters_in_scene": ["Alice", "Silent"], "required_beats": [],
                              "secret_canon": "DO NOT SEND THIS"}}
        brief = "# Brief\n## Voice References\n- Alice — see sample\n- Guest — see sample\n## Hard Constraints\nKeep story-time."
        voices = "# Voices\n## Alice\nALICE SAMPLE\n### Dialogue\nNested sample\n## Silent\nSILENT SAMPLE\n## Guest\nGUEST SAMPLE\n"
        view = roles.build_prose_input_view(contract, brief, voices)
        messages = roles.build_author_role_messages("prose", contract, {
            roles.AUTHOR_ROLE_READS["prose"][0]: brief,
            roles.AUTHOR_ROLE_READS["prose"][1]: voices,
            "90_canon/canon.md": "FULL CANON MUST NOT LEAK",
        })
        payload = json.loads(messages[1]["content"])
        self.assertEqual(view["inputs"]["voice_samples"], payload["voice_samples"])
        self.assertIn("GUEST SAMPLE", payload["voice_samples"])
        self.assertIn("Nested sample", payload["voice_samples"])
        self.assertNotIn("SILENT SAMPLE", payload["voice_samples"])
        self.assertEqual(set(payload), {"writing_brief", "voice_samples"})
        self.assertNotIn("DO NOT SEND THIS", json.dumps(messages))
        self.assertNotIn("FULL CANON MUST NOT LEAK", json.dumps(messages))

    def test_voice_references_accept_markdown_names(self):
        brief = ("## Voice References\n- **Alice** — see sample\n"
                 "2. [Guest](../samples.md#guest) – reference\n"
                 "| **Character** | Sample |\n|---|---|\n| Silent | path |\n"
                 "## Hard Constraints\n- Not a speaker\n")
        self.assertEqual(roles.brief_voice_characters(brief), ["Alice", "Guest", "Silent"])

    def test_real_brief_grouped_speakers_and_pov_annotation(self):
        brief = ("## Voice References\nSources loaded separately from `../voices.md`:\n"
                 "- **Alice（POV）** — dialogue and internal narration\n"
                 "- **Guest / Silent** — visible source dialogue\n---\n## Hard Constraints\nKeep current time.")
        self.assertEqual(roles.brief_voice_characters(brief), ["Alice", "Guest", "Silent"])
        samples = "### Alice\nA\n### Guest\nG\n### Silent\nS\n### Unlisted\nU"
        self.assertNotIn("Unlisted", roles.brief_voice_samples(brief, samples))

    def test_no_dialogue_needs_no_voice_samples(self):
        for block in ("", "- None (no dialogue)\n", "- 无对白\n"):
            with self.subTest(block=block):
                brief = f"# Brief\n## Voice References\n{block}## Hard Constraints\nObserve silently."
                self.assertEqual(roles.brief_voice_samples(brief, "## Alice\nUnneeded sample"), "")

    def test_missing_references_or_samples_do_not_fall_back_to_cast(self):
        with self.assertRaisesRegex(ContractError, "BRIEF_VOICE_REFERENCES_MISSING"):
            roles.brief_voice_samples("Brief without references", "## Alice\nSample")
        with self.assertRaisesRegex(ContractError, "VOICE_SAMPLE_CHARACTER_MISSING"):
            roles.brief_voice_samples("## Voice References\n- Guest — see sample", "## Alice\nSample")


if __name__ == "__main__":
    unittest.main()
