# Writing package adaptation and application-owned execution

`tools.cnw_input_pack.prepare_scene_input` adapts the declared V5 scene-pack
format into a private registered project and a V2 draft. The package describes
the materials and writing requirements; the pinned CNW engine owns the workflow.
This API is the legacy input/contract layer. `studio.ps1 project-pack` is the
formal package entry. Legacy scene tasks use separate registered instances;
native V2 tasks share their declared project group and remain isolated from
other groups.

```powershell
.\tools\studio.ps1 project-pack -InputFile <ZIP> -DataHome <absolute-path>
```

`-Offline` selects source acquisition behavior only; it does not select model
execution. To execute the prepared package job, pass an explicit execution mode:

```powershell
.\tools\studio.ps1 project-pack -JobFile <job-record> -DataHome <absolute-path> -Offline -Mode offline -ExecuteJob
```

`-Mode offline` requests offline CNW execution and never grants a Provider call.
The normal CLI does not expose a user-selectable mock-response switch; without
an explicitly isolated test transport, generic V2 Provider stages fail closed.
In tests, the existing final model boundary may be replaced by a fixture-bound
simulated transport, whose receipts remain marked `SIMULATED`/`MOCK_ONLY`.
`-Mode live` preserves Live intent in an independent execution attempt; it never
silently falls back to offline or relabels a simulated Run. The real checked
stages, request-bound Controller/Owner interfaces and shared accounting have
current07 offline engineering acceptance. Production trust deployment is still
pending. Missing or invalid grants refuse before Key, slot, reserve and HTTP;
an available Key, an engineering ACCEPT or ZIP import is not a grant.
`-NewAttempt` requires explicit Live execution and preserves all older attempts,
contracts, histories and fees. The actual owner package's full story delivery
has not been accepted.

Use `-SourceRepository <local-Git-repository> -Offline` for a local source.
Without a local repository the app uses a private DataHome cache for the exact
declared GitHub commit. `-Offline` forbids network fallback, including implicit
Git partial-clone fetches. Source repositories are never checked out or modified.
Temporary source staging is also under the selected DataHome.

## Native V2 packages

`workpack_index.json` uses `schema="cnw_workpack_index_v2"` with nonempty
`projects` and `tasks` arrays. `PACK_MANIFEST.json` binds archive bytes. Each
project declares an `alias`, display `project_id`, CNW `materials` directory,
explicit `fifth_lens.id/responsibility`, and optional source declarations.
An alias is a portable package-local name, not a copied instance identity.
The app generates and registers the instance and internal task/Run IDs.

Each source declares a distinct alias, `format` (`md`, `txt`, or `json`) and
either a package `file` or a pinned Git `authority`. Materials are writing
inputs, never installed registry, run_state, receipts, ledger, Key or executable
instructions. Each task points to a writing `requirements` JSON; requirements
cannot supply internal permissions, Policy, Provider, source/instance identities
or overwrite reserved contract fields. They preserve explicit locale, POV,
target/reference bounds and story requirements.

| Intent | Explicit source/dependency | Actual interpretation |
|---|---|---|
| `INSERT_BETWEEN` | Project's source alias and selection containing ordered anchors | Use the frozen real anchors; preserve required entry/exit and original route |
| `ADAPT_SOURCE` | Project's source alias and line-range or JSON Pointer selection | Consume the selected revision/value; no fabricated before/after anchors |
| `ORIGINAL_EPISODE` | No source/selection; `kind="episode"`, boolean `first_episode` | First episode uses its Canon/Arc; continuation selects `previous_task` in the same project |

The parser orders dependencies, rejects cycles, missing/foreign predecessors
and ambiguous sources, and retains original declarations. JSON canonical value
identity and actual wire excerpt bytes have separate hashes. A continuation
materializes only from a qualifying predecessor in its execution mode; simulated
carry-forward is a fixture identity and cannot enter production continuity.
Project/task imports and interruption histories are not overwritten on retry.

Native bindings use `cnw_native_input_binding_v1` and independent-attempt
`cnw_native_input_binding_v2`. Jobs use `cnw_input_pack_job_v2`; legacy jobs keep
their original format. These are StoryStudio interfaces, not CNW upstream schemas.

## Legacy scene packages

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

Original numeric goals/reference bounds are preserved. New V2 contracts freeze
`unit.length_policy="ADVISORY"`: being above/below the reference does not trigger
length-only continuation, rewriting or rejection. Actual required events,
omissions and content findings still flow through Completeness/Refine/Re-review.
Empty output, transport truncation, input/output token caps and approved fees
remain independent hard checks. Old contracts without the field keep their
historical capacity/length semantics and snapshots; old `CAPACITY_PENDING`
records are not rewritten to manufacture progress. Offline consumer evidence
does not prove Live capacity, story quality or final package acceptance.

Remaining gates in existing R5 Atoms are field-to-role consumption,
legal production authorization, and complete package-shaped
eleven-stage review/revision/export verification. Live operation and private
cutover remain subject to their existing gates.

## Application-owned Run preparation and current gates

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
orchestration remain distinct gates. Current07 offline engineering is frozen at
`b93d0094`; current08 safe engineering and current09 product verification remain
unaccepted. The final gate requires all tasks in the owner's actual package to
produce, review and export their requested stories, with traceable requirements
and true Provider receipts. It cannot be satisfied by parser success or mocks.
