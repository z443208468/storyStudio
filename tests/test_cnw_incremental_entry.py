"""Ordinary public _INBOX and derived-material update entry, with mocked API."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import cnw_project as p, cnw_import_workflow as w
from tools import cnw_runner as r
from tests.test_cnw_chapter_arc import mock_receipt
from tools.cnw_contract import ContractError
from tools.cnw_runner import ROOT


class IncrementalEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix=".incremental-entry-", dir=ROOT / "workspace")
        self.addCleanup(self.tmp.cleanup)
        self.parent = Path(self.tmp.name)
        self.root = self.parent / "ORDINARY"
        (self.root / "_INBOX").mkdir(parents=True)
        self.write("_INBOX/one.md", "A has blue eyes.")
        self.write("_INBOX/two.md", "B keeps a bell.")
        self.calls = []
        self.extra_documents = {}
        self.forbidden = None
        self.api = patch.object(w, "cnw_live_call", side_effect=self.provider)
        self.api.start()
        self.addCleanup(self.api.stop)
        w.run_import(self.root)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
        return path

    def provider(self, run, *, messages, **kwargs):
        payload = json.loads(messages[1]["content"])
        self.calls.append(payload)
        sources = payload["original_sources"]
        name = next(iter(sources))
        text = sources[name]["text"]
        entry = {"status": "CONFIRMED", "text": text, "source_refs": [name]}
        docs = {doc: [entry] for doc in w.DOCUMENTS} if "required_initial_documents" in payload else {"03_project_design/project_design.md": [entry]}
        docs.update({doc: [entry] for doc in self.extra_documents})
        conflicts = []
        if text == "A has gray eyes.":
            docs["90_canon/canon.md"] = [entry]
            conflicts = [{"old_file": "90_canon/canon.md", "old_quote": "A has blue eyes.",
                "new_file": "90_canon/canon.md", "new_entry": 0, "reason": "same actor different eye color"}]
        if self.forbidden:
            docs[self.forbidden] = [entry]
        return json.dumps({"source_notes": {s: "mock inventory" for s in sources}, "documents": docs,
            "conflicts": conflicts, "next_action": "Read the added material."}), {"status": "MOCK_ONLY"}

    def update(self, input_path):
        return p.incremental_update(self.parent, "ORDINARY", input_path)

    def test_no_manifest_new_and_unchanged_inbox_do_not_copy_old_sources(self):
        old = {name: (self.root / name).read_bytes() for name in ("_INBOX/one.md", "_INBOX/two.md", "90_canon/canon.md")}
        added = self.write("_INBOX/new.md", "C carries the ladder.")
        result = self.update(added)
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(set(self.calls[-1]["original_sources"]), {"_INBOX/new.md"})
        self.assertNotIn("required_initial_documents", self.calls[-1])
        self.assertFalse((self.root / "_INBOX/source_manifest.json").exists())
        self.assertFalse((self.root / "_INBOX/originals").exists())
        for name, data in old.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        count = len(self.calls)
        self.assertEqual(self.update(added)["status"], "NO_NEW_OR_CHANGED_SOURCES")
        self.assertEqual(len(self.calls), count)
        log = (self.root / "00_meta/source_log.md").read_text(encoding="utf-8")
        self.assertTrue(all(name in log for name in ("_INBOX/one.md", "_INBOX/two.md", "_INBOX/new.md")))

    def test_changed_source_conflict_keeps_old_canon_and_both_versions(self):
        canon = (self.root / "90_canon/canon.md").read_bytes()
        path = self.write("_INBOX/one.md", "A has gray eyes.")
        result = self.update(path)
        self.assertEqual(result["conflicts"], 1)
        self.assertEqual(set(self.calls[-1]["original_sources"]), {"_INBOX/one.md"})
        self.assertEqual((self.root / "90_canon/canon.md").read_bytes(), canon)
        questions = (self.root / "90_canon/unresolved_questions.md").read_text(encoding="utf-8")
        self.assertIn("A has blue eyes.", questions)
        self.assertIn("A has gray eyes.", questions)

    def test_external_staging_preserves_legacy_candidates_without_manifest(self):
        candidate = self.write("90_canon/canon_candidates.json", '{"keep":"old unmanifest candidate"}')
        old = candidate.read_bytes()
        incoming = self.parent / "external.md"
        raw = b"New source bytes.\r\n"
        incoming.write_bytes(raw)
        self.update(incoming)
        staged = list((self.root / "_INBOX/originals").glob("*.md"))
        self.assertEqual(len(staged), 1)
        self.assertEqual(staged[0].read_bytes(), raw)
        self.assertEqual(candidate.read_bytes(), old)
        self.assertFalse((self.root / "_INBOX/source_manifest.json").exists())
        count = len(self.calls)
        self.assertEqual(self.update(incoming)["provider_call"], "none")
        self.assertEqual(len(self.calls), count)

    def test_review_cards_plot_appropriate_append_and_original_draft_forbidden(self):
        names = ("05_scene_cards/card.md", "06_plot/ep01_plot.md", "08_review/beta.md")
        for name in names:
            self.write(name, "Existing derived conclusion.\n")
        self.extra_documents = {name: True for name in names}
        path = self.write("_INBOX/review.md", "Added review feedback.")
        self.update(path)
        for name in names:
            self.assertIn(name, self.calls[-1]["existing_documents"])
            self.assertTrue((self.root / name).read_bytes().startswith(b"Existing derived conclusion.\n"))
        self.forbidden = "07_draft/ep01.md"
        path = self.write("_INBOX/forbidden.md", "Do not overwrite draft.")
        with self.assertRaisesRegex(ContractError, "IMPORT_DOCUMENT_INVALID"):
            self.update(path)
        self.assertFalse((self.root / "07_draft/ep01.md").exists())

    def test_pending_recovery_precedes_new_staging(self):
        changed = self.write("_INBOX/new.md", "C carries the ladder.")
        with patch.object(w, "_apply", side_effect=OSError("MOCK interrupted")):
            with self.assertRaises(OSError):
                self.update(changed)
        count = len(self.calls)
        incoming = self.parent / "external.md"
        incoming.write_text("next source", encoding="utf-8")
        result = self.update(incoming)
        self.assertTrue(result["requested_input_deferred"])
        self.assertEqual(len(self.calls), count)
        self.assertFalse((self.root / "_INBOX/originals").exists())
        self.assertFalse((self.root / w.PENDING).exists())

    def test_incremental_requires_semantic_initial_import_not_manifest(self):
        (self.root / w.STATE).unlink()
        with self.assertRaisesRegex(ContractError, "INCREMENTAL_REQUIRES_INITIAL_IMPORT"):
            self.update(self.root / "_INBOX/one.md")

    def test_mixed_original_context_and_unknown_citations_are_distinguished(self):
        added = self.write("_INBOX/added.md", "C carries the ladder.")
        def provider(run, *, messages, **kwargs):
            payload = json.loads(messages[1]["content"])
            return json.dumps({"source_notes": {"_INBOX/added.md": "new source"},
                "documents": {"03_project_design/project_design.md": [{"status": "CONFIRMED", "text": "C carries the ladder.",
                    "source_refs": ["_INBOX/added.md", "90_canon/canon.md", "07_draft/not_supplied.md"]}]},
                "conflicts": [], "next_action": "Read the updated index."}), {"status": "MOCK_ONLY"}
        with patch.object(w, "cnw_live_call", side_effect=provider):
            result = self.update(added)
        records = list((Path(result["run_dir"]) / "artifacts").glob("classification_organized-*.json"))
        claim = next(iter(json.loads(records[0].read_text(encoding="utf-8")).values()))
        self.assertEqual(claim["source_kinds"]["90_canon/canon.md"], "project_context")
        self.assertNotIn("07_draft/not_supplied.md", claim["sources"])
        self.assertEqual(claim["unverified_source_refs"], ["07_draft/not_supplied.md"])
        self.assertIn("Unverified source citations", (self.root / "03_project_design/project_design.md").read_text(encoding="utf-8"))

    def test_all_unknown_citations_do_not_support_confirmed_entry(self):
        added = self.write("_INBOX/added.md", "C carries the ladder.")
        value = {"source_notes": {"_INBOX/added.md": "new source"}, "documents": {"03_project_design/project_design.md": [
            {"status": "CONFIRMED", "text": "Unsupported assertion.", "source_refs": ["not_in_request.md"]}]},
            "conflicts": [], "next_action": "Read source."}
        with patch.object(w, "cnw_live_call", return_value=(json.dumps(value), {"status": "MOCK_ONLY"})):
            with self.assertRaisesRegex(ContractError, "IMPORT_ENTRY_INVALID"):
                self.update(added)

    def test_official_model_logs_are_kept_with_deterministic_source_accounting(self):
        self.extra_documents = {"00_meta/source_log.md": True, "00_meta/ai_work_log.md": True}
        added = self.write("_INBOX/added.md", "C carries the ladder.")
        self.update(added)
        for name in self.extra_documents:
            text = (self.root / name).read_text(encoding="utf-8")
            self.assertIn("C carries the ladder.", text)
            self.assertIn("Classification: CONFIRMED", text)
        self.assertIn("SHA256=", (self.root / "00_meta/source_log.md").read_text(encoding="utf-8"))
        self.assertIn("Next action:", (self.root / "00_meta/ai_work_log.md").read_text(encoding="utf-8"))

    def test_reconsume_only_log_routing_keeps_exact_old_receipt_and_rejects_source_change(self):
        run = self.root / "reconsume"
        run.mkdir()
        r.save_state(run, {"run_id": run.name, "provider_requests": []})
        payload = {"allowed_existing_documents": ["90_canon/canon.md"], "original_sources": {"source.md": "actual source"},
            "existing_documents": {"90_canon/canon.md": "existing Canon"}, "author_reference_sources": {"CLAUDE": "complete method"}}
        messages = [{"role": "system", "content": "fixed method"}, {"role": "user", "content": json.dumps(payload)}]
        _, receipt = mock_receipt(run, {"stage": "project_import", "role_id": "project_organization", "messages": messages}, "{}", "RECONSUME-MOCK")
        request_path = run / receipt["request_path"]
        request_path.write_text(json.dumps({"messages": messages, "model": r.MODEL, "max_tokens": w.IMPORT_OUTPUT_CAP}), encoding="utf-8")
        receipt["request_sha256"] = r.sha(request_path.read_bytes())
        receipt["request_fingerprint"] = r.sha(json.dumps({"stage": "project_import", "role_id": "project_organization", "messages": messages,
            "output_cap": w.IMPORT_OUTPUT_CAP, "model": r.MODEL, "url": r.API_URL, "extra": None}, ensure_ascii=False, sort_keys=True).encode())
        state = r.load_state(run)
        state["provider_requests"] = [receipt]
        r.save_state(run, state)
        original_receipts = r.load_state(run)["provider_requests"]
        payload["allowed_existing_documents"].extend(["00_meta/source_log.md", "00_meta/ai_work_log.md"])
        current = [messages[0], {"role": "user", "content": json.dumps(payload)}]
        self.assertEqual(w._reconsume_bookkeeping_response(run, "project_import", current)[0], "{}")
        self.assertEqual(r.load_state(run)["provider_requests"], original_receipts)
        self.assertTrue(list((run / "artifacts").glob("response_reconsume-*.json")))
        for key in ("original_sources", "existing_documents", "author_reference_sources"):
            copy = json.loads(json.dumps(payload))
            copy[key]["new"] = "changed actual input"
            changed = [messages[0], {"role": "user", "content": json.dumps(copy)}]
            self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", changed))
        copy = json.loads(json.dumps(payload))
        copy["allowed_existing_documents"].append("07_draft/new.md")
        self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", [messages[0], {"role": "user", "content": json.dumps(copy)}]))
        with patch.object(r, "API_URL", "https://different.example"):
            self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", current))
        with patch.object(r, "MODEL", "different-model"):
            self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", current))
        with patch.object(w, "IMPORT_OUTPUT_CAP", w.IMPORT_OUTPUT_CAP + 1):
            self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", current))
        self.assertIsNone(w._reconsume_bookkeeping_response(run, "project_import", [{"role": "system", "content": "changed method"}, current[1]]))
        raw_path = run / receipt["raw_response_path"]
        old_raw = raw_path.read_bytes()
        raw_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "LIVE_RAW_RESPONSE_HASH_MISMATCH"):
            w._reconsume_bookkeeping_response(run, "project_import", current)
        raw_path.write_bytes(old_raw)
        request_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ContractError, "LIVE_REQUEST_HASH_MISMATCH"):
            # Tampered request is not accepted as a compatible successful call.
            w._reconsume_bookkeeping_response(run, "project_import", current)


if __name__ == "__main__":
    unittest.main()
