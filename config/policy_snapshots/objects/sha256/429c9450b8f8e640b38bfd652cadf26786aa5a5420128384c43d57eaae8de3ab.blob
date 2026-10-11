"""Build the reviewed Atom-02 content-addressed identity inventory.

Historical files are imported only from their recorded Git revisions and are
accepted only when the recovered Windows checkout bytes match the recorded
SHA-256. Unknown historical hashes are indexed as unavailable; they are never
reconstructed from a newer configuration.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from .policy_snapshots import DEFAULT_STORE, SnapshotStore
except ImportError:
    from policy_snapshots import DEFAULT_STORE, SnapshotStore

ROOT = Path(__file__).resolve().parents[1]
CURRENT_ASSETS = {
    "legacy_combined_production_config": ["config/production.example.json"],
    "legacy_project_policy": ["config/cnw_production_policy.json"],
    "provider_pricing": ["config/p2_cost_pricing_2026-10-10.json"],
    "app_policy": ["config/policies/app_policy.v1.json"],
    "provider_policy": ["config/policies/provider_policy.deepseek_flash.v1.json"],
    "project_policy": ["config/policies/project_policy.template.v1.json"],
    "prompt": [
        "prompts/cnw/brief.md", "prompts/cnw/plot.md", "prompts/cnw/prose.md",
        "prompts/cnw/scene_cards.md",
    ],
    "workflow": [
        "third_party/claude-novel-workflow/templates/config/workflow.template.yml",
        "third_party/claude-novel-workflow/templates/config/ai_roles.template.yml",
        "third_party/claude-novel-workflow/templates/config/project.template.yml",
        "third_party/claude-novel-workflow/docs/THREE_LAYER_REVIEW.md",
        "third_party/claude-novel-workflow/docs/HOW_TO_ADAPT.md",
    ],
    "tool": [
        "tools/cnw_runner.py", "tools/cnw_roles.py", "tools/cnw_review.py",
        "tools/cnw_lint.py", "tools/cnw_project.py", "tools/cnw_contract.py",
        "tools/cnw_generate.py", "tools/cnw_import_workflow.py",
        "tools/cnw_maintenance.py", "tools/cnw_sprint.py",
        "tools/cnw_sprint_live.py", "tools/cnw_recovery.py",
        "tools/cnw_export.py", "tools/p2_cost_guard.py", "tools/critics_bridge.py",
        "tools/policy_snapshots.py", "tools/build_policy_snapshots.py",
    ],
}
HISTORIC_GIT_ASSETS = [
    {
        "kind": "legacy_combined_production_config",
        "path": "config/production.example.json",
        "commit": "29dec841a55d78ac843101bdf87c15dfe240a803",
        "sha256": "b5dc2bebb54f9ee4beca56ad3bf2d9b88f9ab6831d7bd9211bedcd57a3a9e959",
    },
    {
        "kind": "tool",
        "path": "tools/p2_cost_guard.py",
        "commit": "3c0d8c23e251ccf76d80ac72fce2b9f18515bc7d",
        "sha256": "ab8a40b15687b8fc35faffbef5c34553649f818f188c7e4cdfa57ba9342c21e3",
    },
]
MISSING_HISTORIC_IDENTITIES = [
    {"kind": "legacy_combined_production_config", "sha256": "d5debd560ee2c91ffcb7ca0c08f6dec7014e7436691795e74a23912b715a8d96", "source_ref": "historical run state provider_config_sha256", "reason": "exact original bytes not present in current checkout, Atom-00 file archive, or Git path history"},
    {"kind": "tool", "sha256": "7a650695452b549f431325a14a690c51238d880b6d117388e0fa144eb8470e28", "source_ref": "historical run state cost_guard_runner_sha256", "reason": "exact original bytes not present in current checkout, Atom-00 file archive, or Git path history"},
    {"kind": "tool", "sha256": "ead9b205791ea7e96bcdba475b7c9d92a117710949cb82c9c33b6441c8712815", "source_ref": "historical run state cost_guard_runner_sha256", "reason": "exact original bytes not present in current checkout, Atom-00 file archive, or Git path history"},
]


def git_checkout_bytes(commit: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=ROOT,
        capture_output=True, check=True,
    )
    # The historical run identities were recorded from Windows CRLF working
    # copies. Git stores normalized LF blobs, so materialize the checkout form
    # and rely on expected SHA validation rather than trusting this conversion.
    return result.stdout.replace(b"\n", b"\r\n")


def main() -> int:
    store = SnapshotStore(DEFAULT_STORE)
    for kind, paths in CURRENT_ASSETS.items():
        for relative in paths:
            source = ROOT / relative
            store.put_bytes(source.read_bytes(), kind=kind, source_ref=relative)
    for item in HISTORIC_GIT_ASSETS:
        raw = git_checkout_bytes(item["commit"], item["path"])
        store.put_bytes(raw, kind=item["kind"], source_ref=f"git:{item['commit']}:{item['path']}", expected_sha256=item["sha256"])
    for item in MISSING_HISTORIC_IDENTITIES:
        store.mark_legacy_missing(item["sha256"], kind=item["kind"], source_ref=item["source_ref"], reason=item["reason"])
    print(f"snapshot_entries={len(store._read_index()['entries'])}")
    print(f"store={DEFAULT_STORE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
