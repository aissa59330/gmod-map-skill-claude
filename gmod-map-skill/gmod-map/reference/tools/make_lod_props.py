"""Versions LOD des props de décor les plus coûteux (Blender + Plumber -> SMD + QC pour studiomdl).

blender -b -P tools/make_lod_props.py -- <dossier_sortie> <bounds.json> <modèle1> <modèle2> ...
Pour chaque modèle :
- LOD0 = maillage d'origine (réduit seulement au-delà d'un plafond selon la taille : aucune perte visible de près),
  LOD1 = 50 %, LOD2 = 20 % (Decimate), distances de bascule proportionnelles à la taille ;
- origine/orientation vérifiées contre les bornes du modèle d'origine (sinon le modèle est ignoré) ;
- QC $staticprop, mêmes textures ($cdmaterials d'origine).
Sortie : <nom>.qc + smd, et un rapport lod_report.txt.
"""
import json
import math
import os
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, BOUNDS, MODELS = argv[0], json.load(open(argv[1], encoding="utf-8")), argv[2:]
os.makedirs(OUT, exist_ok=True)
ROOTS = [l.strip() for l in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "content_paths.txt"),
                                 encoding="utf-8") if l.strip() and not l.startswith("#")]
S = 100.0
report = []


def find_mdl(rel):
    for r in ROOTS:
        p = os.path.join(r, rel.replace("/", os.sep))
        if os.path.exists(p):
            return p


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def write_smd(o, path, matmap):
    me = o.data
    uv = me.uv_layers.active.data if me.uv_layers.active else None
    with open(path, "w", encoding="ascii") as f:
        f.write('version 1\nnodes\n0 "root" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\nend\ntriangles\n')
        for p in me.polygons:
            mname = matmap.get(p.material_index, "default")
            f.write(mname + "\n")
            for li in p.loop_indices:
                lp = me.loops[li]
                co = me.vertices[lp.vertex_index].co * S
                n = lp.normal
                u, v = (uv[li].uv if uv else (0.0, 0.0))
                f.write(f"0 {co.x:.4f} {co.y:.4f} {co.z:.4f} {n.x:.4f} {n.y:.4f} {n.z:.4f} {u:.5f} {v:.5f}\n")
        f.write("end\n")


def decimated_copy(src, ratio):
    o = src.copy()
    o.data = src.data.copy()
    bpy.context.collection.objects.link(o)
    if ratio < 0.999:
        d = o.modifiers.new("dec", "DECIMATE")
        d.ratio = max(0.02, ratio)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="dec")
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(o.data)
    bm.free()
    return o


for rel in MODELS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("bl_ext.user_default.plumber", default_set=True)
    src = find_mdl(rel)
    if not src:
        report.append(f"IGNORE {rel} : introuvable")
        continue
    try:
        bpy.ops.import_scene.plumber_mdl(filepath=src)
    except Exception as e:
        report.append(f"IGNORE {rel} : import {e}")
        continue
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.polygons) > 0]
    if not meshes:
        report.append(f"IGNORE {rel} : aucun maillage")
        continue
    # fige d'éventuels squelettes, puis fusionne tout le corps par défaut
    for o in meshes:
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            if m.type == "ARMATURE":
                bpy.ops.object.modifier_apply(modifier=m.name)
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ---- contrôle de l'origine et de l'orientation contre les bornes du modèle d'origine ----
    ref = BOUNDS.get(rel)
    co = [v.co * S for v in body.data.vertices]
    mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    ok = False
    if ref:
        for k in range(4):        # le modèle importé peut être tourné d'un quart de tour autour de z
            R = Matrix.Rotation(math.radians(90 * k), 4, "Z")
            pts = [R @ c for c in co]
            a = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
            b = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            exact = sum(1 for i in range(3) if abs(a[i] - ref["min"][i]) < 3) + sum(1 for i in range(3) if abs(b[i] - ref["max"][i]) < 3)
            within = all(a[i] >= ref["min"][i] - 3 and b[i] <= ref["max"][i] + 3 for i in range(3))
            if exact == 6 or (within and exact >= 5):     # maillage dans les bornes d'origine (bornes de collision parfois plus larges)
                if k:
                    body.data.transform(R)
                ok = True
                break
    if not ok:
        report.append(f"IGNORE {rel} : bornes différentes de l'original ({[round(x) for x in mn]} {[round(x) for x in mx]} vs {ref})")
        continue

    # ---- matériaux : nom de base dans le SMD, dossiers en $cdmaterials ----
    matmap, dirs = {}, []
    for i, m in enumerate(body.data.materials):
        name = (m.name if m else "default").replace("\\", "/")
        if name.startswith("materials/"):
            name = name[len("materials/"):]
        d, base = (name.rsplit("/", 1) + [""])[:2] if "/" in name else ("", name)
        matmap[i] = base
        if d and d + "/" not in dirs:
            dirs.append(d + "/")

    size = max(ref["max"][i] - ref["min"][i] for i in range(3))
    base_tris = tri_count(body)
    t0 = min(base_tris, 2000)          # LOD0 = original jusqu'à 2000 triangles (aucune perte visible de près)
    name = os.path.splitext(os.path.basename(rel))[0]
    lods = []
    for lod, target in ((0, t0), (1, t0 * 0.5), (2, t0 * 0.2)):
        o = decimated_copy(body, target / base_tris)
        p = os.path.join(OUT, f"{name}_lod{lod}.smd")
        write_smd(o, p, matmap)
        lods.append(tri_count(o))
    d1, d2 = int(max(300, size * 8)), int(max(700, size * 18))
    qc = [f'$modelname "gnl/{name}.mdl"', "$staticprop", '$surfaceprop "metal"']
    qc += [f'$cdmaterials "{d}"' for d in dirs] or ['$cdmaterials ""']
    qc += [f'$body body "{name}_lod0.smd"', f'$sequence idle "{name}_lod0.smd"',
           f"$lod {d1}", "{", f'  replacemodel "{name}_lod0.smd" "{name}_lod1.smd"', "}",
           f"$lod {d2}", "{", f'  replacemodel "{name}_lod0.smd" "{name}_lod2.smd"', "}"]
    open(os.path.join(OUT, f"{name}.qc"), "w", encoding="ascii").write("\n".join(qc) + "\n")
    report.append(f"OK {rel} : {base_tris} -> LOD {lods} (bascule {d1}/{d2}) mats {len(matmap)}")

open(os.path.join(OUT, "lod_report.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
print("\n".join(report))
