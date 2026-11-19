"""Ambiance « base occupée par les Séparatistes » : props le long des murs + traces de combat.

Packs utilisés (éléments requis / collection du serveur) :
- Star Wars - Misc Prop Pack (Lord Trilobite, 1987994709) : consoles, panneaux, tuyaux, cuves de bacta, chaises
- Star Wars Rogue One Prop Pack (Lord Trilobite, 946190478) : alarmes, caisses kyber, réservoirs
- SW Modelpack Miscellaneous (KingPommes, 1841418570) : caisses impériales, consoles de pont
- SW Modelpack Death Star (KingPommes, 1518614446) : panneaux muraux, écrans, cellules d'énergie, lampes

Chaque prop est posé contre un mur, tourné vers la salle, et refusé s'il touche une ouverture, un bloc,
un autre prop, un spawn ou s'il passe à moins de 96 u du tracé de marche.
"""
import json
import math
import os
import random

import props as P
import walk
from geom import Block

HERE = os.path.dirname(os.path.abspath(__file__))
PB = json.load(open(os.path.join(HERE, "prop_bounds_packs.json"), encoding="utf-8"))

LT = "models/lordtrilobite/starwars/"
KP = "models/kingpommes/starwars/"

# modèle -> axe local de la face avant (vérifié sur planche Blender : tools/prop_faces.py)
FRONT = {
    LT + "isd/imp_console_large01.mdl": "+x", LT + "isd/imp_console_medium01.mdl": "+x", LT + "isd/imp_console_medium02.mdl": "+x",
    LT + "isd/imp_console_medium03.mdl": "+x", LT + "isd/imp_console_small01.mdl": "+x",
    LT + "isd/imp_greeblewall01.mdl": "+x", LT + "isd/imp_greeblewall02.mdl": "+x", LT + "isd/imp_greeblewall03.mdl": "+x",
    LT + "isd/imp_greeblewall04.mdl": "+x", LT + "isd/imp_greeblepanel02.mdl": "+x",
    LT + "isd/imp_wallpipes01.mdl": "+x", LT + "isd/imp_wallpipes02.mdl": "+x", LT + "isd/isd_bridgepanel01.mdl": "+x",
    LT + "isd/imp_light_alarm01.mdl": "-x",
    KP + "deathstar/wallpanel01.mdl": "-x", KP + "deathstar/wallpanel04.mdl": "-x", KP + "deathstar/wallpanel10.mdl": "-x",
    KP + "deathstar/wallpanel15a.mdl": "+x", KP + "deathstar/wallpanel16a.mdl": "+x",
    KP + "deathstar/viewscreen03.mdl": "-x", KP + "deathstar/viewscreen04.mdl": "-x", KP + "deathstar/viewscreen03b.mdl": "-x",
    KP + "misc/bridge_console_wall_2.mdl": "-x", KP + "misc/bridge_console1.mdl": "-x",
    KP + "deathstar/laserconsole02.mdl": "+y", KP + "deathstar/laserconsole01.mdl": "+y",
}
# hauteur de pose des éléments muraux (au-dessus du sol), sinon posés au sol sur leur vrai pied
MOUNT = {LT + "isd/imp_wallpipes02.mdl": 128, LT + "isd/imp_wallpipes01.mdl": 128, LT + "isd/imp_light_alarm01.mdl": 140}
WALL_OFFSET = 10      # devant le lambris (6) + moulure (4)
# objets posés (pas de face) : caisses, réservoirs, cellules d'énergie, cuves
FREE = [LT + "props/kyber_crate_static.mdl", LT + "props/fueltank_scarif1_static.mdl",
        KP + "misc/imp_crate_double_closed.mdl", KP + "misc/imp_crate_single_closed.mdl", KP + "deathstar/powercell1b.mdl",
        KP + "deathstar/powercell2b.mdl", LT + "props/bactatankb.mdl", LT + "props/imp_chair01.mdl",
        LT + "props/table_cantina01.mdl", KP + "deathstar/floorlight.mdl", KP + "deathstar/ceilinglight.mdl"]

# catalogue par zone : (modèles muraux, objets posés, pas entre deux props)
CATALOG = {
    "industriel": ([KP + "deathstar/wallpanel15a.mdl", KP + "deathstar/wallpanel16a.mdl",
                    LT + "isd/imp_greeblewall03.mdl", LT + "isd/imp_console_medium02.mdl"],
                   [KP + "misc/imp_crate_double_closed.mdl", LT + "props/fueltank_scarif1_static.mdl",
                    KP + "deathstar/powercell1b.mdl", LT + "props/kyber_crate_static.mdl"], 320),
    "sentinelle": ([LT + "isd/imp_console_large01.mdl", LT + "isd/imp_console_medium01.mdl", KP + "deathstar/viewscreen04.mdl",
                    KP + "deathstar/wallpanel01.mdl", KP + "deathstar/wallpanel04.mdl", LT + "isd/isd_bridgepanel01.mdl",
                    KP + "misc/bridge_console_wall_2.mdl", LT + "isd/imp_greeblewall01.mdl"],
                   [KP + "deathstar/powercell2b.mdl", KP + "misc/imp_crate_single_closed.mdl"], 288),
    "prison": ([KP + "deathstar/wallpanel10.mdl", LT + "isd/imp_greeblewall02.mdl", LT + "isd/imp_console_small01.mdl"],
               [KP + "misc/imp_crate_single_closed.mdl"], 352),
    "glace": ([LT + "isd/imp_greeblewall01.mdl"], [KP + "misc/imp_crate_single_closed.mdl"], 512),
}
CORRIDOR_MAX_DEPTH = 12          # dans un couloir étroit, seulement des éléments plats


def box_of(model, pos, yaw):
    if model in P.BOUNDS:
        a, b = P.BOUNDS[model]
    else:
        e = PB[model]
        a, b = e["min"], e["max"]
    P.BOUNDS[model] = (tuple(a), tuple(b))
    return P.world_box(model, pos, yaw)


def overlap(a, b, m=0):
    return (a[0] - m < b[3] and b[0] - m < a[3] and a[1] - m < b[4] and b[1] - m < a[4]
            and a[2] < b[5] and b[2] < a[5])


def seg_dist2d(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def build(w):
    M = w.meta
    import theme
    rnd = random.Random(408)
    placed = [P.world_box(m, p, y) for (m, p, y) in M["props"]]
    blocks = [b.box if isinstance(b, Block) else b.bbox for b in w.blocks
              if not (isinstance(b, Block) and b.mat in ("kit/dado", "kit/trim", "kit/beam", "tools/toolsclip"))]
    for e in w.ents:
        if e["classname"] in ("func_door", "func_button", "func_breakable", "func_movelinear"):
            blocks += [s.box if isinstance(s, Block) else s.bbox for s in e["solids"]]
    spawns = [(p[0] - 24, p[1] - 24, p[2], p[0] + 24, p[1] + 24, p[2] + 80)
              for grp in list(M["def_spawns"].values()) + list(M["atk_respawns"].values()) for p in grp]
    spawns += [(p[0] - 24, p[1] - 24, p[2], p[0] + 24, p[1] + 24, p[2] + 80) for p in M["player_starts"]]
    routes = [walk.MAIN, walk.CONDUITS]
    segs = [(r[i], r[i + 1]) for r in routes for i in range(len(r) - 1)]

    def near_route(bx):
        cx, cy = (bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2
        rad = max(bx[3] - bx[0], bx[4] - bx[1]) / 2
        for (a, b) in segs:
            if not (min(a[3], b[3]) - 80 < bx[5] and bx[2] < max(a[3], b[3]) + 120):
                continue
            if seg_dist2d(cx, cy, a[1], a[2], b[1], b[2]) < 96 + rad:
                return True
        return False

    def blocks_opening(bx, room):
        """Le prop est-il devant une ouverture (porte, couloir, cellule) d'un mur de la salle ?"""
        x0, y0, z0, x1, y1, z1 = room
        for o in w.spaces:
            b = o.box
            if b == room or b[5] <= bx[2] or b[2] >= bx[5]:
                continue
            m = 64
            if b[3] >= x0 and b[0] < x0 and bx[0] < x0 + 160:           # mur x0
                if b[1] - m < bx[4] and bx[1] < b[4] + m:
                    return True
            if b[0] <= x1 and b[3] > x1 and bx[3] > x1 - 160:           # mur x1
                if b[1] - m < bx[4] and bx[1] < b[4] + m:
                    return True
            if b[4] >= y0 and b[1] < y0 and bx[1] < y0 + 160:           # mur y0
                if b[0] - m < bx[3] and bx[0] < b[3] + m:
                    return True
            if b[1] <= y1 and b[4] > y1 and bx[4] > y1 - 160:           # mur y1
                if b[0] - m < bx[3] and bx[0] < b[3] + m:
                    return True
        return False

    def supported(bx, zf, room):
        """Un plancher (dalle, mezzanine, coursive) existe-t-il sous le prop ?"""
        if zf == room[2]:
            return True
        cx, cy = (bx[0] + bx[3]) / 2, (bx[1] + bx[4]) / 2
        return any(abs(b[5] - zf) <= 2 and b[0] + 8 <= cx <= b[3] - 8 and b[1] + 8 <= cy <= b[4] - 8 for b in blocks)

    import collections
    REJ = M.setdefault("rejets", collections.Counter())

    def try_place(model, pos, yaw, room, zf=None):
        bx = box_of(model, pos, yaw)
        if bx[0] < room[0] - 2 or bx[3] > room[3] + 2 or bx[1] < room[1] - 2 or bx[4] > room[4] + 2:
            REJ["hors_salle"] += 1
            return False
        if blocks_opening(bx, room):
            REJ["ouverture"] += 1
            nm = next((x.name for x in w.spaces if x.box == room), "?")
            M.setdefault("rej_ouv", collections.Counter())[nm] += 1
            return False
        if not supported(bx, room[2] if zf is None else zf, room):
            REJ["sans_plancher"] += 1
            return False
        if any(overlap(bx, o, 8) for o in placed):
            REJ["autre_prop"] += 1
            nm = next((x.name for x in w.spaces if x.box == room), "?")
            M.setdefault("rej_prop", collections.Counter())[nm + ":" + model.split("/")[-1]] += 1
            return False
        if any(overlap(bx, o) for o in blocks):
            REJ["bloc"] += 1
            return False
        if any(overlap(bx, s_) for s_ in spawns):
            REJ["spawn"] += 1
            return False
        if near_route(bx):
            REJ["trace"] += 1
            return False
        if any(overlap(bx, o, 8) for o in placed) or any(overlap(bx, o) for o in blocks):
            return False
        if any(overlap(bx, s) for s in spawns) or near_route(bx):
            return False
        placed.append(bx)
        M["props"].append((model, pos, yaw))
        return True

    count = 0

    # ===== intérieur : un ensemble fonctionnel par travée (entre deux nervures) =====
    CR2, CR1 = KP + "misc/imp_crate_double_closed.mdl", KP + "misc/imp_crate_single_closed.mdl"
    KY, FT = LT + "props/kyber_crate_static.mdl", LT + "props/fueltank_scarif1_static.mdl"
    PC, PC2 = KP + "deathstar/powercell1b.mdl", KP + "deathstar/powercell2b.mdl"
    CL, CM, CS = LT + "isd/imp_console_large01.mdl", LT + "isd/imp_console_medium01.mdl", LT + "isd/imp_console_small01.mdl"
    CH, FL, FG = LT + "props/imp_chair01.mdl", KP + "deathstar/floorlight.mdl", LT + "props/imp_floorgreeble01.mdl"
    BT, LC = LT + "props/bactatankb.mdl", KP + "deathstar/laserconsole01.mdl"
    WP, PIPE, SCR = KP + "deathstar/wallpanel01.mdl", LT + "isd/imp_wallpipes02.mdl", KP + "deathstar/viewscreen03.mdl"
    # élément : (modèle, décalage le long du mur, distance au mur, z en plus, mode, rotation en plus)
    #   mode "mur" : dos contre le mur, face vers la salle ; "libre" : centre à la distance donnée
    SETS = {
        "stockage": (260, [(CR2, -70, 40, 0, "libre", 90), (CR2, -70, 40, 32, "libre", 90), (CR1, 0, 34, 0, "libre", 0),
                           (CR2, 70, 40, 0, "libre", 90), (KY, 0, 140, 0, "libre", 0)]),
        "energie": (220, [(PC, -60, 50, 0, "libre", 0), (PC, 60, 50, 0, "libre", 0), (CS, 0, 0, 0, "mur", 0), (FL, 0, 150, 0, "libre", 0)]),
        "poste": (220, [(CL, 0, 0, 0, "mur", 0), (FL, 90, 60, 0, "libre", 0)]),
        "double_poste": (220, [(CM, -60, 0, 0, "mur", 0), (CM, 60, 0, 0, "mur", 0), (FL, 0, 90, 0, "libre", 0)]),
        "machine": (300, [(FG, -60, 50, 0, "libre", 90), (PC2, 100, 50, 0, "libre", 0), (CS, 20, 0, 0, "mur", 0)]),
        "carburant": (220, [(FT, -60, 45, 0, "libre", 0), (FT, 60, 45, 0, "libre", 0), (CR1, 0, 150, 0, "libre", 15)]),
        "medical": (200, [(BT, -55, 40, 0, "libre", 0), (BT, 55, 40, 0, "libre", 0), (CS, 0, 0, 0, "mur", 0)]),
        "commande": (360, [(CL, 0, 0, 0, "mur", 0), (FL, -120, 150, 0, "libre", 0), (FL, 120, 150, 0, "libre", 0)]),
        "ecran": (220, [(SCR, 0, 0, 40, "mur", 0)]),
        "panneau": (110, [(WP, 0, 0, 0, "mur", 0)]),
        "tuyaux": (110, [(WP, 0, 0, 0, "mur", 0)]),
    }
    PALETTE = {          # ensembles proposés par thème (pondérés par répétition) ; "" = travée laissée vide
        "industriel": ["stockage", "stockage", "energie", "machine", "carburant", "poste", "tuyaux", "", ""],
        "sentinelle": ["poste", "double_poste", "energie", "commande", "panneau", "ecran", "stockage", "", ""],
        "donnees": ["double_poste", "poste", "commande", "panneau", "energie", "", ""],
        "prison": ["poste", "panneau", "stockage", "medical", "", ""],
        "glace": ["", "", "panneau"],
    }
    SPACE_THEME = {"garrison": ["stockage", "stockage", "medical", "double_poste", "energie", "carburant", ""],
                   "factory": ["machine", "machine", "energie", "commande", "stockage", "carburant", "tuyaux", ""]}

    def place_element(el, s_box, side, ang, ub, zf, d_rib):
        model, du, dist, dz, mode, rot = el
        e = PB.get(model)
        if not e:
            return None
        u = ub + du
        x0, y0, z0, x1, y1, z1 = s_box
        base = WALL_OFFSET
        if mode == "mur":
            fr = FRONT.get(model, "+x")
            ax, sg = fr[1], (1 if fr[0] == "+" else -1)
            if ax == "x":
                back = -e["min"][0] if sg > 0 else e["max"][0]
                yaw = ang if sg > 0 else (ang + 180) % 360
            else:
                back = -e["min"][1] if sg > 0 else e["max"][1]
                yaw = (ang - 90) % 360 if sg > 0 else (ang + 90) % 360
            dist = base + back
        else:
            dist = base + dist
            yaw = (ang + rot) % 360
        zz = zf + (MOUNT[model] if model in MOUNT else (-e["min"][2] + 2)) + dz
        if side == "x0":
            pos = (x0 + dist, u, zz)
        elif side == "x1":
            pos = (x1 - dist, u, zz)
        elif side == "y0":
            pos = (u, y0 + dist, zz)
        else:
            pos = (u, y1 - dist, zz)
        return (model, pos, yaw)

    hangar = next(x for x in w.spaces if x.name == "hangar")
    hb = hangar.box
    for side in ("y0", "y1"):
        for u in range(hb[0] + 640, hb[3] - 383, 512):
            M.setdefault("bays", []).append(("hangar", side, u - 200, u + 200, hb[2], hb, 0))
    SPACE_THEME_EXT = {"hangar": ["stockage", "carburant", "energie", "stockage", "carburant", ""]}

    for (sname, side, b0, b1, zf, s_box, d_rib) in M.get("bays", []):
        sp = next(x for x in w.spaces if x.name == sname)
        t = theme.theme_of(sp.zone, sp.wall)
        options = SPACE_THEME_EXT.get(sname) or SPACE_THEME.get(sname) or PALETTE.get(t)
        if not options:
            continue
        ang = {"x0": 0, "x1": 180, "y0": 90, "y1": 270}[side]
        width = b1 - b0
        fits = [o for o in options if o == "" or SETS[o][0] <= width]
        choice = rnd.choice(fits) if fits else ""
        if not choice:
            continue
        ub = (b0 + b1) / 2
        mark_p, mark_l = len(placed), len(M["props"])
        ok = True
        for el in SETS[choice][1]:
            res = place_element(el, s_box, side, ang, ub, zf, d_rib)
            if res is None or not try_place(res[0], res[1], res[2], s_box, zf):
                ok = False
                break
        if not ok:                      # tout ou rien : un ensemble incomplet n'a pas de sens
            del placed[mark_p:]
            del M["props"][mark_l:]
            continue
        count += len(SETS[choice][1])

    INTERIEUR_PAR_TRAVEES = True
    for s in w.spaces:
        if INTERIEUR_PAR_TRAVEES:
            break
        t = theme.theme_of(s.zone, s.wall)
        if s.sky or t not in CATALOG or s.name.endswith("_d") or "doorway" in s.name or "pit" in s.name:
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        if z1 - z0 < 160:
            continue
        wall_models, free_models, step = CATALOG[t]
        narrow = min(x1 - x0, y1 - y0) <= 448
        for zf in [z0] + M.get("floors", {}).get(s.name, []):
            # murs : x0 (intérieur +x, angle 0), x1 (180), y0 (90), y1 (270)
            for side, ang in (("x0", 0), ("x1", 180), ("y0", 90), ("y1", 270)):
                length = (y1 - y0) if side in ("x0", "x1") else (x1 - x0)
                n = int(length // step)
                for i in range(n):
                    u = (i + 0.5) * length / n + rnd.uniform(-24, 24)
                    model = rnd.choice(wall_models)
                    if model not in PB and model not in P.BOUNDS:
                        continue
                    e = PB.get(model)
                    depth = min(e["max"][0] - e["min"][0], e["max"][1] - e["min"][1]) if e else 40
                    if narrow and depth > CORRIDOR_MAX_DEPTH:
                        model = rnd.choice([m for m in wall_models if PB.get(m) and PB[m]["max"][0] - PB[m]["min"][0] <= CORRIDOR_MAX_DEPTH]
                                           or [LT + "isd/imp_greeblewall01.mdl"])
                        e = PB[model]
                    fr = FRONT.get(model, "+x")
                    ax, sg = fr[1], (1 if fr[0] == "+" else -1)
                    if ax == "x":
                        back = -e["min"][0] if sg > 0 else e["max"][0]
                        yaw = ang if sg > 0 else (ang + 180) % 360
                    else:
                        back = -e["min"][1] if sg > 0 else e["max"][1]
                        yaw = (ang - 90) % 360 if sg > 0 else (ang + 90) % 360
                    zz = zf + MOUNT[model] if model in MOUNT else zf - e["min"][2] + 2
                    off = back + WALL_OFFSET
                    if side == "x0":
                        pos = (x0 + off, y0 + u, zz)
                    elif side == "x1":
                        pos = (x1 - off, y0 + u, zz)
                    elif side == "y0":
                        pos = (x0 + u, y0 + off, zz)
                    else:
                        pos = (x0 + u, y1 - off, zz)
                    if try_place(model, pos, yaw, s.box, zf):
                        count += 1
                    # objet posé devant certains murs des grandes salles
                    if not narrow and rnd.random() < 0.35:
                        fm = rnd.choice(free_models)
                        fe = PB[fm]
                        ext = max(fe["max"][0] - fe["min"][0], fe["max"][1] - fe["min"][1]) / 2 + 48
                        if side == "x0":
                            fp = (x0 + ext + 40, y0 + u + 80, zf - fe["min"][2] + 2)
                        elif side == "x1":
                            fp = (x1 - ext - 40, y0 + u + 80, zf - fe["min"][2] + 2)
                        elif side == "y0":
                            fp = (x0 + u + 80, y0 + ext + 40, zf - fe["min"][2] + 2)
                        else:
                            fp = (x0 + u + 80, y1 - ext - 40, zf - fe["min"][2] + 2)
                        if try_place(fm, fp, rnd.choice([0, 90, 180, 270]), s.box, zf):
                            count += 1

    # extérieurs : zone de largage (canyon), balises et carburant au hangar et au glacier
    outside = [
        (LT + "props/imp_landingbeacon.mdl", (-13900, -900, 0), 90), (LT + "props/imp_landingbeacon.mdl", (-13900, 900, 0), 270),
        (LT + "props/fueltank_scarif1_static.mdl", (-8600, -1300, 0), 0), (LT + "props/fueltank_scarif1_static.mdl", (-8500, -1250, 0), 30),
        (KP + "misc/imp_crate_double_closed.mdl", (-8150, 1450, 16), 0), (KP + "misc/imp_crate_double_closed.mdl", (-8150, 1450, 48), 15),
        (LT + "props/kyber_crate_static.mdl", (-5600, -1300, 20), 90),
        (LT + "props/imp_landingbeacon.mdl", (-10880 - 900, -6016 - 700, M["zones"]["11"][2]), 45),
        (LT + "props/imp_landingbeacon.mdl", (-10880 - 900, -6016 + 700, M["zones"]["11"][2]), 135),
        (LT + "props/fueltank_scarif1_static.mdl", (-12300, -5200, M["zones"]["11"][2]), 60),
    ]
    for (m, p, y) in outside:
        e = PB.get(m)
        if not e:
            continue
        pz = (p[0], p[1], (p[2] - e["min"][2] + 2) if p[2] in (0, M["zones"]["11"][2]) else p[2])
        zbox = next((sp.box for sp in w.spaces if sp.box[0] <= p[0] <= sp.box[3] and sp.box[1] <= p[1] <= sp.box[4]
                     and sp.box[2] <= pz[2] <= sp.box[5]), None)
        if zbox and try_place(m, pz, y, zbox):
            count += 1

    for (model, pos, yaw) in M["props"][len(M["props"]) - count:]:
        w.ent("prop_static", pos, model=model, angles=f"0 {yaw} 0", solid=6, skin=0, fademindist=-1, fadescale=1)

    # ---------- droïdes abattus : ragdolls « débris » (les joueurs passent au travers) ----------
    # CGI CIS Droid Pack (Workshop 721821542, élément requis)
    droids = ["models/tfa/comm/gg/pm_sw_droid_b1.mdl"] * 5 + ["models/tfa/comm/gg/pm_sw_droid_commander.mdl",
              "models/tfa/comm/gg/pm_sw_droid_tactical.mdl", "models/tfa/comm/gg/pm_sw_droid_commando.mdl"]
    per_zone = {"2": 4, "3b": 3, "3a": 2, "4": 5, "5": 4, "6": 4, "7": 3, "8": 3, "11": 2}
    ndroid = 0
    for zone, n in per_zone.items():
        rooms = [sp for sp in w.spaces if sp.zone == zone and (sp.box[3] - sp.box[0]) * (sp.box[4] - sp.box[1]) >= 160000
                 and "closet" not in sp.name and not sp.name.endswith("_d")]
        if not rooms:
            continue
        room = max(rooms, key=lambda sp: (sp.box[3] - sp.box[0]) * (sp.box[4] - sp.box[1]))
        x0, y0, z0, x1, y1, z1 = room.box
        tries = 0
        while n > 0 and tries < 400:
            tries += 1
            px, py = rnd.uniform(x0 + 96, x1 - 96), rnd.uniform(y0 + 96, y1 - 96)
            bx = (px - 40, py - 40, z0, px + 40, py + 40, z0 + 72)
            if any(overlap(bx, o) for o in blocks) or any(overlap(bx, o) for o in placed) or near_route(bx):
                continue
            if any(overlap(bx, sp_) for sp_ in spawns):
                continue
            # droïde abattu = prop_static couché et allégé (plus de physique ni de réseau)
            rnd.choice(droids)
            w.ent("prop_static", (px, py, z0 + 1), model="models/givre_noir/droid_b1_couche.mdl",
                  angles=f"0 {rnd.randint(0, 359)} {rnd.choice([0, 0, 8, -8])}", solid=0, skin=0)
            placed.append(bx)
            n -= 1
            ndroid += 1

    # ---------- traces du passage séparatiste ----------
    decals = ["decals/scorch1", "decals/scorch2", "decals/smscorch1", "decals/smscorch2", "decals/burn01a"]
    shots = ["decals/metal/shot1", "decals/metal/shot2", "decals/metal/shot3", "decals/metal/shot4", "decals/metal/shot5"]
    nd = 0
    for s in w.spaces:
        if s.name.endswith("_d") or "doorway" in s.name or "pit" in s.name or "ciel" in s.zone or s.zone in ("1", "11"):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        area = (x1 - x0) * (y1 - y0)
        for _ in range(max(1, int(area / 600000))):
            px, py = rnd.uniform(x0 + 48, x1 - 48), rnd.uniform(y0 + 48, y1 - 48)
            w.ent("infodecal", (px, py, z0 + 1), texture=rnd.choice(decals))          # brûlure au sol
            nd += 1
        if z1 - z0 < 128:
            continue
        for _ in range(max(1, int(((x1 - x0) + (y1 - y0)) / 1400))):                    # impacts de tir sur les murs
            side = rnd.choice("abcd")
            zz = rnd.uniform(z0 + 40, min(z1 - 24, z0 + 180))
            if side == "a":
                p = (x0 + 1, rnd.uniform(y0 + 32, y1 - 32), zz)
            elif side == "b":
                p = (x1 - 1, rnd.uniform(y0 + 32, y1 - 32), zz)
            elif side == "c":
                p = (rnd.uniform(x0 + 32, x1 - 32), y0 + 1, zz)
            else:
                p = (rnd.uniform(x0 + 32, x1 - 32), y1 - 1, zz)
            for k in range(rnd.randint(2, 4)):
                w.ent("infodecal", (p[0], p[1], p[2] + rnd.uniform(-24, 24)), texture=rnd.choice(shots))
                nd += 1

    # fumée d'épaves (canyon, hangar, glacier) et étincelles sur du matériel touché
    for (x, y, z) in [(-12900, 1150, 0), (-10400, -1150, 0), (-7600, 1650, 0), (-6000, -1650, 0),
                      (-12300, -5200, M["zones"]["11"][2]), (-9200, -7600, M["zones"]["11"][2])]:
        w.ent("env_smokestack", (x, y, z + 16), targetname="", InitialState=1, BaseSpread=40, SpreadSpeed=20, Speed=60,
              StartSize=60, EndSize=220, Rate=12, JetLength=420, WindAngle=30, WindSpeed=20,
              SmokeMaterial="particle/SmokeStack.vmt", rendercolor="70 70 75", renderamt=180, roll=12, twist=4)
        w.ent("env_fire", (x, y, z + 8), health=0, firesize=96, fireattack=2, firetype=0, spawnflags=1 + 2 + 32,
              ignitionpoint=0, damagescale=0, StartDisabled=0)
    sparks = 0
    for (model, pos, yaw) in M["props"]:
        if "console" in model and rnd.random() < 0.18 and sparks < 24:
            w.ent("env_spark", (pos[0], pos[1], pos[2] + 40), MaxDelay=4, Magnitude=1, TrailLength=1, spawnflags=64)
            sparks += 1
    # lumières qui grésillent (dégâts) : ~1 lumière intérieure sur 6
    flick = 0
    for e in w.ents:
        if e["classname"] == "light" and "targetname" not in e["kv"] and rnd.random() < 0.16:
            e["kv"]["style"] = 10          # un seul style de grésillement : max 4 styles par face (moteur)
            flick += 1
    M["dressing_stats"] = {"props": count, "decals": nd, "sparks": sparks, "flicker": flick, "droides": ndroid}
    return count
