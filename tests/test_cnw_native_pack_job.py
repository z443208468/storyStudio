"""Native package -> actual application-owned INSERT/ADAPT/original chapter jobs."""
from __future__ import annotations

import copy
import contextlib
import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tests import test_cnw_pack_job as fixtures
from tests.test_cnw_input_pack import encoded, sha
from tools import cnw_input_pack, cnw_native_pack as native, cnw_pack_app as app, cnw_runner as runner
from tools.cnw_contract import ContractError


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        self.owner = fixtures.PackageJobTests()
        self.owner.setUp()
        self.addCleanup(self.owner.doCleanups)
        self.f = self.owner.f
        self.files = {}
        self.contexts = {}
        self.model = self.owner.model
        self.model.transport_cache = {}
        self.model.run_context = {}
        self.model._interrupt_once_for = None
        self.model._interrupt_run_id = None
        self.model._interrupted = set()
        groups = []
        for alias, display, names, setting in (("harbor", "TEST_HARBOR", ("Mira", "Keeper"), "harbor"),
                                                ("orchard", "TEST_ORCHARD", ("梅", "园丁"), "果园"),
                                                ("original", "TEST_ORIGINAL", ("Sana", "Keeper"), "coast")):
            first, second = names
            prefix = f"projects/{alias}/materials"
            material = {
                "01_theme/theme.md": f"Thematic choice at {setting}.", "02_logline/logline.md": f"A practical offer at {setting}.",
                "03_project_design/project_design.md": f"Project {alias}: a small visible repair.",
                "04_chapter_design/arc_index.md": "| Arc | Range |\n|---|---|\n| arc_01 | EP001-EP002 |",
                "04_chapter_design/arc_01.md": f"ARC_{alias}: practical choice at {setting}.",
                "04_chapter_design/arc_01_episode_details.md": f"EP001 and EP002 follow the choices at {setting}.",
                "90_canon/canon.md": f"CANON_{alias}: {first} and {second} are neighbors, never siblings.",
                "90_canon/character_bible.md": f"{first} asks directly; {second} offers a practical tool.",
                "90_canon/world_bible.md": f"WORLD_{alias}: only ordinary tools at {setting}.",
                "90_canon/timeline.md": f"TIMELINE_{alias}: the repair happens in one afternoon.",
                "90_canon/glossary.md": f"{setting}: the shared local place.",
                "92_style_engine/style_guide.md": "Write visible actions and direct requests.",
                "92_style_engine/forbidden_patterns.md": "## Layer 1\n| Rule | Pattern | Cap |\n|---|---|---|\n| Surface | `SURFACE_NATIVE` | 0 |\n## Layer 2\n| Rule | Pattern | Cap |\n|---|---|---|\n| Structure | `STRUCTURE_NATIVE` | 0 |",
                "92_style_engine/character_voice_samples.md": f"## {first}\nCould you help?\n## {second}\nTake the tool.",
            }
            self.files.update({prefix + "/" + name: value.encode() for name,value in material.items()})
            sources = []
            if alias == "harbor":
                self.files["sources/harbor_A.md"] = b"A_ONLY_HARBOR_DO_NOT_CONSUME\n"
                self.files["sources/harbor_B.md"] = b"B_ONLY_HARBOR: Mira asks for a tool.\nA neighbor answers.\nThey choose a next step.\n"
                self.files["sources/harbor_C.md"] = b"C_ONLY_HARBOR_DO_NOT_CONSUME\n"
                sources = [{"alias": letter, "file": f"sources/harbor_{letter}.md", "format": "md"} for letter in "ABC"]
            if alias == "orchard":
                self.files["sources/orchard_A.md"] = b"A_ONLY_ORCHARD_DO_NOT_CONSUME\n"
                self.files["sources/orchard_B.json"] = encoded({"chapters": [{"text": "梅请园丁扶住树枝。", "emotion": "calm", "tag": "B_ONLY_ORCHARD"}], "outside": "JSON_OUTSIDE_POINTER_DO_NOT_CONSUME"}).replace(b"\n", b"").replace(b"  ", b"")
                sources = [{"alias": "A", "file": "sources/orchard_A.md", "format": "md"}, {"alias": "B", "file": "sources/orchard_B.json", "format": "json"}]
            groups.append({"alias": alias, "project_id": display, "materials": prefix,
                           "sources": sources, "fifth_lens": {"id": alias + "-promise", "responsibility": f"Check NATIVE_PROMISE_{alias}: the tool leads to an observable next request."}})
        specs = [
            ("HARBOR_INSERT", "harbor", "INSERT_BETWEEN", {"source": "B", "selection": {"before_line": 1, "after_line": 3}}),
            ("HARBOR_ADAPT", "harbor", "ADAPT_SOURCE", {"source": "B", "selection": {"start_line": 1, "end_line": 2}}),
            ("ORCHARD_ADAPT", "orchard", "ADAPT_SOURCE", {"source": "B", "selection": {"json_pointer": "/chapters/0"}}),
            # Deliberately declare the continuation first: the app schedules it.
            ("EP002", "original", "ORIGINAL_EPISODE", {"first_episode": False, "previous_task": "EP001"}),
            ("EP001", "original", "ORIGINAL_EPISODE", {"first_episode": True}),
        ]
        tasks = []
        for alias, group, intent, fields in specs:
            names, setting = (("梅", "园丁"), "果园") if group == "orchard" else (("Sana", "Keeper"), "coast") if group == "original" else (("Mira", "Keeper"), "harbor")
            requirement = {"kind": "episode" if intent == "ORIGINAL_EPISODE" else "scene", "language_locale": "zh-CN" if group == "orchard" else "en-US", "pov": names[0],
                "target_visible_chars": 180, "min_visible_chars": 100, "max_visible_chars": 320,
                "chapter_context": f"CONTEXT_{group}: practical choice at {setting}.", "entry_state": "The repair is unsettled.",
                "exit_state": "The neighbors choose a next step.", "role_in_story": f"A small visible repair at {setting}.",
                "reader_reward": "A practical offer earns a concrete next request.", "characters_in_scene": list(names),
                "arc_ref": "04_chapter_design/arc_01.md", "character_knowledge_boundary_ref": "90_canon/canon.md",
                "voice_sample_refs": list(names), "forbidden_future_revelations": ["Do not invent a family relationship."],
                "required_beats": [{"beat_id": "B01", "goal": f"{names[0]} asks for help and chooses a next step."}],
                "new_plot_pre_designed": False}
            path = "tasks/" + alias + ".json"
            self.files[path] = encoded(requirement)
            tasks.append({"alias": alias, "project": group, "work_intent": intent, "requirements": path, **fields})
            self.contexts[alias] = {"names": names, "setting": setting}
        self.index = {"schema": "cnw_workpack_index_v2", "projects": groups, "tasks": tasks}
        self.package = self.f.base / "native.zip"
        self.write_pack()

    def write_pack(self):
        self.files["workpack_index.json"] = encoded(self.index)
        manifest = {"schema": "STORYSTUDIO_INPUT_PACK_V2", "files": {n: sha(raw) for n,raw in self.files.items()}}
        with zipfile.ZipFile(self.package, "w") as archive:
            for name, raw in {**self.files, "PACK_MANIFEST.json": encoded(manifest)}.items():
                archive.writestr(name, raw)

    def transport(self, run, *, stage, role_id, messages, output_cap, extra=None):
        self.assertTrue(self.f.temp._finalizer.alive)
        self.assertTrue(run.resolve().is_relative_to(self.f.home.resolve()))
        state = runner.load_state(run)
        contract = json.loads((run / "artifacts/contract.json").read_text(encoding="utf-8"))
        alias = contract["unit"]["id"].removeprefix("TASK-")
        context = dict(self.contexts[alias])
        intent = contract["work_intent"]
        action = {"INSERT_BETWEEN": "the missing hinge repair between the request and the decision",
                  "ADAPT_SOURCE": "a fresh telling of the selected borrowing moment"}.get(intent)
        if intent == "ORIGINAL_EPISODE":
            action = "the next visit to return the tool" if contract["story"].get("previous_episode_ref") else "the first borrowing visit"
        context["setting"] += ": " + action
        self.model.run_context[state["run_id"]] = context
        wire = json.dumps(messages, ensure_ascii=False)
        group = "original" if alias.startswith("EP") else "orchard" if alias.startswith("ORCHARD") else "harbor"
        for other in {"original", "orchard", "harbor"} - {group}:
            self.assertNotIn("CANON_" + other, wire)
            self.assertNotIn("CONTEXT_" + other, wire)
        if stage == "plot":
            self.assertIn("CONTEXT_" + group, wire)
            if group == "harbor":
                self.assertIn("B_ONLY_HARBOR", wire)
                self.assertNotIn("A_ONLY_HARBOR_DO_NOT_CONSUME", wire)
                self.assertNotIn("C_ONLY_HARBOR_DO_NOT_CONSUME", wire)
            if group == "orchard":
                self.assertIn("B_ONLY_ORCHARD", wire)
                self.assertNotIn("A_ONLY_ORCHARD_DO_NOT_CONSUME", wire)
                self.assertNotIn("JSON_OUTSIDE_POINTER_DO_NOT_CONSUME", wire)
            if alias == "EP001":
                self.assertFalse((run.parent.parent / "contracts/TASK-EP002.json").exists())
            if alias == "EP002":
                self.assertIn("where to return it", wire)
                binding = json.loads((run.parent.parent / contract["input_pack"]["index_file"]).read_text(encoding="utf-8"))
                self.assertEqual(binding["previous_binding"]["status"], "SIMULATED_CARRY_FORWARD")
                self.assertFalse(binding["previous_binding"]["promoted"])
        if stage == "multi_lens_review" and role_id == "story_specific":
            self.assertIn("NATIVE_PROMISE_" + group, wire)
        if group == "orchard" and stage == "multi_lens_review" and role_id == "canon":
            claim = "梅接住它，说园丁是自己的哥哥。"
            self.assertIn(claim, wire)
            finding = {"lens_id": "canon", "findings": [{"finding_id": state["run_id"] + "-CANON-01", "severity": "P1",
                "issue": "正文把邻居写成兄妹，违反当前项目 Canon。", "evidence": claim,
                "recommendation": "删除虚构的兄妹关系，保留求助与行动。"}]}
            return self.model._workflow_response(run, messages, json.dumps(finding, ensure_ascii=False), stage=stage, role_id=role_id)
        if group == "orchard" and stage in {"prose", "refine"}:
            self.assertIn("简体中文", wire)
            if stage == "refine":
                self.assertIn("OMITTED-READER-PAYOFF", wire)
                self.assertIn("正文把邻居写成兄妹", wire)
            body = ("梅摸了摸树枝，抬头问园丁借一块木片。园丁把木片递过来，梅接住它，说园丁是自己的哥哥。" if stage == "prose" else
                    "梅扶住树枝，问园丁借一块木片。园丁递来木片，梅把枝条扶稳，再问明天把木片还到哪里。") * 4
            return self.model._workflow_response(run, messages, body, stage=stage, role_id=role_id)
        if group == "orchard" and stage == "re_review":
            packet = json.loads(messages[1]["content"])
            self.assertIn("再问明天把木片还到哪里", packet["draft"])
            self.assertNotIn("说园丁是自己的哥哥", packet["draft"])
            self.assertEqual(sha(packet["draft"].encode("utf-8")), packet["changed_context"]["v1_sha256"])
            self.assertIn("说园丁是自己的哥哥", packet["changed_context"]["diff"])
        return self.model._transport(run, stage=stage, role_id=role_id, messages=messages, output_cap=output_cap, extra=extra)

    def entry(self, *, job=None, execute=True, transport=True):
        args = ["--data-home", str(self.f.home), "--offline"]
        args += ["--job", job] if job else ["--input", str(self.package)]
        if execute:
            args.append("--execute-job")
        stream = io.StringIO()
        boundary = patch.object(runner, "cnw_live_call", side_effect=self.transport) if transport else contextlib.nullcontext()
        with self.owner.disconnected(), boundary, contextlib.redirect_stdout(stream):
            code = app.main(args)
        return code, json.loads(stream.getvalue())

    def test_native_five_tasks_use_real_application_and_defer_original_continuation(self):
        archive_before = self.package.read_bytes()
        pointer_before = (self.f.base / "pointer.json").read_bytes()
        code, prepared = self.entry(execute=False)
        self.assertEqual(code, 0, prepared.get("blocking_code"))
        self.assertEqual(len(prepared["projects"]), 3)
        self.assertEqual(len({p["project_instance_id"] for p in prepared["projects"].values()}), 3)
        second = next(r for r in prepared["tasks"] if r["task_alias"] == "EP002")
        self.assertEqual(second["status"], "WAITING_PREDECESSOR")
        self.assertNotIn("contract", second)
        self.assertFalse((Path(second["project_root"]) / "runs" / second["planned_run_id"]).exists())
        original_root = Path(second["project_root"])
        self.assertFalse((original_root / "_INBOX/source_manifest.json").exists())
        origin_path = Path(prepared["job_record"]).parent / "origin.json"
        origin_before = origin_path.read_bytes()
        self.model._interrupt_once_for = "scene_cards"
        code, interrupted = self.entry(job=prepared["job_record"])
        self.assertEqual(code, 2)
        self.assertEqual(interrupted["status"], "JOB_EXECUTION_INCOMPLETE")
        deferred_contract = original_root / "contracts/TASK-EP002.json"
        prior_run = original_root / "runs" / next(r for r in prepared["tasks"] if r["task_alias"] == "EP001")["planned_run_id"]
        link = os.link
        interruption = {}
        def interrupt_contract_publication(source, destination, *args, **kwargs):
            if Path(destination) == deferred_contract and not interruption:
                interruption["prior_bytes"] = {p: sha(p.read_bytes()) for p in prior_run.rglob("*") if p.is_file() and not p.name.endswith(".lock")}
                interruption["requests"] = len(self.model.requests)
                interruption["pending_bytes"] = Path(source).read_bytes()
                raise OSError("SYNTHETIC_DEFERRED_CONTRACT_PUBLICATION_INTERRUPTION")
            return link(source, destination, *args, **kwargs)
        with patch.object(os, "link", side_effect=interrupt_contract_publication):
            code, publication_interrupted = self.entry(job=prepared["job_record"])
        self.assertEqual(code, 2, publication_interrupted)
        self.assertTrue(interruption, publication_interrupted)
        self.assertEqual(publication_interrupted["status"], "JOB_PREPARATION_INCOMPLETE")
        self.assertEqual(publication_interrupted["interrupted_task"], "EP002")
        failed_second = next(t for t in publication_interrupted["tasks"] if t["task_alias"] == "EP002")
        self.assertEqual(failed_second["preparation"]["interrupted_stage"], "task_preparation")
        self.assertFalse(deferred_contract.exists())
        self.assertFalse((original_root / "runs" / second["planned_run_id"]).exists())
        self.assertEqual(origin_path.read_bytes(), origin_before)
        code, finished = self.entry(job=prepared["job_record"])
        self.assertEqual(code, 0, [(r["task_alias"], r.get("execution", {}).get("interruptions")) for r in finished["tasks"]])
        self.assertEqual(finished["status"], "MOCK_STORIES_EXPORTED")
        self.assertEqual(origin_path.read_bytes(), origin_before)
        self.assertEqual({p: sha(p.read_bytes()) for p in interruption["prior_bytes"]}, interruption["prior_bytes"])
        self.assertEqual(deferred_contract.read_bytes(), interruption["pending_bytes"])
        self.assertEqual(len(list((original_root / "contracts").glob("TASK-EP002.json"))), 1)
        captures = []
        for task in finished["tasks"]:
            root = Path(task["project_root"]); run = root / "runs" / task["planned_run_id"]
            state = runner.load_state(run)
            self.assertFalse(state["fixture_only"])
            self.assertEqual(set(task["execution"]["stages"]), set(runner.CNW_STAGES))
            for stage in runner.CNW_STAGES:
                artifact = state["stages"][stage]["artifact"]
                self.assertEqual(sha((run / artifact["path"]).read_bytes()), artifact["sha256"])
            contract = json.loads((run / "artifacts/contract.json").read_text(encoding="utf-8"))
            if contract["work_intent"] != "INSERT_BETWEEN":
                self.assertNotIn("before_anchor", contract["story"])
                self.assertNotIn("after_anchor", contract["story"])
            if task["task_alias"] == "ORCHARD_ADAPT":
                selected = contract["story"]["source_selection"]
                self.assertNotEqual(selected["canonical_selected_value_sha256"], selected["wire_excerpt_sha256"])
            target = Path(task["execution"]["export"]["result"]["deliverables"])
            exports = {p.relative_to(root).as_posix(): {"raw_utf8": p.read_bytes().decode("utf-8"), "sha256": sha(p.read_bytes())}
                       for p in target.iterdir() if p.is_file()}
            captures.append({"task": task, "contract": contract, "run_state": state,
                             "artifacts": {s: runner._read_stage_text(run, state, s) for s in runner.CNW_STAGES}, "export_files": exports})
        continuation = next(c for c in captures if c["task"]["task_alias"] == "EP002")
        prior = next(c for c in captures if c["task"]["task_alias"] == "EP001")
        self.assertEqual(continuation["contract"]["story"]["previous_episode_sha256"], sha(prior["artifacts"]["refine"].encode()))
        by_alias = {c["task"]["task_alias"]: c for c in captures}
        for first, second in (("EP001", "EP002"), ("HARBOR_INSERT", "HARBOR_ADAPT")):
            for stage in ("plot", "scene_cards", "writing_brief", "prose", "refine"):
                self.assertNotEqual(by_alias[first]["artifacts"][stage], by_alias[second]["artifacts"][stage])
        self.assertIn("the next visit to return the tool", continuation["artifacts"]["plot"])
        self.assertIn("the next visit to return the tool", continuation["artifacts"]["refine"])
        for capture in captures:
            task = capture["task"]
            target = Path(task["execution"]["export"]["result"]["deliverables"])
            self.assertEqual((target / "02_修订稿.txt").read_text(encoding="utf-8"), capture["artifacts"]["refine"])
            instructions = (target / "05_复用操作说明.md").read_text(encoding="utf-8")
            self.assertIn("project-pack -DataHome $DataHome -JobFile $JobFile", instructions)
            self.assertIn(finished["job_id"], instructions)
            self.assertIn("MOCK_ONLY / SIMULATED", instructions)
            self.assertIn("Live 未授权", instructions)
            self.assertNotIn("produce -Mode live", instructions)
        self.assertFalse((original_root / "07_draft/episodes/EP001.md").exists())
        requests = len(self.model.requests)
        before = {p: sha(p.read_bytes()) for t in finished["tasks"] for p in (Path(t["project_root"]) / "runs" / t["planned_run_id"]).rglob("*") if p.is_file() and not p.name.endswith(".lock")}
        code, again = self.entry(job=prepared["job_record"])
        self.assertEqual(code, 0, again.get("blocking_code"))
        self.assertEqual(len(self.model.requests), requests)
        self.assertEqual({p: sha(p.read_bytes()) for p in before}, before)
        self.assertEqual(self.package.read_bytes(), archive_before)
        self.assertEqual((self.f.base / "pointer.json").read_bytes(), pointer_before)
        actual_requests = []
        for capture in captures:
            task, state = capture["task"], capture["run_state"]
            run = Path(task["project_root"]) / "runs" / task["planned_run_id"]
            for receipt in state["provider_requests"]:
                request_raw = (run / receipt["request_path"]).read_bytes()
                response_raw = (run / receipt["raw_response_path"]).read_bytes()
                self.assertEqual(sha(request_raw), receipt["request_sha256"])
                self.assertEqual(sha(response_raw), receipt["raw_response_sha256"])
                actual_requests.append({"task_alias": task["task_alias"], "run_id": state["run_id"], "stage": receipt["stage"],
                    "role_id": receipt["role_id"], "messages": json.loads(request_raw)["messages"], "receipt": receipt,
                    "request_utf8": request_raw.decode("utf-8"), "response_utf8": response_raw.decode("utf-8")})
        destination = os.environ.get("ATOM09_NATIVE_JOB_EVIDENCE_OUTPUT")
        if destination:
            Path(destination).write_bytes(encoded({"execution": "SIMULATED_OFFLINE_NATIVE_PACKAGE", "prepared": prepared, "finished": finished,
                "origin_unchanged": True, "tasks": captures, "model_requests": actual_requests,
                "deferred_contract_publication_interrupted_and_resumed": True,
                "predecessor_bytes_unchanged": True}))

    def test_invalid_source_or_chapter_dependencies_refuse_before_registration(self):
        original = copy.deepcopy(self.index)
        for problem in ("missing_source", "cross_project", "cycle", "duplicate", "runtime"):
            self.index = copy.deepcopy(original)
            if problem == "missing_source":
                self.index["tasks"][0].pop("source")
            elif problem == "cross_project":
                self.index["tasks"][3]["previous_task"] = "HARBOR_INSERT"
            elif problem == "cycle":
                self.index["tasks"][4].update(first_episode=False, previous_task="EP002")
            elif problem == "duplicate":
                self.index["tasks"].append(copy.deepcopy(self.index["tasks"][0]))
            else:
                self.files["projects/harbor/materials/94_runtime/run_state.json"] = b"{}"
            self.write_pack()
            with self.subTest(problem=problem), self.assertRaises(ContractError):
                app.import_package(self.package, data_home=self.f.home, offline=True)
            self.assertFalse((self.f.home / "projects").exists())
            self.files.pop("projects/harbor/materials/94_runtime/run_state.json", None)

    def test_reserved_aliases_refuse_before_registration(self):
        original = copy.deepcopy(self.index)
        for name in ("CON", "nul", "COM1", "LPT9"):
            self.index = copy.deepcopy(original)
            self.index["tasks"][0]["alias"] = name
            self.write_pack()
            with self.subTest(alias=name), self.assertRaises(ContractError):
                app.import_package(self.package, data_home=self.f.home, offline=True)
            self.assertFalse((self.f.home / "projects").exists())

    def test_distinct_aliases_do_not_share_a_contract_path(self):
        self.index["projects"] = self.index["projects"][:1]
        self.index["tasks"] = self.index["tasks"][:2]
        self.index["tasks"][0]["alias"] = "A"
        self.index["tasks"][1]["alias"] = "TASK-A"
        self.write_pack()
        code, prepared = self.entry(execute=False)
        self.assertEqual(code, 0)
        self.assertNotEqual(prepared["status"], "IMPORT_INCOMPLETE", prepared.get("blocking_code"))
        self.assertEqual(len({t["unit_id"] for t in prepared["tasks"]}), 2)
        self.assertEqual(len({t["contract"] for t in prepared["tasks"]}), 2)
        for row in prepared["tasks"]:
            self.assertEqual(json.loads(Path(row["contract"]).read_text())["unit"]["id"], row["unit_id"])

    def test_sealed_job_preparation_interruption_is_recorded_and_resumes(self):
        self.index["projects"] = self.index["projects"][2:]
        self.index["tasks"] = self.index["tasks"][3:]
        self.write_pack()
        archive = self.package.read_bytes()
        link = os.link
        interrupted = []
        def interrupt_first_contract(source, destination, *args, **kwargs):
            if Path(destination).name == "TASK-EP001.json" and not interrupted:
                interrupted.append(Path(destination))
                raise OSError("SYNTHETIC_SEALED_JOB_PREPARATION_INTERRUPTION")
            return link(source, destination, *args, **kwargs)
        with patch.object(os, "link", side_effect=interrupt_first_contract):
            code, report = self.entry(execute=False)
        self.assertEqual(code, 2)
        self.assertTrue(interrupted)
        self.assertEqual(report["status"], "JOB_PREPARATION_INCOMPLETE")
        self.assertEqual(report["interrupted_task"], "EP001")
        first = next(t for t in report["tasks"] if t["task_alias"] == "EP001")
        self.assertEqual(first["preparation"]["interrupted_stage"], "task_preparation")
        self.assertEqual(first["preparation"]["interruptions"][-1]["error_type"], "OSError")
        self.assertFalse(interrupted[0].exists())
        origin = Path(report["job_record"]).parent / "origin.json"
        origin_bytes = origin.read_bytes()
        code, recovered = self.entry(job=report["job_record"], execute=False)
        self.assertEqual(code, 0)
        self.assertEqual(recovered["status"], "RUNS_PREPARED_WITH_PENDING_TASKS")
        first = next(t for t in recovered["tasks"] if t["task_alias"] == "EP001")
        self.assertEqual(first["preparation"]["status"], "PREPARED")
        self.assertEqual(len(first["preparation"]["interruptions"]), 1)
        self.assertEqual(origin.read_bytes(), origin_bytes)
        self.assertEqual(self.package.read_bytes(), archive)
        self.assertFalse(self.model.requests)
        run = Path(first["project_root"]) / "runs" / first["planned_run_id"]
        self.assertFalse(runner.load_state(run)["provider_requests"])
        self.assertEqual(len(list(run.parent.iterdir())), 1)

    def test_prepare_preserves_actual_execution_failure_without_model_or_fee_calls(self):
        self.index["projects"] = self.index["projects"][2:]
        self.index["tasks"] = self.index["tasks"][3:]
        self.write_pack()
        code, stopped = self.entry(transport=False)
        self.assertEqual(code, 2)
        self.assertEqual(stopped["status"], "JOB_EXECUTION_INCOMPLETE")
        self.assertEqual(stopped["blocking_code"], "OFFLINE_PROVIDER_FORBIDDEN")
        record = Path(stopped["job_record"])
        origin_bytes = (record.parent / "origin.json").read_bytes()
        first = next(t for t in stopped["tasks"] if t["task_alias"] == "EP001")
        run = Path(first["project_root"]) / "runs" / first["planned_run_id"]
        before = {p: p.read_bytes() for p in run.rglob("*") if p.is_file() and not p.name.endswith(".lock")}
        code, prepared = self.entry(job=str(record), execute=False, transport=False)
        self.assertEqual(code, 2)  # Preparing again does not resolve execution failure.
        for field in ("status", "blocking_code", "interrupted_task"):
            self.assertEqual(field in prepared, field in stopped)
            self.assertEqual(prepared.get(field), stopped.get(field))
        self.assertEqual((record.parent / "origin.json").read_bytes(), origin_bytes)
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertFalse(self.model.requests)
        self.assertFalse(runner.load_state(run)["provider_requests"])


class NativeImmutableTests(unittest.TestCase):
    def test_partial_write_is_retained_outside_final_file_and_can_resume(self):
        with tempfile.TemporaryDirectory(prefix="storystudio-native-publication-") as temporary:
            root = Path(temporary)
            path, raw = root / "binding.json", b'{"complete":"immutable declaration"}\n'
            original = tempfile.NamedTemporaryFile

            @contextlib.contextmanager
            def cut_write(*args, **kwargs):
                with original(*args, **kwargs) as stream:
                    class InterruptedStream:
                        def write(self, content):
                            stream.write(content[:9]); stream.flush()
                            raise OSError("SYNTHETIC_NATIVE_PARTIAL_WRITE")
                    yield InterruptedStream()

            with patch.object(tempfile, "NamedTemporaryFile", side_effect=cut_write), self.assertRaises(OSError):
                native._immutable(path, raw)
            self.assertFalse(path.exists())
            self.assertTrue(any(p.is_file() and p.read_bytes() == raw[:9] for p in root.rglob("*")))
            native._immutable(path, raw)
            native._immutable(path, raw)
            self.assertEqual(path.read_bytes(), raw)
            with self.assertRaises(ContractError):
                native._immutable(path, b"different")
            self.assertEqual(path.read_bytes(), raw)
