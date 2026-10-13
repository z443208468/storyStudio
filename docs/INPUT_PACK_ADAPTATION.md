# Legacy scene input adaptation (R5 Atom-03/04 repairs)

`tools.cnw_input_pack.prepare_scene_input` adapts the declared V5 scene-pack
format into a private registered project and a V2 draft. The package describes
the materials and writing requirements; the pinned CNW engine owns the workflow.
This API is the input/contract layer. `studio.ps1 project-pack` provides its
formal package entry and processes all declared tasks in separate instances.

```powershell
.\tools\studio.ps1 project-pack -InputFile <ZIP> -DataHome <absolute-path>
```

`-Offline` selects source acquisition behavior only; it does not select model
execution. To execute the prepared package job, pass an explicit execution mode:

```powershell
.\tools\studio.ps1 project-pack -JobFile <job-record> -DataHome <absolute-path> -Offline -Mode offline -ExecuteJob
```

`-Mode offline` runs the deterministic mock path and its results remain marked
`SIMULATED`/`MOCK_ONLY`. `-Mode live` preserves Live intent and currently returns
`LIVE_ROUTE_NOT_READY`; it does not silently fall back to offline, call a
Provider, or reserve fees. Live becomes available only after its project-bound
trusted-review, authorization and fee adapters pass their own gates.

Use `-SourceRepository <local-Git-repository> -Offline` for a local source.
Without a local repository the app uses a private DataHome cache for the exact
declared GitHub commit. `-Offline` forbids network fallback, including implicit
Git partial-clone fetches. Source repositories are never checked out or modified.
Temporary source staging is also under the selected DataHome.

The app derives the fifth Lens from explicit project policy or the seed's
Story-specific Lens row in `00_meta/OUTPUT_REQUIREMENTS.md`, preserving the
source SHA, locator, original text and result in the immutable input binding.
Duplicate/conflicting duties reject. It returns a private job record, drafts,
contract hashes and deterministic offline identity results. These results grant
no Provider authorization. Repeating import creates new instances and jobs;
partial failures preserve all prior progress. Unknown occupied roots/caches
are refused, and the global setup pointer is not changed.

The underlying adapter verifies `PACK_MANIFEST.json` against every archive file,
reads `workpack_index.json`, and handles one declared scene per call. It only
reads the exact work-order commit/path/blob from the repository passed by its
caller. The formal `project-pack` entry prepares that repository: either the
explicit read-only local source or the DataHome cache populated from the
declared GitHub source. The adapter itself performs no network transfer. No
checkout, embedded installer, or package instruction is executed. The selected
source is registered through the existing immutable source-manifest/index
implementation.

Use a new instance created by `project_paths.create_project` under an explicitly
chosen DataHome. Pass that instance's root, the package path, declared scene root,
source repository and actual project fifth Lens duties to `prepare_scene_input`.
Pass its returned draft path to the existing `cnw_project.write_contract_draft`.
Existing project content is refused. Package installation holds the project
write lock; an interrupted installation retains its completed files and must
not be overwritten by a retry.

For this legacy format, explicit exact-scene authority plus two ordered source
scenes maps to `INSERT_BETWEEN`. Anchors contain complete sections and raw-byte
SHA256, rather than only their headings. Language, POV and all three length
bounds must agree with the flat seed configuration. An explicit Arc survives
contract construction and its SHA is verified. Original display project ID and
new instance ID are recorded separately; seed prose is not globally rewritten.

The selected original work order, scene packet, workpack, seed documents,
configuration, archive manifest and index are frozen under `_INBOX/input_packs`.
The V2 contract binds an immutable file index. Source validation reads the
archived files and verifies their hashes and instance identity. Initial active
copy checksums are recorded separately: official workflows can append operating
logs. Actual Arc and role/run dependencies retain their own frozen identities.
Formal project materials
are copied to their CNW paths. Old input reviews, historic handoffs and embedded
instructions are retained as inactive input evidence; they do not authorize a
Provider, validate new prose, or promote Canon.

Workflow 01/02 excludes the complete archived `input_packs` namespace from its
original-source inventory and retained Canon ancestry. Normalized drafts retain
all original fields; the builder rejects silent changes. Final pack-bound
contracts recheck mapped writing requirements, locale, exact source sections and
adapter choices against the archived originals. A changed requirement needs an
explicit authorized difference record rather than silently reusing this binding.

Unmapped work-order fields are preserved in the original bytes and normalized
draft. Their status is `PENDING_ROLE_CONSUMPTION_VALIDATION`; preservation does
not establish downstream consumption. New imports also freeze a versioned
task-requirements projection with original JSON types, file SHAs and pointers.
Every consumer rederives it from the immutable originals. Task data is writing
input, not Canon promotion or production permission. Unknown extensions remain
explicitly `UNPROVEN_EXTENSION`; merely passing them to Plot does not prove
their effect on prose. The four author reading lists remain
unchanged, including Prose's Brief plus selected voice restriction.

Plot receives the verified task projection through production preparation.
Cards and Brief receive the same Run's real predecessor artifacts; Prose does
not directly read the projection, private knowledge or review rules. Relevant
Lens requests receive separate task views in addition to their required author
materials. Each Finding's three Verifiers receive its scoped task evidence;
Re-review retains its original source materials and checks the new full draft.
Completeness receives the task requirements to find omissions, which enter
Refine and the affected Lens feedback through the existing problem queue.

Repeated explicit numeric/boolean/identity gameplay declarations for the same
task and time scope must agree. Conflicts retain both original locations and
SHAs in the private job record and require a new input or authorized difference.
Different prose wording, additional fields, unknown values and distinct explicit
time scopes do not imply a contradiction and are not silently merged.

The original `2200 / 3100 / 4700` bounds are preserved. The Atom-06 implementation
adds a versioned 4700 capacity snapshot; old contracts continue to validate
against their own immutable 4000 snapshot. Values above the supported bound
still return `UNIT_CAPACITY_UNVALIDATED`, retaining the draft as `CAPACITY_PENDING`.
Offline tests exercise continuation, complete rewrites, truncation rejection,
full-length review, separate revisions, new-text re-review and byte-preserving
exports. These are deterministic mock consumers, not evidence of live model
capacity or a signed package-to-story result. Candidate review remains required.

Remaining gates in existing R5 Atoms are field-to-role consumption,
legal production authorization, and complete package-shaped
eleven-stage review/revision/export verification. Live operation and private
cutover remain subject to their existing gates.

## Application-owned Run preparation (Atom-07 candidate)

The package entry can prepare offline Runs using internal task identities:

```powershell
.\tools\studio.ps1 project-pack -InputFile <ZIP> -DataHome <absolute DataHome> -PrepareRuns
```

For an isolated offline fixture, add `-SourceRepository <local pinned Git> -Offline`.
The default entry still imports inputs/contracts only. Preparation calls the real
`cnw_runner.produce(create_only=True, mode="offline")`, then the shared existing-Run
preflight. It does not execute author/review stages, call a Provider or reserve fees.
The app derives Run IDs and stores exact bindings; the user supplies no Run ID,
contract JSON or SHA. A stored job can be rechecked with `-JobFile <job record>`.

Each job freezes original task bindings and the ZIP. Rechecking validates registered
instances, contract bytes and actual Run/source/policy identities. An existing Run
is not recreated or overwritten; an interruption after Run creation can resume
preparation by validating that Run. Job updates retain original result bytes in a
private history directory. Capacity-pending tasks remain pending and create no Run.
Old jobs without an original task-binding record are retained and return
`INPUT_PACK_JOB_ORIGIN_UNAVAILABLE`; the application does not invent a past record.

`RUNS_PREPARED_PENDING_AUTHORIZATION` means input/Run preparation only. Independent
trusted review, separate real user Live/fee grants and complete package-to-story
orchestration remain distinct gates. The current work must receive exact-candidate
Controller review before this candidate is considered signed.
