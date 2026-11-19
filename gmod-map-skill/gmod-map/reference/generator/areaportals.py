"""Areaportals toujours ouverts sur chaque ouverture sans porte (jonction volume ↔ volume).

Un portail ouvert limite le rendu à ce qu'on voit À TRAVERS l'ouverture (en plus du VVIS).
Le portail (8 u d'épaisseur) est posé dans le plan de l'ouverture, côté du volume voisin.
Ceux que VBSP refuse (ne séparent pas deux zones) sont listés dans areaportal_skip.json
par tools/fit_areaportals.py, et ne sont plus générés.
"""
import json
import os

from geom import Block, MAT_PORTAL

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_FILE = os.path.join(HERE, "areaportal_skip.json")
SKIP_NAMES = ("_d", "doorway", "ciel")


def _skips():
    if os.path.exists(SKIP_FILE):
        return set(json.load(open(SKIP_FILE, encoding="utf-8")))
    return set()


def _overlap(a, b):
    return a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4] and a[2] < b[5] and b[2] < a[5]


def build(w):
    M = w.meta
    skip = _skips()
    existing = [sb.box for e in w.ents if e["classname"] == "func_areaportal" for sb in e["solids"]]
    seen = set()
    out = []
    for s in w.spaces:
        if any(k in s.name for k in SKIP_NAMES):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        for o in w.spaces:
            if o is s or any(k in o.name for k in SKIP_NAMES):
                continue
            b = o.box
            if b[5] <= z0 or b[2] >= z1:
                continue
            key = "|".join(sorted((s.name, o.name)))
            if key in seen:
                continue
            za, zb = max(z0, b[2]), min(z1, b[5])
            box = None
            if b[3] >= x0 and b[0] < x0 and b[1] < y1 and b[4] > y0:
                box = (x0 - 8, max(y0, b[1]), za, x0, min(y1, b[4]), zb)
            elif b[0] <= x1 and b[3] > x1 and b[1] < y1 and b[4] > y0:
                box = (x1, max(y0, b[1]), za, x1 + 8, min(y1, b[4]), zb)
            elif b[4] >= y0 and b[1] < y0 and b[0] < x1 and b[3] > x0:
                box = (max(x0, b[0]), y0 - 8, za, min(x1, b[3]), y0, zb)
            elif b[1] <= y1 and b[4] > y1 and b[0] < x1 and b[3] > x0:
                box = (max(x0, b[0]), y1, za, min(x1, b[3]), y1 + 8, zb)
            if not box or box[3] - box[0] < 8 or box[4] - box[1] < 8 or box[5] - box[2] < 32:
                continue
            seen.add(key)
            if key in skip:
                continue
            grown = (box[0] - 64, box[1] - 64, box[2], box[3] + 64, box[4] + 64, box[5])
            if any(_overlap(grown, ex) for ex in existing):      # déjà un portail de porte à cet endroit
                continue
            k = len(out) + 1
            name = f"gn_ap_open_{k}"
            w.ent("func_areaportal", solids=[Block(box, MAT_PORTAL)], targetname=name, StartOpen=1, PortalVersion=1)
            out.append((name, key, box))
            existing.append(box)
    M["open_portals"] = out
    return out
