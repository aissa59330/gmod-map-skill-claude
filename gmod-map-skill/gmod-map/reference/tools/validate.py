"""Vérifications statiques de givre_noir (avant compilation).

- toutes les entités ponctuelles sont dans un volume d'air (sinon leak / entité dans le vide)
- spawns : hull 32x32x72 libre, sol à moins de 24 u en dessous
- comptes : 80 info_player_start, >= 16 gn_def_spawn_<zone>, gn_atk_respawn_<n>
- pas de ligne de vue entre un spawn défenseur et un spawn/respawn attaquant
- relais gn_phase_<n>_start/_done pour n = 1..11
- toutes les cibles des sorties (I/O) existent
"""
import json
import os
import sys
from collections import Counter, defaultdict

from srctools.vmf import VMF
from srctools import Keyvalues, Vec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def inside(b, p, e=0.0):
    return b[0] - e <= p[0] <= b[3] + e and b[1] - e <= p[1] <= b[4] + e and b[2] - e <= p[2] <= b[5] + e


def overlap(a, b):
    return a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4] and a[2] < b[5] and b[2] < a[5]


def seg_hits_box(p, q, b):
    """Segment p->q intersecte-t-il la boîte b (slab test) ?"""
    t0, t1 = 0.0, 1.0
    for i in range(3):
        d = q[i] - p[i]
        lo, hi = b[i], b[i + 3]
        if abs(d) < 1e-9:
            if p[i] <= lo or p[i] >= hi:
                return False
        else:
            a, c = (lo - p[i]) / d, (hi - p[i]) / d
            if a > c:
                a, c = c, a
            t0, t1 = max(t0, a), min(t1, c)
            if t0 >= t1:
                return False
    return True


def main():
    side = json.load(open(os.path.join(ROOT, "maps_src", "givre_noir.json"), encoding="utf-8"))
    vmf = VMF.parse(Keyvalues.parse(open(os.path.join(ROOT, "maps_src", "givre_noir.vmf"), encoding="utf-8")))
    airs = [s["box"] for s in side["spaces"]]
    solids = [tuple(b) for b in side["solids"]]
    errors, warns = [], []

    names = Counter()
    for ent in vmf.entities:
        if ent["targetname"]:
            names[ent["targetname"]] += 1
        if ent.solids or not ent["origin"]:
            continue
        o = Vec.from_str(ent["origin"])
        if not any(inside(a, o) for a in airs):
            errors.append(f"entité hors de l'air : {ent['classname']} {ent['targetname']} @ {o}")

    door_boxes = []
    for (name, axis, pos, lo, hi, z0, z1) in side.get("door_specs", []):
        door_boxes.append((pos, lo, z0, pos + 16, hi, z1) if axis == "x" else (lo, pos, z0, hi, pos + 16, z1))

    def hull_ok(p):
        hb = (p[0] - 16, p[1] - 16, p[2] + 1, p[0] + 16, p[1] + 16, p[2] + 72)
        if any(overlap(hb, s) for s in door_boxes):
            return "hull dans une porte fermée"
        if any(overlap(hb, s) for s in solids):
            return "hull dans un solide"
        if not any(inside(a, (p[0], p[1], p[2] + 36)) for a in airs):
            return "hors de l'air"
        probe = (p[0] - 15, p[1] - 15, p[2] - 24, p[0] + 15, p[1] + 15, p[2] + 0.5)
        if not any(overlap(probe, s) for s in solids):
            return "pas de sol dessous"
        return None

    groups = {"player_start": side["player_starts"]}
    for z, pts in side["def_spawns"].items():
        groups[f"def_{z}"] = pts
    for n, pts in side["atk_respawns"].items():
        groups[f"atk_{n}"] = pts
    for g, pts in groups.items():
        for p in pts:
            r = hull_ok(p)
            if r:
                errors.append(f"spawn {g} {tuple(round(v) for v in p)} : {r}")

    # points du tracé de marche : libres et posés sur un sol (rampes exclues : testées en jeu)
    boxes_only = [tuple(b) for b in side.get("solids_boxes", side["solids"])]
    for route in ("walk", "walk_3a"):
        for (wname, x, y, z) in side.get(route, []):
            hb = (x - 16, y - 16, z + 1, x + 16, y + 16, z + 72)
            probe = (x - 15, y - 15, z - 24, x + 15, y + 15, z + 0.5)
            if any(overlap(hb, b) for b in boxes_only):
                r = "hull dans un solide"
            elif not any(inside(a, (x, y, z + 36)) for a in airs):
                r = "hors de l'air"
            elif not any(overlap(probe, b) for b in side["solids"]):
                r = "pas de sol dessous"
            else:
                r = None
            if r and r != "hull dans une porte fermée":
                errors.append(f"tracé {route} {wname} {(x, y, z)} : {r}")

    if names["gn_aa_counter"] != 1:
        errors.append("gn_aa_counter manquant")
    n_starts = sum(1 for e in vmf.by_class["info_player_start"])
    if n_starts < 100:
        errors.append(f"{n_starts} info_player_start (100 attendus)")
    for z in ("1", "2", "3a", "3b", "4", "5", "6", "7", "8", "9", "10", "11"):
        grid = side["def_spawns"].get(z, [])
        if names[f"gn_def_spawn_{z}"] < 1 or len(grid) < 16:   # 1 repère central ; la grille (>=16) est dans le sidecar
            errors.append(f"gn_def_spawn_{z} : repère {names[f'gn_def_spawn_{z}']}, grille {len(grid)} < 16")
    for n in range(2, 12):
        if names[f"gn_atk_respawn_{n}"] < 1:
            errors.append(f"gn_atk_respawn_{n} manquant")
    for n in range(1, 12):
        for k in ("start", "done"):
            if names[f"gn_phase_{n}_{k}"] != 1:
                errors.append(f"relais gn_phase_{n}_{k} : {names[f'gn_phase_{n}_{k}']}")
    for i in (1, 2, 3):
        if names[f"aa_{i}"] != 1:
            errors.append(f"aa_{i} manquant")

    # chaque porte (hors portes de la salle du hack) doit fermer toute la section de son volume
    for (name, axis, pos, lo, hi, z0, z1) in side.get("door_specs", []):
        c = (pos + 8, (lo + hi) / 2, (z0 + z1) / 2) if axis == "x" else ((lo + hi) / 2, pos + 8, (z0 + z1) / 2)
        hosts = [a for a in airs if inside(a, c)]
        if not hosts:
            errors.append(f"porte {name} hors de tout volume")
            continue
        for a in hosts:
            t0, t1 = (a[1], a[4]) if axis == "x" else (a[0], a[3])
            if lo > t0 or hi < t1 or z0 > a[2] or z1 < a[5]:
                errors.append(f"porte {name} ne ferme pas toute la section ({lo}..{hi}, z {z0}..{z1}) du volume {a}")

    # classes d'entités connues de Gmod (FGD) + entrées existantes
    fgd_dir = os.path.join("C:/Program Files (x86)/Steam/steamapps/common/GarrysMod", "bin")
    known = set()
    import re as _re
    for f in ("base.fgd", "halflife2.fgd", "garrysmod.fgd"):
        fp = os.path.join(fgd_dir, f)
        if os.path.exists(fp):
            txt = open(fp, encoding="utf-8", errors="ignore").read()
            known |= {m.lower() for m in _re.findall(r"@\w+Class[^=]*=\s*([\w]+)", txt)}
    if known:
        for cls in sorted({e["classname"].lower() for e in vmf.entities}):
            if cls not in known:
                errors.append(f"classe d'entité inconnue de Gmod : {cls}")
    else:
        warns.append("FGD de Gmod introuvables : classes non vérifiées")

    # ponts et portes : jamais « non solides » (func_movelinear flag 8, func_door flag 4)
    for ent in vmf.entities:
        sf = int(ent["spawnflags"] or 0)
        if ent["classname"] == "func_movelinear" and sf & 8:
            errors.append(f"pont non solide : {ent['targetname']}")
        if ent["classname"] == "func_door" and sf & 4:
            errors.append(f"porte non solide : {ent['targetname']}")

    # cibles des sorties
    special = {"!self", "!activator", "!caller", "!player"}
    for ent in vmf.entities:
        for out in ent.outputs:
            if out.target not in special and names[out.target] == 0:
                errors.append(f"sortie vers une cible inexistante : {ent['targetname']} {out.output} -> {out.target}")

    # lignes de vue défenseurs <-> attaquants (yeux à +64), échantillonnées
    atk = [("start", p) for p in side["player_starts"][::7]]
    for n, pts in side["atk_respawns"].items():
        atk += [(f"atk_{n}", p) for p in pts[::3]]
    seen = defaultdict(int)
    for z, pts in side["def_spawns"].items():
        for d in pts[::3]:
            de = (d[0], d[1], d[2] + 64)
            for g, a in atk:
                ae = (a[0], a[1], a[2] + 64)
                if not any(seg_hits_box(de, ae, s) for s in solids):
                    seen[(f"def_{z}", g)] += 1
    for (dz, g), c in seen.items():
        errors.append(f"ligne de vue : {dz} voit {g} ({c} paires)")

    # bornes
    for a in airs:
        if any(abs(v) > 16384 - 32 for v in a):
            errors.append(f"volume hors limites {a}")

    print(f"entités={len(vmf.entities)}  info_player_start={n_starts}  noms gn_={sum(1 for n in names if n.startswith('gn_'))}")
    for w_ in warns:
        print("AVERT :", w_)
    for e in errors:
        print("ERREUR :", e)
    print("VALIDATION :", "OK" if not errors else f"{len(errors)} erreur(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
