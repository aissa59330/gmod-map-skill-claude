"""Habillage : remplace les textures dev/ par des textures de base de Gmod (contenu HL2 livré avec
le jeu : hl2_misc / hl2_textures / garrysmod — rien à télécharger pour les joueurs).

Le tracé garde ses matériaux « logiques » (MAT_* de geom.py) ; le thème est appliqué à l'export,
selon la zone de chaque brush et son rôle (sol / mur / plafond / bloc).
"""
from geom import (MAT_FLOOR, MAT_WALL, MAT_CEIL, MAT_ICE, MAT_ROCK, MAT_METAL, MAT_GRATE, MAT_CRATE,
                  MAT_HAZARD, MAT_DOOR, MAT_SWITCH, MAT_COMPUTER, MAT_RAIL)

# thème -> (sol, mur, plafond)
# Base de SENTINELLE : textures « Star Wars - Imperial Materials » (Lord Trilobite, Workshop 1206775008,
# élément requis). Extérieurs : contenu HL2 de base.
LT = "lordtrilobite/"
SURF = {
    "exterieur": ("nature/snowfloor001a", "nature/rockwall006a", "nature/rockwall006a"),
    "glacier": ("nature/snowfloor002a", "nature/snowwall001a", "nature/snowwall001a"),
    # base de la République (zones techniques) : panneaux gris clair, sol sombre
    "industriel": (LT + "ds_floor01_dirty", LT + "isd_metal02_dirty", LT + "isd_metal05_dirty"),
    "sentinelle": (LT + "isd_floor01", LT + "isd_metal03", LT + "isd_metal05"),
    "donnees": (LT + "ds_floor01", LT + "isd_metal03", LT + "isd_metal05"),
    "prison": (LT + "isd_floor01", LT + "isd_metal03", LT + "isd_metal05"),
    "glace": ("nature/snowfloor002a", "nature/snowwall002a", "nature/snowwall002a"),
}
# kit architectural : (lambris, moulure, nervure, poutre, cadre)
KIT = {
    "industriel": (LT + "isd_metal07_dirty", LT + "isd_metal04_dirty", LT + "isd_metal04_dirty", LT + "isd_metal06_dirty", LT + "isd_metal04_dirty"),
    "sentinelle": (LT + "isd_metal07", LT + "isd_metal04", LT + "isd_metal04", LT + "isd_metal06", LT + "isd_metal04"),
    "donnees": (LT + "isd_metal07", LT + "isd_metal04", LT + "isd_metal04", LT + "isd_metal06", LT + "isd_metal04"),
    "prison": (LT + "isd_metal07", LT + "isd_metal04", LT + "isd_metal06", LT + "isd_metal06", LT + "isd_metal04"),
    "glace": ("nature/snowwall001a", "nature/snowwall001a", "nature/snowwall001a", "nature/snowwall001a", LT + "isd_metal04"),
    "exterieur": (LT + "isd_metal07", LT + "isd_metal04", LT + "isd_metal04", LT + "isd_metal06", LT + "isd_metal04"),
    "glacier": (LT + "isd_metal07", LT + "isd_metal04", LT + "isd_metal04", LT + "isd_metal06", LT + "isd_metal04"),
}
KIT_INDEX = {"kit/dado": 0, "kit/trim": 1, "kit/rib": 2, "kit/beam": 3, "kit/frame": 4}
# plus de bande noir/jaune : matériau selon l'objet (déduit de la zone)
HAZARD_BY_ZONE = {"1": LT + "isd_exteriorshieldpanel", "11": LT + "isd_exteriorshieldpanel",
                  "2": LT + "isd_exteriorgreebles02", "4": LT + "isd_exteriorgreebles02",
                  "8": LT + "isd_exteriorgreebles", "9": LT + "isd_lights01", "4-5": LT + "isd_metal04"}
FACADE = "givre_noir/ext_facade"      # copie 1024 de isd_exteriorgreebles (tools/make_textures.py), échelle 0.5           # façade de la base vue depuis le hangar

ZONE_THEME = {
    "1": "exterieur", "2": "exterieur", "11": "glacier",
    "3a": "industriel", "3b": "industriel", "4": "industriel", "4-5": "industriel", "5": "industriel",
    "5-6": "sentinelle", "6": "donnees", "6-7": "sentinelle", "7": "prison", "7-8": "sentinelle",
    "8": "sentinelle", "8-9": "sentinelle", "9": "sentinelle", "10": "sentinelle",
    "ciel": "exterieur",
}

# matériaux indépendants du thème
FIXED = {
    MAT_GRATE: LT + "imp_metalgrate02",         # grille ajourée ($alphatest) : passerelles en func_detail
    MAT_COMPUTER: LT + "isd_control_panel03",
    MAT_HAZARD: "props/hazardstrip001a",
    MAT_DOOR: LT + "imp_door01_off",
    MAT_SWITCH: LT + "isd_control_panel01",
    MAT_RAIL: LT + "imp_metalgrate02",
    MAT_CRATE: LT + "imp_crate_white01",
    MAT_CEIL: LT + "isd_metal07",               # murets / couverts bas
    MAT_ROCK: "nature/rockwall006a",
}
BLOCK_METAL = {"industriel": LT + "isd_metal04_dirty", "sentinelle": LT + "isd_metal02", "donnees": LT + "isd_metal02",
               "prison": LT + "isd_metal02", "exterieur": LT + "isd_metal04_dirty", "glacier": LT + "isd_metal04_dirty",
               "glace": LT + "isd_metal04"}
WORLD_FLOOR_GRATE = LT + "imp_floorgrate01"    # grille opaque pour le world (pas de transparence)
LIGHT_PANEL = LT + "isd_lights03"


def theme_of(zone, mat):
    t = ZONE_THEME.get(zone, "industriel")
    if mat == MAT_ICE and t not in ("exterieur", "glacier"):
        return "glace"
    return t


def retheme(mat, zone, role, kind="detail", space=None):
    """role : floor | wall | wall_x0/x1/y0/y1 | ceil | block | top."""
    if mat.startswith("tools/"):
        return mat
    if mat == "lights/fluorescentcool001a":
        return LIGHT_PANEL
    if mat.startswith("kit/"):
        t = ZONE_THEME.get(zone, "industriel")
        return KIT.get(t, KIT["sentinelle"])[KIT_INDEX[mat]]
    if mat == MAT_HAZARD:
        return HAZARD_BY_ZONE.get(zone, LT + "isd_metal04")
    if space == "hangar" and role == "wall_x1":
        return FACADE
    if role.startswith("wall"):
        role = "wall"
    # placards (spawns défenseurs) d'une zone extérieure : intérieur de base, pas de roche
    if space and space.startswith("closet") and ZONE_THEME.get(zone, "") in ("exterieur", "glacier"):
        f, wl, c = SURF["sentinelle"]
        return f if role in ("floor", "top") else (c if role == "ceil" else wl)
    t = theme_of(zone, mat)
    floor, wall, ceil = SURF[t]
    if mat == MAT_ICE:
        return floor if role in ("floor", "top") else (wall if t != "exterieur" else "nature/snowwall001a")
    if role == "floor" or (role == "top" and mat in (MAT_FLOOR, MAT_METAL)):
        if mat == MAT_GRATE:
            return WORLD_FLOOR_GRATE if kind == "world" else FIXED[MAT_GRATE]
        return floor if mat in (MAT_FLOOR, MAT_WALL, MAT_CEIL, MAT_METAL, MAT_ROCK) else FIXED.get(mat, floor)
    if role == "ceil":
        return ceil
    if role == "wall":
        return wall if mat in (MAT_WALL, MAT_METAL, MAT_ROCK, MAT_CEIL) else FIXED.get(mat, wall)
    # blocs posés dans l'air
    if mat == MAT_GRATE and kind == "world":
        return WORLD_FLOOR_GRATE
    if mat == MAT_METAL:
        return BLOCK_METAL[t]
    if mat == MAT_FLOOR:
        return floor
    if mat == MAT_WALL:
        return wall
    return FIXED.get(mat, mat)
