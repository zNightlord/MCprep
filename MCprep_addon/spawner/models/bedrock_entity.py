"""
bedrock_entity_format.py
========================
Dataclasses for the Minecraft Bedrock Edition ``minecraft:client_entity``
resource-pack descriptor file.

These files live at:
    <pack>/entity/<entity_name>.entity.json

They are the *recommended entry point* for importing a Bedrock entity:
they declare which geometry, textures, animations, and render-controllers
belong to an entity, allowing the handler to locate all associated assets
automatically rather than requiring the user to find the geo file by hand.

Schema overview
---------------
{
  "format_version": "1.8.0",
  "minecraft:client_entity": {
    "description": {
      "identifier": "minecraft:axolotl",

      "materials":  { "default": "axolotl", "limbs": "axolotl_limbs" },

      "textures": {
        "blue": "textures/entity/axolotl/axolotl_blue",
        ...
      },

      "geometry": {
        "default": "geometry.axolotl",
        "baby":    "geometry.axolotl.baby"
      },

      "animations": {
        "idle_float": "animation.axolotl.idle_underwater",
        ...
      },

      "scripts": {
        "pre_animation": [ "variable.pitch = query.body_x_rotation;" ],
        "initialize":    [ ... ],
        "animate":       [ ... ],          # can be strings or {ref: condition} dicts
        "scale":         "query.is_baby ? 2.0 : 1.0"
      },

      "animation_controllers": [
        { "general": "controller.animation.axolotl.general" }
      ],

      "render_controllers": [
        "controller.render.axolotl.v2"
        # or with conditions:
        # { "controller.render.foo": "q.is_baby" }
      ],

      "spawn_egg":           { "texture": "spawn_egg_axolotl" },
      "enable_attachables":  false
    }
  }
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Scripts block ──────────────────────────────────────────────────────────────

@dataclass
class BedrockEntityScripts:
    """
    The ``scripts`` block inside a client entity description.

    pre_animation  – Molang expressions evaluated each frame before animations run.
    initialize     – Molang expressions evaluated once on entity spawn.
    animate        – References to animations/controllers that run each frame.
                     Each entry is either a plain string (unconditional) or a
                     ``{anim_ref: molang_condition}`` dict (conditional).
    scale          – Molang expression that sets the entity's render scale.
    """
    pre_animation: list[str] = field(default_factory=list)
    initialize:    list[str] = field(default_factory=list)
    # animate entries are str | dict[str, str] — stored as-is for flexibility
    animate:       list = field(default_factory=list)
    scale:         Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "BedrockEntityScripts":
        return cls(
            pre_animation=list(d.get("pre_animation", [])),
            initialize=list(d.get("initialize", [])),
            animate=list(d.get("animate", [])),
            scale=d.get("scale"),
        )


# ── Render controller entry ────────────────────────────────────────────────────

@dataclass
class BedrockRenderControllerEntry:
    """
    One render-controller reference, with an optional Molang condition.

    ref       – e.g. ``"controller.render.axolotl.v2"``
    condition – Molang expression; empty string means unconditional.
    """
    ref:       str
    condition: str = ""

    @classmethod
    def from_raw(cls, raw) -> "BedrockRenderControllerEntry":
        """Accept either a plain string or a ``{ref: condition}`` dict."""
        if isinstance(raw, str):
            return cls(ref=raw)
        if isinstance(raw, dict):
            # The dict has exactly one key: the controller ref; value is condition.
            for ref, cond in raw.items():
                return cls(ref=ref, condition=str(cond))
        return cls(ref=str(raw))


# ── Entity description ─────────────────────────────────────────────────────────

@dataclass
class BedrockEntityDescription:
    """
    The ``description`` block inside ``minecraft:client_entity``.

    All dict fields use the variant name (e.g. ``"default"``, ``"baby"``) as
    key, matching the in-game variant system.

    geometry            – variant → geometry identifier (e.g. ``"geometry.axolotl"``).
    textures            – variant → texture path (relative to pack root, no extension).
    materials           – variant → material identifier.
    animations          – short key → full animation reference.
    animation_controllers – list of ``{short_key: controller_ref}`` dicts.
    render_controllers  – list of ``BedrockRenderControllerEntry``.
    scripts             – optional Molang scripts block.
    spawn_egg           – spawn-egg texture/overlay metadata.
    enable_attachables  – whether equipment attachables render on this entity.
    """
    identifier: str

    geometry:              dict[str, str] = field(default_factory=dict)
    textures:              dict[str, str] = field(default_factory=dict)
    materials:             dict[str, str] = field(default_factory=dict)
    animations:            dict[str, str] = field(default_factory=dict)
    animation_controllers: list[dict[str, str]] = field(default_factory=list)
    render_controllers:    list[BedrockRenderControllerEntry] = field(default_factory=list)
    scripts:               Optional[BedrockEntityScripts] = None
    spawn_egg:             dict[str, str] = field(default_factory=dict)
    enable_attachables:    bool = False

    # ── Construction ───────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: dict) -> "BedrockEntityDescription":
        scripts = (
            BedrockEntityScripts.from_dict(d["scripts"])
            if "scripts" in d else None
        )
        render_controllers = [
            BedrockRenderControllerEntry.from_raw(rc)
            for rc in d.get("render_controllers", [])
        ]
        return cls(
            identifier=d["identifier"],
            geometry=dict(d.get("geometry", {})),
            textures=dict(d.get("textures", {})),
            materials=dict(d.get("materials", {})),
            animations=dict(d.get("animations", {})),
            animation_controllers=list(d.get("animation_controllers", [])),
            render_controllers=render_controllers,
            scripts=scripts,
            spawn_egg=dict(d.get("spawn_egg", {})),
            enable_attachables=bool(d.get("enable_attachables", False)),
        )

    # ── Convenience helpers ────────────────────────────────────────────────────

    @property
    def default_geometry(self) -> Optional[str]:
        """The ``"default"`` geometry identifier, or the first available one."""
        return self.geometry.get("default") or next(iter(self.geometry.values()), None)

    @property
    def default_texture_path(self) -> Optional[str]:
        """The ``"default"`` texture path, or the first available one."""
        return self.textures.get("default") or next(iter(self.textures.values()), None)

    def geometry_for_variant(self, variant: str = "default") -> Optional[str]:
        """Return the geometry identifier for *variant*, falling back to ``default``."""
        return self.geometry.get(variant) or self.default_geometry

    def texture_for_variant(self, variant: str = "default") -> Optional[str]:
        """Return the texture path for *variant*, falling back to ``default``."""
        return self.textures.get(variant) or self.default_texture_path


# ── Entity file root ───────────────────────────────────────────────────────────

@dataclass
class BedrockEntityFile:
    """
    Parsed Bedrock ``minecraft:client_entity`` descriptor file.

    This is the recommended entry point for importing a Bedrock entity into
    Blender: the handler reads this file first, resolves the geometry
    identifier, locates the associated ``.geo.json``, and stores the full
    entity metadata as custom properties on the imported armature.
    """
    format_version: str
    description:    BedrockEntityDescription

    # ── Constructors ───────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: dict) -> "BedrockEntityFile":
        entity_block = d.get("minecraft:client_entity", {})
        desc_dict    = entity_block.get("description", {})
        return cls(
            format_version=str(d.get("format_version", "unknown")),
            description=BedrockEntityDescription.from_dict(desc_dict),
        )

    @classmethod
    def from_json(cls, text: str) -> "BedrockEntityFile":
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_path(cls, path: "str | Path") -> "BedrockEntityFile":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_json(fh.read())

    # ── Serialisation helpers (used when writing to Blender custom props) ──────

    def description_as_props(self) -> dict[str, str]:
        """
        Return all entity metadata as a flat dict of ``{mc_key: json_string}``
        pairs, ready to be stored as Blender custom properties.

        Keys are prefixed with ``mc_`` to avoid conflicts with Blender's own
        ID properties.  Complex values (dicts, lists) are JSON-encoded strings
        so they survive round-trips through ``bpy.types.Object`` custom props.
        """
        d = self.description
        props: dict[str, str] = {
            "mc_format_version": self.format_version,
            "mc_identifier":     d.identifier,
        }
        def _j(val) -> str:
            return json.dumps(val, ensure_ascii=False)

        if d.geometry:
            props["mc_geometry"] = _j(d.geometry)
        if d.textures:
            props["mc_textures"] = _j(d.textures)
        if d.materials:
            props["mc_materials"] = _j(d.materials)
        if d.animations:
            props["mc_animations"] = _j(d.animations)
        if d.animation_controllers:
            props["mc_animation_controllers"] = _j(d.animation_controllers)
        if d.render_controllers:
            props["mc_render_controllers"] = _j(
                [{"ref": rc.ref, "condition": rc.condition} for rc in d.render_controllers]
            )
        if d.scripts:
            s = d.scripts
            if s.pre_animation:
                props["mc_scripts_pre_animation"] = _j(s.pre_animation)
            if s.initialize:
                props["mc_scripts_initialize"] = _j(s.initialize)
            if s.animate:
                props["mc_scripts_animate"] = _j(s.animate)
            if s.scale is not None:
                props["mc_scripts_scale"] = s.scale
        if d.spawn_egg:
            props["mc_spawn_egg"] = _j(d.spawn_egg)
        if d.enable_attachables:
            props["mc_enable_attachables"] = "true"
        return props


"""
bedrock_model_handler.py
========================
Blender import handler for Minecraft Bedrock Edition geometry models.

Two entry points
----------------
**Geometry file** (.geo.json)  — import a single model directly::

    from bedrock_model_format  import BedrockModelFile
    from bedrock_model_handler import BedrockModelBlenderHandler

    model   = BedrockModelFile.from_path("allay.geo.json")
    handler = BedrockModelBlenderHandler(context=bpy.context)
    handler.import_geometry(model)

**Entity file** (recommended) — entity descriptor drives everything::

    from bedrock_entity_format import BedrockEntityFile
    from bedrock_model_handler import BedrockModelBlenderHandler

    entity  = BedrockEntityFile.from_path("entity/axolotl.entity.json")
    handler = BedrockModelBlenderHandler(
        context=bpy.context,
        resource_pack_root="/path/to/resource_pack",
    )
    arm_obj = handler.import_from_entity(entity, geo_variant="default")
    # → armature with geometry + entity metadata as custom properties

Coordinate system
-----------------
Bedrock: X-right, Y-up, Z-south  (right-hand, Y-up)
Blender: X-right, Z-up,  Y-north (right-hand, Z-up)

Conversion: (Bx, By, Bz) → (Bx/16, −Bz/16, By/16)
det(M) = +1 — winding order is preserved, no face flipping required.

Bone structure
--------------
• One Blender armature with all Bedrock bones.
• Bone head = bone pivot; tail offset +Z by 1 Bedrock unit.
• Default bone rotations are applied in Pose Mode (animatable).
• Locator bones created as half-length children of their parent bone.
• One mesh object per bone, vertex-group weighted 1.0 to that bone.
  Set SINGLE_MESH = True to produce one combined mesh instead.

Entity metadata (custom properties)
------------------------------------
When imported via ``import_from_entity()``, the resulting armature object
receives the full entity descriptor as Blender custom properties:

    arm_obj["mc_identifier"]              → "minecraft:axolotl"
    arm_obj["mc_geometry"]                → JSON string of geometry variant dict
    arm_obj["mc_textures"]                → JSON string of texture variant dict
    arm_obj["mc_animations"]              → JSON string
    arm_obj["mc_animation_controllers"]   → JSON string
    arm_obj["mc_render_controllers"]      → JSON string
    arm_obj["mc_scripts_scale"]           → raw Molang expression string
    ... (see BedrockEntityFile.description_as_props for full list)

These strings can be parsed back with ``json.loads()`` or read directly by
animation tooling that also understands the entity format.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Optional

import bmesh
import bpy
import mathutils

try:
    from .bedrock_model_format import (
        BedrockCube,
        BedrockBone,
        BedrockGeometry,
        BedrockModelFile,
    )
    from .bedrock_entity_format import (
        BedrockEntityFile,
        BedrockEntityDescription,
    )
    from .mc_model_shared import (
        detect_mc_format,
        MC_FORMAT_BEDROCK_GEO,
        MC_FORMAT_BEDROCK_ENTITY,
    )
except ImportError:
    from bedrock_model_format import (
        BedrockCube,
        BedrockBone,
        BedrockGeometry,
        BedrockModelFile,
    )
    from bedrock_entity_format import (
        BedrockEntityFile,
        BedrockEntityDescription,
    )
    from mc_model_shared import (
        detect_mc_format,
        MC_FORMAT_BEDROCK_GEO,
        MC_FORMAT_BEDROCK_ENTITY,
    )

# ── Module constants ───────────────────────────────────────────────────────────

SCALE       = 1.0 / 16.0       # Bedrock units → Blender metres
BONE_LENGTH = 1.0 * SCALE       # armature tail offset (1 Bedrock unit)

# True  → one combined mesh for the whole model (vertex groups per bone).
# False → one mesh object per bone (cleaner object hierarchy, default).
SINGLE_MESH = False


# ── Coordinate helpers (module-level for external use) ─────────────────────────

def conv_pos(x: float, y: float, z: float) -> mathutils.Vector:
    """Bedrock model-space position → Blender world-space Vector."""
    s = SCALE
    return mathutils.Vector((x * s, -z * s, y * s))


def conv_rot(rx_deg: float, ry_deg: float, rz_deg: float) -> mathutils.Euler:
    """
    Bedrock XYZ-degree bone Euler → Blender XYZ Euler.

    Conjugates the rotation matrix by the basis-change matrix M:
        R_blender = M @ R_bedrock @ Mᵀ
    where M maps: X→X, Y→Z, Z→−Y.
    """
    M = mathutils.Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
    R_bd = mathutils.Euler(
        (math.radians(rx_deg), math.radians(ry_deg), math.radians(rz_deg)), "XYZ"
    ).to_matrix()
    return (M @ R_bd @ M.transposed()).to_euler("XYZ")


# ── Box UV layout ──────────────────────────────────────────────────────────────
#
# For a cube with size (W, H, D) at box UV offset (u, v):
#
#        u    u+D  u+D+W  u+2D+W  u+2D+2W
#   v    [    ][top:WxD][bot:WxD][       ]   row height D
#   v+D  [W:DxH][N:WxH][ E:DxH][S:WxH  ]   row height H
#
# Vertex layout (origin = minimum corner, size = W×H×D):
#   0 (ox,   oy,   oz  )  −X −Y −Z      4 (ox,   oy,   oz+D)  −X −Y +Z
#   1 (ox+W, oy,   oz  )  +X −Y −Z      5 (ox+W, oy,   oz+D)  +X −Y +Z
#   2 (ox+W, oy+H, oz  )  +X +Y −Z      6 (ox+W, oy+H, oz+D)  +X +Y +Z
#   3 (ox,   oy+H, oz  )  −X +Y −Z      7 (ox,   oy+H, oz+D)  −X +Y +Z

# _FACE_TABLE: face_name → (vert_loop, texel_rect_fn, uv_corner_order)
#   vert_loop       – 4 indices (CCW from outside in Bedrock space).
#   texel_rect_fn   – lambda(u,v,W,H,D) → (px0,py0,px1,py1).
#   uv_corner_order – which texture corner maps to each loop vertex:
#                     TL=top-left, TR=top-right, BL=bottom-left, BR=bottom-right
#                     ("top" = smaller py value, i.e. closer to texture row 0).

_FACE_TABLE: dict[str, tuple] = {
    "north": (
        [0, 3, 2, 1],
        lambda u, v, W, H, D: (u + D,        v + D, u + D + W,     v + D + H),
        ["BL", "TL", "TR", "BR"],       # left = West when facing −Z
    ),
    "south": (
        [4, 5, 6, 7],
        lambda u, v, W, H, D: (u + 2*D + W,  v + D, u + 2*D + 2*W, v + D + H),
        ["BR", "BL", "TL", "TR"],       # left = East when facing +Z (mirrored)
    ),
    "east": (
        [1, 2, 6, 5],
        lambda u, v, W, H, D: (u + D + W,    v + D, u + 2*D + W,   v + D + H),
        ["BR", "TR", "TL", "BL"],       # left = South when facing +X
    ),
    "west": (
        [0, 4, 7, 3],
        lambda u, v, W, H, D: (u,            v + D, u + D,          v + D + H),
        ["BL", "BR", "TR", "TL"],       # left = North when facing −X
    ),
    "up": (
        [3, 7, 6, 2],
        lambda u, v, W, H, D: (u + D,        v,     u + D + W,      v + D),
        ["TL", "BL", "BR", "TR"],       # viewed from above, North = up
    ),
    "down": (
        [0, 1, 5, 4],
        lambda u, v, W, H, D: (u + D + W,    v,     u + 2*D + W,    v + D),
        ["TR", "TL", "BL", "BR"],       # viewed from below (mirrored)
    ),
}

_UV_CORNERS = {
    "TL": (0.0, 0.0), "TR": (1.0, 0.0),
    "BL": (0.0, 1.0), "BR": (1.0, 1.0),
}


def _box_uv_loops(
    u: float, v: float,
    W: float, H: float, D: float,
    tw: int, th: int,
    face: str,
    mirror: bool = False,
) -> list[tuple[float, float]]:
    """4 UV coordinates (Blender UV space, Y-up) for one face using box UV."""
    _, rect_fn, corner_order = _FACE_TABLE[face]
    px0, py0, px1, py1 = rect_fn(u, v, W, H, D)

    def _to_uv(cx: float, cy: float) -> tuple[float, float]:
        pu = px0 + cx * (px1 - px0)
        pv = py0 + cy * (py1 - py0)
        return pu / tw, 1.0 - pv / th  # Y-flip to Blender convention

    uvs = []
    for corner in corner_order:
        cx, cy = _UV_CORNERS[corner]
        if mirror:
            cx = 1.0 - cx
        uvs.append(_to_uv(cx, cy))
    return uvs


def _per_face_uv_loops(
    entry,          # BedrockFaceUVEntry
    tw: int, th: int,
    face: str,
    mirror: bool = False,
) -> list[tuple[float, float]]:
    """4 UV coordinates for one face using per-face explicit UV data."""
    u0, v0 = entry.uv
    wu, hv = entry.uv_size
    px0, py0, px1, py1 = u0, v0, u0 + wu, v0 + hv
    _, _, corner_order = _FACE_TABLE[face]

    def _to_uv(cx: float, cy: float) -> tuple[float, float]:
        pu = px0 + cx * (px1 - px0)
        pv = py0 + cy * (py1 - py0)
        return pu / tw, 1.0 - pv / th

    uvs = []
    for corner in corner_order:
        cx, cy = _UV_CORNERS[corner]
        if mirror:
            cx = 1.0 - cx
        uvs.append(_to_uv(cx, cy))
    return uvs


# ── Main handler ───────────────────────────────────────────────────────────────

class BedrockModelBlenderHandler:
    """
    Drives the full Bedrock model import pipeline.

    Parameters
    ----------
    context
        Blender context (defaults to ``bpy.context``).
    resource_pack_root
        Absolute path to the resource pack root (the folder containing
        ``entity/``, ``models/``, ``textures/``, etc.).
        Used when searching for geo files from an entity descriptor.
    """

    def __init__(
        self,
        context: Optional[bpy.types.Context] = None,
        resource_pack_root: Optional[str] = None,
    ) -> None:
        self.ctx = context or bpy.context
        self.resource_pack_root: Optional[Path] = (
            Path(resource_pack_root) if resource_pack_root else None
        )

    # ══════════════════════════════════════════════════════════════════════════
    # Public API — geometry
    # ══════════════════════════════════════════════════════════════════════════

    def import_geometry(
        self,
        model: BedrockModelFile,
        geo_index: int = 0,
        geo_identifier: Optional[str] = None,
        import_locators: bool = True,
        apply_rest_rotation: bool = True,
    ) -> Optional[bpy.types.Object]:
        """
        Import one geometry from a parsed ``BedrockModelFile``.

        Parameters
        ----------
        model
            Parsed geometry file (from ``BedrockModelFile.from_path``).
        geo_index
            Which geometry to import when the file contains multiple.
            Ignored if *geo_identifier* is supplied.
        geo_identifier
            Import the geometry whose ``description.identifier`` matches this
            string (e.g. ``"geometry.axolotl"``).  If not found, falls back to
            *geo_index*.
        import_locators
            Create zero-length child bones at each locator position.
        apply_rest_rotation
            Apply default bone rotations in Pose Mode so they can be keyed.

        Returns the armature object, or ``None`` if the model is empty.
        """
        if not model.geometries:
            return None

        # Resolve geometry index
        idx = geo_index
        if geo_identifier:
            for i, g in enumerate(model.geometries):
                if g.description.identifier == geo_identifier:
                    idx = i
                    break

        idx = max(0, min(idx, len(model.geometries) - 1))
        geo = model.geometries[idx]

        arm_obj = self._create_armature(geo, import_locators)
        self._create_mesh_objects(geo, arm_obj)
        if apply_rest_rotation:
            self._apply_rest_rotations(geo, arm_obj)

        bpy.ops.object.mode_set(mode="OBJECT")
        self.ctx.view_layer.objects.active = arm_obj
        return arm_obj

    # ══════════════════════════════════════════════════════════════════════════
    # Public API — entity (recommended entry point)
    # ══════════════════════════════════════════════════════════════════════════

    def import_from_entity(
        self,
        entity: BedrockEntityFile,
        geo_variant:  str = "default",
        geo_filepath: Optional["str | Path"] = None,
        extra_search_dirs: Optional[list[str]] = None,
        import_locators:    bool = True,
        apply_rest_rotation: bool = True,
    ) -> Optional[bpy.types.Object]:
        """
        Import a Bedrock entity using its client-entity descriptor as the
        primary source of truth.

        Pipeline
        --------
        1. Resolve the geometry identifier for *geo_variant* from the entity.
        2. Locate the corresponding ``.geo.json`` file (explicit or searched).
        3. Call ``import_geometry()`` to build the armature and meshes.
        4. Write entity metadata to Blender custom properties on the armature.

        Parameters
        ----------
        entity
            Parsed ``BedrockEntityFile``.
        geo_variant
            Geometry variant key from ``entity.description.geometry``
            (default: ``"default"``).
        geo_filepath
            Explicit path to the geo JSON file.  When provided, the geo-search
            step is skipped.
        extra_search_dirs
            Additional directories to scan when searching for the geo file.
            The handler always searches the standard Bedrock geo paths under
            ``resource_pack_root`` first.
        import_locators
            Passed through to ``import_geometry()``.
        apply_rest_rotation
            Passed through to ``import_geometry()``.

        Returns the armature object (with custom properties set), or ``None``.
        """
        desc = entity.description
        geo_id = desc.geometry_for_variant(geo_variant)
        if not geo_id:
            print(f"[BedrockModelBlenderHandler] No geometry for variant '{geo_variant}'")
            return None

        # ── Locate geo file ────────────────────────────────────────────────────
        geo_path: Optional[Path] = None
        if geo_filepath:
            geo_path = Path(geo_filepath)
        else:
            geo_path = self._find_geo_file(geo_id, extra_search_dirs or [])

        if geo_path is None or not geo_path.is_file():
            print(
                f"[BedrockModelBlenderHandler] Could not locate geo file for "
                f"identifier '{geo_id}'"
            )
            return None

        # ── Import geometry ────────────────────────────────────────────────────
        model   = BedrockModelFile.from_path(geo_path)
        arm_obj = self.import_geometry(
            model,
            geo_identifier=geo_id,
            import_locators=import_locators,
            apply_rest_rotation=apply_rest_rotation,
        )

        # ── Store entity metadata as custom properties ─────────────────────────
        if arm_obj is not None:
            self._store_entity_properties(arm_obj, entity)

        return arm_obj

    # ══════════════════════════════════════════════════════════════════════════
    # Geo-file search
    # ══════════════════════════════════════════════════════════════════════════

    def _find_geo_file(
        self,
        geo_identifier: str,
        extra_dirs: list[str],
    ) -> Optional[Path]:
        """
        Scan for a JSON file that contains *geo_identifier* as a geometry
        identifier.

        Search order
        ------------
        1. ``<resource_pack_root>/models/entity/``  (canonical Bedrock location)
        2. ``<resource_pack_root>/models/``          (some vanilla packs)
        3. ``<resource_pack_root>/entity/``          (older / modded packs)
        4. Each directory in *extra_dirs* (recursively).

        The scan short-circuits on the first match.
        """
        search_roots: list[Path] = []

        if self.resource_pack_root:
            rpr = self.resource_pack_root
            for sub in ("models/entity", "models", "entity"):
                candidate = rpr / sub
                if candidate.is_dir():
                    search_roots.append(candidate)

        for d in extra_dirs:
            p = Path(d)
            if p.is_dir():
                search_roots.append(p)

        for root in search_roots:
            result = self._scan_dir_for_geo(root, geo_identifier)
            if result:
                return result
        return None

    @staticmethod
    def _scan_dir_for_geo(directory: Path, geo_identifier: str) -> Optional[Path]:
        """Walk *directory* recursively; return path of first file matching *geo_identifier*."""
        for fpath in sorted(directory.rglob("*.json")):
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if detect_mc_format(data) != MC_FORMAT_BEDROCK_GEO:
                    continue
                gm = BedrockModelFile.from_dict(data)
                for geo in gm.geometries:
                    if geo.description.identifier == geo_identifier:
                        return fpath
            except Exception:
                continue
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # Entity custom properties
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _store_entity_properties(
        arm_obj: bpy.types.Object,
        entity: BedrockEntityFile,
    ) -> None:
        """
        Write ``entity`` descriptor data as Blender custom properties on
        *arm_obj*.

        All values are plain strings (JSON-encoded for complex types) so they
        survive round-trips through Blender's IDProperty system and are
        accessible from drivers, scripts, and the Properties panel.

        Retrieved at runtime::

            import json
            anims = json.loads(arm_obj["mc_animations"])
            scale = arm_obj["mc_scripts_scale"]
        """
        for key, value in entity.description_as_props().items():
            arm_obj[key] = value

        # Mark as read/write and visible in the UI
        for key in entity.description_as_props():
            if key in arm_obj:
                try:
                    ui = arm_obj.id_properties_ui(key)
                    ui.update(description=f"Bedrock entity data: {key}")
                except Exception:
                    pass  # older Blender versions may not support this

    # ══════════════════════════════════════════════════════════════════════════
    # Armature
    # ══════════════════════════════════════════════════════════════════════════

    def _create_armature(
        self,
        geo: BedrockGeometry,
        import_locators: bool,
    ) -> bpy.types.Object:
        """Build the armature from all bones in the geometry."""
        identifier = geo.description.identifier
        arm  = bpy.data.armatures.new(identifier)
        arm_obj = bpy.data.objects.new(identifier, arm)
        self.ctx.collection.objects.link(arm_obj)

        self.ctx.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="EDIT")
        edit_bones = arm.edit_bones

        eb_map: dict[str, bpy.types.EditBone] = {}

        # ── Create bones ───────────────────────────────────────────────────────
        for bone in geo.bones:
            eb = edit_bones.new(bone.name)
            head = conv_pos(*bone.pivot)
            eb.head = head
            eb.tail = head + mathutils.Vector((0.0, 0.0, BONE_LENGTH))
            eb.use_connect = False
            eb_map[bone.name] = eb

        # ── Parent hierarchy ───────────────────────────────────────────────────
        for bone in geo.bones:
            if bone.parent and bone.parent in eb_map:
                eb_map[bone.name].parent = eb_map[bone.parent]

        # ── Locator bones ──────────────────────────────────────────────────────
        if import_locators:
            for bone in geo.bones:
                for loc_name, loc_pos in bone.locators.items():
                    eb_loc = edit_bones.new(f"{bone.name}.{loc_name}")
                    head = conv_pos(*loc_pos)
                    eb_loc.head = head
                    eb_loc.tail = head + mathutils.Vector((0.0, 0.0, BONE_LENGTH * 0.5))
                    eb_loc.use_connect = False
                    if bone.name in eb_map:
                        eb_loc.parent = eb_map[bone.name]

        bpy.ops.object.mode_set(mode="OBJECT")
        return arm_obj

    def _apply_rest_rotations(
        self,
        geo: BedrockGeometry,
        arm_obj: bpy.types.Object,
    ) -> None:
        """Apply default bone rotations in Pose Mode so they can be animated."""
        self.ctx.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode="POSE")
        for bone in geo.bones:
            if bone.rotation is None:
                continue
            pb = arm_obj.pose.bones.get(bone.name)
            if pb is None:
                continue
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = conv_rot(*bone.rotation)
        bpy.ops.object.mode_set(mode="OBJECT")

    # ══════════════════════════════════════════════════════════════════════════
    # Mesh objects
    # ══════════════════════════════════════════════════════════════════════════

    def _create_mesh_objects(
        self,
        geo: BedrockGeometry,
        arm_obj: bpy.types.Object,
    ) -> None:
        tw = geo.description.texture_width
        th = geo.description.texture_height
        if SINGLE_MESH:
            self._create_single_mesh(geo, arm_obj, tw, th)
        else:
            for bone in geo.bones:
                if not bone.cubes:
                    continue
                self._create_bone_mesh(bone, arm_obj, tw, th)

    def _create_bone_mesh(
        self,
        bone: BedrockBone,
        arm_obj: bpy.types.Object,
        tw: int,
        th: int,
    ) -> bpy.types.Object:
        """One mesh object for a single bone, weighted 1.0 to that bone."""
        me = bpy.data.meshes.new(f"{bone.name}.mesh")
        ob = bpy.data.objects.new(bone.name, me)
        self.ctx.collection.objects.link(ob)

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        vert_indices: list[int] = []

        for cube in bone.cubes:
            self._add_cube(bm, uv_layer, cube, tw, th, vert_indices)

        bm.to_mesh(me)
        bm.free()
        me.update()

        vg = ob.vertex_groups.new(name=bone.name)
        vg.add(vert_indices, 1.0, "REPLACE")

        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True

        ob.parent = arm_obj
        return ob

    def _create_single_mesh(
        self,
        geo: BedrockGeometry,
        arm_obj: bpy.types.Object,
        tw: int,
        th: int,
    ) -> bpy.types.Object:
        """One combined mesh, vertex groups per bone."""
        me = bpy.data.meshes.new(f"{geo.description.identifier}.mesh")
        ob = bpy.data.objects.new(geo.description.identifier, me)
        self.ctx.collection.objects.link(ob)

        bm = bmesh.new()
        uv_layer = bm.loops.layers.uv.new("UVMap")
        bone_verts: dict[str, list[int]] = {}

        for bone in geo.bones:
            if not bone.cubes:
                continue
            vert_indices: list[int] = []
            for cube in bone.cubes:
                self._add_cube(bm, uv_layer, cube, tw, th, vert_indices)
            bone_verts[bone.name] = vert_indices

        bm.to_mesh(me)
        bm.free()
        me.update()

        for bone_name, vert_indices in bone_verts.items():
            vg = ob.vertex_groups.new(name=bone_name)
            vg.add(vert_indices, 1.0, "REPLACE")

        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True

        ob.parent = arm_obj
        return ob

    # ══════════════════════════════════════════════════════════════════════════
    # Cube geometry
    # ══════════════════════════════════════════════════════════════════════════

    def _add_cube(
        self,
        bm: bmesh.types.BMesh,
        uv_layer,
        cube: BedrockCube,
        tw: int,
        th: int,
        vert_index_list: list[int],
    ) -> None:
        """
        Append one cube's vertices, faces, and UVs into an open BMesh.
        Newly created vertex indices are appended to *vert_index_list*.
        """
        ox, oy, oz = cube.origin
        W, H, D    = cube.size
        inf        = cube.inflate

        # Inflate: expand origin inward, grow size outward
        if inf:
            ox -= inf;  oy -= inf;  oz -= inf
            W  += 2*inf; H += 2*inf; D += 2*inf

        # ── 8 corners (Bedrock space, minimum-corner layout) ──────────────────
        corners_bd = [
            (ox,     oy,     oz    ),   # 0  −X −Y −Z
            (ox + W, oy,     oz    ),   # 1  +X −Y −Z
            (ox + W, oy + H, oz    ),   # 2  +X +Y −Z
            (ox,     oy + H, oz    ),   # 3  −X +Y −Z
            (ox,     oy,     oz + D),   # 4  −X −Y +Z
            (ox + W, oy,     oz + D),   # 5  +X −Y +Z
            (ox + W, oy + H, oz + D),   # 6  +X +Y +Z
            (ox,     oy + H, oz + D),   # 7  −X +Y +Z
        ]

        # ── Cube-level rotation (format 1.16+) ────────────────────────────────
        if cube.rotation is not None:
            rot_mat = conv_rot(*cube.rotation).to_matrix().to_4x4()
            pivot   = conv_pos(*(cube.pivot or cube.origin))
            bl_verts = []
            for c in corners_bd:
                v = conv_pos(*c)
                bl_verts.append(pivot + rot_mat @ (v - pivot))
        else:
            bl_verts = [conv_pos(*c) for c in corners_bd]

        # ── Add to BMesh ──────────────────────────────────────────────────────
        start_vi  = len(bm.verts)
        bm_verts  = [bm.verts.new(v) for v in bl_verts]
        bm.verts.ensure_lookup_table()
        vert_index_list.extend(range(start_vi, start_vi + len(bm_verts)))

        # ── Faces with UV ─────────────────────────────────────────────────────
        for face_name, (loop_idx, rect_fn, _) in _FACE_TABLE.items():
            # Skip genuinely degenerate faces (e.g. flat wing with one zero dimension)
            skip_map = {
                "north": D == 0, "south": D == 0,
                "east":  W == 0, "west":  W == 0,
                "up":    H == 0, "down":  H == 0,
            }
            if skip_map.get(face_name, False):
                continue

            loop_verts = [bm_verts[i] for i in loop_idx]
            try:
                face = bm.faces.new(loop_verts)
            except ValueError:
                continue  # duplicate face (can happen with inflate=0 cubes)

            face.smooth = True
            bm.faces.ensure_lookup_table()

            uv_co = self._get_uv_for_face(cube, face_name, W, H, D, tw, th)
            for loop, uv in zip(face.loops, uv_co):
                loop[uv_layer].uv = uv

    def _get_uv_for_face(
        self,
        cube: BedrockCube,
        face_name: str,
        W: float, H: float, D: float,
        tw: int, th: int,
    ) -> list[tuple[float, float]]:
        """4 (u, v) pairs for one face, handling both box UV and per-face UV."""
        cuv    = cube.uv
        mirror = cube.mirror

        if cuv.per_face is not None:
            entry = cuv.per_face.get(face_name)
            if entry is not None:
                return _per_face_uv_loops(entry, tw, th, face_name, mirror)
            return [(0.0, 0.0)] * 4   # face not listed → black region

        u, v = cuv.box_uv or (0.0, 0.0)
        return _box_uv_loops(u, v, W, H, D, tw, th, face_name, mirror)


# ── Operators ──────────────────────────────────────────────────────────────────

class BEDROCK_OT_import_auto(bpy.types.Operator):
    """
    Import a Minecraft Bedrock model.

    Accepts either:
    • A geometry file (.geo.json / .json containing ``minecraft:geometry``)
    • A client-entity file (.entity.json / .json containing ``minecraft:client_entity``)

    When an entity file is supplied (recommended), entity metadata is stored
    as custom properties on the created armature.
    """

    bl_idname = "bedrock.import_auto"
    bl_label  = "Import Bedrock Model / Entity (.json)"
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to a Bedrock .geo.json or .entity.json file",
        subtype="FILE_PATH",
    )
    resource_pack_root: bpy.props.StringProperty(
        name="Resource Pack Root",
        description=(
            "Root folder of the Bedrock resource pack (the folder that contains "
            "entity/, models/, textures/, …). Used to locate geo files when "
            "importing from an entity descriptor."
        ),
        subtype="DIR_PATH",
        default="",
    )
    geo_variant: bpy.props.StringProperty(
        name="Geometry Variant",
        description=(
            "Which geometry variant to import from the entity descriptor "
            "(e.g. 'default', 'baby')"
        ),
        default="default",
    )
    geo_index: bpy.props.IntProperty(
        name="Geometry Index",
        description=(
            "Which geometry to import when a geo file contains multiple "
            "(only used for direct geo-file imports)"
        ),
        default=0,
        min=0,
    )
    import_locators: bpy.props.BoolProperty(
        name="Import Locators",
        description="Create child bones at locator positions",
        default=True,
    )
    apply_rest_rotations: bpy.props.BoolProperty(
        name="Apply Rest Rotations",
        description="Set default bone rotations in Pose Mode",
        default=True,
    )
    filter_glob: bpy.props.StringProperty(
        default="*.json;*.geo.json",
        options={"HIDDEN"},
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # ── Parse and detect format ────────────────────────────────────────────
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                raw_data = json.load(fh)
        except Exception as exc:
            self.report({"ERROR"}, f"Cannot read file: {exc}")
            return {"CANCELLED"}

        fmt = detect_mc_format(raw_data)

        handler = BedrockModelBlenderHandler(
            context=context,
            resource_pack_root=self.resource_pack_root or None,
        )

        # ── Branch on detected format ──────────────────────────────────────────
        if fmt == MC_FORMAT_BEDROCK_GEO:
            arm_obj = self._import_geo(handler, raw_data)

        elif fmt == MC_FORMAT_BEDROCK_ENTITY:
            arm_obj = self._import_entity(handler, raw_data)

        else:
            self.report(
                {"ERROR"},
                f"File does not appear to be a Bedrock geometry or entity file "
                f"(detected format: '{fmt}'). "
                f"For Java models use File > Import > Minecraft Java Model."
            )
            return {"CANCELLED"}

        if arm_obj is None:
            self.report({"ERROR"}, "Import produced no objects — check the console")
            return {"CANCELLED"}

        # ── Select result ──────────────────────────────────────────────────────
        for ob in context.selected_objects:
            ob.select_set(False)
        arm_obj.select_set(True)
        context.view_layer.objects.active = arm_obj

        self.report({"INFO"}, f"Imported '{arm_obj.name}'")
        return {"FINISHED"}

    # ── Private execute helpers ────────────────────────────────────────────────

    def _import_geo(
        self,
        handler: BedrockModelBlenderHandler,
        raw_data: dict,
    ) -> Optional[bpy.types.Object]:
        model = BedrockModelFile.from_dict(raw_data)
        if not model.geometries:
            self.report({"ERROR"}, "No geometries found in file")
            return None

        idx = min(self.geo_index, len(model.geometries) - 1)
        self.report(
            {"INFO"},
            f"Geometry file: importing index {idx} "
            f"('{model.geometries[idx].description.identifier}')",
        )
        return handler.import_geometry(
            model,
            geo_index=idx,
            import_locators=self.import_locators,
            apply_rest_rotation=self.apply_rest_rotations,
        )

    def _import_entity(
        self,
        handler: BedrockModelBlenderHandler,
        raw_data: dict,
    ) -> Optional[bpy.types.Object]:
        entity = BedrockEntityFile.from_dict(raw_data)
        desc   = entity.description
        geo_id = desc.geometry_for_variant(self.geo_variant)

        if not geo_id:
            self.report(
                {"ERROR"},
                f"Entity '{desc.identifier}' has no geometry for variant "
                f"'{self.geo_variant}'. Available: {list(desc.geometry.keys())}",
            )
            return None

        self.report(
            {"INFO"},
            f"Entity '{desc.identifier}': importing geometry '{geo_id}' "
            f"(variant '{self.geo_variant}')",
        )

        # Extra search dirs: the folder containing the entity file itself,
        # plus its parent (so loose geo files next to entity files are found).
        fp = Path(self.filepath)
        extra = [str(fp.parent), str(fp.parent.parent)]

        return handler.import_from_entity(
            entity,
            geo_variant=self.geo_variant,
            extra_search_dirs=extra,
            import_locators=self.import_locators,
            apply_rest_rotation=self.apply_rest_rotations,
        )


# ── File menu entry ────────────────────────────────────────────────────────────

def _menu_import(self, _context):
    self.layout.operator(
        BEDROCK_OT_import_auto.bl_idname,
        text="Bedrock Model / Entity (.json)",
    )


# ── Register / Unregister ──────────────────────────────────────────────────────

_CLASSES = [BEDROCK_OT_import_auto]


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(_menu_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(_menu_import)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()