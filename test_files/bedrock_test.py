"""
bedrock_model_qa.py
===================
Test Bedrock entity/geometry spawning by iterating through a resource pack.

Run inside Blender's scripting workspace with MCprep (and the Bedrock importer)
loaded.  Results are printed to the system console.

Configuration
-------------
Set RESOURCE_PACK_PATH to your resource pack root (the folder that contains
``entity/``, ``models/``, ``textures/`` …).  Leave it empty to fall back to
MCprep's active texture-pack path (``context.scene.mcprep_texturepack_path``).

Scan modes
----------
SCAN_ENTITY_FILES   (recommended, default True)
    Walks  <pack>/entity/  for ``.entity.json`` / ``.json`` files that contain
    a ``minecraft:client_entity`` block.  Tests the full pipeline:
    format detection → geo-file search → armature + mesh creation →
    custom-property storage.

SCAN_GEO_FILES      (default False)
    Walks  <pack>/models/entity/  for ``.geo.json`` files and imports them
    directly without an entity descriptor.

TEST_ALL_GEO_VARIANTS  (default False)
    After a successful entity import, re-imports every geometry variant key
    found in the entity's geometry dict (``baby``, ``snow``, etc.).
    Can multiply the test count significantly — leave False for a quick run.

Validation checks (per import)
-------------------------------
• Active object is an ARMATURE.
• Armature has ≥ 1 bone.
• At least one MESH child exists (empty for bone-only entities → warning only).
• Mesh children have ≥ 4 vertices in total.
• ``mc_identifier`` custom property is set (entity-file imports).
• ``mc_textures`` custom property parses as valid JSON (entity-file imports).
• ``mc_geometry`` custom property lists the variant keys (entity-file imports).
"""

import bpy
import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────────

# Root folder of the Bedrock resource pack to test.
# Leave "" to use MCprep's active texturepack path.
RESOURCE_PACK_PATH: str = ""

# Maximum number of files to process.  None = no limit (very slow for large packs).
MAX_CHECK: Optional[int] = 50

# Which file types to scan for
SCAN_ENTITY_FILES:     bool = True   # entity/*.json  (full pipeline, recommended)
SCAN_GEO_FILES:        bool = False  # models/entity/*.geo.json  (direct geo import)

# Re-import every geometry variant key per entity (slow)
TEST_ALL_GEO_VARIANTS: bool = False

# Keep spawned objects in the scene laid out in a grid
PLACE_IN_GRID: bool = True
SPACING:       float = 2.5   # metres between objects

# Run post-import property checks
VALIDATE_CUSTOM_PROPS: bool = True


# ══════════════════════════════════════════════════════════════════════════════
# Result dataclass
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SpawnResult:
    """Outcome of one import attempt."""
    name:        str               # mob name / file stem
    filepath:    Path
    geo_variant: str = "default"

    success:     bool  = False
    error:       str   = ""
    warnings:    list  = field(default_factory=list)

    obj_name:        str = ""
    bone_count:      int = 0
    mesh_child_count:int = 0
    total_verts:     int = 0

    @property
    def short_path(self) -> str:
        return str(self.filepath.name)


# ══════════════════════════════════════════════════════════════════════════════
# File scanning
# ══════════════════════════════════════════════════════════════════════════════

def find_entity_files(pack_root: Path) -> list[Path]:
    """
    Walk ``<pack_root>/entity/`` for Bedrock client-entity descriptor files.
    A file qualifies if it contains a ``minecraft:client_entity`` top-level key.
    Returns a sorted list of matching paths.
    """
    entity_dir = pack_root / "entity"
    if not entity_dir.is_dir():
        print(f"[QA] entity/ folder not found in pack: {pack_root}")
        return []

    found: list[Path] = []
    for fpath in sorted(entity_dir.rglob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if "minecraft:client_entity" in data:
                found.append(fpath)
        except Exception:
            pass  # corrupt / non-JSON files are silently skipped

    print(f"[QA] Found {len(found)} entity files under {entity_dir}")
    return found


def find_geo_files(pack_root: Path) -> list[Path]:
    """
    Walk standard Bedrock geometry directories for raw geo JSON files.
    Search order: ``models/entity/`` → ``models/`` → ``entity/``.
    A file qualifies if it contains ``minecraft:geometry`` or a
    legacy ``geometry.*`` top-level key.
    """
    search_dirs = [
        pack_root / "models" / "entity",
        pack_root / "models",
        pack_root / "entity",
    ]
    found: list[Path] = []
    seen: set[Path] = set()

    for d in search_dirs:
        if not d.is_dir():
            continue
        for fpath in sorted(d.rglob("*.json")):
            if fpath in seen:
                continue
            seen.add(fpath)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if "minecraft:geometry" in data or any(
                    k.startswith("geometry.") for k in data
                ):
                    found.append(fpath)
            except Exception:
                pass

    print(f"[QA] Found {len(found)} geo files under {pack_root}")
    return found


# ══════════════════════════════════════════════════════════════════════════════
# Post-import validation
# ══════════════════════════════════════════════════════════════════════════════

def validate_import(
    arm_obj: bpy.types.Object,
    result:  SpawnResult,
    is_entity_import: bool,
) -> None:
    """
    Run post-import checks and populate *result* with counts and warnings.
    Sets ``result.success = True`` only if the critical checks pass.
    """
    # ── Must be an armature ───────────────────────────────────────────────────
    if arm_obj is None:
        result.error = "Active object is None after import"
        return
    if arm_obj.type != 'ARMATURE':
        result.error = (
            f"Active object '{arm_obj.name}' is {arm_obj.type}, expected ARMATURE"
        )
        return

    result.obj_name   = arm_obj.name
    result.bone_count = len(arm_obj.data.bones)

    if result.bone_count == 0:
        result.error = "Armature has no bones"
        return

    # ── Mesh children ─────────────────────────────────────────────────────────
    mesh_children = [c for c in arm_obj.children if c.type == 'MESH']
    result.mesh_child_count = len(mesh_children)
    result.total_verts = sum(len(c.data.vertices) for c in mesh_children)

    if not mesh_children:
        # Some valid entities (pure rig helpers) have no cubes — warn, don't fail
        result.warnings.append("No MESH children — bone-only entity?")
    elif result.total_verts < 4:
        result.error = (
            f"Mesh children exist but have only {result.total_verts} vertex/vertices "
            f"(expected ≥ 4)"
        )
        return

    # ── Custom properties (entity imports only) ───────────────────────────────
    if is_entity_import and VALIDATE_CUSTOM_PROPS:
        mc_id = arm_obj.get("mc_identifier", "")
        if not mc_id:
            result.warnings.append("mc_identifier custom prop is missing or empty")

        for prop_key in ("mc_textures", "mc_geometry", "mc_animations"):
            raw = arm_obj.get(prop_key, "")
            if raw:
                try:
                    json.loads(raw)
                except json.JSONDecodeError:
                    result.warnings.append(
                        f"{prop_key} is not valid JSON: {raw[:60]!r}"
                    )
            # Missing animation props are common for simple mobs — don't warn

    result.success = True


# ══════════════════════════════════════════════════════════════════════════════
# Grid placement / cleanup
# ══════════════════════════════════════════════════════════════════════════════

def place_in_grid(arm_obj: bpy.types.Object, linear_index: int, width: int) -> None:
    """Position *arm_obj* in a 2-D grid based on *linear_index*."""
    row = linear_index // width
    col = linear_index % width
    arm_obj.location = (row * SPACING, col * SPACING, 0.0)


def delete_last_import(context: bpy.types.Context) -> None:
    """Delete the active object (and its children) created by the last import."""
    arm = context.active_object
    if arm is None:
        return
    children = list(arm.children_recursive)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [arm] + children:
        ob.select_set(True)
    bpy.ops.object.delete(use_global=True)


# ══════════════════════════════════════════════════════════════════════════════
# Per-file import attempt
# ══════════════════════════════════════════════════════════════════════════════

def attempt_import(
    context:    bpy.types.Context,
    filepath:   Path,
    pack_root:  str,
    geo_variant: str = "default",
) -> tuple[bool, Optional[bpy.types.Object]]:
    """
    Call ``bedrock.import_auto`` for *filepath* and return
    ``(success, active_object)``.  The caller is responsible for cleanup.
    """
    try:
        ret = bpy.ops.bedrock.import_auto(
            filepath=str(filepath),
            resource_pack_root=pack_root,
            geo_variant=geo_variant,
            import_locators=False,           # locators slow the test down
            apply_rest_rotations=True,
        )
        if 'FINISHED' not in ret:
            return False, None
        return True, context.active_object
    except Exception:
        return False, None


# ══════════════════════════════════════════════════════════════════════════════
# Main test driver
# ══════════════════════════════════════════════════════════════════════════════

def check_bedrock_models(context: bpy.types.Context) -> None:
    """
    Entry point — scans for files, runs imports, prints a full report.
    """
    # ── Resolve resource pack root ────────────────────────────────────────────
    pack_root_str = RESOURCE_PACK_PATH.strip()
    if not pack_root_str:
        pack_root_str = bpy.path.abspath(
            getattr(context.scene, "mcprep_texturepack_path", "")
        )
    if not pack_root_str:
        print("[QA] ERROR: No resource pack path set.  "
              "Set RESOURCE_PACK_PATH or use MCprep's active pack.")
        return

    pack_root = Path(pack_root_str)
    if not pack_root.is_dir():
        print(f"[QA] ERROR: Resource pack path does not exist: {pack_root}")
        return

    print(f"\n{'═'*60}")
    print(f"  Bedrock Model QA")
    print(f"  Pack : {pack_root}")
    print(f"{'═'*60}\n")

    # ── Collect files to test ─────────────────────────────────────────────────
    test_files: list[tuple[Path, bool]] = []   # (path, is_entity_file)

    if SCAN_ENTITY_FILES:
        for f in find_entity_files(pack_root):
            test_files.append((f, True))

    if SCAN_GEO_FILES:
        entity_paths = {t[0] for t in test_files}
        for f in find_geo_files(pack_root):
            if f not in entity_paths:
                test_files.append((f, False))

    if not test_files:
        print("[QA] No files found to test.  "
              "Check RESOURCE_PACK_PATH and SCAN_* settings.")
        return

    total = len(test_files)
    cap   = MAX_CHECK if MAX_CHECK is not None else total
    print(f"Total files found : {total}")
    print(f"Processing up to  : {cap}\n")

    width = max(1, int(cap ** 0.5))

    # ── Run imports ───────────────────────────────────────────────────────────
    all_results:  list[SpawnResult] = []
    successful:   list[SpawnResult] = []
    failed:       list[SpawnResult] = []
    prior_obj = None
    grid_index = 0

    for file_index, (filepath, is_entity) in enumerate(test_files):
        if file_index >= cap:
            break

        mob_name = filepath.stem.replace(".entity", "").replace(".geo", "")

        # ── Determine variants to test ────────────────────────────────────────
        variants_to_test: list[str] = ["default"]

        if TEST_ALL_GEO_VARIANTS and is_entity:
            try:
                with open(filepath, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                geo_dict = (
                    raw.get("minecraft:client_entity", {})
                       .get("description", {})
                       .get("geometry", {})
                )
                if geo_dict:
                    variants_to_test = list(geo_dict.keys())
            except Exception:
                pass  # fall back to ["default"]

        # ── Import each variant ───────────────────────────────────────────────
        for variant in variants_to_test:
            label = f"#{file_index:03d} {mob_name}"
            if variant != "default":
                label += f" [{variant}]"

            result = SpawnResult(
                name=mob_name,
                filepath=filepath,
                geo_variant=variant,
            )

            ok, arm_obj = attempt_import(context, filepath, pack_root_str, variant)

            if not ok:
                result.error = "Operator returned non-FINISHED status"
                failed.append(result)
                all_results.append(result)
                print(f"  FAIL  {label} — {result.error}")
                continue

            # Sanity-check: did we actually get a new object?
            current_obj = context.active_object
            if current_obj == prior_obj:
                result.error = "Active object unchanged between iterations"
                failed.append(result)
                all_results.append(result)
                print(f"  FAIL  {label} — {result.error}")
                break

            prior_obj = current_obj

            # ── Validation ────────────────────────────────────────────────────
            try:
                validate_import(current_obj, result, is_entity)
            except Exception as exc:
                result.error = f"Validation raised: {exc}"

            if result.success:
                successful.append(result)
                warn_str = (
                    f"  ({len(result.warnings)} warning(s))"
                    if result.warnings else ""
                )
                print(
                    f"  OK    {label}"
                    f"  bones={result.bone_count}"
                    f"  meshes={result.mesh_child_count}"
                    f"  verts={result.total_verts}"
                    f"{warn_str}"
                )
                if PLACE_IN_GRID:
                    place_in_grid(current_obj, grid_index, width)
                    grid_index += 1
                else:
                    delete_last_import(context)
            else:
                failed.append(result)
                print(f"  FAIL  {label} — {result.error}")
                if not PLACE_IN_GRID:
                    delete_last_import(context)

            all_results.append(result)

        print(f"  {file_index + 1}/{min(total, cap)}")

    # ══════════════════════════════════════════════════════════════════════════
    # Report
    # ══════════════════════════════════════════════════════════════════════════

    print(f"\n{'═'*60}")
    print(f"  RESULTS")
    print(f"{'═'*60}")
    print(f"  Succeeded : {len(successful)}")
    print(f"  Failed    : {len(failed)}")

    # ── Warnings summary ──────────────────────────────────────────────────────
    warned = [r for r in successful if r.warnings]
    if warned:
        print(f"\n  ── Warnings ({len(warned)}) ──")
        for r in warned:
            for w in r.warnings:
                print(f"    {r.name} [{r.geo_variant}]: {w}")

    # ── Failure summary ───────────────────────────────────────────────────────
    if not failed:
        print("\n  No failures!  ✓")
    else:
        print(f"\n  ── Failures ({len(failed)}) ──")
        for r in failed:
            print(f"    {r.name} [{r.geo_variant}]  ({r.short_path})")
            print(f"      {r.error}")

    # ── Stats ─────────────────────────────────────────────────────────────────
    if successful:
        avg_bones = sum(r.bone_count  for r in successful) / len(successful)
        avg_verts = sum(r.total_verts for r in successful) / len(successful)
        max_bones = max(r.bone_count  for r in successful)
        print(f"\n  ── Geometry stats (successful) ──")
        print(f"    Avg bones   : {avg_bones:.1f}  (max {max_bones})")
        print(f"    Avg verts   : {avg_verts:.1f}")
        bone_only = [r for r in successful if r.mesh_child_count == 0]
        if bone_only:
            print(f"    Bone-only   : {len(bone_only)} entities had no mesh cubes")

    print(f"{'═'*60}\n")


# ── Run ────────────────────────────────────────────────────────────────────────

check_bedrock_models(bpy.context)
print("Finished Bedrock QA check")
