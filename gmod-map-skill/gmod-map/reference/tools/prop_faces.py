"""Planche « faces » : chaque modèle vu de face depuis +X (colonne A) et depuis -X (colonne B),
et vu depuis +Y (colonne C). Sert à trouver la vraie face avant (écrans, détails).

blender -b -P tools/prop_faces.py -- <sortie.png> <modèle1> <modèle2> ...
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
OUT, models = argv[0], argv[1:]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
roots = [l.strip() for l in open(os.path.join(ROOT, "tools", "content_paths.txt"), encoding="utf-8")
         if l.strip() and not l.startswith("#")]
roots.append(r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod")
bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils
addon_utils.enable("bl_ext.user_default.plumber", default_set=True)
S = 0.01
ROW = 3.6       # hauteur d'une ligne (360 u)
COL = 7.0       # largeur d'une colonne (700 u)
scene = bpy.context.scene


def load(path, loc, rotz):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.plumber_mdl(filepath=path, import_materials=True, import_animations=False, scale=S)
    for o in [o for o in bpy.data.objects if o not in before]:
        if o.parent is None:
            o.location = loc
            o.rotation_euler = (0, 0, rotz)


for i, mdl in enumerate(models):
    path = next((os.path.join(r, mdl.replace("/", os.sep)) for r in roots
                 if os.path.exists(os.path.join(r, mdl.replace("/", os.sep)))), None)
    z = -i * ROW
    if path:
        # colonne A : tel quel (on voit la face +X) ; B : tourné de 180° (on voit la face -X) ;
        # C : tourné de -90° (on voit la face +Y)
        load(path, (0, 0, z), 0)
        load(path, (0, COL, z), math.pi)
        load(path, (0, 2 * COL, z), -math.pi / 2)
    t = bpy.data.curves.new(f"t{i}", "FONT")
    t.body = f"{i}: {os.path.basename(mdl)[:-4]}" + ("" if path else " [ABSENT]")
    t.size = 0.35
    to = bpy.data.objects.new(f"t{i}", t)
    to.location = (0.5, -2.6, z - 0.5)
    to.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    scene.collection.objects.link(to)
for j, lab in enumerate(["A: face +X", "B: face -X", "C: face +Y"]):
    t = bpy.data.curves.new(f"h{j}", "FONT"); t.body = lab; t.size = 0.5
    to = bpy.data.objects.new(f"h{j}", t); to.location = (0.5, j * COL - 1, 1.2); to.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    scene.collection.objects.link(to)

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.display.shading.show_cavity = True
n = len(models)
scene.render.resolution_x = 1800
scene.render.resolution_y = int(1800 * (n * ROW + 2) / (3 * COL + 2))
world = bpy.data.worlds.new("w"); scene.world = world; world.color = (0.2, 0.21, 0.24)
cam_d = bpy.data.cameras.new("c"); cam_d.type = "ORTHO"
cam = bpy.data.objects.new("c", cam_d); scene.collection.objects.link(cam); scene.camera = cam
cam_d.ortho_scale = 3 * COL + 2
cam_d.sensor_fit = "HORIZONTAL"
cam.location = (60, COL, -(n - 1) * ROW / 2 + 0.8)
cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)     # regarde vers -X
cam_d.clip_end = 200
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("SHEET", OUT)
