# Generic project contract

This contract defines identity and isolation requirements for a StoryStudio project instance. It is a target interface for the R5 refactor; stage acceptance records what is already implemented. It does not replace CNW’s stage/work-unit contract, canon approval, provider policy, or review artifacts.

## Project identity record

Each new project instance has exactly one `project_identity.json` at its registered project root. The record is versioned and binds an immutable random `project_instance_id` to the selected DataHome, canonical project root, creation time, and mutable descriptive metadata. The display `project_id` is a user-facing label and may be repeated across distinct instances.

```json
{
  "schema_version": "story_studio_project_identity_v1",
  "project_instance_id": "<generated immutable identifier>",
  "project_id": "<user-selected display identifier>",
  "display_name": "<optional project name>",
  "data_home_id": "<stable identity for the explicitly selected DataHome>",
  "registered_project_root": "<canonical absolute path>",
  "created_at": "<UTC timestamp>",
  "status": "ACTIVE"
}
```

The concrete schema may add fields without changing the invariants. Paths and IDs are validated; identity metadata is never silently rewritten to make a copied directory appear unique.

## Instance lifecycle

- `setup --data-home <path>` explicitly selects the user’s private root. A machine-local pointer persists only that choice. A new process must resolve to the same root. A newly created root gets a protected ACL; an existing root with inherited or broad access is rejected unchanged. Missing, malformed, inaccessible, or unsafe pointer state fails closed.
- `project init --project-id <label>` creates a fresh internal instance ID under the selected DataHome, validates space/access/path safety, and registers exactly one writable location.
- `relocate` moves an instance while retaining its ID. The registry transitions under lock; the old root is not writable after the new root is activated. If the transition cannot be verified, neither root is silently selected.
- `fork` or `clone-as-new` creates a fresh instance ID and requires new approval/contracts. It does not inherit live runs, cost attribution, or Controller acceptance.
- A copied identity record cannot be registered or opened at a second writable root. The resolver returns `PROJECT_INSTANCE_COLLISION` until an explicit supported lifecycle operation resolves ownership.
- A project command without a selected, registered project returns `PROJECT_REQUIRED`; a write without explicit DataHome returns `DATA_HOME_REQUIRED`.

## Binding production data

Contracts, source snapshots, runs, review artifacts, provider receipts, cost attribution, and exports carry or derive the same `project_instance_id`. A run is bound to `project_instance_id + run_id + frozen contract/source identity`. New work never chooses source text based on project name or application install location. Old contracts remain byte-preserved and use a signed-off external mapping until a specific compatibility stage accepts a reader.

CNW work-unit/project contracts continue to define method inputs, role boundaries, and review constraints. The generic identity record does not loosen CNW’s source/provenance checks or implicitly approve any creative Canon. NK/CritiCS configuration and readiness are independent optional integration choices.

## Filesystem, privacy, and recovery

The resolver checks canonical roots, traversal, links/reparse points, containment, project ownership, and write access. Paths are checked again within the operation’s lock before mutation. External source selection authorizes only a one-time read-only import, hashing and copy into the project; it does not authorize production reads from arbitrary external paths. Private project files and credentials remain outside Git. Shared financial state has one writable owner.

Identity registration must be recoverable after interruption. Incomplete identity/registry pairs fail with an actionable state and are not repaired by changing project IDs or selecting whichever root is convenient. The exact registry and crash-recovery protocol are versioned in the implementation and verified by the active plan.
