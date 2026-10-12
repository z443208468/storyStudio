"""Adapt declared legacy CNW scene packs without running their installer.

Input documents and old review declarations remain private input evidence.
The adapter grants neither Canon promotion nor production authorization.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

try:
    from .cnw_contract import ContractError, _safe_source_file, resolve_json_pointer
    from .cnw_project import (_registered_project_identity, _reject_duplicate_json_keys,
                              _initialize_project_root, _import_source_unlocked)
    from .project_transactions import project_write_lock
except ImportError:  # existing direct-script contract CLI
    from cnw_contract import ContractError, _safe_source_file, resolve_json_pointer
    from cnw_project import (_registered_project_identity, _reject_duplicate_json_keys,
                            _initialize_project_root, _import_source_unlocked)
    from project_transactions import project_write_lock

METHOD_PIN = "97ad71fe5e5e76a82275c6c63d4add06fb60ab6e"
MAX_PACK_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
ACTIVE_DIRS = {"00_meta", "01_theme", "02_logline", "03_project_design",
               "04_chapter_design", "90_canon", "92_style_engine", "93_data", "94_runtime"}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("INPUT_PACK_JSON_INVALID", "input declaration is not UTF-8 JSON") from exc


def _bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _safe_name(name: str) -> str:
    parts = name.split("/")
    if (not name or "\\" in name or "\x00" in name or
            any(not p or p in {".", ".."} or re.search(r'[<>:"|?*\x00-\x1f]', p) or p.endswith((".", " ")) or
                re.match(r"^(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)", p, re.I)
                for p in parts)):
        raise ContractError("INPUT_PACK_PATH_UNSAFE", "archive path is not a portable relative path")
    return PurePosixPath(name).as_posix()


def read_input_pack(path: str | Path) -> dict:
    """Verify the complete declaration before selecting any scene or writing."""
    archive = Path(path).read_bytes()
    if len(archive) > MAX_PACK_BYTES:
        raise ContractError("INPUT_PACK_TOO_LARGE", "compressed archive exceeds the input limit")
    files, folded, total = {}, set(), 0
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            if len(z.infolist()) > 5000:
                raise ContractError("INPUT_PACK_TOO_LARGE", "too many archive entries")
            for info in z.infolist():
                name = _safe_name(info.filename.rstrip("/") if info.is_dir() else info.filename)
                if name.casefold() in folded:
                    raise ContractError("INPUT_PACK_DUPLICATE_PATH", "duplicate or case-conflicting archive path")
                folded.add(name.casefold())
                if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                    raise ContractError("INPUT_PACK_PATH_UNSAFE", "links and encrypted entries are unsupported")
                if info.is_dir():
                    continue
                total += info.file_size
                if info.file_size > MAX_FILE_BYTES or total > MAX_PACK_BYTES:
                    raise ContractError("INPUT_PACK_TOO_LARGE", "expanded archive exceeds the input limit")
                files[name] = z.read(info)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise ContractError("INPUT_PACK_ARCHIVE_INVALID", "cannot verify archive bytes") from exc
    manifests = [n for n in files if n == "PACK_MANIFEST.json" or n.count("/") == 1 and n.endswith("/PACK_MANIFEST.json")]
    if len(manifests) != 1:
        raise ContractError("INPUT_PACK_MANIFEST_REQUIRED", "select one declared pack root")
    manifest_name = manifests[0]
    prefix = manifest_name.removesuffix("PACK_MANIFEST.json")
    if any(not n.startswith(prefix) for n in files):
        raise ContractError("INPUT_PACK_PATH_UNSAFE", "archive contains files outside its declared root")
    files = {n[len(prefix):]: raw for n, raw in files.items()}
    manifest = _json(files["PACK_MANIFEST.json"])
    if not isinstance(manifest, dict) or manifest.get("schema") != "CQ_INPUT_PACK_MANIFEST_V5" or not isinstance(manifest.get("files"), dict):
        raise ContractError("INPUT_PACK_FORMAT_UNSUPPORTED", "unsupported manifest declaration")
    declared = manifest["files"]
    if set(declared) != set(files) - {"PACK_MANIFEST.json"}:
        raise ContractError("INPUT_PACK_FILE_SET_MISMATCH", "manifest and archive file sets differ")
    for name, expected in declared.items():
        _safe_name(name)
        if not isinstance(expected, str) or _sha(files[name]) != expected.lower():
            raise ContractError("INPUT_PACK_HASH_MISMATCH", "declared file bytes differ")
    for name in files:
        if any(parent.as_posix() in files for parent in PurePosixPath(name).parents if parent.as_posix() != "."):
            raise ContractError("INPUT_PACK_PATH_UNSAFE", "archive file is also a parent directory")
    index = _json(files.get("workpack_index.json", b"{}"))
    if not isinstance(index, dict) or index.get("schema") != "cnw_workpack_index_v1" or not isinstance(index.get("workpacks"), list):
        raise ContractError("INPUT_PACK_INDEX_INVALID", "declared workpack index is missing")
    scenes = []
    for item in index["workpacks"]:
        if not isinstance(item, dict) or not isinstance(item.get("root"), str):
            raise ContractError("INPUT_PACK_INDEX_INVALID", "workpack entry requires a root")
        seed = _safe_name(item["root"])
        if not re.fullmatch(r"scenes/[^/]+/project_seed", seed):
            raise ContractError("INPUT_PACK_INDEX_INVALID", "unsupported scene seed layout")
        scene = seed.removesuffix("/project_seed")
        if scene in scenes or scene + "/work_order.draft.json" not in files:
            raise ContractError("INPUT_PACK_INDEX_INVALID", "duplicate scene or missing work order")
        scenes.append(scene)
    if not scenes or {n.removesuffix("/work_order.draft.json") for n in files if re.fullmatch(r"scenes/[^/]+/work_order\.draft\.json", n)} != set(scenes):
        raise ContractError("INPUT_PACK_INDEX_INVALID", "work orders and declared scenes differ")
    return {"pack_sha256": _sha(archive), "files": files, "scenes": scenes}


def _source_bytes(repository: str | Path, authority: dict) -> bytes:
    if not isinstance(authority, dict):
        raise ContractError("INPUT_PACK_AUTHORITY_REQUIRED", "work order must declare its original authority")
    commit, blob, path = (authority.get(k) for k in ("commit", "blob_sha1", "source_file"))
    if (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit) or
            not isinstance(blob, str) or not re.fullmatch(r"[0-9a-f]{40}", blob) or not isinstance(path, str)):
        raise ContractError("INPUT_PACK_AUTHORITY_INVALID", "authority requires exact commit, blob and path")
    _safe_name(path)
    repo = Path(repository).resolve(strict=True)
    # Read-only object access must not silently fetch promised objects from a
    # partial clone. Source acquisition belongs to the explicit app cache path.
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
    kind = subprocess.run(["git", "--no-pager", "-c", "protocol.allow=never", "-C", str(repo), "cat-file", "-t", commit],
                          env=env, capture_output=True, timeout=30)
    if kind.returncode:
        raise ContractError("PINNED_SOURCE_UNAVAILABLE", "declared commit object is absent in the selected repository")
    if kind.stdout.strip() != b"commit":
        raise ContractError("INPUT_PACK_AUTHORITY_INVALID", "declared source commit is not a commit object")
    result = subprocess.run(["git", "--no-pager", "-c", "protocol.allow=never", "-C", str(repo), "show", f"{commit}:{path}"],
                            env=env, capture_output=True, timeout=30)
    if result.returncode:
        raise ContractError("PINNED_SOURCE_UNAVAILABLE", "declared source object is absent in the selected repository")
    raw = result.stdout
    if hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest() != blob:
        raise ContractError("PINNED_SOURCE_BLOB_MISMATCH", "selected source object differs from the declared blob")
    return raw


def _scene_anchor(raw: bytes, name: str) -> dict:
    if not isinstance(name, str) or not name.strip():
        raise ContractError("SOURCE_ANCHOR_INVALID", "work order must name both source scenes")
    try:
        lines = raw.splitlines(keepends=True)
        titles = [line.decode("utf-8-sig").strip() for line in lines]
    except UnicodeError as exc:
        raise ContractError("IMPORT_ENCODING_INVALID", "source scene must be UTF-8") from exc
    pattern = re.compile(r"^##\s+" + re.escape(name) + r"(?:[|｜\s]|$)")
    found = [i for i, title in enumerate(titles) if pattern.search(title)]
    if len(found) != 1:
        raise ContractError("SOURCE_ANCHOR_AMBIGUOUS", "named source scene is absent or repeated")
    start = found[0]
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^##\s+", titles[i])), len(lines))
    while end > start + 1 and not titles[end - 1]:
        end -= 1
    if end == start + 1:
        raise ContractError("SOURCE_ANCHOR_EMPTY", "scene heading has no source content")
    return {"scene": name, "source_line": start + 1, "source_line_end": end,
            "sha256": _sha(b"".join(lines[start:end]))}


def _locale(raw: bytes, work_order: dict) -> str:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ContractError("INPUT_PACK_CONFIG_INVALID", "project config must be UTF-8") from exc
    # The legacy format declares flat scalar YAML. Read only these identity
    # scalars; no executable YAML tags, object constructors or default locale.
    values = {}
    for key in ("language", "project_id", "work_unit", "method_pin", "source_pin",
                "target_visible_chars", "min_visible_chars", "max_visible_chars", "pov", "unit_kind", "planning_mode"):
        found = re.findall(r"^" + key + r":\s*([^\n\r]+?)\s*$", text, re.M)
        if len(found) != 1:
            raise ContractError("INPUT_PACK_CONFIG_INVALID", f"one explicit flat {key} is required")
        values[key] = found[0].strip()
    if (values["project_id"] != work_order.get("project_id") or values["work_unit"] != work_order.get("unit_id") or
            values["method_pin"] != METHOD_PIN or values["source_pin"] != work_order.get("source_pin")):
        raise ContractError("INPUT_PACK_IDENTITY_MISMATCH", "seed config and work order identities differ")
    for key, field in (("unit_kind", "kind"), ("planning_mode", "planning_mode"), ("pov", "pov"),
                       ("target_visible_chars", "target_visible_chars"), ("min_visible_chars", "min_visible_chars"),
                       ("max_visible_chars", "max_visible_chars")):
        if values[key] != str(work_order.get(field)):
            raise ContractError("INPUT_PACK_CONFIG_MISMATCH", "work order and config disagree on the writing requirements")
    return values["language"]


def _active_seed(relative: str) -> bool:
    parts = relative.split("/")
    return (parts[0] in ACTIVE_DIRS or relative == "07_draft/manuscript_index.md") and Path(relative).suffix.lower() in {".md", ".txt", ".json", ".yml", ".yaml"}


def _validate_lens_derivation(raw: bytes, derivation: dict, responsibility: str) -> None:
    try:
        if _sha(raw) != derivation.get("source_sha256") or derivation.get("derived_responsibility") != responsibility:
            raise ValueError("source identity differs")
        locator = derivation["locator"]
        if "json_pointer" in locator:
            if locator["json_pointer"] != "/review/fifth_lens/responsibility":
                raise ValueError("not the project fifth Lens field")
            value = resolve_json_pointer(_json(raw), locator["json_pointer"])
            if not isinstance(value, str) or value != derivation["original_text"] or value.strip() != responsibility:
                raise ValueError("selected JSON responsibility differs")
        else:
            line = locator["line"]
            lines = raw.decode("utf-8-sig").splitlines()
            if type(line) is not int or not 1 <= line <= len(lines) or lines[line-1] != derivation["original_text"]:
                raise ValueError("selected duty row differs")
            cells = [v.strip() for v in lines[line-1].strip().strip("|").split("|")]
            if len(cells) != 3 or cells[0].casefold() not in {"story-specific lens", "story_specific lens", "第五 lens"} or cells[2] != responsibility:
                raise ValueError("not an explicit story-specific duty")
    except (KeyError, TypeError, ValueError, UnicodeError, ContractError) as exc:
        raise ContractError("INPUT_PACK_LENS_DERIVATION_INVALID", "derived fifth Lens does not match its actual seed locator") from exc


def prepare_scene_input(pack_path: str | Path, *, scene_root: str, project_root: str | Path,
                        source_repo: str | Path, fifth_lens: dict,
                        source_staging_root: str | Path | None = None) -> dict:
    """Prepare one new registered instance and V2 draft, preserving all inputs.

    Contract creation and capacity validation remain in cnw_project.
    Unsupported bounds are retained, never lowered by the input adapter.
    """
    pack = read_input_pack(pack_path)
    if scene_root not in pack["scenes"]:
        raise ContractError("INPUT_PACK_SCENE_REQUIRED", "select one scene from the verified index")
    files = pack["files"]
    draft_name = scene_root + "/work_order.draft.json"
    order = _json(files[draft_name])
    if not isinstance(order, dict) or order.get("kind") != "scene" or order.get("planning_mode") != "author_plot":
        raise ContractError("INPUT_PACK_WORK_ORDER_UNSUPPORTED", "this adapter requires an author-planned scene")
    authority = order.get("original_authority")
    if not isinstance(authority, dict):
        raise ContractError("INPUT_PACK_AUTHORITY_REQUIRED", "work order must declare its original authority")
    if order.get("author_method_pin") != METHOD_PIN or order.get("source_pin") != authority.get("commit"):
        raise ContractError("INPUT_PACK_IDENTITY_MISMATCH", "work order pins differ")
    if (order.get("work_intent", "INSERT_BETWEEN") != "INSERT_BETWEEN" or
            authority.get("binding_policy") != "PINNED_GIT_BLOB_EXACT_CUE_SECTION"):
        raise ContractError("WORK_INTENT_UNSUPPORTED", "legacy insertion needs an explicit exact-scene source binding")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,95}", str(order.get("unit_id"))):
        raise ContractError("WORK_UNIT_ID_INVALID", "unsafe work unit ID")
    seed_prefix = scene_root + "/project_seed/"
    seed = {n[len(seed_prefix):]: raw for n, raw in files.items() if n.startswith(seed_prefix)}
    workpack = _json(seed.get("workpack.json", b"{}"))
    packet = _json(seed.get("scene_packet.json", b"{}"))
    if (not isinstance(workpack, dict) or workpack.get("schema") != "cnw_story_prep_v1" or
            workpack.get("project_id") != order.get("project_id") or workpack.get("upstream_commit") != METHOD_PIN or
            not isinstance(packet, dict) or packet.get("standalone_trial") is not True):
        raise ContractError("INPUT_PACK_WORKPACK_INVALID", "this format requires a pinned standalone scene workpack")
    context = seed.get(order.get("source_context_file", ""), b"").decode("utf-8-sig")
    if not context.strip():
        raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "source_context_file")
    for name in seed:
        if (any(part.lower() in {"runs", "runtime", "deliverables", ".git", "provider_raw"} for part in name.split("/")) or
                Path(name).name.lower().startswith(".env") or Path(name).suffix.lower() in {".pem", ".key"} or
                Path(name).name.lower() in {"run_state.json", "cost_ledger.json", "cost_ledger.jsonl"}):
            raise ContractError("INPUT_PACK_PRIVATE_RUNTIME_UNSUPPORTED", "seed must contain inputs rather than keys or prior run data")
    locale = _locale(seed.get("config/project.yml", b""), order)
    if not isinstance(fifth_lens, dict) or not all(isinstance(fifth_lens.get(k), str) and fifth_lens[k].strip() for k in ("id", "responsibility")):
        raise ContractError("PRE_FLIGHT_MISSING_PROJECT_INPUT", "explicit fifth Lens duties are required")
    source = _source_bytes(source_repo, order["original_authority"])
    before = _scene_anchor(source, order["original_authority"].get("before_scene"))
    after = _scene_anchor(source, order["original_authority"].get("after_scene"))
    if before["source_line_end"] >= after["source_line"]:
        raise ContractError("SOURCE_ANCHOR_INVALID", "source scenes must be ordered and non-overlapping")
    root = Path(project_root).resolve(strict=True)
    identity = _registered_project_identity(root)
    staging = None
    if source_staging_root is not None:
        try:
            from .project_paths import _ensure_private_directory
        except ImportError:
            from project_paths import _ensure_private_directory
        staging = _ensure_private_directory(Path(source_staging_root), root=root.parent.parent,
                                            code="INPUT_PACK_STAGING_UNSAFE")
    derivation = fifth_lens.get("derivation")
    if derivation is not None:
        if (not isinstance(derivation, dict) or derivation.get("source_file") not in seed or
                _sha(seed[derivation["source_file"]]) != derivation.get("source_sha256") or
                derivation.get("derived_responsibility") != fifth_lens["responsibility"].strip()):
            raise ContractError("INPUT_PACK_LENS_DERIVATION_INVALID", "fifth Lens must retain its actual seed source identity")
        _validate_lens_derivation(seed[derivation["source_file"]], derivation, fifth_lens["responsibility"].strip())
    def require_empty():
        if any(p.name not in {"project_identity.json", ".story-studio-project-write.lock"} for p in root.iterdir()):
            raise ContractError("INPUT_PACK_TARGET_NOT_EMPTY", "seed import requires a fresh registered instance")
    require_empty()
    with project_write_lock(root):
        require_empty()
        snapshot = f"_INBOX/input_packs/{pack['pack_sha256']}"
        records = {}
        selected = {"PACK_MANIFEST.json": files["PACK_MANIFEST.json"], "workpack_index.json": files["workpack_index.json"],
                    draft_name: files[draft_name], **{seed_prefix + n: raw for n, raw in seed.items()}}
        for name, raw in selected.items():
            target = root / snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(raw)
            records[f"{snapshot}/{name}"] = _sha(raw)
        active, initial_active_sha256 = [], {}
        for name, raw in seed.items():
            if not _active_seed(name):
                continue
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(raw)
            # Active project files remain editable by official workflows.
            # Their initial transfer is recorded; the archived input bytes
            # stay immutable and actual role/run dependencies freeze separately.
            initial_active_sha256[name] = _sha(raw)
            active.append(name)
        try:
            from . import cnw_task_requirements as task_requirements
        except ImportError:
            import cnw_task_requirements as task_requirements
        task_sources = {"work_order": (f"{snapshot}/{draft_name}", files[draft_name]),
                        "scene_packet": (f"{snapshot}/{seed_prefix}scene_packet.json", seed["scene_packet.json"])}
        for key, name in (("temporal_envelope", "93_data/temporal_envelope.json"),
                          ("gameplay_snapshot", "93_data/gameplay_snapshot.json")):
            if name in seed:
                task_sources[key] = (f"{snapshot}/{seed_prefix}{name}", seed[name])
        task_context = task_requirements.derive_task_context(sources=task_sources, identity=identity,
                                                            scene_root=scene_root, pack_sha256=pack["pack_sha256"])
        task_raw = task_requirements.encode(task_context)
        task_name = f"{snapshot}/derived/task_requirements.v1.json"
        target = root / task_name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as out:
            out.write(task_raw)
        records[task_name] = _sha(task_raw)
        index = {"schema_version": "cnw_input_pack_binding_v1", "pack_sha256": pack["pack_sha256"],
                 "project_instance_id": identity["project_instance_id"], "scene_root": scene_root,
                 "original_project_id": order["project_id"], "project_id": identity["project_id"],
                 "files": records, "original_work_order": f"{snapshot}/{draft_name}",
                 "active_materials": sorted(active), "input_review_status": "UNTRUSTED_INPUT_DECLARATIONS",
                 "initial_active_sha256": initial_active_sha256,
                 "task_context": {"schema_version": task_requirements.SCHEMA, "recipe_version": task_requirements.RECIPE,
                                  "file": task_name, "sha256": _sha(task_raw)},
                 "adapter_choices": {"fifth_lens": {k: fifth_lens[k].strip() for k in ("id", "responsibility")},
                                     **({"fifth_lens_derivation": derivation} if derivation is not None else {}),
                                     "integrations": {"nk": "DISABLED", "critics": "DISABLED"}},
                 "field_consumption_status": "PENDING_ROLE_CONSUMPTION_VALIDATION"}
        index_name = f"{snapshot}/binding.json"
        (root / index_name).write_bytes(_bytes(index))
        # Use the existing implementations inside this same transaction;
        # their public wrappers would reacquire the non-reentrant project lock.
        _initialize_project_root(root, identity["project_id"], new_project=True)
        with tempfile.TemporaryDirectory(prefix="storystudio-pack-source-", dir=staging) as temp:
            source_file = Path(temp) / PurePosixPath(order["original_authority"]["source_file"]).name
            source_file.write_bytes(source)
            imported = _import_source_unlocked(input_file=source_file, project_root=root)
        normalized = {**order, "schema_version": "cnw_work_unit_draft_v2", "work_intent": "INSERT_BETWEEN",
                  "language_locale": locale, "chapter_context": context,
                  "before_scene": before["scene"], "after_scene": after["scene"],
                  "before_line": before["source_line"], "before_line_end": before["source_line_end"],
                  "after_line": after["source_line"], "after_line_end": after["source_line_end"],
                  "source_id": imported["source_id"], "source_revision_id": imported["source_revision_id"],
                  "source_manifest_revision_sha256": imported["source_manifest_sha256"],
                  "source_index_revision_sha256": imported["source_index_sha256"],
                  "review": {"fifth_lens": fifth_lens}, "integrations": {"nk": "DISABLED", "critics": "DISABLED"},
                  "input_pack": {"schema_version": "cnw_input_pack_binding_v1", "pack_sha256": pack["pack_sha256"],
                                 "index_file": index_name, "index_sha256": _sha(_bytes(index))}}
        draft_path = root / "contracts" / f"{order['unit_id']}.draft.json"
        with draft_path.open("xb") as out:
            out.write(_bytes(normalized))
    return {"status": "INPUT_PACK_DRAFT_PREPARED", "project_root": str(root), "draft": str(draft_path),
            "pack_sha256": pack["pack_sha256"], "original_project_id": order["project_id"],
            "project_instance_id": identity["project_instance_id"], "provider_call": "none",
            "field_consumption_status": "PENDING_ROLE_CONSUMPTION_VALIDATION",
            "requested_max_visible_chars": order.get("max_visible_chars"),
            "capacity_status": "PENDING_CONTRACT_VALIDATION",
            "inactive_seed_files": sorted(set(seed) - set(active))}


def validate_input_pack_binding(project_root: Path, binding: dict, *, contract: dict | None = None) -> dict:
    if not isinstance(binding, dict) or binding.get("schema_version") != "cnw_input_pack_binding_v1":
        raise ContractError("INPUT_PACK_BINDING_INVALID", "unsupported binding schema")
    pack_sha = binding.get("pack_sha256")
    if (not isinstance(pack_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", pack_sha) or
            binding.get("index_file") != f"_INBOX/input_packs/{pack_sha}/binding.json" or
            not isinstance(binding.get("index_sha256"), str)):
        raise ContractError("INPUT_PACK_BINDING_INVALID", "binding must select its own immutable pack index")
    index_raw = _safe_source_file(project_root, binding.get("index_file", "")).read_bytes()
    if _sha(index_raw) != binding.get("index_sha256"):
        raise ContractError("INPUT_PACK_BINDING_HASH_MISMATCH", "input binding changed")
    index = _json(index_raw)
    identity = _json(_safe_source_file(project_root, "project_identity.json").read_bytes())
    if (not isinstance(index, dict) or index.get("schema_version") != binding["schema_version"] or
            index.get("pack_sha256") != binding.get("pack_sha256") or
            index.get("project_instance_id") != identity.get("project_instance_id") or
            index.get("project_id") != identity.get("project_id") or
            not isinstance(index.get("files"), dict) or not index["files"]):
        raise ContractError("INPUT_PACK_BINDING_INVALID", "input binding differs from this project instance")
    for name, expected in index["files"].items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ContractError("INPUT_PACK_BINDING_INVALID", "material records require paths and byte hashes")
        if _sha(_safe_source_file(project_root, name).read_bytes()) != expected:
            raise ContractError("INPUT_PACK_MATERIAL_CHANGED", "frozen work order or seed material changed")
    choices = index.get("adapter_choices", {})
    if index.get("task_context") is not None:
        try:
            from .cnw_task_requirements import verify_bound_task_context
        except ImportError:
            from cnw_task_requirements import verify_bound_task_context
        verify_bound_task_context(project_root, index)
    derivation = choices.get("fifth_lens_derivation")
    if derivation is not None:
        prefix = f"_INBOX/input_packs/{index['pack_sha256']}/{index['scene_root']}/project_seed/"
        raw = _safe_source_file(project_root, prefix + derivation["source_file"]).read_bytes()
        _validate_lens_derivation(raw, derivation, choices["fifth_lens"]["responsibility"])
    if contract is not None:
        _validate_mapped_requirements(project_root, index, contract)
    return index


def _original_order(project_root: Path, index: dict) -> dict:
    return _json(_safe_source_file(project_root, index["original_work_order"]).read_bytes())


def validate_input_pack_draft(project_root: Path, draft: dict) -> None:
    index = validate_input_pack_binding(project_root, draft["input_pack"])
    original = _original_order(project_root, index)
    if any(key not in draft or _bytes(draft[key]) != _bytes(value) for key, value in original.items()):
        raise ContractError("INPUT_PACK_REQUIREMENT_MISMATCH", "normalized draft changed an original requirement without an authorization diff")


def _validate_mapped_requirements(root: Path, index: dict, contract: dict) -> None:
    original = _original_order(root, index)
    unit, story = contract.get("unit", {}), contract.get("story", {})
    def require(actual, expected):
        if actual != expected:
            raise ContractError("INPUT_PACK_REQUIREMENT_MISMATCH", "contract no longer represents the selected input task")
    require(contract.get("work_intent"), "INSERT_BETWEEN")
    for key, field in (("id", "unit_id"), ("kind", "kind"), ("planning_mode", "planning_mode"), ("pov", "pov"),
                       ("target_visible_chars", "target_visible_chars"), ("min_visible_chars", "min_visible_chars"),
                       ("max_visible_chars", "max_visible_chars")):
        expected = original.get(field)
        require(unit.get(key), expected.strip() if key == "pov" and isinstance(expected, str) else expected)
    for key in ("arc_ref", "entry_state", "exit_state", "role_in_story", "reader_reward", "required_beats",
                "characters_in_scene", "character_knowledge_boundary_ref", "voice_sample_refs", "forbidden_future_revelations"):
        expected = original.get(key)
        require(story.get(key), expected.strip() if isinstance(expected, str) else expected)
    prefix = f"_INBOX/input_packs/{index['pack_sha256']}/{index['scene_root']}/project_seed/"
    locale = _locale(_safe_source_file(root, prefix + "config/project.yml").read_bytes(), original)
    require(unit.get("language_locale"), locale)
    require(unit.get("language"), locale)
    require(story.get("chapter_context"), _safe_source_file(root, prefix + original["source_context_file"]).read_bytes().decode("utf-8-sig").strip())
    require(story.get("arc_sha256"), _sha(_safe_source_file(root, prefix + original["arc_ref"]).read_bytes()))
    for key in ("id", "responsibility"):
        require(contract.get("review", {}).get("fifth_lens", {}).get(key), index["adapter_choices"]["fifth_lens"][key])
    require(contract.get("integrations"), index["adapter_choices"]["integrations"])
    source = _safe_source_file(root, story.get("source_file", "")).read_bytes()
    require(hashlib.sha1(b"blob " + str(len(source)).encode("ascii") + b"\0" + source).hexdigest(), original["original_authority"]["blob_sha1"])
    for kind in ("before", "after"):
        require(story.get(kind + "_anchor"), _scene_anchor(source, original["original_authority"][kind + "_scene"]))
