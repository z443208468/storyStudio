# ATOM-05 native bridge entry: successor evidence

Parent C=`01d348e4ccb2bd905cb1ea30ba64bde0b429f8e0`,
T=`82c10d66aea1c5fc5fb2136c918251eb97afdb5d`.
The independent parent's RETURN is preserved byte-for-byte in
`ATOM05_CONTROLLER_RETURN_01d348e_20261013.md` and has not been changed to ACCEPT.

## Root and actual production boundary

`critics_bridge.main/__main__` previously accepted registered project materials,
created output directories and invoked the native library without the P2
wrapper's account/admission/slot boundary.

The bridge now jointly resolves input, consumed critique and output before
directory creation, Provider configuration or native execution. Registered
participation requires a private typed Python invocation supplied by the
wrapper; a CLI switch, boolean or JSON cannot provide this context. The bridge
revalidates the actual RunAccount against `for_run`, parent/child/project/action/
stage, exact material paths and bytes, and the currently installed accounting
HTTP dispatcher. Legacy input and output remain the legacy route.

The wrapper constructs this context only after its existing bindings and account
checks and supplies its actual per-call capture dispatcher. Its ordinary CLI
authorization remains unchanged. This internal cost context does not grant Live
authorization or independent Controller attestation.

Owned consumers inspected: the P2 wrapper is the production caller of bridge
`main`; W10 and native result adapters consume its path/build helpers; policy
snapshots freeze its source; the old offline diagnostic dynamically imports the
module. The immutable context uses NamedTuple to retain that diagnostic's
existing importlib loading pattern without mandatory sys.modules registration.
No native CritiCS template or method implementation is modified.

## Actual effects and regressions

- Six direct `main` combinations cover registered input, critique or output,
  including three actions. No-context, boolean and JSON context reject before
  Provider configuration and directory creation; slot/reservation spies stay at
  zero, and materials remain unchanged. A network-denied credential-free child
  exercises the real `__main__` branch and rejects with the same guard.
- Registered component positives now execute the actual bridge `main`, guard,
  material reader, directory and output/receipt writers. Only the native model
  method and HTTP transport are deterministic fictional boundaries. Two actual
  registered RunAccounts use the real shared ledger and slot: one SETTLED, one
  nonzero UNKNOWN, followed by real result readback and foreign-parent rejection.
- True legacy compatibility now also runs actual bridge main and output/receipt
  persistence for both legacy output flags. The fictional native boundary reads
  the real input/feedback; zero Provider calls and byte-identical synthetic ledger
  are asserted. Fictional receipts are explicitly marked MOCK_ONLY/SIMULATED.
- The old dynamic import pattern is checked directly. Snapshot consumers and
  native adapter regressions are included in the full affected module run.

`bridge_entry_retest`: exit 1, **51 passed, 26 subtests**, one subprocess fixture
failure. The runpy bootstrap did not reproduce the normal script's tools search
path, so registration could not be resolved in that child. Original failure is
retained. The bootstrap now supplies the normal tools directory; no expected
guard or assertion was weakened. This first check's source map predates adding
the bridge to the external harness's hash list and is not presented as full
bridge provenance.

`python311_bridge_final`: the corresponding first attempt retained the same
fixture failure; three actual component tests passed. It precedes the final
NamedTuple/dynamic-import change and is not the final source verdict.

`bridge_entry_final`: exit 0, **53 passed, 26 subtests**, on all final source bytes
including the bridge. Raw commands, before/after SHA and actual fictional native
artifacts are preserved in the adjacent native-entry manifest/records. The final
Python 3.11 result (`python311_bridge_retest`) is **5 unittest tests OK** on the
same final source bytes, covering direct entry, true V1, registered accounting,
wrapper downgrade and dynamic import.

Earlier promotion/NK sources and evidence are unchanged. Earlier 133/66 is not
claimed as a run of this modified bridge. Parent wrapper-route and all original
RETURN records remain available. No real Provider or private migration ran.

`CURRENT_ATOM=ATOM05; CURRENT_ATOM_CLOSURE_VERDICT=PENDING_CONTROLLER`

`NEXT_ATOM_PERMISSION=DENIED; GIT_PUSH_AUTHORIZATION=PENDING`

`INPUT_PACK_TO_STORY_GATE=RETURN/NOT_RUN; GENERIC_LIVE_PRODUCTION=NOT_RUN`

`CUTOVER_BLOCKED=true; PRIVATE_MIGRATION=NOT_RUN; TS_RESUME=NOT_RUN`
