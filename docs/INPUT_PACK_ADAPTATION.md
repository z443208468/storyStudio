# Legacy scene input adaptation (R5 Atom-03 repair)

`tools.cnw_input_pack.prepare_scene_input` adapts the declared V5 scene-pack
format into a private registered project and a V2 draft. The package describes
the materials and writing requirements; the pinned CNW engine owns the workflow.
This API is the input/contract layer. A studio CLI package route is still pending
Atom-04 repair.

The adapter verifies `PACK_MANIFEST.json` against every archive file, reads
`workpack_index.json`, and selects an explicitly named scene. It obtains the
source through an explicitly selected local Git repository at the work order's
exact commit/path/blob. No checkout, download, embedded installer, or package
instruction is executed. The selected source is registered through the existing
immutable source-manifest/index implementation.

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
not establish downstream consumption. The four author reading lists remain
unchanged, including Prose's Brief plus selected voice restriction.

The original `2200 / 3100 / 4700` bounds are preserved. At this repair stage,
normal contract validation still returns `UNIT_CAPACITY_UNVALIDATED` for 4700.
Atom-06 must validate the capacity and actual consumers before this package can
form a usable production contract. This is not package-to-story acceptance.

Remaining gates in existing R5 Atoms are the CLI entry, field-to-role consumption,
4700 length handling, legal production authorization, and complete package-shaped
eleven-stage review/revision/export verification. Live operation and private
cutover remain subject to their existing gates.
