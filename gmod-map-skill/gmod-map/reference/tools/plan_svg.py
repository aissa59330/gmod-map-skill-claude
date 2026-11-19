"""Plan schématique (vue de dessus) de givre_noir en SVG, depuis maps_src/givre_noir.json.

python tools/plan_svg.py shots/iter_N/plan.svg
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
side = json.load(open(os.path.join(ROOT, "maps_src", "givre_noir.json"), encoding="utf-8"))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "shots", "plan.svg")

NAMES = {"1": "1 Canyon", "2": "2 Hangar (AA)", "3a": "3a Conduits", "3b": "3b Porte principale",
         "4": "4 Usine", "5": "5 Garnison (3 étages)", "6": "6 Centre de données", "7": "7 Bloc de détention",
         "8": "8 Tour de comm.", "9": "9 Noyau", "10": "10 Exfiltration", "11": "11 Glacier / LAAT"}
COL = {"1": "#7fa7c9", "2": "#5d8fb8", "3a": "#c9a35f", "3b": "#d08a4e", "4": "#b5656b", "5": "#9b6fb3",
       "6": "#4fa3a0", "7": "#c26f9b", "8": "#6c8fd6", "9": "#d65f4f", "10": "#e09a3c", "11": "#a9d3ee"}
TRANS = "#8a8f99"

xs = [s["box"][0] for s in side["spaces"]] + [s["box"][3] for s in side["spaces"]]
ys = [s["box"][1] for s in side["spaces"]] + [s["box"][4] for s in side["spaces"]]
X0, X1, Y0, Y1 = min(xs) - 600, max(xs) + 600, min(ys) - 1700, max(ys) + 600
SC = 1600 / (X1 - X0)
W, H = 1600, (Y1 - Y0) * SC


def tx(x): return (x - X0) * SC
def ty(y): return (Y1 - y) * SC


parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}" '
         f'font-family="Segoe UI, Arial" font-size="13">',
         f'<rect width="100%" height="100%" fill="#14181f"/>']
# grille 1024
for gx in range(-16384, 16385, 1024):
    if X0 <= gx <= X1:
        parts.append(f'<line x1="{tx(gx):.1f}" y1="0" x2="{tx(gx):.1f}" y2="{H:.0f}" stroke="#1d232c"/>')
for gy in range(-16384, 16385, 1024):
    if Y0 <= gy <= Y1:
        parts.append(f'<line x1="0" y1="{ty(gy):.1f}" x2="{W}" y2="{ty(gy):.1f}" stroke="#1d232c"/>')
# espaces, triés par altitude (les plus hauts dessus)
for s in sorted(side["spaces"], key=lambda s: s["box"][2]):
    x0, y0, z0, x1, y1, z1 = s["box"]
    c = COL.get(s["zone"], TRANS)
    op = 0.55 if s["zone"] in COL else 0.8
    if "closet" in s["name"]:
        c, op = "#555c66", 0.9
    parts.append(f'<rect x="{tx(x0):.1f}" y="{ty(y1):.1f}" width="{(x1 - x0) * SC:.1f}" height="{(y1 - y0) * SC:.1f}" '
                 f'fill="{c}" fill-opacity="{op}" stroke="#0b0e12" stroke-width="0.6"/>')
# étiquettes de zones
for z, b in side["zones"].items():
    x0, y0, z0, x1, y1, z1 = b
    cx, cy = tx((x0 + x1) / 2), ty((y0 + y1) / 2)
    alt = f"sol {z0:+d}" if z0 else "sol 0"
    if z == "9":
        alt = "anneau +2304 (fosse +1280)"
    if z == "10":
        alt = "puits +2304 -> +6912"
    if z == "8":
        alt = "sol +768, niveaux +1280/+1792/+2304"
    if z == "5":
        alt = "sol 0, étages +384/+768"
    parts.append(f'<text x="{cx:.0f}" y="{cy:.0f}" text-anchor="middle" fill="#fff" font-weight="700" '
                 f'stroke="#000" stroke-width="3" paint-order="stroke">{NAMES.get(z, z)}</text>')
    parts.append(f'<text x="{cx:.0f}" y="{cy + 15:.0f}" text-anchor="middle" fill="#dde" font-size="11" '
                 f'stroke="#000" stroke-width="3" paint-order="stroke">{alt}</text>')
# spawns
for (x, y, z) in side["player_starts"][::4]:
    parts.append(f'<circle cx="{tx(x):.1f}" cy="{ty(y):.1f}" r="1.6" fill="#3cf"/>')
for z, pts in side["def_spawns"].items():
    for (x, y, zz) in pts[::4]:
        parts.append(f'<circle cx="{tx(x):.1f}" cy="{ty(y):.1f}" r="1.6" fill="#f44"/>')
for n, pts in side["atk_respawns"].items():
    x, y, zz = pts[0]
    parts.append(f'<circle cx="{tx(x):.1f}" cy="{ty(y):.1f}" r="4" fill="none" stroke="#3cf" stroke-width="2"/>'
                 f'<text x="{tx(x) + 6:.0f}" y="{ty(y) - 5:.0f}" fill="#3cf" font-size="10">R{n}</text>')
# légende
ly = H - 70
parts.append(f'<text x="16" y="{ly:.0f}" fill="#fff" font-size="15" font-weight="700">Opération Givre Noir — plan (vue de dessus, grille 1024 u)</text>')
parts.append(f'<text x="16" y="{ly + 22:.0f}" fill="#bbb" font-size="12">Gris : transitions (3 voies) · Gris foncé : placards défenseurs · '
             f'Points bleus : spawns attaquants · Rouges : défenseurs · Rn : respawn de la phase n · '
             f'Les zones 9-11 sont superposées en hauteur (noyau z 2304, puits jusqu\'à 6912, glacier tout en haut, z 6912)</text>')
parts.append("</svg>")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write("\n".join(parts))
print("plan :", out)
