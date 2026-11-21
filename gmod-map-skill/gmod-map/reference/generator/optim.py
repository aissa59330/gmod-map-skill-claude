"""Passe d'optimisation appliquée juste avant l'export du .vmf (100 joueurs + bots).

- props : distance de disparition (fade) selon la taille, collision simplifiée (boîte, ou aucune pour le décor
  inaccessible), ombres dynamiques coupées sur les props animés ;
- réduction des entités networkées (droïdes animés, ragdolls, étincelles, feux) ;
- un seul repère info_target par groupe de spawn (les grilles complètes restent dans docs/narration.md) ;
- faces cachées des func_detail en nodraw (voir hide_faces, appelé par build_map.py).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
# versions LOD maison (tools/make_lod_props.py + studiomdl) : modèle d'origine -> models/givre_noir/lod/<nom>.mdl
LOD_DIR = os.path.join(os.path.dirname(HERE), "compile_game", "models", "gnl")   # chemin court : limite de 260 caractères de Source
LOD = {f[:-4] for f in os.listdir(LOD_DIR) if f.endswith(".mdl")} if os.path.isdir(LOD_DIR) else set()
PB = {}
for fn in ("prop_bounds_packs.json",):
    p = os.path.join(HERE, fn)
    if os.path.exists(p):
        PB.update(json.load(open(p, encoding="utf-8")))

# décor inaccessible ou plaqué au mur : aucune collision (rien à calculer côté serveur)
NO_COLLIDE = ("droid_b1_", "wallpanel", "viewscreen", "greeblewall", "greeblepanel", "wallpipes", "bridgepanel", "light_alarm",
              "bridge_console_wall", "pipe_large", "_16.mdl", "ceilinglight", "rockcliff")
# modèles très lourds : disparition plus tôt
HEAVY_FADE = {"generator_portable": (1400, 1900), "viewscreen03": (1200, 1600), "powercell1b": (1100, 1500),
              "pipe_large_512": (2200, 2800), "imp_console_large01": (1500, 2000)}
SKYBOX = ("_16.mdl",)


def _size(model):
    e = PB.get(model)
    if not e:
        return 64
    return max(e["max"][i] - e["min"][i] for i in range(3))


def fade_for(model):
    for k, v in HEAVY_FADE.items():
        if k in model:
            return v
    s = _size(model)
    if s < 40:
        return (800, 1100)
    if s < 96:
        return (1300, 1700)
    if s < 200:
        return (2000, 2600)
    return (3000, 3800)


def apply(w):
    M = w.meta
    st = {"fade": 0, "sans_collision": 0, "boite": 0, "droides_usine": 0, "ragdolls": 0, "etincelles": 0,
          "feux": 0, "reperes_supprimes": 0}
    keep = []
    seen_targets = set()
    n_drone, n_rag, n_spark, n_fire = 0, 0, 0, 0
    outdoor = [sp.box for sp in w.spaces if sp.sky and not sp.name.startswith("ciel")]
    for e in w.ents:
        c = e["classname"]
        kv = e["kv"]
        m = str(kv.get("model", "")).lower()
        if str(kv.get("targetname", "")).startswith("fx_"):
            keep.append(e)                         # effets scriptés (generator/fx.py) : jamais touchés
            continue
        if c == "prop_static":
            if any(k in m for k in SKYBOX):
                keep.append(e)
                continue
            mn, mx = fade_for(m)
            o = [float(v) for v in str(kv.get("origin", "0 0 0")).split()]
            if any(b[0] <= o[0] <= b[3] and b[1] <= o[1] <= b[4] and b[2] <= o[2] <= b[5] for b in outdoor):
                mn, mx = max(mn, 2400), max(mx, 3200)       # plaines : un peu plus loin qu'à l'intérieur, sans excès
            kv["fademindist"], kv["fademaxdist"] = mn, mx
            st["fade"] += 1
            if any(k in m for k in NO_COLLIDE):
                kv["solid"] = 0
                st["sans_collision"] += 1
            else:
                kv["solid"] = 2                    # boîte englobante : collision la moins chère possible
                st["boite"] += 1
            kv["disableselfshadowing"] = 1
            base = os.path.splitext(os.path.basename(m))[0]
            if base in LOD:
                kv["model"] = f"models/gnl/{base}.mdl"
                st["lod"] = st.get("lod", 0) + 1
        elif c == "prop_dynamic" and "droid" in m:
            n_drone += 1
            if n_drone % 3 == 2:                   # 1 droïde sur 3 retiré (chaîne + stock gardent leur rythme)
                st["droides_usine"] += 1
                continue
            kv["fademindist"], kv["fademaxdist"] = 1400, 1900
            kv["disableshadows"] = 1
            kv["DisableBoneFollowers"] = 1
        elif c == "prop_ragdoll":
            n_rag += 1
            if n_rag % 2 == 0:                     # moitié des droïdes abattus (physique serveur + réseau)
                st["ragdolls"] += 1
                continue
            kv["fademindist"], kv["fademaxdist"] = 1200, 1600
            kv["disableshadows"] = 1
        elif c == "env_spark":
            n_spark += 1
            if n_spark > 6:
                st["etincelles"] += 1
                continue
        elif c == "env_fire":
            n_fire += 1
            if n_fire % 2 == 0:
                st["feux"] += 1
                continue
        elif c == "info_target" and str(kv.get("targetname", "")).startswith(("gn_def_spawn_", "gn_atk_respawn_")):
            name = kv["targetname"]
            if name in seen_targets:
                st["reperes_supprimes"] += 1
                continue
            seen_targets.add(name)
            # repère unique au centre de la grille
            grid = M["def_spawns"].get(name[len("gn_def_spawn_"):]) if name.startswith("gn_def_spawn_") \
                else M["atk_respawns"].get(name[len("gn_atk_respawn_"):])
            if grid:
                kv["origin"] = "%g %g %g" % (sum(p[0] for p in grid) / len(grid), sum(p[1] for p in grid) / len(grid), grid[0][2])
        keep.append(e)
    w.ents[:] = keep
    M["optim_stats"] = st
    return st


# ---------------- faces cachées ----------------
class _Grid:
    def __init__(self, boxes, cell=512):
        self.cell = cell
        self.g = {}
        for b in boxes:
            for ix in range(int(b[0] // cell), int(b[3] // cell) + 1):
                for iy in range(int(b[1] // cell), int(b[4] // cell) + 1):
                    self.g.setdefault((ix, iy), []).append(b)

    def inside(self, p):
        for b in self.g.get((int(p[0] // self.cell), int(p[1] // self.cell)), ()):
            if b[0] < p[0] < b[3] and b[1] < p[1] < b[4] and b[2] < p[2] < b[5]:
                return True
        return False


def hidden_face_tester(world_boxes):
    grid = _Grid(world_boxes)

    def hidden(lo, hi, n):
        """Face d'une boîte (lo, hi) de normale sortante n (axe) : cachée si 5 points juste derrière sont dans du world."""
        ax = 0 if abs(n[0]) > 0.5 else (1 if abs(n[1]) > 0.5 else 2)
        sgn = 1 if n[ax] > 0 else -1
        plane = hi[ax] if sgn > 0 else lo[ax]
        o = [i for i in range(3) if i != ax]
        pts = []
        for fa in (0.02, 0.98, 0.5):
            for fb in (0.02, 0.98, 0.5):
                if (fa == 0.5) != (fb == 0.5):
                    continue
                p = [0, 0, 0]
                p[ax] = plane + sgn * 2
                p[o[0]] = lo[o[0]] + fa * (hi[o[0]] - lo[o[0]])
                p[o[1]] = lo[o[1]] + fb * (hi[o[1]] - lo[o[1]])
                pts.append(p)
        return all(grid.inside(p) for p in pts)
    return hidden
