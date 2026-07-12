"""
bedrock_variant_props.py
========================
WindowManager pointer property group for Bedrock mob variant selection.

Two operators
-------------
``bedrock.import_variant_picker``   — File browser → variant popup → import.
``bedrock.apply_variant``           — Polls selected armature → same popup
                                      → swaps materials/textures in place.

All enum *values* are uppercase (``"RED"``, ``"PLAINS"``, ``"FARMER"`` …).
Geometry/texture keys returned to the handler are lowercased automatically.

WindowManager pointer
---------------------
``wm.bedrock_variants``  (BedrockVariantProperties)
    .mob_identifier            "minecraft:fox"
    .available_geo_variants    JSON list of keys from the entity file
    .fox_type                  "RED" | "SNOW"
    .villager_profession       "FARMER" | "NONE" | …
    .villager_biome            "PLAINS" | "DESERT" | …
    .villager_level            1 – 5
    .is_baby                   bool
    … (all other mob-specific props)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
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


# ══════════════════════════════════════════════════════════════════════════════
# Shared enum item tables  (identifier = UPPERCASE)
# ══════════════════════════════════════════════════════════════════════════════

_DYE_COLORS = [
    ("WHITE",      "White",      "", 0),
    ("ORANGE",     "Orange",     "", 1),
    ("MAGENTA",    "Magenta",    "", 2),
    ("LIGHT_BLUE", "Light Blue", "", 3),
    ("YELLOW",     "Yellow",     "", 4),
    ("LIME",       "Lime",       "", 5),
    ("PINK",       "Pink",       "", 6),
    ("GRAY",       "Gray",       "", 7),
    ("LIGHT_GRAY", "Light Gray", "", 8),
    ("CYAN",       "Cyan",       "", 9),
    ("PURPLE",     "Purple",     "", 10),
    ("BLUE",       "Blue",       "", 11),
    ("BROWN",      "Brown",      "", 12),
    ("GREEN",      "Green",      "", 13),
    ("RED",        "Red",        "", 14),
    ("BLACK",      "Black",      "", 15),
]

_COLLAR_COLORS = _DYE_COLORS

_GENERIC_SIZE = [
    ("SMALL",  "Small",  "", 0),
    ("MEDIUM", "Medium", "", 1),
    ("LARGE",  "Large",  "", 2),
]


# ══════════════════════════════════════════════════════════════════════════════
# WindowManager PropertyGroup
# ══════════════════════════════════════════════════════════════════════════════

class BedrockVariantProperties(PropertyGroup):
    """
    All Bedrock mob variant selectors in one flat group.
    Registered on WindowManager — accessible as ``wm.bedrock_variants``.
    Enum identifiers are UPPERCASE; use ``.lower()`` when comparing to
    Bedrock entity file keys.
    """

    # ── Internal (set by operators) ────────────────────────────────────────────
    mob_identifier: StringProperty(
        name="Mob",
        description="Minecraft identifier of the active mob (auto-set)",
        default="",
    )
    available_geo_variants: StringProperty(
        name="Available Geometry Variants",
        description="JSON list of geometry keys in the entity file",
        default="[]",
    )

    # ── Universal ──────────────────────────────────────────────────────────────
    is_baby: BoolProperty(
        name="Is Baby",
        description="Use the baby / small variant geometry",
        default=False,
    )

    # ── Fox ───────────────────────────────────────────────────────────────────
    fox_type: EnumProperty(
        name="Fox Type",
        items=[
            ("RED",  "Red",  "Classic red fox",   0),
            ("SNOW", "Snow", "Arctic snow fox",   1),
        ],
        default="RED",
    )

    # ── Villager / Zombie Villager ─────────────────────────────────────────────
    villager_profession: EnumProperty(
        name="Profession",
        items=[
            ("NONE",          "None (Unemployed)", "", 0),
            ("ARMORER",       "Armorer",           "", 1),
            ("BUTCHER",       "Butcher",           "", 2),
            ("CARTOGRAPHER",  "Cartographer",      "", 3),
            ("CLERIC",        "Cleric",            "", 4),
            ("FARMER",        "Farmer",            "", 5),
            ("FISHERMAN",     "Fisherman",         "", 6),
            ("FLETCHER",      "Fletcher",          "", 7),
            ("LEATHERWORKER", "Leatherworker",     "", 8),
            ("LIBRARIAN",     "Librarian",         "", 9),
            ("MASON",         "Mason",             "", 10),
            ("NITWIT",        "Nitwit",            "", 11),
            ("SHEPHERD",      "Shepherd",          "", 12),
            ("TOOLSMITH",     "Toolsmith",         "", 13),
            ("WEAPONSMITH",   "Weaponsmith",       "", 14),
        ],
        default="NONE",
    )
    villager_biome: EnumProperty(
        name="Biome Style",
        items=[
            ("PLAINS",  "Plains",  "", 0),
            ("DESERT",  "Desert",  "", 1),
            ("JUNGLE",  "Jungle",  "", 2),
            ("SAVANNA", "Savanna", "", 3),
            ("SNOW",    "Snow",    "", 4),
            ("SWAMP",   "Swamp",   "", 5),
            ("TAIGA",   "Taiga",   "", 6),
        ],
        default="PLAINS",
    )
    villager_level: IntProperty(
        name="Trade Level",
        description="1 Novice · 2 Apprentice · 3 Journeyman · 4 Expert · 5 Master",
        min=1, max=5, default=1,
    )

    # ── Horse ─────────────────────────────────────────────────────────────────
    horse_variant: EnumProperty(
        name="Coat Color",
        items=[
            ("WHITE",      "White",      "", 0),
            ("CREAMY",     "Creamy",     "", 1),
            ("CHESTNUT",   "Chestnut",   "", 2),
            ("BROWN",      "Brown",      "", 3),
            ("BLACK",      "Black",      "", 4),
            ("GRAY",       "Gray",       "", 5),
            ("DARK_BROWN", "Dark Brown", "", 6),
        ],
        default="BROWN",
    )
    horse_markings: EnumProperty(
        name="Markings",
        items=[
            ("NONE",       "None",       "", 0),
            ("WHITE",      "White",      "", 1),
            ("WHITEFIELD", "Whitefield", "", 2),
            ("WHITE_DOTS", "White Dots", "", 3),
            ("BLACK_DOTS", "Black Dots", "", 4),
        ],
        default="NONE",
    )
    horse_armor: EnumProperty(
        name="Armor",
        items=[
            ("NONE",    "None",    "", 0),
            ("LEATHER", "Leather", "", 1),
            ("IRON",    "Iron",    "", 2),
            ("GOLD",    "Gold",    "", 3),
            ("DIAMOND", "Diamond", "", 4),
        ],
        default="NONE",
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
            ("CREAMY", "Creamy", "", 0),
            ("WHITE",  "White",  "", 1),
            ("BROWN",  "Brown",  "", 2),
            ("GRAY",   "Gray",   "", 3),
        ],
        default="CREAMY",
    )
    llama_decor_color: EnumProperty(
        name="Carpet / Decor",
        items=[("NONE", "None", "", 0)] + [(c[0], c[1], c[2], c[3] + 1) for c in _DYE_COLORS],
        default="NONE",
    )

    # ── Cat ───────────────────────────────────────────────────────────────────
    cat_type: EnumProperty(
        name="Cat Type",
        items=[
            ("TABBY",   "Tabby",         "", 0),
            ("TUXEDO",  "Tuxedo",        "", 1),
            ("RED",     "Red",           "", 2),
            ("SIAMESE", "Siamese",       "", 3),
            ("BRITISH", "British",       "", 4),
            ("CALICO",  "Calico",        "", 5),
            ("PERSIAN", "Persian",       "", 6),
            ("RAGDOLL", "Ragdoll",       "", 7),
            ("WHITE",   "White",         "", 8),
            ("JELLIE",  "Jellie",        "", 9),
            ("BLACK",   "Black",         "", 10),
        ],
        default="TABBY",
    )
    cat_collar_color: EnumProperty(
        name="Collar Color",
        items=_COLLAR_COLORS,
        default="RED",
    )

    # ── Wolf ──────────────────────────────────────────────────────────────────
    wolf_variant: EnumProperty(
        name="Wolf Variant",
        items=[
            ("PALE",     "Pale",     "Classic grey wolf",      0),
            ("SPOTTED",  "Spotted",  "Spotted jungle wolf",    1),
            ("SNOWY",    "Snowy",    "Snowy tundra wolf",      2),
            ("BLACK",    "Black",    "Black old-growth wolf",  3),
            ("ASHEN",    "Ashen",    "Ashen savanna wolf",     4),
            ("RUSTY",    "Rusty",    "Rusty badlands wolf",    5),
            ("STRIPED",  "Striped",  "Striped wolf",           6),
            ("WOODS",    "Woods",    "Woods wolf",             7),
            ("CHESTNUT", "Chestnut", "Chestnut wolf",          8),
        ],
        default="PALE",
    )
    wolf_collar_color: EnumProperty(
        name="Collar Color",
        items=_COLLAR_COLORS,
        default="RED",
    )
    wolf_angry: BoolProperty(
        name="Angry",
        description="Show the hostile/threatening pose",
        default=False,
    )

    # ── Rabbit ────────────────────────────────────────────────────────────────
    rabbit_type: EnumProperty(
        name="Rabbit Type",
        items=[
            ("BROWN",           "Brown",           "", 0),
            ("WHITE",           "White",           "", 1),
            ("BLACK",           "Black",           "", 2),
            ("WHITE_SPLOTCHED", "White Splotched", "", 3),
            ("GOLD",            "Gold",            "", 4),
            ("SALT",            "Salt & Pepper",   "", 5),
            ("EVIL",            "Killer Bunny",    "", 6),
        ],
        default="BROWN",
    )

    # ── Sheep ─────────────────────────────────────────────────────────────────
    sheep_color: EnumProperty(
        name="Wool Color",
        items=_DYE_COLORS,
        default="WHITE",
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
            ("RED",   "Red Mooshroom",   "", 0),
            ("BROWN", "Brown Mooshroom", "", 1),
        ],
        default="RED",
    )

    # ── Panda ─────────────────────────────────────────────────────────────────
    panda_main_gene: EnumProperty(
        name="Main Gene",
        items=[
            ("LAZY",       "Lazy",       "", 0),
            ("WORRIED",    "Worried",    "", 1),
            ("PLAYFUL",    "Playful",    "", 2),
            ("AGGRESSIVE", "Aggressive", "", 3),
            ("WEAK",       "Weak",       "", 4),
            ("BROWN",      "Brown",      "", 5),
            ("NORMAL",     "Normal",     "", 6),
        ],
        default="NORMAL",
    )
    panda_hidden_gene: EnumProperty(
        name="Hidden Gene",
        items=[
            ("LAZY",       "Lazy",       "", 0),
            ("WORRIED",    "Worried",    "", 1),
            ("PLAYFUL",    "Playful",    "", 2),
            ("AGGRESSIVE", "Aggressive", "", 3),
            ("WEAK",       "Weak",       "", 4),
            ("BROWN",      "Brown",      "", 5),
            ("NORMAL",     "Normal",     "", 6),
        ],
        default="NORMAL",
    )

    # ── Parrot ────────────────────────────────────────────────────────────────
    parrot_variant: EnumProperty(
        name="Parrot Color",
        items=[
            ("RED_BLUE",    "Red & Blue",    "", 0),
            ("BLUE",        "Blue",          "", 1),
            ("GREEN",       "Green",         "", 2),
            ("YELLOW_BLUE", "Yellow & Blue", "", 3),
            ("GRAY",        "Gray",          "", 4),
        ],
        default="RED_BLUE",
    )

    # ── Axolotl ───────────────────────────────────────────────────────────────
    axolotl_variant: EnumProperty(
        name="Axolotl Color",
        items=[
            ("LUCY", "Lucy (Pink)",  "", 0),
            ("WILD", "Wild (Brown)", "", 1),
            ("GOLD", "Gold",         "", 2),
            ("CYAN", "Cyan",         "", 3),
            ("BLUE", "Blue (Rare)",  "", 4),
        ],
        default="LUCY",
    )

    # ── Frog ──────────────────────────────────────────────────────────────────
    frog_variant: EnumProperty(
        name="Frog Type",
        items=[
            ("TEMPERATE", "Temperate (Orange)", "", 0),
            ("WARM",      "Warm (White)",       "", 1),
            ("COLD",      "Cold (Green)",       "", 2),
        ],
        default="TEMPERATE",
    )

    # ── Tropical Fish ─────────────────────────────────────────────────────────
    tropical_fish_pattern: EnumProperty(
        name="Body Pattern",
        items=[
            ("KOB",       "Kob",       "", 0),
            ("SUNSTREAK", "Sunstreak", "", 1),
            ("SNOOPER",   "Snooper",   "", 2),
            ("DASHER",    "Dasher",    "", 3),
            ("BRINELY",   "Brinely",   "", 4),
            ("SPOTTY",    "Spotty",    "", 5),
            ("FLOPPER",   "Flopper",   "", 6),
            ("STRIPEY",   "Stripey",   "", 7),
            ("GLITTER",   "Glitter",   "", 8),
            ("BLOCKFISH", "Blockfish", "", 9),
            ("BETTY",     "Betty",     "", 10),
            ("CLAYFISH",  "Clayfish",  "", 11),
        ],
        default="KOB",
    )
    tropical_fish_base_color: EnumProperty(
        name="Body Color",
        items=_DYE_COLORS,
        default="WHITE",
    )
    tropical_fish_pattern_color: EnumProperty(
        name="Pattern Color",
        items=_DYE_COLORS,
        default="RED",
    )

    # ── Slime / Magma Cube ────────────────────────────────────────────────────
    slime_size: EnumProperty(
        name="Size",
        items=_GENERIC_SIZE,
        default="LARGE",
    )

    # ── Creeper ───────────────────────────────────────────────────────────────
    creeper_powered: BoolProperty(
        name="Charged",
        description="Lightning-struck / electrified variant",
        default=False,
    )

    # ── Shulker ───────────────────────────────────────────────────────────────
    shulker_color: EnumProperty(
        name="Shulker Color",
        items=[("DEFAULT", "Default (Purple)", "", 0)]
              + [(c[0], c[1], c[2], c[3] + 1) for c in _DYE_COLORS],
        default="DEFAULT",
    )

    # ── Bee ───────────────────────────────────────────────────────────────────
    bee_has_nectar: BoolProperty(
        name="Carrying Nectar",
        description="Full abdomen / pollen-covered variant",
        default=False,
    )
    bee_angry: BoolProperty(
        name="Angry",
        description="Stinger-out aggressive pose",
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
        description="Import as Zombified Piglin",
        default=False,
    )

    # ── Hoglin ────────────────────────────────────────────────────────────────
    hoglin_is_zombified: BoolProperty(
        name="Zoglin (Zombified)",
        description="Import as Zoglin",
        default=False,
    )

    # ── Warden ────────────────────────────────────────────────────────────────
    warden_anger: EnumProperty(
        name="Anger Level",
        items=[
            ("CALM",     "Calm",     "Default idle pose",       0),
            ("AGITATED", "Agitated", "Partially emerged",       1),
            ("ANGRY",    "Angry",    "Full attack / alert pose", 2),
        ],
        default="CALM",
    )

    # ── Armadillo ─────────────────────────────────────────────────────────────
    armadillo_state: EnumProperty(
        name="State",
        items=[
            ("UNROLLED", "Unrolled", "Normal walking state", 0),
            ("ROLLED",   "Rolled",   "Defensive ball",       1),
        ],
        default="UNROLLED",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Mob variant registry
# ══════════════════════════════════════════════════════════════════════════════

_REGISTRY: dict[str, dict] = {

    "fox":          {"icon": "GHOST_ENABLED",   "groups": [("Fox",    ["fox_type"]),                                                   ("Age",  ["is_baby"])],              "geo_fn": "fox"},
    "axolotl":      {"icon": "COLORSET_01_VEC", "groups": [("Variant",["axolotl_variant"]),                                            ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "frog":         {"icon": "COLORSET_03_VEC", "groups": [("Variant",["frog_variant"])],                                                                                   "geo_fn": "default"},
    "rabbit":       {"icon": "COLORSET_04_VEC", "groups": [("Type",   ["rabbit_type"]),                                                ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "sheep":        {"icon": "COLORSET_02_VEC", "groups": [("Wool",   ["sheep_color"]),                                                ("State",["sheep_sheared"]),          ("Age",  ["is_baby"])],    "geo_fn": "sheep",  "note": "Sheared removes the wool mesh."},
    "mooshroom":    {"icon": "COLORSET_02_VEC", "groups": [("Variant",["mooshroom_variant"]),                                          ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "panda":        {"icon": "COLORSET_14_VEC", "groups": [("Genetics",["panda_main_gene","panda_hidden_gene"]),                       ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default", "note": "Gene combination determines appearance."},
    "parrot":       {"icon": "COLORSET_10_VEC", "groups": [("Color",  ["parrot_variant"])],                                                                                 "geo_fn": "default"},
    "cat":          {"icon": "COLORSET_12_VEC", "groups": [("Type",   ["cat_type"]),                                                   ("Collar",["cat_collar_color"])],    "geo_fn": "default"},
    "wolf":         {"icon": "COLORSET_14_VEC", "groups": [("Variant",["wolf_variant"]),                                               ("Collar",["wolf_collar_color"]),    ("State",["wolf_angry"]),   ("Age",["is_baby"])], "geo_fn": "wolf", "note": "Collar visible on tamed wolves only."},
    "bee":          {"icon": "COLORSET_05_VEC", "groups": [("State",  ["bee_has_nectar","bee_angry"])],                                                                     "geo_fn": "bee"},
    "goat":         {"icon": "COLORSET_02_VEC", "groups": [("Variant",["goat_is_screaming"]),                                          ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "horse":        {"icon": "COLORSET_12_VEC", "groups": [("Coat",   ["horse_variant"]),                                              ("Markings",["horse_markings"]),     ("Armor",["horse_armor"]),  ("Age",["is_baby"])], "geo_fn": "baby_or_default"},
    "donkey":       {"icon": "COLORSET_12_VEC", "groups": [("Equipment",["horse_has_chest"]),                                          ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "mule":         {"icon": "COLORSET_12_VEC", "groups": [("Equipment",["horse_has_chest"])],                                                                              "geo_fn": "default"},
    "llama":        {"icon": "COLORSET_12_VEC", "groups": [("Variant",["llama_variant"]),                                              ("Carpet",["llama_decor_color"]),    ("Age",  ["is_baby"])],    "geo_fn": "baby_or_default"},
    "trader_llama": {"icon": "COLORSET_12_VEC", "groups": [("Carpet", ["llama_decor_color"])],                                                                              "geo_fn": "default"},
    "villager":     {"icon": "COLORSET_07_VEC", "groups": [("Profession",["villager_profession"]),                                     ("Biome", ["villager_biome"]),       ("Trade Level",["villager_level"]), ("Age",["is_baby"])], "geo_fn": "baby_or_default", "note": "Biome = clothing style · Profession = hat/apron · Level = badge."},
    "zombie_villager": {"icon":"COLORSET_07_VEC","groups":[("Profession",["villager_profession"]),                                     ("Biome", ["villager_biome"]),       ("Age",  ["is_baby"])],    "geo_fn": "baby_or_default"},
    "creeper":      {"icon": "COLORSET_03_VEC", "groups": [("State",  ["creeper_powered"])],                                                                               "geo_fn": "default"},
    "shulker":      {"icon": "COLORSET_09_VEC", "groups": [("Color",  ["shulker_color"])],                                                                                 "geo_fn": "default"},
    "slime":        {"icon": "COLORSET_03_VEC", "groups": [("Size",   ["slime_size"])],                                                                                    "geo_fn": "slime"},
    "magma_cube":   {"icon": "COLORSET_01_VEC", "groups": [("Size",   ["slime_size"])],                                                                                    "geo_fn": "slime"},
    "tropicalfish": {"icon": "COLORSET_06_VEC", "groups": [("Body",   ["tropical_fish_base_color"]),                                   ("Pattern",["tropical_fish_pattern","tropical_fish_pattern_color"])], "geo_fn": "default"},
    "piglin":       {"icon": "COLORSET_08_VEC", "groups": [("Variant",["piglin_is_zombified"]),                                        ("Age",  ["is_baby"])],              "geo_fn": "piglin"},
    "hoglin":       {"icon": "COLORSET_08_VEC", "groups": [("Variant",["hoglin_is_zombified"]),                                        ("Age",  ["is_baby"])],              "geo_fn": "baby_or_default"},
    "zombie":       {"icon": "COLORSET_03_VEC", "groups": [("Age",    ["is_baby"])],                                                                                       "geo_fn": "baby_or_default"},
    "warden":       {"icon": "COLORSET_04_VEC", "groups": [("Anger Level",["warden_anger"])],                                                                              "geo_fn": "default",           "note": "Anger level affects the sonic shriek rig."},
    "armadillo":    {"icon": "COLORSET_13_VEC", "groups": [("State",  ["armadillo_state"])],                                                                               "geo_fn": "armadillo"},

    # ── Mobs with minimal or no configurable variants ─────────────────────────
    **{name: {"icon": icon, "groups": grps, "geo_fn": fn}
       for name, icon, grps, fn in [
        ("allay",          "COLORSET_06_VEC", [],                             "default"),
        ("bat",            "COLORSET_14_VEC", [],                             "default"),
        ("blaze",          "COLORSET_01_VEC", [],                             "default"),
        ("camel",          "COLORSET_12_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("chicken",        "COLORSET_02_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("cod",            "COLORSET_06_VEC", [],                             "default"),
        ("cow",            "COLORSET_02_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("dolphin",        "COLORSET_06_VEC", [],                             "default"),
        ("drowned",        "COLORSET_04_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("enderman",       "COLORSET_09_VEC", [],                             "default"),
        ("ghast",          "COLORSET_07_VEC", [],                             "default"),
        ("glow_squid",     "COLORSET_03_VEC", [],                             "default"),
        ("guardian",       "COLORSET_04_VEC", [],                             "default"),
        ("iron_golem",     "COLORSET_07_VEC", [],                             "default"),
        ("ocelot",         "COLORSET_12_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("phantom",        "COLORSET_09_VEC", [],                             "default"),
        ("pig",            "COLORSET_01_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("pillager",       "COLORSET_07_VEC", [],                             "default"),
        ("polar_bear",     "COLORSET_07_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("pufferfish",     "COLORSET_05_VEC", [],                             "default"),
        ("ravager",        "COLORSET_01_VEC", [],                             "default"),
        ("salmon",         "COLORSET_01_VEC", [],                             "default"),
        ("silverfish",     "COLORSET_14_VEC", [],                             "default"),
        ("skeleton",       "COLORSET_07_VEC", [],                             "default"),
        ("sniffer",        "COLORSET_13_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("snow_golem",     "COLORSET_07_VEC", [],                             "default"),
        ("spider",         "COLORSET_14_VEC", [],                             "default"),
        ("squid",          "COLORSET_06_VEC", [],                             "default"),
        ("strider",        "COLORSET_01_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("turtle",         "COLORSET_03_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("vindicator",     "COLORSET_07_VEC", [],                             "default"),
        ("witch",          "COLORSET_07_VEC", [],                             "default"),
        ("wither",         "COLORSET_09_VEC", [],                             "default"),
        ("wither_skeleton","COLORSET_14_VEC", [],                             "default"),
        ("zoglin",         "COLORSET_08_VEC", [("Age",["is_baby"])],          "baby_or_default"),
        ("zombie_horse",   "COLORSET_03_VEC", [("Age",["is_baby"])],          "baby_or_default"),
    ]},
}


# ══════════════════════════════════════════════════════════════════════════════
# Geometry variant resolution     (returns lowercase entity-file keys)
# ══════════════════════════════════════════════════════════════════════════════

def resolve_geo_variant(mob_id: str, props: BedrockVariantProperties) -> str:
    """
    Map the current variant properties to a geometry dict key suitable for
    passing to ``BedrockModelBlenderHandler.import_from_entity()``.

    Enum values are uppercase inside the PropertyGroup; this function always
    returns lowercase strings that match Bedrock entity file conventions.
    """
    name = mob_id.split(":")[-1]
    fn   = _REGISTRY.get(name, {}).get("geo_fn", "default")

    if fn == "default":
        return "default"

    if fn == "baby_or_default":
        return "baby" if props.is_baby else "default"

    if fn == "fox":
        if props.is_baby:
            return "baby"
        return "snow" if props.fox_type == "SNOW" else "default"

    if fn == "sheep":
        if props.sheep_sheared:
            return "sheared"
        return "baby" if props.is_baby else "default"

    if fn == "wolf":
        if props.wolf_angry:
            return "angry"
        return "baby" if props.is_baby else "default"

    if fn == "bee":
        if props.bee_angry and props.bee_has_nectar:
            return "angry_nectar"
        if props.bee_angry:
            return "angry"
        if props.bee_has_nectar:
            return "nectar"
        return "default"

    if fn == "slime":
        return props.slime_size.lower()       # "SMALL" → "small"

    if fn == "piglin":
        if props.piglin_is_zombified:
            return "zombified"
        return "baby" if props.is_baby else "default"

    if fn == "armadillo":
        return "rolled" if props.armadillo_state == "ROLLED" else "default"

    return "default"


def collect_variant_metadata(
    mob_id: str, props: BedrockVariantProperties
) -> dict[str, str]:
    """
    Build a flat ``{mc_variant_<attr>: value}`` dict of the current selections
    for *mob_id*.  Written as custom properties on the armature after import.
    """
    name  = mob_id.split(":")[-1]
    entry = _REGISTRY.get(name, {})
    flat: list[str] = []
    for _, grp_props in entry.get("groups", []):
        flat.extend(grp_props)

    return {
        f"mc_variant_{p}": str(getattr(props, p))
        for p in flat
        if hasattr(props, p)
    }


def restore_variant_from_armature(
    arm_obj: bpy.types.Object, props: BedrockVariantProperties
) -> None:
    """
    Read ``mc_variant_*`` custom properties from *arm_obj* back into *props*
    so the popup opens pre-filled with the armature's last-used settings.
    """
    for key, raw in arm_obj.items():
        if not key.startswith("mc_variant_"):
            continue
        attr = key[len("mc_variant_"):]
        if not hasattr(props, attr):
            continue
        val = str(raw)
        try:
            # Bool stored as "True" / "False"
            if val == "True":
                setattr(props, attr, True)
            elif val == "False":
                setattr(props, attr, False)
            else:
                setattr(props, attr, val)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Texture variant resolution
# ══════════════════════════════════════════════════════════════════════════════

def _find_tex_key(mc_textures: dict[str, str], *candidates: str) -> Optional[str]:
    """
    Return the first candidate key that exists in *mc_textures*, or the last
    candidate as a fallback even if absent (caller handles missing).
    """
    for c in candidates:
        if c in mc_textures:
            return c
    # Fuzzy: key or path *contains* any candidate as a substring
    for c in candidates:
        c_low = c.lower()
        for k, v in mc_textures.items():
            if c_low in k.lower() or c_low in v.lower():
                return k
    return candidates[-1] if candidates else "default"


def resolve_texture_targets(
    mob_id: str,
    props: BedrockVariantProperties,
    mc_textures: dict[str, str],
) -> list[dict]:
    """
    Return a list of texture targets for the current variant selection.

    Each entry is a dict::

        {
          "hint":  str,   # substring hint for matching material nodes
          "key":   str,   # key to look up in mc_textures
          "label": str,   # human-readable description for operator reports
        }

    The ``hint`` is used by ``_apply_image_to_meshes`` to decide which
    Image Texture nodes to update (empty string → update all nodes).

    Villager (multi-layer example)
    ------------------------------
    Returns up to three targets: **body** (biome-based), **profession**
    (overlay), and optionally a **level badge** texture if present in the
    entity's texture dict.

    All comparisons use ``.lower()`` to handle uppercase enum values.
    """
    name  = mob_id.split(":")[-1]
    p     = props

    # ── Villager / Zombie Villager ─────────────────────────────────────────────
    if name in ("villager", "zombie_villager"):
        biome  = p.villager_biome.lower()           # "plains", "desert" …
        prof   = p.villager_profession.lower()      # "farmer", "none" …
        level  = p.villager_level                   # 1 – 5

        body_key = _find_tex_key(
            mc_textures,
            f"body_{biome}", f"base_{biome}", biome,
            f"villager_{biome}", "base", "default",
        )
        targets = [{"hint": "body",       "key": body_key,
                    "label": f"Body ({biome})"}]

        if prof not in ("none", "nitwit"):
            prof_key = _find_tex_key(
                mc_textures,
                f"profession_{prof}", prof,
                f"{prof}_{biome}", f"villager_{prof}", "default",
            )
            targets.append({"hint": "profession", "key": prof_key,
                             "label": f"Profession ({prof})"})

        level_key = _find_tex_key(
            mc_textures,
            f"level_{level}", f"badge_{level}",
            f"trade_level_{level}", f"merchant_{level}",
        )
        if level_key and level_key in mc_textures:
            targets.append({"hint": "level", "key": level_key,
                             "label": f"Level badge ({level})"})

        return targets

    # ── Horse (coat + markings overlay) ───────────────────────────────────────
    if name == "horse":
        coat  = p.horse_variant.lower()
        marks = p.horse_markings.lower()
        coat_key   = _find_tex_key(mc_textures, coat, f"horse_{coat}", "default")
        marks_key  = _find_tex_key(mc_textures, marks, f"markings_{marks}", f"horse_markings_{marks}")
        targets = [{"hint": "body",     "key": coat_key,  "label": f"Coat ({coat})"}]
        if marks != "none" and marks_key in mc_textures:
            targets.append({"hint": "markings", "key": marks_key, "label": f"Markings ({marks})"})
        return targets

    # ── Simple single-texture mobs ─────────────────────────────────────────────
    _single: dict[str, str] = {
        "fox":       (lambda: f"baby_{p.fox_type.lower()}" if p.is_baby else p.fox_type.lower())(),
        "axolotl":   p.axolotl_variant.lower(),
        "frog":      p.frog_variant.lower(),
        "rabbit":    p.rabbit_type.lower(),
        "parrot":    p.parrot_variant.lower(),
        "cat":       p.cat_type.lower(),
        "wolf":      p.wolf_variant.lower(),
        "sheep":     (f"sheared_{p.sheep_color.lower()}"
                      if p.sheep_sheared else p.sheep_color.lower()),
        "mooshroom": p.mooshroom_variant.lower(),
        "llama":     p.llama_variant.lower(),
        "shulker":   ("default" if p.shulker_color == "DEFAULT"
                      else p.shulker_color.lower()),
        "tropicalfish": f"{p.tropical_fish_base_color.lower()}_{p.tropical_fish_pattern.lower()}",
    }

    if name in _single:
        hint_val = _single[name]
        key = _find_tex_key(mc_textures, hint_val, hint_val.split("_")[0], "default")
        return [{"hint": "", "key": key, "label": f"Texture ({hint_val})"}]

    # ── Generic fallback ───────────────────────────────────────────────────────
    return [{"hint": "", "key": "default", "label": "Default texture"}]


# ══════════════════════════════════════════════════════════════════════════════
# Texture application helpers
# ══════════════════════════════════════════════════════════════════════════════

def _collect_tex_nodes(
    arm_obj: bpy.types.Object,
) -> list[tuple[bpy.types.Material, bpy.types.Node, bpy.types.Object]]:
    """
    Return all (material, TEX_IMAGE node, mesh_object) triples found on every
    MESH child (recursive) of *arm_obj*.
    """
    results = []
    for ob in arm_obj.children_recursive:
        if ob.type != 'MESH':
            continue
        for slot in ob.material_slots:
            mat = slot.material
            if mat is None or not mat.use_nodes or mat.node_tree is None:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    results.append((mat, node, ob))
    return results


def _set_image_on_nodes(
    nodes: list[tuple],
    image: bpy.types.Image,
    hint: str,
) -> int:
    """
    Assign *image* to every node in *nodes* whose material or current image
    path contains *hint* (case-insensitive).  An empty *hint* updates all nodes.
    Returns the count of nodes updated.
    """
    count = 0
    for mat, node, _ob in nodes:
        if hint:
            current_path = (node.image.filepath if node.image else "").lower()
            mat_name     = mat.name.lower()
            hint_low     = hint.lower()
            if hint_low not in current_path and hint_low not in mat_name:
                continue
        node.image = image
        count += 1
    return count


def apply_variant_textures(
    arm_obj: bpy.types.Object,
    props: BedrockVariantProperties,
    resource_pack_root: str = "",
) -> list[str]:
    """
    Swap Image Texture nodes on all mesh children of *arm_obj* to match the
    variant settings in *props*.

    Returns a list of human-readable status strings (for operator reports).

    Texture path resolution
    -----------------------
    1. ``mc_textures`` custom prop (JSON dict from entity file) → texture path
       relative to the pack root (e.g. ``"textures/entity/fox/fox_red"``).
    2. Prepend *resource_pack_root* (or ``arm_obj["mc_resource_pack_root"]``) and
       append ``.png`` to get the absolute file path.
    3. Load / reuse via ``bpy.data.images.load(check_existing=True)``.
    4. Assign to matching Image Texture nodes.
    """
    mob_id = arm_obj.get("mc_identifier", "")
    if not mob_id:
        return ["No mc_identifier on armature — was it imported via the variant picker?"]

    try:
        mc_textures: dict[str, str] = json.loads(arm_obj.get("mc_textures", "{}"))
    except Exception:
        mc_textures = {}

    rpr = resource_pack_root or arm_obj.get("mc_resource_pack_root", "")

    targets  = resolve_texture_targets(mob_id, props, mc_textures)
    all_nodes = _collect_tex_nodes(arm_obj)
    messages: list[str] = []

    for target in targets:
        hint     = target["hint"]
        tex_key  = target["key"]
        label    = target["label"]
        rel_path = mc_textures.get(tex_key, "")

        if not rel_path:
            messages.append(f"⚠  {label}: key '{tex_key}' not in mc_textures")
            continue

        # Build absolute path
        full_path = ""
        if rpr:
            candidate = Path(rpr) / f"{rel_path}.png"
            if candidate.is_file():
                full_path = str(candidate)
            else:
                # Try without extension
                candidate2 = Path(rpr) / rel_path
                if candidate2.is_file():
                    full_path = str(candidate2)

        if not full_path:
            messages.append(
                f"⚠  {label}: file not found "
                f"(key={tex_key!r}, path={rel_path!r}, pack={rpr!r})"
            )
            continue

        try:
            img = bpy.data.images.load(full_path, check_existing=True)
            img.colorspace_settings.name = "sRGB"
        except Exception as exc:
            messages.append(f"✗  {label}: image load failed — {exc}")
            continue

        n = _set_image_on_nodes(all_nodes, img, hint)
        messages.append(f"✓  {label}: applied '{img.name}' to {n} node(s)")

    return messages or ["No texture targets resolved for this mob"]


# ══════════════════════════════════════════════════════════════════════════════
# Shared popup draw
# ══════════════════════════════════════════════════════════════════════════════

def draw_variant_popup(layout: bpy.types.UILayout, props: BedrockVariantProperties) -> None:
    """Draw the variant properties relevant to ``props.mob_identifier``."""
    mob_id = props.mob_identifier
    name   = mob_id.split(":")[-1] if ":" in mob_id else mob_id
    entry  = _REGISTRY.get(name)

    # ── Header ─────────────────────────────────────────────────────────────────
    hdr = layout.box()
    row = hdr.row(align=True)
    row.label(text=mob_id or "Unknown mob", icon=entry["icon"] if entry else "QUESTION")

    try:
        avail = json.loads(props.available_geo_variants)
    except Exception:
        avail = []
    if avail:
        hdr.label(text="Variants in file: " + ", ".join(avail), icon="INFO")

    layout.separator(factor=0.4)

    if entry is None:
        layout.label(text="No registry entry — showing universal props.", icon="ERROR")
        layout.prop(props, "is_baby")
        return

    groups = entry.get("groups", [])
    if not groups:
        layout.label(text="No configurable variants for this mob.", icon="CHECKMARK")
        return

    for group_label, prop_names in groups:
        box = layout.box()
        col = box.column(align=True)
        if group_label:
            col.label(text=group_label, icon="PROPERTIES")
        for pname in prop_names:
            col.prop(props, pname)

    note = entry.get("note", "")
    if note:
        layout.separator(factor=0.3)
        nb = layout.box()
        nb.scale_y = 0.75
        nb.label(text=note, icon="NONE")


# ══════════════════════════════════════════════════════════════════════════════
# Operator 1 — Import with variant picker  (file → popup → import)
# ══════════════════════════════════════════════════════════════════════════════

class BEDROCK_OT_import_variant_picker(Operator):
    """
    Open a file browser, detect the mob type, show a variant popup, then import.
    Returns ``RUNNING_MODAL`` while the dialog is open (Blender handles the loop).
    """

    bl_idname  = "bedrock.import_variant_picker"
    bl_label   = "Bedrock — Choose Variant & Import"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(
        name="File Path", subtype="FILE_PATH",
        options={"HIDDEN", "SKIP_SAVE"},
    )
    resource_pack_root: StringProperty(
        name="Resource Pack Root",
        description="Folder containing entity/, models/, textures/ …",
        subtype="DIR_PATH",
        options={"HIDDEN", "SKIP_SAVE"},
        default="",
    )
    import_locators: BoolProperty(name="Import Locators",      default=True,  options={"HIDDEN","SKIP_SAVE"})
    apply_rest_rotations: BoolProperty(name="Apply Rest Rotations", default=True, options={"HIDDEN","SKIP_SAVE"})
    filter_glob: StringProperty(default="*.json;*.geo.json", options={"HIDDEN"})

    # ── Modal dialog ───────────────────────────────────────────────────────────

    def invoke(self, context: bpy.types.Context, _event) -> set:
        wm    = context.window_manager
        props = wm.bedrock_variants

        ok, mob_id, avail = self._parse_file()
        if not ok:
            self.report({"ERROR"}, f"Cannot detect mob type from: {self.filepath}")
            return {"CANCELLED"}

        props.mob_identifier        = mob_id
        props.available_geo_variants = json.dumps(avail)
        props.is_baby               = False   # reset each invocation

        return context.window_manager.invoke_props_dialog(
            self, width=340, confirm_text="Import",
        )

    def modal(self, context: bpy.types.Context, event) -> set:
        # invoke_props_dialog drives the modal loop and calls execute() on OK.
        # Pass all events through so Blender can handle OK / Cancel / Escape.
        return {"PASS_THROUGH"}

    def draw(self, context: bpy.types.Context) -> None:
        draw_variant_popup(self.layout, context.window_manager.bedrock_variants)

    def execute(self, context: bpy.types.Context) -> set:
        wm    = context.window_manager
        props = wm.bedrock_variants
        mob_id     = props.mob_identifier
        geo_variant = resolve_geo_variant(mob_id, props)

        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception as exc:
            self.report({"ERROR"}, f"Cannot read file: {exc}")
            return {"CANCELLED"}

        fmt     = detect_mc_format(raw)
        handler = BedrockModelBlenderHandler(
            context=context,
            resource_pack_root=self.resource_pack_root or None,
        )
        arm_obj: Optional[bpy.types.Object] = None
        fp = Path(self.filepath)

        if fmt == MC_FORMAT_BEDROCK_ENTITY:
            entity  = BedrockEntityFile.from_dict(raw)
            arm_obj = handler.import_from_entity(
                entity,
                geo_variant=geo_variant,
                extra_search_dirs=[str(fp.parent), str(fp.parent.parent)],
                import_locators=self.import_locators,
                apply_rest_rotation=self.apply_rest_rotations,
            )
        elif fmt == MC_FORMAT_BEDROCK_GEO:
            model   = BedrockModelFile.from_dict(raw)
            arm_obj = handler.import_geometry(
                model,
                import_locators=self.import_locators,
                apply_rest_rotation=self.apply_rest_rotations,
            )
        else:
            self.report({"ERROR"}, "File is not a Bedrock geometry or entity JSON")
            return {"CANCELLED"}

        if arm_obj is None:
            self.report({"ERROR"}, "Import produced no objects")
            return {"CANCELLED"}

        # ── Store variant metadata + pack root on armature ─────────────────────
        arm_obj["mc_selected_variant"] = geo_variant
        arm_obj["mc_selected_mob"]     = mob_id
        if self.resource_pack_root:
            arm_obj["mc_resource_pack_root"] = self.resource_pack_root
        for k, v in collect_variant_metadata(mob_id, props).items():
            arm_obj[k] = v

        for ob in context.selected_objects:
            ob.select_set(False)
        arm_obj.select_set(True)
        context.view_layer.objects.active = arm_obj

        self.report({"INFO"},
                    f"Imported '{arm_obj.name}' · {mob_id} · variant='{geo_variant}'")
        return {"FINISHED"}

    # ── Parse helper ───────────────────────────────────────────────────────────

    def _parse_file(self) -> tuple[bool, str, list[str]]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except Exception:
            return False, "", []

        fmt = detect_mc_format(raw)
        if fmt == MC_FORMAT_BEDROCK_ENTITY:
            ef   = BedrockEntityFile.from_dict(raw)
            return True, ef.description.identifier, list(ef.description.geometry.keys())
        if fmt == MC_FORMAT_BEDROCK_GEO:
            gf = BedrockModelFile.from_dict(raw)
            if gf.geometries:
                return True, gf.geometries[0].description.identifier, ["default"]
        return False, "", []


# ══════════════════════════════════════════════════════════════════════════════
# Operator 2 — Apply variant textures  (polls selected armature)
# ══════════════════════════════════════════════════════════════════════════════

class BEDROCK_OT_apply_variant(Operator):
    """
    Read ``mc_identifier`` from the active armature, open the same variant
    popup pre-filled with its last-used settings, then swap material textures
    to match the chosen variant.

    Poll condition: active object must be an armature with ``mc_identifier``.
    """

    bl_idname  = "bedrock.apply_variant"
    bl_label   = "Bedrock — Apply Variant Textures"
    bl_options = {"REGISTER", "UNDO"}

    resource_pack_root: StringProperty(
        name="Resource Pack Root",
        description=(
            "Override the resource pack used for texture lookup.  "
            "Leave blank to use the value stored on the armature."
        ),
        subtype="DIR_PATH",
        default="",
    )

    # ── Poll ───────────────────────────────────────────────────────────────────

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        ob = context.active_object
        return (
            ob is not None
            and ob.type == "ARMATURE"
            and bool(ob.get("mc_identifier", ""))
        )

    # ── Modal dialog ───────────────────────────────────────────────────────────

    def invoke(self, context: bpy.types.Context, _event) -> set:
        arm   = context.active_object
        wm    = context.window_manager
        props = wm.bedrock_variants

        mob_id = arm.get("mc_identifier", "")
        name   = mob_id.split(":")[-1]

        # Pre-fill from armature's saved mc_variant_* custom properties
        props.mob_identifier = mob_id
        restore_variant_from_armature(arm, props)

        # Populate available variant keys from mc_geometry custom prop
        try:
            geo_dict = json.loads(arm.get("mc_geometry", "{}"))
            avail    = list(geo_dict.keys())
        except Exception:
            avail = ["default"]
        props.available_geo_variants = json.dumps(avail)

        # Pre-fill resource pack root from armature if operator field is blank
        if not self.resource_pack_root:
            self.resource_pack_root = arm.get("mc_resource_pack_root", "")

        return context.window_manager.invoke_props_dialog(
            self, width=340, confirm_text="Apply Textures",
        )

    def modal(self, context: bpy.types.Context, event) -> set:
        return {"PASS_THROUGH"}

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        draw_variant_popup(layout, context.window_manager.bedrock_variants)

        # Resource pack override field at the bottom of the dialog
        layout.separator(factor=0.5)
        box = layout.box()
        box.label(text="Texture Pack Override", icon="TEXTURE")
        box.prop(self, "resource_pack_root", text="Pack Root")

    def execute(self, context: bpy.types.Context) -> set:
        arm   = context.active_object
        wm    = context.window_manager
        props = wm.bedrock_variants
        mob_id = arm.get("mc_identifier", "")

        rpr = self.resource_pack_root or arm.get("mc_resource_pack_root", "")

        msgs = apply_variant_textures(arm, props, rpr)

        # Persist updated variant selection back to armature
        arm["mc_selected_variant"] = resolve_geo_variant(mob_id, props)
        for k, v in collect_variant_metadata(mob_id, props).items():
            arm[k] = v
        if rpr:
            arm["mc_resource_pack_root"] = rpr

        level = "INFO"
        for msg in msgs:
            self.report({"INFO"}, msg)
            if msg.startswith("⚠") or msg.startswith("✗"):
                level = "WARNING"

        self.report({level}, f"Variant textures applied to '{arm.name}'")
        return {"FINISHED"}


# ══════════════════════════════════════════════════════════════════════════════
# Operator 3 — File browser entry point (wraps import picker)
# ══════════════════════════════════════════════════════════════════════════════

class BEDROCK_OT_open_variant_picker(Operator):
    """Open a file browser then launch the variant import picker."""

    bl_idname  = "bedrock.open_variant_picker"
    bl_label   = "Bedrock Model — Import with Variants"
    bl_options = {"REGISTER", "UNDO"}

    filepath:           StringProperty(subtype="FILE_PATH",  options={"SKIP_SAVE"})
    resource_pack_root: StringProperty(subtype="DIR_PATH",   options={"SKIP_SAVE"}, default="")
    filter_glob:        StringProperty(default="*.json;*.geo.json", options={"HIDDEN"})

    def invoke(self, context, _event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        return bpy.ops.bedrock.import_variant_picker(
            "INVOKE_DEFAULT",
            filepath=self.filepath,
            resource_pack_root=self.resource_pack_root,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Menu entry
# ══════════════════════════════════════════════════════════════════════════════

def _menu_import(self, _context):
    self.layout.operator(
        BEDROCK_OT_open_variant_picker.bl_idname,
        text="Bedrock Model — Variants (.json)",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Register / Unregister
# ══════════════════════════════════════════════════════════════════════════════

_CLASSES = [
    BedrockVariantProperties,
    BEDROCK_OT_import_variant_picker,
    BEDROCK_OT_apply_variant,
    BEDROCK_OT_open_variant_picker,
]


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)

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