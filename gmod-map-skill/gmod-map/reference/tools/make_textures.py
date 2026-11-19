"""Textures allégées (embarquées dans le .bsp par compile.ps1).

python tools/make_textures.py
- façade du hangar : isd_exteriorgreebles 2048 DXT5 (5,3 Mo) -> givre_noir/ext_facade 1024 DXT5 (1,3 Mo),
  posée à l'échelle 0.5 au lieu de 0.25 (même taille au mur ; la façade se voit de loin).
Les panneaux maison sont déjà en DXT1 (tools/make_signs.py).
"""
import os

from PIL import Image
from srctools.vtf import VTF, ImageFormats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = r"C:\Users\<UTILISATEUR>\AppData\Local\Temp\gmpublisher\star_wars_imperial_materials_1206775008\materials\lordtrilobite"
OUT = os.path.join(ROOT, "compile_game", "materials", "givre_noir")
os.makedirs(OUT, exist_ok=True)


def downscale(src_vtf, dst_name, size, fmt):
    with open(src_vtf, "rb") as f:
        v = VTF.read(f)
        im = v.get().to_PIL().convert("RGBA")
    im = im.resize((size, size), Image.LANCZOS)
    o = VTF(size, size, fmt=fmt)
    o.get().copy_from(im.tobytes(), ImageFormats.RGBA8888)
    o.compute_mipmaps()
    with open(os.path.join(OUT, dst_name + ".vtf"), "wb") as f:
        o.save(f)
    return os.path.getsize(os.path.join(OUT, dst_name + ".vtf"))


n = downscale(os.path.join(SRC, "isd_exteriorgreebles.vtf"), "ext_facade", 1024, ImageFormats.DXT5)
vmt = open(os.path.join(SRC, "isd_exteriorgreebles.vmt"), encoding="utf-8", errors="ignore").read()
vmt = vmt.replace('"lordtrilobite/isd_exteriorgreebles"', '"givre_noir/ext_facade"')
open(os.path.join(OUT, "ext_facade.vmt"), "w", encoding="ascii", errors="ignore").write(vmt)
print("ext_facade.vtf", n // 1024, "Ko")
