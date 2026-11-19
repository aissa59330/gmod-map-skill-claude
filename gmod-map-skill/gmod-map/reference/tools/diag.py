"""Diagnostic de performance de givre_noir (lecture seule).

python tools/diag.py [maps_src/givre_noir.vmf]  ->  rapport texte sur la sortie + logs/diag_<date>.txt
- brushes world / func_detail / entités de brushes, faces et taille des faces
- entités par classe, estimation des edicts (réseau) vs entités serveur-seules vs compile-seules
- props : nombre par type, polycount LOD0 (VTX), nb de LODs, collision (.phy), $staticprop
- lumières dynamiques, brouillard (farz)
- textures : résolution VTF, format, densité de texels sur les faces (flou si étirée)
"""
import collections
import datetime
import os
import struct
import sys

from srctools import Keyvalues
from srctools.vmf import VMF
from srctools.vtf import VTF
from srctools.vpk import VPK

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GMOD = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod"
VMF_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "maps_src", "givre_noir.vmf")
CONTENT = [l.strip() for l in open(os.path.join(ROOT, "tools", "content_paths.txt"), encoding="utf-8")
           if l.strip() and not l.startswith("#")]
CONTENT += [os.path.join(ROOT, "compile_game"), os.path.join(GMOD, "garrysmod")]
VPKS = []
for p in (os.path.join(GMOD, "garrysmod", "garrysmod_dir.vpk"), os.path.join(GMOD, "sourceengine", "hl2_misc_dir.vpk"),
          os.path.join(GMOD, "sourceengine", "hl2_textures_dir.vpk")):
    if os.path.exists(p):
        VPKS.append(VPK(p))

out_lines = []


def P(*a):
    s = " ".join(str(x) for x in a)
    out_lines.append(s)
    print(s)


def find_file(rel):
    rel = rel.replace("\\", "/").lower()
    for c in CONTENT:
        f = os.path.join(c, rel)
        if os.path.exists(f):
            return ("fs", f)
    for v in VPKS:
        try:
            return ("vpk", v[rel])
        except KeyError:
            pass
    return None


def read_bytes(ref):
    if ref[0] == "fs":
        return open(ref[1], "rb").read()
    return ref[1].read()


# ---------------- modèles ----------------
def vtx_info(model):
    """(triangles LOD0, nombre de LODs) depuis le .dx90.vtx"""
    ref = find_file(model[:-4] + ".dx90.vtx")
    if not ref:
        return None, None
    b = read_bytes(ref)
    (ver, _vc, _mb1, _mb2, _mbv, _ck, nlods, _mro, nbp, bpo) = struct.unpack_from("<iiHHiiiiii", b, 0)
    tris = 0
    for i in range(nbp):
        bp = bpo + i * 8
        nmodels, mo = struct.unpack_from("<ii", b, bp)
        for m in range(min(nmodels, 1)):               # modèle 0 de chaque body part (sous-modèle par défaut)
            mh = bp + mo + m * 8
            nl, lo = struct.unpack_from("<ii", b, mh)
            if nl == 0:
                continue
            lh = mh + lo                                # LOD 0
            nmesh, meo, _sw = struct.unpack_from("<iif", b, lh)
            for k in range(nmesh):
                me = lh + meo + k * 9
                nsg, sgo = struct.unpack_from("<ii", b, me)
                for g in range(nsg):
                    sg = me + sgo + g * 25
                    _nv, _vo, nind, _io, _ns, _so = struct.unpack_from("<iiiiii", b, sg)
                    tris += nind // 3
    return tris, nlods


def mdl_info(model):
    ref = find_file(model)
    if not ref:
        return None
    b = read_bytes(ref)
    flags = struct.unpack_from("<i", b, 152)[0]
    phy = find_file(model[:-4] + ".phy")
    phy_size = len(read_bytes(phy)) if phy else 0
    phy_solids = struct.unpack_from("<i", read_bytes(phy), 8)[0] if phy else 0
    return {"static": bool(flags & 0x10), "phy_bytes": phy_size, "phy_solids": phy_solids}


# ---------------- textures ----------------
def vtf_info(mat):
    ref = find_file("materials/" + mat.lower() + ".vmt")
    if not ref:
        return None
    txt = read_bytes(ref).decode("utf-8", "ignore")
    import re
    m = re.search(r'"?\$basetexture"?\s+"?([^"\s]+)"?', txt, re.I)
    if not m:
        return {"vmt": True}
    vref = find_file("materials/" + m.group(1).lower() + ".vtf")
    if not vref:
        return {"base": m.group(1), "missing": True}
    b = read_bytes(vref)
    w, h = struct.unpack_from("<HH", b, 16)
    fmt = struct.unpack_from("<i", b, 52)[0]
    names = {0: "RGBA8888", 2: "RGB888", 3: "BGR888", 12: "BGRA8888", 13: "DXT1", 14: "DXT3", 15: "DXT5", 4: "RGB565"}
    return {"base": m.group(1), "w": w, "h": h, "fmt": names.get(fmt, str(fmt)), "bytes": len(b),
            "selfillum": "$selfillum" in txt.lower()}


def main():
    vmf = VMF.parse(Keyvalues.parse(open(VMF_PATH, encoding="utf-8")))
    P("=" * 78)
    P("DIAGNOSTIC givre_noir -", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "-", os.path.basename(VMF_PATH))
    P("=" * 78)

    # ---- brushes ----
    world = list(vmf.brushes)
    per_class = collections.Counter()
    ent_brushes = 0
    detail_solids = 0
    for e in vmf.entities:
        n = len(e.solids)
        if n:
            per_class[e["classname"]] += n
            ent_brushes += n
            if e["classname"] == "func_detail":
                detail_solids += n
    P("\n[2] BRUSHES")
    P(f"  world (structure, découpe la visibilité) : {len(world)}")
    P(f"  func_detail                              : {detail_solids}")
    P(f"  autres entités de brushes                : {ent_brushes - detail_solids}  {dict(per_class.most_common(8))}")
    # faces world par matériau, et faces minuscules (fragmentation)
    small = 0
    sides = 0
    for s in world:
        lo, hi = s.get_bbox()
        d = sorted([hi.x - lo.x, hi.y - lo.y, hi.z - lo.z])
        sides += len(s.sides)
        if d[1] < 64:
            small += 1
    P(f"  world : {sides} faces ; brushes dont la 2e dimension < 64 u (lamelles) : {small}")

    # ---- entités ----
    P("\n[5] ENTITÉS")
    cls = collections.Counter(e["classname"] for e in vmf.entities)
    COMPILE_ONLY = {"light", "light_spot", "light_environment", "infodecal", "func_detail", "prop_static",
                    "env_cubemap", "info_overlay", "func_viscluster", "info_lighting", "worldspawn",
                    "info_node", "info_node_hint"}          # info_node : convertis en graphe au chargement, puis supprimés
    SERVER_ONLY = {"logic_relay", "logic_timer", "math_counter", "logic_case", "logic_auto", "logic_compare",
                   "logic_branch", "info_target", "info_player_start", "game_text", "trigger_once", "trigger_multiple",
                   "trigger_hurt", "info_null", "point_template", "func_areaportal"}
    comp = sum(v for k, v in cls.items() if k in COMPILE_ONLY)
    srv = sum(v for k, v in cls.items() if k in SERVER_ONLY)
    net = sum(v for k, v in cls.items() if k not in COMPILE_ONLY and k not in SERVER_ONLY)
    P(f"  total dans le .vmf : {sum(cls.values())}  | compilées (disparaissent) : {comp}"
      f" | serveur sans réseau (approx.) : {srv} | NETWORKÉES (edicts) : {net}")
    P("  classes networkées :", ", ".join(f"{k}={v}" for k, v in cls.most_common() if k not in COMPILE_ONLY and k not in SERVER_ONLY))
    P("  classes serveur    :", ", ".join(f"{k}={v}" for k, v in cls.most_common() if k in SERVER_ONLY))
    P(f"  lumières statiques (light/spot) : {cls['light'] + cls['light_spot']} ; dynamiques (light_dynamic) : {cls['light_dynamic']}"
      f" ; env_projectedtexture : {cls['env_projectedtexture']} ; point_spotlight : {cls['point_spotlight']}")
    for e in vmf.by_class["env_fog_controller"]:
        P(f"  env_fog_controller {e['targetname']} : start {e['fogstart']} end {e['fogend']} maxdensity {e['fogmaxdensity']}"
          f" farz {e['farz']} (-1 = aucun plan de coupe)")
    for e in vmf.by_class["sky_camera"]:
        P(f"  sky_camera : scale {e['scale']} fogenable {e['fogenable']}")

    # ---- props ----
    P("\n[3] PROPS")
    kinds = collections.Counter()
    by_model = collections.Counter()
    by_model_kind = {}
    for e in vmf.entities:
        c = e["classname"]
        if c.startswith("prop_") or c in ("npc_combine_s",):
            kinds[c] += 1
            by_model[e["model"].lower()] += 1
            by_model_kind[e["model"].lower()] = c
    P("  par type :", dict(kinds))
    P(f"  NPC : {sum(v for k, v in cls.items() if k.startswith('npc_'))}")
    rows = []
    for mdl, n in by_model.items():
        tris, nl = vtx_info(mdl)
        mi = mdl_info(mdl) or {}
        rows.append((tris or 0, mdl, n, nl, mi, by_model_kind[mdl]))
    rows.sort(reverse=True)
    P(f"  {'tris LOD0':>9} {'nb':>4} {'tris x nb':>9} {'LODs':>4} {'statiq':>6} {'phy(o)':>8} {'type':<14} modèle")
    total = 0
    for tris, mdl, n, nl, mi, kind in rows:
        total += tris * n
        P(f"  {tris:>9} {n:>4} {tris * n:>9} {str(nl):>4} {str(mi.get('static', '?')):>6} {mi.get('phy_bytes', 0):>8} "
          f"{kind:<14} {mdl.replace('models/', '')}")
    P(f"  => triangles de props si tout était visible : {total}")

    # ---- droïdes ----
    P("\n[4] DROÏDES")
    dro = collections.Counter((e["classname"], e["model"].split("/")[-1]) for e in vmf.entities if "droid" in e["model"].lower())
    for (c, m), n in dro.items():
        P(f"  {c:<14} {m:<34} x{n}")

    # ---- textures ----
    P("\n[6] TEXTURES (faces de brushes)")
    use = collections.defaultdict(lambda: {"faces": 0, "min_scale": 99.0, "max_scale": 0.0})
    for s in list(vmf.brushes) + [sol for e in vmf.entities for sol in e.solids]:
        for sd in s.sides:
            m = sd.mat.lower()
            if m.startswith("tools/"):
                continue
            u = use[m]
            u["faces"] += 1
            sc = max(abs(sd.uaxis.scale), abs(sd.vaxis.scale))
            u["min_scale"] = min(u["min_scale"], sc)
            u["max_scale"] = max(u["max_scale"], sc)
    P(f"  {'faces':>6} {'résol.':>10} {'format':>8} {'Ko':>6} {'u/texel max':>11} {'texels/u min':>12}  matériau")
    for m, u in sorted(use.items(), key=lambda kv: -kv[1]["faces"]):
        vi = vtf_info(m) or {}
        res = f"{vi.get('w', '?')}x{vi.get('h', '?')}"
        dens = 1 / u["max_scale"] if u["max_scale"] else 0
        flag = ""
        if vi.get("w") and max(vi["w"], vi["h"]) > 1024:
            flag += " >1024"
        if dens and dens < 2:
            flag += " ÉTIRÉE(flou)"
        if vi.get("missing"):
            flag += " VTF MANQUANTE"
        P(f"  {u['faces']:>6} {res:>10} {vi.get('fmt', '?'):>8} {vi.get('bytes', 0) // 1024:>6} {u['max_scale']:>11.3f} {dens:>12.2f}  {m}{flag}")

    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    path = os.path.join(ROOT, "logs", "diag_" + datetime.datetime.now().strftime("%Y%m%d_%H%M") + ".txt")
    open(path, "w", encoding="utf-8").write("\n".join(out_lines) + "\n")
    print("\nRapport :", path)


main()
