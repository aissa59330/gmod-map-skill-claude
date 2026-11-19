"""Droïde B1 de DÉCOR, statique et allégé (Blender) -> sources SMD + QC pour studiomdl.

blender -b -P tools/make_static_droid.py -- <dossier_sortie>
- importe pm_sw_droid_b1 (Plumber), garde le corps, baisse les bras (pose), fige la pose dans le maillage ;
- Decimate : LOD0 ~1500 triangles, LOD1 50 %, LOD2 20 % ;
- deux variantes : « debout » (chaîne de montage) et « couche » (droïde abattu) ;
- écrit droid_<variante>_lod<n>.smd + droid_<variante>.qc ($staticprop, mêmes textures que le pack).
Pour le décor de la map uniquement : les playermodels/PNJ des joueurs ne sont pas touchés.
"""
import math
import os
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index("--") + 1]
os.makedirs(OUT, exist_ok=True)
SRC = r"C:\Users\<UTILISATEUR>\AppData\Local\Temp\gmpublisher\cgi_cis_droid_pack_721821542\models\tfa\comm\gg\pm_sw_droid_b1.mdl"
TARGET = 1500
S = 100.0          # Plumber importe à l'échelle 0.01

bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable("bl_ext.user_default.plumber", default_set=True)
bpy.ops.import_scene.plumber_mdl(filepath=SRC)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("body.smd"))
for o in list(bpy.data.objects):
    if o not in (arm, body):
        bpy.data.objects.remove(o, do_unlink=True)


def extent_xy(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    xs = [(obj.matrix_world @ v.co) for v in m.vertices]
    ev.to_mesh_clear()
    return max(abs(v.x) for v in xs), max(abs(v.y) for v in xs)


# ---- bras baissés : on cherche l'axe local qui rapproche le plus les mains du corps ----
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
for side in ("L", "R"):
    pb = arm.pose.bones[f"ValveBiped.Bip01_{side}_UpperArm"]
    pb.rotation_mode = "XYZ"
    best = None
    for ax in range(3):
        for sg in (1, -1):
            e = [0, 0, 0]
            e[ax] = sg * math.radians(70)
            pb.rotation_euler = e
            bpy.context.view_layer.update()
            ext = extent_xy(body)
            score = max(ext)
            if best is None or score < best[0]:
                best = (score, tuple(e))
    pb.rotation_euler = best[1]
    bpy.context.view_layer.update()
    print("POSE", side, "rotation", [round(math.degrees(a)) for a in best[1]], "envergure", round(best[0] * S, 1))
bpy.ops.object.mode_set(mode="OBJECT")

# ---- fige la pose dans le maillage ----
bpy.context.view_layer.objects.active = body
body.select_set(True)
for m in list(body.modifiers):
    if m.type == "ARMATURE":
        bpy.ops.object.modifier_apply(modifier=m.name)
body.parent = None
body.matrix_world = Matrix.Identity(4) @ body.matrix_world
bpy.data.objects.remove(arm, do_unlink=True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def tri_count(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


base_tris = tri_count(body)
print("TRIS origine", base_tris)


def make_variant(name, lying):
    v = body.copy()
    v.data = body.data.copy()
    bpy.context.collection.objects.link(v)
    if lying:      # couché sur le dos, centré
        v.data.transform(Matrix.Rotation(math.radians(-90), 4, "Y"))
    # pieds / dos à z = 0, centré en x/y
    co = [v.matrix_world @ p.co for p in v.data.vertices]
    mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    v.data.transform(Matrix.Translation(Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))))
    out = []
    for lod, ratio in ((0, TARGET / base_tris), (1, 0.5 * TARGET / base_tris), (2, 0.2 * TARGET / base_tris)):
        o = v.copy()
        o.data = v.data.copy()
        bpy.context.collection.objects.link(o)
        d = o.modifiers.new("dec", "DECIMATE")
        d.ratio = ratio
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="dec")
        bm = bmesh.new()
        bm.from_mesh(o.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.to_mesh(o.data)
        bm.free()
        path = os.path.join(OUT, f"droid_{name}_lod{lod}.smd")
        write_smd(o, path)
        print("LOD", name, lod, tri_count(o), "tris ->", path)
        out.append((tri_count(o), path))
    dims = [round((mx[i] - mn[i]) * S, 1) for i in range(3)]
    return out, dims


def write_smd(o, path):
    me = o.data
    uv = me.uv_layers.active.data
    mats = [m.name.split("/")[-1] for m in me.materials] or ["body"]
    try:
        me.calc_normals_split()
    except Exception:
        pass
    with open(path, "w", encoding="ascii") as f:
        f.write('version 1\nnodes\n0 "root" -1\nend\nskeleton\ntime 0\n0 0 0 0 0 0 0\nend\ntriangles\n')
        for p in me.polygons:
            f.write(mats[p.material_index if p.material_index < len(mats) else 0] + "\n")
            for li in p.loop_indices:
                lp = me.loops[li]
                co = me.vertices[lp.vertex_index].co * S
                n = lp.normal
                u, vv = uv[li].uv
                f.write(f"0 {co.x:.4f} {co.y:.4f} {co.z:.4f} {n.x:.4f} {n.y:.4f} {n.z:.4f} {u:.5f} {vv:.5f}\n")
        f.write("end\n")


for name, lying in (("debout", False), ("couche", True)):
    lods, dims = make_variant(name, lying)
    qc = f'''$modelname "givre_noir/droid_b1_{name}.mdl"
$staticprop
$surfaceprop "metal"
$cdmaterials "models/tfa/sw/droid_b/"
$body body "droid_{name}_lod0.smd"
$sequence idle "droid_{name}_lod0.smd"
$lod 500
{{
  replacemodel "droid_{name}_lod0.smd" "droid_{name}_lod1.smd"
}}
$lod 1100
{{
  replacemodel "droid_{name}_lod0.smd" "droid_{name}_lod2.smd"
}}
'''
    open(os.path.join(OUT, f"droid_{name}.qc"), "w", encoding="ascii").write(qc)
    print("VARIANTE", name, "dims", dims, "tris LOD", [t for t, _ in lods])
