"""Planche de vérification des props (Blender + Plumber).

blender -b -P tools/prop_sheet.py -- <sortie.png> <page> <modèle1> <modèle2> ...
Chaque modèle est posé dans une case avec : flèche rouge = +X local, flèche verte = +Y local,
sol gris à z=0 (pied du modèle), nom en dessous. Vue en 3/4 depuis +X +Y.
Les dossiers de contenu sont lus dans tools/content_paths.txt.
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
roots.append(os.path.join(ROOT, "compile_game"))   # modèles maison (décor statique)

bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils
addon_utils.enable("bl_ext.user_default.plumber", default_set=True)
S = 0.01
CELL = 4.0          # 400 unités Hammer par case
COLS = 5
scene = bpy.context.scene


def mat(name, rgb, emit=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    return m


red, green, grey = mat("r", (1, 0.1, 0.1)), mat("g", (0.1, 0.9, 0.1)), mat("s", (0.35, 0.35, 0.38))

for i, mdl in enumerate(models):
    cx, cy = (i % COLS) * CELL, -(i // COLS) * CELL
    path = None
    for r in roots:
        p = os.path.join(r, mdl.replace("/", os.sep))
        if os.path.exists(p):
            path = p
            break
    before = set(bpy.data.objects)
    if path:
        try:
            bpy.ops.import_scene.plumber_mdl(filepath=path, import_materials=True, import_animations=False, scale=S)
        except Exception as e:
            print("ERR", mdl, e)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location = (cx, cy, 0)
    # sol + flèches
    bpy.ops.mesh.primitive_plane_add(size=CELL * 0.9, location=(cx, cy, -0.005))
    bpy.context.object.data.materials.append(grey)
    for (d, m) in (((1, 0, 0), red), ((0, 1, 0), green)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.6, location=(cx + d[0] * 0.8, cy + d[1] * 0.8, 0.02),
                                            rotation=(0, math.pi / 2, 0) if d[0] else (math.pi / 2, 0, 0))
        bpy.context.object.data.materials.append(m)
    t = bpy.data.curves.new(f"t{i}", "FONT")
    t.body = f"{i}: " + os.path.basename(mdl).replace(".mdl", "") + ("" if path else "  [ABSENT]")
    t.size = 0.22
    to = bpy.data.objects.new(f"t{i}", t)
    to.location = (cx - CELL * 0.45, cy - CELL * 0.47, 0.01)
    scene.collection.objects.link(to)

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
rows = (len(models) + COLS - 1) // COLS
scene.render.resolution_x, scene.render.resolution_y = 2000, max(500, 420 * rows)
world = bpy.data.worlds.new("w"); scene.world = world; world.color = (0.12, 0.13, 0.15)
cam_d = bpy.data.cameras.new("c"); cam_d.type = "ORTHO"
cam = bpy.data.objects.new("c", cam_d); scene.collection.objects.link(cam); scene.camera = cam
w_ = COLS * CELL
h_ = rows * CELL
cam_d.ortho_scale = max(w_, h_ * 2000 / scene.render.resolution_y) * 1.05
center = Vector(((COLS - 1) * CELL / 2, -(rows - 1) * CELL / 2, 0))
cam.location = center + Vector((40, 40, 40))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_d.clip_end = 500
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("SHEET", OUT)
