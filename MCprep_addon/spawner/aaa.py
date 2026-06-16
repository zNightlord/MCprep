"""
mc_model_shared.py
==================
Shared constants, coordinate-system utilities, and rotation helpers for the
Minecraft Java Edition (java_model_handler.py) and Bedrock Edition
(bedrock_model_handler.py) importers.

Coordinate systems
------------------
Both Java and Bedrock model files use:
    X-right, Y-up, Z-south  (right-hand Y-up)

Blender uses:
    X-right, Z-up, Y-north  (right-hand Z-up)

Basis-change matrix M (MC model-space → Blender world-space):
    Blender X =  MC X
    Blender Y = -MC Z
    Blender Z =  MC Y

    det(M) = +1 → no orientation flip, winding order is preserved.

Unit scale
----------
16 Minecraft units = 1 Blender unit (≈ 1 metre, 1 Minecraft block).

    Java vertex  : centred at (8,8,8), so a full block spans [-0.5, 0.5]³ in Blender.
    Bedrock vertex: absolute origin (0,0,0), units are 1/16 of a block, no centering.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional, Union

import mathutils

# ── Unit scale ─────────────────────────────────────────────────────────────────

MC_SCALE: float = 1.0 / 16.0       # Minecraft units → Blender metres
BONE_LENGTH: float = MC_SCALE       # default armature tail offset (1 MC unit)

# ── Face direction constants ───────────────────────────────────────────────────

NORTH: str = "north"
SOUTH: str = "south"
UP:    str = "up"
DOWN:  str = "down"
WEST:  str = "west"
EAST:  str = "east"

FACE_DIRECTIONS: tuple[str, ...] = (NORTH, SOUTH, UP, DOWN, WEST, EAST)

# ── 8-vertex cube layout shared by both formats ────────────────────────────────
#
# Java element vertices are generated in this specific order by mcmodel.py's
# add_element() — note that index 0 uses elm_to[1] (maxY), not elm_from[1]:
#
#   Index  Java model coords            Mnemonics
#   0      (minX, maxY, minZ)           −X +Y −Z
#   1      (maxX, maxY, minZ)           +X +Y −Z
#   2      (maxX, minY, minZ)           +X −Y −Z
#   3      (minX, minY, minZ)           −X −Y −Z
#   4      (minX, maxY, maxZ)           −X +Y +Z
#   5      (maxX, maxY, maxZ)           +X +Y +Z
#   6      (maxX, minY, maxZ)           +X −Y +Z
#   7      (minX, minY, maxZ)           −X −Y +Z
#
# Face vertex loops (CCW from outside in MC model space):
#   DOWN uses the *effective* order after mcmodel.py's loop reversal.
#
JAVA_FACE_VERT_LOOPS: dict[str, list[int]] = {
    NORTH: [0, 1, 2, 3],   # −Z face
    SOUTH: [5, 4, 7, 6],   # +Z face
    UP:    [1, 0, 4, 5],   # +Y face
    DOWN:  [3, 2, 6, 7],   # −Y face  (pre-reversed; matches mcmodel.py's reversal)
    WEST:  [4, 0, 3, 7],   # −X face
    EAST:  [1, 5, 6, 2],   # +X face
}

# Bedrock cubes use a more natural layout (minY at indices 0-3):
#   0  (ox,   oy,   oz  )  −X −Y −Z
#   1  (ox+W, oy,   oz  )  +X −Y −Z
#   2  (ox+W, oy+H, oz  )  +X +Y −Z
#   3  (ox,   oy+H, oz  )  −X +Y −Z
#   4  (ox,   oy,   oz+D)  −X −Y +Z
#   5  (ox+W, oy,   oz+D)  +X −Y +Z
#   6  (ox+W, oy+H, oz+D)  +X +Y +Z
#   7  (ox,   oy+H, oz+D)  −X +Y +Z
#
# (Used internally in bedrock_model_handler.py; defined there.)


# ── Coordinate conversion ──────────────────────────────────────────────────────

def java_vertex(
    x: float, y: float, z: float,
    offset: tuple[float, float, float] = (8.0, 8.0, 8.0),
    scale: float = MC_SCALE,
) -> mathutils.Vector:
    """
    Java model-space vertex → Blender world-space Vector.

    Replicates the transformation inside mcmodel.py's ``rotate_around`` without
    the angular rotation component (rotation is handled separately):

        Blender X = -(Jx - offset.x) * scale
        Blender Y =  (Jz - offset.z) * scale
        Blender Z =  (Jy - offset.y) * scale

    The default offset (8, 8, 8) centres the 0-16 block grid at the Blender origin,
    so a full-block element spans [-0.5, 0.5]³.
    """
    return mathutils.Vector((
        -(x - offset[0]) * scale,
         (z - offset[2]) * scale,
         (y - offset[1]) * scale,
    ))


def bedrock_vertex(
    x: float, y: float, z: float,
    scale: float = MC_SCALE,
) -> mathutils.Vector:
    """
    Bedrock model-space vertex → Blender world-space Vector.
    No centering offset — Bedrock uses absolute positions relative to the armature root.
    """
    return mathutils.Vector((x * scale, -z * scale, y * scale))


# ── Rotation conversion ────────────────────────────────────────────────────────

def java_axis_angle_to_matrix(axis: str, angle_deg: float) -> mathutils.Matrix:
    """
    Java legacy element rotation (axis char + degrees, ±45° in 22.5° steps)
    → Blender 3×3 rotation matrix.

    The rotation axis label is in Java model space; we map it to Blender's basis:
        Java X  →  Blender  X
        Java Y  →  Blender  Z   (MC Y-up becomes Blender Z-up)
        Java Z  →  Blender −Y   (MC Z-south becomes Blender −Y-north)
    """
    r = math.radians(angle_deg)
    _axis_map: dict[str, mathutils.Vector] = {
        'x': mathutils.Vector(( 1.0,  0.0,  0.0)),
        'y': mathutils.Vector(( 0.0,  0.0,  1.0)),   # MC Y → Blender Z
        'z': mathutils.Vector(( 0.0, -1.0,  0.0)),   # MC Z → Blender −Y
    }
    bl_axis = _axis_map.get(axis.lower(), mathutils.Vector((0.0, 0.0, 1.0)))
    return mathutils.Matrix.Rotation(r, 3, bl_axis)


def mc_quaternion_to_matrix(x: float, y: float, z: float, w: float) -> mathutils.Matrix:
    """
    Convert a Minecraft 1.21.4 quaternion (stored in Java model space) to a
    Blender 3×3 rotation matrix.

    Method: express as a rotation matrix in Java model space, then conjugate
    by the basis-change matrix M to convert to Blender space:
        R_blender = M @ R_java @ Mᵀ

    The basis-change matrix M is:
        [ 1  0  0 ]
        [ 0  0 -1 ]       (maps Java Y-up → Blender Z-up, Java Z-south → Blender −Y)
        [ 0  1  0 ]
    """
    M = mathutils.Matrix((
        ( 1.0,  0.0,  0.0),
        ( 0.0,  0.0, -1.0),
        ( 0.0,  1.0,  0.0),
    ))
    # Blender's Quaternion constructor uses (w, x, y, z) ordering
    q = mathutils.Quaternion((w, x, y, z))
    R_java = q.to_matrix()
    return M @ R_java @ M.transposed()


def bedrock_euler_to_blender(
    rx: float, ry: float, rz: float
) -> mathutils.Euler:
    """
    Bedrock XYZ-degree bone Euler → Blender XYZ Euler.

    Same conjugation as ``mc_quaternion_to_matrix`` but applied to
    a rotation matrix built from XYZ Euler angles:
        R_blender = M @ R_bedrock @ Mᵀ
    """
    M = mathutils.Matrix((
        ( 1.0,  0.0,  0.0),
        ( 0.0,  0.0, -1.0),
        ( 0.0,  1.0,  0.0),
    ))
    R_bd = mathutils.Euler(
        (math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ"
    ).to_matrix()
    return (M @ R_bd @ M.transposed()).to_euler("XYZ")


# ── Format detection ───────────────────────────────────────────────────────────

#: Possible return values of ``detect_mc_format``.
MC_FORMAT_BEDROCK_GEO    = "bedrock_geometry"
MC_FORMAT_BEDROCK_ENTITY = "bedrock_entity"
MC_FORMAT_JAVA_MODEL     = "java_model"
MC_FORMAT_UNKNOWN        = "unknown"


def detect_mc_format(source: "Union[dict, str, Path]") -> str:
    """
    Inspect a JSON file or already-parsed dict and identify its Minecraft format.

    Returns one of the ``MC_FORMAT_*`` constants:

    =====================  ================================================
    ``bedrock_geometry``   Bedrock ``.geo.json`` — modern ``minecraft:geometry``
                           list or legacy ``geometry.<name>`` key-per-model.
    ``bedrock_entity``     Bedrock ``minecraft:client_entity`` description file.
    ``java_model``         Minecraft Java Edition block/item model.
    ``unknown``            Unrecognised structure.
    =====================  ================================================

    Parameters
    ----------
    source
        Either a ``dict`` (already-parsed JSON), a file path string, or a
        ``pathlib.Path``.  File paths are read and parsed automatically.

    Detection heuristics (in priority order)
    -----------------------------------------
    1. ``"minecraft:geometry"`` key present → **bedrock_geometry** (modern).
    2. Any top-level key starting with ``"geometry."`` → **bedrock_geometry** (legacy 1.12).
    3. ``"minecraft:client_entity"`` key present → **bedrock_entity**.
    4. No ``"format_version"`` AND (``"elements"`` OR ``"parent"`` OR ``"textures"``)
       → **java_model**  (Java models never carry ``format_version``).
    5. Anything else → **unknown**.

    Examples
    --------
    >>> detect_mc_format({"minecraft:geometry": [...]})
    'bedrock_geometry'
    >>> detect_mc_format({"parent": "block/cube_all", "textures": {...}})
    'java_model'
    >>> detect_mc_format("/path/to/axolotl.entity.json")
    'bedrock_entity'
    """
    # ── Load from file if needed ───────────────────────────────────────────────
    if isinstance(source, (str, Path)):
        try:
            with open(source, "r", encoding="utf-8") as fh:
                data: dict = json.load(fh)
        except Exception:
            return MC_FORMAT_UNKNOWN
    else:
        data = source

    if not isinstance(data, dict):
        return MC_FORMAT_UNKNOWN

    # ── Bedrock geometry (modern, 1.16+) ───────────────────────────────────────
    if "minecraft:geometry" in data:
        return MC_FORMAT_BEDROCK_GEO

    # ── Bedrock geometry (legacy 1.12.0 — keys like "geometry.entity_name") ───
    if any(k.startswith("geometry.") for k in data):
        return MC_FORMAT_BEDROCK_GEO

    # ── Bedrock client entity descriptor ──────────────────────────────────────
    if "minecraft:client_entity" in data:
        return MC_FORMAT_BEDROCK_ENTITY

    # ── Java Edition block/item model ─────────────────────────────────────────
    # Java models never use "format_version" (a Bedrock convention).
    if "format_version" not in data:
        if "elements" in data or "parent" in data or "textures" in data:
            return MC_FORMAT_JAVA_MODEL

    return MC_FORMAT_UNKNOWN