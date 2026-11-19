"""Nuancier : convertit des textures (.vmt -> $basetexture .vtf) en vignettes PNG sur une planche.

python tools/texture_sheet.py <sortie.png> <dossier_materials> [filtre]
"""
import os
import re
import sys

from PIL import Image, ImageDraw
from srctools.vtf import VTF

out, root = sys.argv[1], sys.argv[2]
flt = sys.argv[3] if len(sys.argv) > 3 else ""
items = []
for dp, _, files in os.walk(root):
    for f in sorted(files):
        if f.endswith(".vmt") and flt in f:
            txt = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            m = re.search(r'"?\$basetexture"?\s+"?([^"\s]+)"?', txt, re.I)
            if not m:
                continue
            vtf = os.path.join(os.path.dirname(root.rstrip("/\\")), "materials", m.group(1).replace("/", os.sep) + ".vtf")
            if not os.path.exists(vtf):
                vtf = os.path.join(root, m.group(1).split("/", 1)[-1].replace("/", os.sep) + ".vtf")
            if os.path.exists(vtf):
                items.append((os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")[:-4], vtf))
T, PAD, COLS = 160, 24, 8
rows = (len(items) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * T, rows * (T + PAD)), (30, 32, 36))
d = ImageDraw.Draw(sheet)
for i, (name, path) in enumerate(items):
    try:
        with open(path, "rb") as fh:
            v = VTF.read(fh)
            img = v.get().to_PIL().convert("RGB").resize((T - 4, T - 4))
        sheet.paste(img, ((i % COLS) * T + 2, (i // COLS) * (T + PAD) + 2))
    except Exception as e:
        d.text(((i % COLS) * T + 4, (i // COLS) * (T + PAD) + 60), "ERR", fill=(255, 80, 80))
    d.text(((i % COLS) * T + 2, (i // COLS) * (T + PAD) + T), name[-26:], fill=(220, 220, 220))
sheet.save(out)
print("SHEET", out, len(items))
