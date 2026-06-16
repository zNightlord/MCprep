"""
bedrock_variant_props.py
========================
WindowManager pointer property group storing all Bedrock mob variant
selectors, and a modal popup operator that shows only the properties
relevant to the mob being imported.

Usage
-----
Invoke the popup from an operator or script::

    bpy.ops.bedrock.import_variant_picker(
        filepath="/path/to/entity/fox.entity.json",
        resource_pack_root="/path/to/resource_pack",
    )

The operator parses the entity file, detects the mob identifier, pre-populates
``bpy.context.window_manager.bedrock_variants``, and presents a popup dialog
whose contents change based on the mob type.  On OK the import runs and the
selected variant is stored as ``arm_obj["mc_selected_variant"]``.

Reading variant state from anywhere::

    wm    = bpy.context.window_manager
    props = wm.bedrock_variants           # BedrockVariantProperties instance
    print(props.mob_identifier)           # e.g. "minecraft:fox"
    print(props.fox_type)                 # "red" or "snow"
    print(props.is_baby)                  # True / False

Mob coverage
------------
Universal     : is_baby
Fox           : fox_type (red/snow)
Villager      : profession, biome, level
Zombie Villager: profession, biome
Horse         : variant, markings, armor
Donkey/Mule   : has_chest
Llama         : variant, decor_color
Cat           : cat_type, collar_color
Wolf          : wolf_variant, collar_color, angry
Rabbit        : rabbit_type
Sheep         : color, sheared
Mooshroom     : mooshroom_variant
Panda         : main_gene, hidden_gene
Parrot        : parrot_variant
Axolotl       : axolotl_variant
Frog          : frog_variant
Tropical Fish : pattern, base_color, pattern_color
Slime/Magma   : slime_size
Creeper       : powered
Shulker       : shulker_color
Bee           : has_nectar, angry
Goat          : is_screaming
Piglin        : is_zombified
Hoglin        : is_zombified
Warden        : anger_level
Armadillo     : state
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup, Operator, WindowManager

try:
    from .bedrock_entity_format import BedrockEntityFile
    from .bedrock_model_handler  import BedrockModelBlenderHandler
    from .mc_model_shared        import detect_mc_format, MC_FORMAT_BEDROCK_ENTITY, MC_FORMAT_BEDROCK_GEO
    from .bedrock_model_format   import BedrockModelFile
except ImportError:
    from bedrock_entity_format import BedrockEntityFile
    from bedrock_model_handler  import BedrockModelBlenderHandler
    from mc_model_shared        import detect_mc_format, MC_FORMAT_BEDROCK_ENTITY, MC_FORMAT_BEDROCK_GEO
    from bedrock_model_format   import BedrockModelFile


# ═══════════════════════════════════════════════════════════════════════════════
# Shared enum item tables
# ═══════════════════════════════════════════════════════════════════════════════

_DYE_COLORS = [
    ("white",      "White",      "", 0),
    ("orange",     "Orange",     "", 1),
    ("magenta",    "Magenta",    "", 2),
    ("light_blue", "Light Blue", "", 3),
    ("yellow",     "Yellow",     "", 4),
    ("lime",       "Lime",       "", 5),
    ("pink",       "Pink",       "", 6),
    ("gray",       "Gray",       "", 7),
    ("light_gray", "Light Gray", "", 8),
    ("cyan",       "Cyan",       "", 9),
    ("purple",     "Purple",     "", 10),
    ("blue",       "Blue",       "", 11),
    ("brown",      "Brown",      "", 12),
    ("green",      "Green",      "", 13),
    ("red",        "Red",        "", 14),
    ("black",      "Black",      "", 15),
]

_COLLAR_COLORS = _DYE_COLORS  # same palette

_GENERIC_SIZE = [
    ("small",  "Small",  "", 0),
    ("medium", "Medium", "", 1),
    ("large",  "Large",  "", 2),
]


# ═══════════════════════════════════════════════════════════════════════════════
# WindowManager PropertyGroup — all variant properties live here
# ═══════════════════════════════════════════════════════════════════════════════

class BedrockVariantProperties(PropertyGroup):
    """
    Flat container for every Bedrock mob variant selector.
    Registered on ``bpy.types.WindowManager`` as ``bedrock_variants``.

    Only a subset of these properties is shown in the popup at a time;
    the visible set is determined by ``mob_identifier`` via the mob registry.
    """

    # ── Internal state set by the operator ────────────────────────────────────
    mob_identifier: StringProperty(
        name="Mob",
        description="Minecraft identifier of the mob being imported (set automatically)",
        default="",
    )
    available_geo_variants: StringProperty(
        name="Available Variants",
        description="JSON list of geometry variant keys present in the entity file",
        default="[]",
    )

    # ── Universal ──────────────────────────────────────────────────────────────
    is_baby: BoolProperty(
        name="Is Baby",
        description="Import the baby / small variant",
        default=False,
    )

    # ── Fox ───────────────────────────────────────────────────────────────────
    fox_type: EnumProperty(
        name="Fox Type",
        items=[
            ("red",  "Red",  "Classic red fox", 0),
            ("snow", "Snow", "Arctic snow fox", 1),
        ],
        default="red",
    )

    # ── Villager / Zombie Villager ─────────────────────────────────────────────
    villager_profession: EnumProperty(
        name="Profession",
        items=[
            ("none",          "None (Unemployed)", "", 0),
            ("armorer",       "Armorer",           "", 1),
            ("butcher",       "Butcher",           "", 2),
            ("cartographer",  "Cartographer",      "", 3),
            ("cleric",        "Cleric",            "", 4),
            ("farmer",        "Farmer",            "", 5),
            ("fisherman",     "Fisherman",         "", 6),
            ("fletcher",      "Fletcher",          "", 7),
            ("leatherworker", "Leatherworker",     "", 8),
            ("librarian",     "Librarian",         "", 9),
            ("mason",         "Mason",             "", 10),
            ("nitwit",        "Nitwit",            "", 11),
            ("shepherd",      "Shepherd",          "", 12),
            ("toolsmith",     "Toolsmith",         "", 13),
            ("weaponsmith",   "Weaponsmith",       "", 14),
        ],
        default="none",
    )
    villager_biome: EnumProperty(
        name="Biome Style",
        items=[
            ("plains",  "Plains",  "", 0),
            ("desert",  "Desert",  "", 1),
            ("jungle",  "Jungle",  "", 2),
            ("savanna", "Savanna", "", 3),
            ("snow",    "Snow",    "", 4),
            ("swamp",   "Swamp",   "", 5),
            ("taiga",   "Taiga",   "", 6),
        ],
        default="plains",
    )
    villager_level: IntProperty(
        name="Trade Level",
        description="1 = Novice, 2 = Apprentice, 3 = Journeyman, 4 = Expert, 5 = Master",
        min=1, max=5, default=1,
    )

    # ── Horse ─────────────────────────────────────────────────────────────────
    horse_variant: EnumProperty(
        name="Coat Color",
        items=[
            ("white",      "White",      "", 0),
            ("creamy",     "Creamy",     "", 1),
            ("chestnut",   "Chestnut",   "", 2),
            ("brown",      "Brown",      "", 3),
            ("black",      "Black",      "", 4),
            ("gray",       "Gray",       "", 5),
            ("dark_brown", "Dark Brown", "", 6),
        ],
        default="brown",
    )
    horse_markings: EnumProperty(
        name="Markings",
        items=[
            ("none",        "None",        "", 0),
            ("white",       "White",       "", 1),
            ("whitefield",  "Whitefield",  "", 2),
            ("white_dots",  "White Dots",  "", 3),
            ("black_dots",  "Black Dots",  "", 4),
        ],
        default="none",
    )
    horse_armor: EnumProperty(
        name="Armor",
        items=[
            ("none",    "None",    "", 0),
            ("leather", "Leather", "", 1),
            ("iron",    "Iron",    "", 2),
            ("gold",    "Gold",    "", 3),
            ("diamond", "Diamond", "", 4),
        ],
        default="none",
    )

    # ── Donkey / Mule ─────────────────────────────────────────────────────────
    horse_has_chest: BoolProperty(
        name="Has Chest",
        description="Equipped with a chest",
        default=False,
    )

    # ── Llama ─────────────────────────────────────────────────────────────────
    llama_variant: EnumProperty(
        name="Llama Color",
        items=[
            ("creamy", "Creamy", "", 0),
            ("white",  "White",  "", 1),
            ("brown",  "Brown",  "", 2),
            ("gray",   "Gray",   "", 3),
        ],
        default="creamy",
    )
    llama_decor_color: EnumProperty(
        name="Carpet / Decor",
        items=[("none", "None", "", 0)] + [(c[0], c[1], c[2], c[3] + 1) for c in _DYE_COLORS],
        default="none",
    )

    # ── Cat ───────────────────────────────────────────────────────────────────
    cat_type: EnumProperty(
        name="Cat Type",
        items=[
            ("tabby",    "Tabby",         "", 0),
            ("tuxedo",   "Tuxedo",         "", 1),
            ("red",      "Red",            "", 2),
            ("siamese",  "Siamese",        "", 3),
            ("british",  "British",        "", 4),
            ("calico",   "Calico",         "", 5),
            ("persian",  "Persian",        "", 6),
            ("ragdoll",  "Ragdoll",        "", 7),
            ("white",    "White",          "", 8),
            ("jellie",   "Jellie",         "", 9),
            ("black",    "Black",          "", 10),
        ],
        default="tabby",
    )
    cat_collar_color: EnumProperty(
        name="Collar Color",
        items=_COLLAR_COLORS,
        default="red",
    )

    # ── Wolf ──────────────────────────────────────────────────────────────────
    wolf_variant: EnumProperty(
        name="Wolf Variant",
        items=[
            ("pale",     "Pale",     "Classic grey wolf",      0),
            ("spotted",  "Spotted",  "Spotted jungle wolf",    1),
            ("snowy",    "Snowy",    "Snowy tundra wolf",      2),
            ("black",    "Black",    "Black old-growth wolf",  3),
            ("ashen",    "Ashen",    "Ashen savanna wolf",     4),
            ("rusty",    "Rusty",    "Rusty badlands wolf",    5),
            ("striped",  "Striped",  "Striped wolf",           6),
            ("woods",    "Woods",    "Woods wolf",             7),
            ("chestnut", "Chestnut", "Chestnut wolf",          8),
        ],
        default="pale",
    )
    wolf_collar_color: EnumProperty(
        name="Collar Color",
        items=_COLLAR_COLORS,
        default="red",
    )
    wolf_angry: BoolProperty(
        name="Angry",
        description="Show the angry / threatened pose",
        default=False,
    )

    # ── Rabbit ────────────────────────────────────────────────────────────────
    rabbit_type: EnumProperty(
        name="Rabbit Type",
        items=[
            ("brown",          "Brown",          "", 0),
            ("white",          "White",          "", 1),
            ("black",          "Black",          "", 2),
            ("white_splotched","White Splotched", "", 3),
            ("gold",           "Gold",            "", 4),
            ("salt",           "Salt & Pepper",   "", 5),
            ("evil",           "Killer Bunny",    "", 6),
        ],
        default="brown",
    )

    # ── Sheep ─────────────────────────────────────────────────────────────────
    sheep_color: EnumProperty(
        name="Wool Color",
        items=_DYE_COLORS,
        default="white",
    )
    sheep_sheared: BoolProperty(
        name="Sheared",
        description="Import the sheared (no wool) geometry",
        default=False,
    )

    # ── Mooshroom ─────────────────────────────────────────────────────────────
    mooshroom_variant: EnumProperty(
        name="Mooshroom Type",
        items=[
            ("red",   "Red Mooshroom",   "", 0),
            ("brown", "Brown Mooshroom", "", 1),
        ],
        default="red",
    )

    # ── Panda ─────────────────────────────────────────────────────────────────
    panda_main_gene: EnumProperty(
        name="Main Gene",
        items=[
            ("lazy",       "Lazy",       "", 0),
            ("worried",    "Worried",    "", 1),
            ("playful",    "Playful",    "", 2),
            ("aggressive", "Aggressive", "", 3),
            ("weak",       "Weak",       "", 4),
            ("brown",      "Brown",      "", 5),
            ("normal",     "Normal",     "", 6),
        ],
        default="normal",
    )
    panda_hidden_gene: EnumProperty(
        name="Hidden Gene",
        items=[
            ("lazy",       "Lazy",       "", 0),
            ("worried",    "Worried",    "", 1),
            ("playful",    "Playful",    "", 2),
            ("aggressive", "Aggressive", "", 3),
            ("weak",       "Weak",       "", 4),
            ("brown",      "Brown",      "", 5),
            ("normal",     "Normal",     "", 6),
        ],
        default="normal",
    )

    # ── Parrot ────────────────────────────────────────────────────────────────
    parrot_variant: EnumProperty(
        name="Parrot Color",
        items=[
            ("red_blue",   "Red & Blue",    "", 0),
            ("blue",       "Blue",          "", 1),
            ("green",      "Green",         "", 2),
            ("yellow_blue","Yellow & Blue", "", 3),
            ("gray",       "Gray",          "", 4),
        ],
        default="red_blue",
    )

    # ── Axolotl ───────────────────────────────────────────────────────────────
    axolotl_variant: EnumProperty(
        name="Axolotl Color",
        items=[
            ("lucy", "Lucy (Pink)",  "", 0),
            ("wild", "Wild (Brown)", "", 1),
            ("gold", "Gold",         "", 2),
            ("cyan", "Cyan",         "", 3),
            ("blue", "Blue (Rare)",  "", 4),
        ],
        default="lucy",
    )

    # ── Frog ──────────────────────────────────────────────────────────────────
    frog_variant: EnumProperty(
        name="Frog Type",
        items=[
            ("temperate", "Temperate (Orange)", "", 0),
            ("warm",      "Warm (White)",        "", 1),
            ("cold",      "Cold (Green)",        "", 2),
        ],
        default="temperate",
    )

    # ── Tropical Fish ─────────────────────────────────────────────────────────
    tropical_fish_pattern: EnumProperty(
        name="Body Pattern",
        items=[
            ("kob",       "Kob",       "", 0),
            ("sunstreak", "Sunstreak", "", 1),
            ("snooper",   "Snooper",   "", 2),
            ("dasher",    "Dasher",    "", 3),
            ("brinely",   "Brinely",   "", 4),
            ("spotty",    "Spotty",    "", 5),
            ("flopper",   "Flopper",   "", 6),
            ("stripey",   "Stripey",   "", 7),
            ("glitter",   "Glitter",   "", 8),
            ("blockfish", "Blockfish", "", 9),
            ("betty",     "Betty",     "", 10),
            ("clayfish",  "Clayfish",  "", 11),
        ],
        default="kob",
    )
    tropical_fish_base_color: EnumProperty(
        name="Body Color",
        items=_DYE_COLORS,
        default="white",
    )
    tropical_fish_pattern_color: EnumProperty(
        name="Pattern Color",
        items=_DYE_COLORS,
        default="red",
    )

    # ── Slime / Magma Cube ────────────────────────────────────────────────────
    slime_size: EnumProperty(
        name="Size",
        items=_GENERIC_SIZE,
        default="large",
    )

    # ── Creeper ───────────────────────────────────────────────────────────────
    creeper_powered: BoolProperty(
        name="Charged",
        description="Show the charged (lightning-struck) variant",
        default=False,
    )

    # ── Shulker ───────────────────────────────────────────────────────────────
    shulker_color: EnumProperty(
        name="Shulker Color",
        items=[("default", "Default (Purple)", "", 0)]
              + [(c[0], c[1], c[2], c[3] + 1) for c in _DYE_COLORS],
        default="default",
    )

    # ── Bee ───────────────────────────────────────────────────────────────────
    bee_has_nectar: BoolProperty(
        name="Carrying Nectar",
        description="Bee with pollen / full abdomen",
        default=False,
    )
    bee_angry: BoolProperty(
        name="Angry",
        description="Stinger-out angry pose",
        default=False,
    )

    # ── Goat ──────────────────────────────────────────────────────────────────
    goat_is_screaming: BoolProperty(
        name="Screaming Goat",
        description="Rare screaming variant",
        default=False,
    )

    # ── Piglin ────────────────────────────────────────────────────────────────
    piglin_is_zombified: BoolProperty(
        name="Zombified",
        description="Import as zombified piglin",
        default=False,
    )

    # ── Hoglin ────────────────────────────────────────────────────────────────
    hoglin_is_zombified: BoolProperty(
        name="Zoglin (Zombified)",
        description="Import as zoglin",
        default=False,
    )

    # ── Warden ────────────────────────────────────────────────────────────────
    warden_anger: EnumProperty(
        name="Anger Level",
        items=[
            ("calm",     "Calm",     "Default idle pose",      0),
            ("agitated", "Agitated", "Partially emerged",      1),
            ("angry",    "Angry",    "Fully alert attack pose", 2),
        ],
        default="calm",
    )

    # ── Armadillo ─────────────────────────────────────────────────────────────
    armadillo_state: EnumProperty(
        name="State",
        items=[
            ("unrolled", "Unrolled", "Normal walking state", 0),
            ("rolled",   "Rolled",   "Defensive ball",       1),
        ],
        default="unrolled",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Mob variant registry
# ═══════════════════════════════════════════════════════════════════════════════
#
# Maps the Minecraft mob name (without "minecraft:" prefix) to a dict that
# describes what to show in the popup.
#
# Schema per entry
# ----------------
# "groups": list of (header_label, [prop_attr_names]) — drawn in order.
# "note":   optional informational string shown at the bottom of the popup.
# "geo_fn": name of the function in _GEO_RESOLVERS that maps props → geo variant key.

_REGISTRY: dict[str, dict] = {

    # ── Passive / Neutral ──────────────────────────────────────────────────────

    "fox": {
        "icon": "GHOST_ENABLED",
        "groups": [
            ("Fox",     ["fox_type"]),
            ("Age",     ["is_baby"]),
        ],
        "note": "Snow fox uses a separate geometry in the entity file.",
        "geo_fn": "fox",
    },

    "axolotl": {
        "icon": "COLORSET_01_VEC",
        "groups": [
            ("Variant", ["axolotl_variant"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "frog": {
        "icon": "COLORSET_03_VEC",
        "groups": [
            ("Variant", ["frog_variant"]),
        ],
        "geo_fn": "default",
    },

    "rabbit": {
        "icon": "COLORSET_04_VEC",
        "groups": [
            ("Rabbit Type", ["rabbit_type"]),
            ("Age",         ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "sheep": {
        "icon": "COLORSET_02_VEC",
        "groups": [
            ("Wool",  ["sheep_color"]),
            ("State", ["sheep_sheared"]),
            ("Age",   ["is_baby"]),
        ],
        "note": "Sheared removes the wool mesh layer.",
        "geo_fn": "sheep",
    },

    "mooshroom": {
        "icon": "COLORSET_02_VEC",
        "groups": [
            ("Variant", ["mooshroom_variant"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "panda": {
        "icon": "COLORSET_14_VEC",
        "groups": [
            ("Genetics", ["panda_main_gene", "panda_hidden_gene"]),
            ("Age",      ["is_baby"]),
        ],
        "note": "Gene combination determines behaviour and appearance.",
        "geo_fn": "baby_or_default",
    },

    "parrot": {
        "icon": "COLORSET_10_VEC",
        "groups": [
            ("Color", ["parrot_variant"]),
        ],
        "geo_fn": "default",
    },

    "cat": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Type",   ["cat_type"]),
            ("Collar", ["cat_collar_color"]),
        ],
        "geo_fn": "default",
    },

    "wolf": {
        "icon": "COLORSET_14_VEC",
        "groups": [
            ("Variant", ["wolf_variant"]),
            ("Collar",  ["wolf_collar_color"]),
            ("State",   ["wolf_angry"]),
            ("Age",     ["is_baby"]),
        ],
        "note": "Collar is only visible on tamed wolves.",
        "geo_fn": "wolf",
    },

    "bee": {
        "icon": "COLORSET_05_VEC",
        "groups": [
            ("State", ["bee_has_nectar", "bee_angry"]),
        ],
        "geo_fn": "bee",
    },

    "goat": {
        "icon": "COLORSET_02_VEC",
        "groups": [
            ("Variant", ["goat_is_screaming"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    # ── Horses / Mounts ────────────────────────────────────────────────────────

    "horse": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Coat",     ["horse_variant"]),
            ("Markings", ["horse_markings"]),
            ("Armor",    ["horse_armor"]),
            ("Age",      ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "donkey": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Equipment", ["horse_has_chest"]),
            ("Age",       ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "mule": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Equipment", ["horse_has_chest"]),
        ],
        "geo_fn": "default",
    },

    "llama": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Variant", ["llama_variant"]),
            ("Carpet",  ["llama_decor_color"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "trader_llama": {
        "icon": "COLORSET_12_VEC",
        "groups": [
            ("Carpet", ["llama_decor_color"]),
        ],
        "geo_fn": "default",
    },

    # ── Villagers ──────────────────────────────────────────────────────────────

    "villager": {
        "icon": "COLORSET_07_VEC",
        "groups": [
            ("Profession",   ["villager_profession"]),
            ("Biome",        ["villager_biome"]),
            ("Trade Level",  ["villager_level"]),
            ("Age",          ["is_baby"]),
        ],
        "note": "Biome affects clothing style; profession affects hat/apron.",
        "geo_fn": "baby_or_default",
    },

    "zombie_villager": {
        "icon": "COLORSET_07_VEC",
        "groups": [
            ("Profession", ["villager_profession"]),
            ("Biome",      ["villager_biome"]),
            ("Age",        ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    # ── Hostile ────────────────────────────────────────────────────────────────

    "creeper": {
        "icon": "COLORSET_03_VEC",
        "groups": [
            ("State", ["creeper_powered"]),
        ],
        "geo_fn": "default",
    },

    "shulker": {
        "icon": "COLORSET_09_VEC",
        "groups": [
            ("Color", ["shulker_color"]),
        ],
        "geo_fn": "default",
    },

    "slime": {
        "icon": "COLORSET_03_VEC",
        "groups": [
            ("Size", ["slime_size"]),
        ],
        "geo_fn": "slime",
    },

    "magma_cube": {
        "icon": "COLORSET_01_VEC",
        "groups": [
            ("Size", ["slime_size"]),
        ],
        "geo_fn": "slime",
    },

    "tropicalfish": {
        "icon": "COLORSET_06_VEC",
        "groups": [
            ("Body",    ["tropical_fish_base_color"]),
            ("Pattern", ["tropical_fish_pattern", "tropical_fish_pattern_color"]),
        ],
        "geo_fn": "default",
    },

    "piglin": {
        "icon": "COLORSET_08_VEC",
        "groups": [
            ("Variant", ["piglin_is_zombified"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "piglin",
    },

    "hoglin": {
        "icon": "COLORSET_08_VEC",
        "groups": [
            ("Variant", ["hoglin_is_zombified"]),
            ("Age",     ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "zombie": {
        "icon": "COLORSET_03_VEC",
        "groups": [
            ("Age", ["is_baby"]),
        ],
        "geo_fn": "baby_or_default",
    },

    "warden": {
        "icon": "COLORSET_04_VEC",
        "groups": [
            ("Anger Level", ["warden_anger"]),
        ],
        "note": "Anger level affects the sonic shriek animation rig.",
        "geo_fn": "default",
    },

    "armadillo": {
        "icon": "COLORSET_13_VEC",
        "groups": [
            ("State", ["armadillo_state"]),
        ],
        "geo_fn": "armadillo",
    },

    # ── Mobs with no extra variants (baby only) ────────────────────────────────
    "allay":          {"icon": "COLORSET_06_VEC", "groups": [],                      "geo_fn": "default"},
    "bat":            {"icon": "COLORSET_14_VEC", "groups": [],                      "geo_fn": "default"},
    "blaze":          {"icon": "COLORSET_01_VEC", "groups": [],                      "geo_fn": "default"},
    "camel":          {"icon": "COLORSET_12_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "chicken":        {"icon": "COLORSET_02_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "cod":            {"icon": "COLORSET_06_VEC", "groups": [],                      "geo_fn": "default"},
    "cow":            {"icon": "COLORSET_02_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "dolphin":        {"icon": "COLORSET_06_VEC", "groups": [],                      "geo_fn": "default"},
    "drowned":        {"icon": "COLORSET_04_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "enderman":       {"icon": "COLORSET_09_VEC", "groups": [],                      "geo_fn": "default"},
    "ghast":          {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "glow_squid":     {"icon": "COLORSET_03_VEC", "groups": [],                      "geo_fn": "default"},
    "guardian":       {"icon": "COLORSET_04_VEC", "groups": [],                      "geo_fn": "default"},
    "iron_golem":     {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "ocelot":         {"icon": "COLORSET_12_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "phantom":        {"icon": "COLORSET_09_VEC", "groups": [],                      "geo_fn": "default"},
    "pig":            {"icon": "COLORSET_01_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "pillager":       {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "polar_bear":     {"icon": "COLORSET_07_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "pufferfish":     {"icon": "COLORSET_05_VEC", "groups": [],                      "geo_fn": "default"},
    "ravager":        {"icon": "COLORSET_01_VEC", "groups": [],                      "geo_fn": "default"},
    "salmon":         {"icon": "COLORSET_01_VEC", "groups": [],                      "geo_fn": "default"},
    "silverfish":     {"icon": "COLORSET_14_VEC", "groups": [],                      "geo_fn": "default"},
    "skeleton":       {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "sniffer":        {"icon": "COLORSET_13_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "snow_golem":     {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "spider":         {"icon": "COLORSET_14_VEC", "groups": [],                      "geo_fn": "default"},
    "squid":          {"icon": "COLORSET_06_VEC", "groups": [],                      "geo_fn": "default"},
    "strider":        {"icon": "COLORSET_01_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "turtle":         {"icon": "COLORSET_03_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "vindicator":     {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "witch":          {"icon": "COLORSET_07_VEC", "groups": [],                      "geo_fn": "default"},
    "wither":         {"icon": "COLORSET_09_VEC", "groups": [],                      "geo_fn": "default"},
    "wither_skeleton":{"icon": "COLORSET_14_VEC", "groups": [],                      "geo_fn": "default"},
    "zoglin":         {"icon": "COLORSET_08_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
    "zombie_horse":   {"icon": "COLORSET_03_VEC", "groups": [("Age", ["is_baby"])],  "geo_fn": "baby_or_default"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Geometry variant resolution
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_geo_variant(mob_id: str, props: BedrockVariantProperties) -> str:
    """
    Determine the geometry dict key to pass to
    ``BedrockModelBlenderHandler.import_from_entity()`` based on the mob's
    identifier and the current variant property values.

    Returns a string key expected inside ``entity.description.geometry``
    (e.g. ``"default"``, ``"baby"``, ``"snow"``).

    If the resolved key is not present in the entity file the handler falls
    back to ``"default"`` automatically.
    """
    name = mob_id.split(":")[-1]        # strip namespace
    entry = _REGISTRY.get(name, {})
    fn    = entry.get("geo_fn", "default")

    # ── Resolver dispatch ──────────────────────────────────────────────────────
    if fn == "default":
        return "default"

    if fn == "baby_or_default":
        return "baby" if props.is_baby else "default"

    if fn == "fox":
        # Entity file keys: "default" (red), "snow", "baby", "sleeping", etc.
        if props.is_baby:
            return "baby"
        return "snow" if props.fox_type == "snow" else "default"

    if fn == "sheep":
        return "sheared" if props.sheep_sheared else (
            "baby" if props.is_baby else "default"
        )

    if fn == "wolf":
        return "angry" if props.wolf_angry else (
            "baby" if props.is_baby else "default"
        )

    if fn == "bee":
        if props.bee_angry and props.bee_has_nectar:
            return "angry_nectar"
        if props.bee_angry:
            return "angry"
        if props.bee_has_nectar:
            return "nectar"
        return "default"

    if fn == "slime":
        return props.slime_size          # "small", "medium", "large"

    if fn == "piglin":
        if props.piglin_is_zombified:
            return "zombified"
        return "baby" if props.is_baby else "default"

    if fn == "armadillo":
        return "rolled" if props.armadillo_state == "rolled" else "default"

    return "default"


def collect_variant_metadata(
    mob_id: str,
    props: BedrockVariantProperties,
) -> dict[str, str]:
    """
    Build a flat dict of all currently selected variant values for *mob_id*.
    Stored as ``arm_obj["mc_selected_variant_*"]`` custom properties after import.
    """
    name = mob_id.split(":")[-1]
    entry = _REGISTRY.get(name, {})
    all_props: list[str] = []
    for _, group_props in entry.get("groups", []):
        all_props.extend(group_props)

    meta: dict[str, str] = {}
    for pname in all_props:
        val = getattr(props, pname, None)
        if val is not None:
            meta[f"mc_variant_{pname}"] = str(val)
    return meta


# ═══════════════════════════════════════════════════════════════════════════════
# Popup draw helper
# ═══════════════════════════════════════════════════════════════════════════════

def draw_variant_popup(layout: bpy.types.UILayout, props: BedrockVariantProperties) -> None:
    """
    Shared draw logic for the variant popup.
    Called from the operator's ``draw()`` method.

    Draws only the property groups relevant to the current mob, with section
    headers, a note (if any), and an info row showing available geo variants.
    """
    mob_id = props.mob_identifier
    name   = mob_id.split(":")[-1] if ":" in mob_id else mob_id
    entry  = _REGISTRY.get(name)

    # ── Header ─────────────────────────────────────────────────────────────────
    header = layout.box()
    row = header.row(align=True)
    icon = entry["icon"] if entry else "QUESTION"
    row.label(text=mob_id or "Unknown mob", icon=icon)

    # ── Available geometry variants info ───────────────────────────────────────
    try:
        avail = json.loads(props.available_geo_variants)
    except Exception:
        avail = []
    if avail:
        info = header.row()
        info.label(text=f"Geo variants: {', '.join(avail)}", icon="INFO")

    layout.separator(factor=0.5)

    # ── No registry entry → show is_baby + note ────────────────────────────────
    if entry is None:
        layout.label(text="No variant data for this mob.", icon="ERROR")
        layout.prop(props, "is_baby")
        return

    groups = entry.get("groups", [])

    if not groups:
        layout.label(text="No configurable variants for this mob.", icon="CHECKMARK")
        return

    # ── Draw each property group ───────────────────────────────────────────────
    for group_label, prop_names in groups:
        box = layout.box()
        col = box.column(align=True)
        if group_label:
            col.label(text=group_label, icon="PROPERTIES")
        for pname in prop_names:
            col.prop(props, pname)

    # ── Optional note ──────────────────────────────────────────────────────────
    note = entry.get("note", "")
    if note:
        layout.separator(factor=0.3)
        note_box = layout.box()
        note_box.scale_y = 0.75
        lines = note.split(". ")
        for ln in lines:
            if ln.strip():
                note_box.label(text=ln.strip(), icon="NONE")


# ═══════════════════════════════════════════════════════════════════════════════
# Popup import operator
# ═══════════════════════════════════════════════════════════════════════════════

class BEDROCK_OT_import_variant_picker(Operator):
    """
    Parse a Bedrock entity / geo file, then open a variant-picker popup.

    The popup draws only the properties relevant to the detected mob type.
    Confirming the popup executes the import with the selected variants.

    Invoke programmatically::

        bpy.ops.bedrock.import_variant_picker(
            filepath="/path/to/entity/fox.entity.json",
            resource_pack_root="/path/to/resource_pack",
        )
    """

    bl_idname = "bedrock.import_variant_picker"
    bl_label  = "Bedrock — Choose Variant"
    bl_options = {"REGISTER", "UNDO"}

    # ── Operator properties (set by caller, not shown directly in popup) ───────
    filepath: StringProperty(
        name="File Path",
        subtype="FILE_PATH",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    resource_pack_root: StringProperty(
        name="Resource Pack Root",
        description="Folder containing entity/, models/, textures/ …",
        subtype="DIR_PATH",
        options={"HIDDEN", "SKIP_SAVE"},
        default="",
    )
    import_locators: bpy.props.BoolProperty(
        name="Import Locators",
        default=True,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    apply_rest_rotations: bpy.props.BoolProperty(
        name="Apply Rest Rotations",
        default=True,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    filter_glob: StringProperty(
        default="*.json;*.geo.json",
        options={"HIDDEN"},
    )

    # ── invoke_props_dialog ────────────────────────────────────────────────────

    def invoke(self, context: bpy.types.Context, _event) -> set:
        wm    = context.window_manager
        props = wm.bedrock_variants

        # Parse the file and populate wm state
        ok, mob_id, avail_variants = self._parse_file(props)
        if not ok:
            self.report({"ERROR"}, f"Cannot detect mob from file: {self.filepath}")
            return {"CANCELLED"}

        props.mob_identifier       = mob_id
        props.available_geo_variants = json.dumps(avail_variants)

        # Reset is_baby each invocation so the popup starts clean
        props.is_baby = False

        # Show the dialog — draw() renders the content
        return context.window_manager.invoke_props_dialog(
            self,
            width=340,
            confirm_text="Import",
        )

    # ── Dialog draw ───────────────────────────────────────────────────────────

    def draw(self, context: bpy.types.Context) -> None:
        draw_variant_popup(self.layout, context.window_manager.bedrock_variants)

    # ── Execute ───────────────────────────────────────────────────────────────

    def execute(self, context: bpy.types.Context) -> set:
        wm    = context.window_manager
        props = wm.bedrock_variants
        mob_id = props.mob_identifier

        geo_variant = resolve_geo_variant(mob_id, props)
        var_meta    = collect_variant_metadata(mob_id, props)

        # ── Detect format and run the appropriate import ───────────────────────
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception as exc:
            self.report({"ERROR"}, f"Cannot read file: {exc}")
            return {"CANCELLED"}

        fmt = detect_mc_format(raw)
        handler = BedrockModelBlenderHandler(
            context=context,
            resource_pack_root=self.resource_pack_root or None,
        )
        arm_obj: Optional[bpy.types.Object] = None

        if fmt == MC_FORMAT_BEDROCK_ENTITY:
            entity  = BedrockEntityFile.from_dict(raw)
            fp      = Path(self.filepath)
            extra   = [str(fp.parent), str(fp.parent.parent)]
            arm_obj = handler.import_from_entity(
                entity,
                geo_variant=geo_variant,
                extra_search_dirs=extra,
                import_locators=self.import_locators,
                apply_rest_rotation=self.apply_rest_rotations,
            )

        elif fmt == MC_FORMAT_BEDROCK_GEO:
            model   = BedrockModelFile.from_dict(raw)
            arm_obj = handler.import_geometry(
                model,
                geo_index=0,
                import_locators=self.import_locators,
                apply_rest_rotation=self.apply_rest_rotations,
            )

        else:
            self.report({"ERROR"}, "File is not a Bedrock geometry or entity JSON")
            return {"CANCELLED"}

        if arm_obj is None:
            self.report({"ERROR"}, "Import produced no objects — check the console")
            return {"CANCELLED"}

        # ── Store selected variant info as custom props ─────────────────────────
        arm_obj["mc_selected_variant"]     = geo_variant
        arm_obj["mc_selected_mob"]         = mob_id
        for k, v in var_meta.items():
            arm_obj[k] = v

        # ── Select result ──────────────────────────────────────────────────────
        for ob in context.selected_objects:
            ob.select_set(False)
        arm_obj.select_set(True)
        context.view_layer.objects.active = arm_obj

        self.report(
            {"INFO"},
            f"Imported '{arm_obj.name}' · mob={mob_id} · variant='{geo_variant}'",
        )
        return {"FINISHED"}

    # ── Private helpers ────────────────────────────────────────────────────────

    def _parse_file(
        self, props: BedrockVariantProperties
    ) -> tuple[bool, str, list[str]]:
        """
        Parse the target file and return (success, mob_identifier, geo_variant_keys).
        """
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            return False, "", []

        fmt = detect_mc_format(raw)

        if fmt == MC_FORMAT_BEDROCK_ENTITY:
            entity   = BedrockEntityFile.from_dict(raw)
            mob_id   = entity.description.identifier
            variants = list(entity.description.geometry.keys())
            return True, mob_id, variants

        if fmt == MC_FORMAT_BEDROCK_GEO:
            model = BedrockModelFile.from_dict(raw)
            if model.geometries:
                identifier = model.geometries[0].description.identifier
                # Geo files have no mob identifier — use geometry name as hint
                return True, identifier, ["default"]
            return False, "", []

        return False, "", []


# ═══════════════════════════════════════════════════════════════════════════════
# File-browser operator (wraps the picker for the File menu)
# ═══════════════════════════════════════════════════════════════════════════════

class BEDROCK_OT_open_variant_picker(Operator):
    """
    Open a file browser to select a Bedrock file, then launch the variant picker.
    Register in File > Import for a one-click entry point.
    """

    bl_idname = "bedrock.open_variant_picker"
    bl_label  = "Bedrock Model — Import with Variants"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})
    resource_pack_root: StringProperty(subtype="DIR_PATH", default="", options={"SKIP_SAVE"})
    filter_glob: StringProperty(default="*.json;*.geo.json", options={"HIDDEN"})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        return bpy.ops.bedrock.import_variant_picker(
            "INVOKE_DEFAULT",
            filepath=self.filepath,
            resource_pack_root=self.resource_pack_root,
        )


def _menu_import(self, _context):
    self.layout.operator(
        BEDROCK_OT_open_variant_picker.bl_idname,
        text="Bedrock Model — Variants (.json)",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Register / Unregister
# ═══════════════════════════════════════════════════════════════════════════════

_CLASSES = [
    BedrockVariantProperties,
    BEDROCK_OT_import_variant_picker,
    BEDROCK_OT_open_variant_picker,
]


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)

    # Attach the property group to WindowManager so it persists for the
    # lifetime of the Blender session and is accessible from any context.
    WindowManager.bedrock_variants = bpy.props.PointerProperty(
        type=BedrockVariantProperties,
        name="Bedrock Variant Picker",
        description="Active Bedrock mob variant selectors",
    )

    bpy.types.TOPBAR_MT_file_import.append(_menu_import)


def unregister() -> None:
    bpy.types.TOPBAR_MT_file_import.remove(_menu_import)

    del WindowManager.bedrock_variants

    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
