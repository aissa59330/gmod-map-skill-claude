"""Rendus de contrôle de givre_noir via Plumber (Blender en ligne de commande).

blender -b -P tools/preview_blender.py -- maps_src/givre_noir.vmf shots/iter_N/blender/
Opérateur d'import Plumber : bpy.ops.import_scene.plumber_vmf
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
VMF_PATH = os.path.abspath(argv[0])
OUT = os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)
SIDE = json.load(open(os.path.splitext(VMF_PATH)[0] + ".json", encoding="utf-8"))
S = 0.01  # échelle Plumber (unités Hammer -> mètres)

bpy.ops.wm.read_factory_settings(use_empty=True)
# Plumber refuse le bloc `editor` au niveau du world : copie nettoyée
import re, tempfile
_txt = open(VMF_PATH, encoding="utf-8").read()
_txt = re.sub(r'\n\teditor\n\t\{\n\t\t"color" "[^"]*"\n\t\}\n', '\n', _txt)
_tmp = os.path.join(tempfile.gettempdir(), "givre_noir_preview.vmf")
open(_tmp, "w", encoding="utf-8").write(_txt)
VMF_PATH = _tmp
ops = [o for o in dir(bpy.ops.import_scene) if "plumber" in o]
print("PLUMBER OPS:", ops)
if "bl_ext.user_default.plumber" not in bpy.context.preferences.addons:
    import addon_utils
    addon_utils.enable("bl_ext.user_default.plumber", default_set=True)
bpy.ops.import_scene.plumber_vmf(filepath=VMF_PATH, import_materials=False, import_props=False,
                                 import_lights=False, import_sky=False, import_sky_camera=False,
                                 import_overlays=False, invisible_solids="SKIP", scale=S)
objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print("IMPORTED MESHES:", len(objs))


def bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
            max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))


BB = {o.name: bbox(o) for o in objs}
# plafonds = dalles posées exactement sur le haut d'un volume d'air
tops = [(s["box"][0] * S, s["box"][1] * S, s["box"][5] * S, s["box"][3] * S, s["box"][4] * S) for s in SIDE["spaces"]]
ceilings = set()
for o in objs:
    b = BB[o.name]
    if b[5] - b[2] > 0.17:
        continue
    for (x0, y0, zt, x1, y1) in tops:
        if abs(b[2] - zt) < 0.02 and b[0] < x1 and x0 < b[3] and b[1] < y1 and y0 < b[4]:
            ceilings.add(o.name)
            break
print("CEILINGS:", len(ceilings))

# matériaux de couleur par hauteur (lisibilité)
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    return m

def color_for(o):
    b = BB[o.name]
    if o.name in ceilings:
        return (0.8, 0.8, 0.85)
    zt = b[5] / S
    ent = o.name.lower()
    if "door" in ent or "func_door" in ent:
        return (0.9, 0.25, 0.2)
    if b[5] - b[2] <= 0.17 and (b[3] - b[0]) * (b[4] - b[1]) > 4:      # sols / dalles
        return (0.55, 0.58, 0.62)
    if zt <= 80:
        return (0.95, 0.75, 0.25)     # couverts bas
    if zt <= 300:
        return (0.35, 0.65, 0.9)
    return (0.45, 0.48, 0.55)

cache = {}
for o in objs:
    c = color_for(o)
    if c not in cache:
        cache[c] = mat(f"c{len(cache)}", c)
    o.data.materials.clear()
    o.data.materials.append(cache[c])
    o.color = (*c, 1)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.show_object_outline = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.film_transparent = False
world = bpy.data.worlds.new("w"); scene.world = world
world.color = (0.08, 0.09, 0.11)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

# étiquettes de zones
labels = []
for z, b in SIDE["zones"].items():
    t = bpy.data.curves.new(f"lbl{z}", "FONT"); t.body = z; t.size = 6.0; t.extrude = 0.2
    to = bpy.data.objects.new(f"lbl{z}", t)
    to.location = ((b[0] + b[3]) / 2 * S, (b[1] + b[4]) / 2 * S, (b[2] + 200) * S)
    to.color = (1, 0.1, 0.6, 1)
    scene.collection.objects.link(to); labels.append((to, b))


def set_visible(pred):
    for o in objs:
        h = not pred(o)
        o.hide_render = h


def render(name):
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("RENDER", scene.render.filepath)


# 1) vues de dessus orthographiques par tranche de hauteur (plafonds masqués)
cam_data.type = "ORTHO"
xs = [s["box"][0] for s in SIDE["spaces"]] + [s["box"][3] for s in SIDE["spaces"]]
ys = [s["box"][1] for s in SIDE["spaces"]] + [s["box"][4] for s in SIDE["spaces"]]
cx, cy = (min(xs) + max(xs)) / 2 * S, (min(ys) + max(ys)) / 2 * S
cam_data.ortho_scale = (max(xs) - min(xs)) * S * 1.04
cam.location = (cx, cy, 300)
cam.rotation_euler = (0, 0, 0)
cam_data.clip_end = 2000
BANDS = [("top_1_sol", -1100, 700), ("top_2_niveau_768", 700, 2250), ("top_3_hauts", 2250, 9000)]
for name, lo, hi in BANDS:
    for to, b in labels:
        to.hide_render = not (lo <= b[2] < hi)
    set_visible(lambda o, lo=lo, hi=hi: o.name not in ceilings and lo * S <= BB[o.name][2] < hi * S)
    render(name)

# 3) une vue par zone : perspective plongeante, plafonds masqués
cam_data.type = "PERSP"
cam_data.lens = 24
for to, _ in labels:
    to.hide_render = True
for z, b in SIDE["zones"].items():
    x0, y0, z0, x1, y1, z1 = [v * S for v in b]
    zc = (z0 + z1) / 2
    span = max(x1 - x0, y1 - y0)
    target = Vector(((x0 + x1) / 2, (y0 + y1) / 2, z0))
    cam.location = target + Vector((-span * 0.55, -span * 0.75, span * 0.85))
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    lo, hi = z0 - 1.2, z1 + 0.2
    def vis(o, lo=lo, hi=hi, x0=x0, y0=y0, x1=x1, y1=y1, z1=z1):
        b = BB[o.name]
        if o.name in ceilings or b[5] <= lo or b[2] >= hi:
            return False
        if b[3] <= x0 + 0.17 or b[4] <= y0 + 0.17:       # murs côté caméra
            return False
        if b[0] > x1 + 2 or b[1] > y1 + 2 or b[3] < x0 - 2 or b[4] < y0 - 2:
            return False
        return not (b[5] - b[2] > 0.17 and b[2] >= z1 - 0.2)
    set_visible(vis)
    render(f"zone_{z}")
print("DONE")
