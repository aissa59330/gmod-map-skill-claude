"""Panneaux de la map (textures maison, intégrées au .bsp par compile.ps1 via bspzip).

python tools/make_signs.py  ->  compile_game/materials/givre_noir/*.vtf + .vmt  et  compile_game/pack_list.txt
Aucun addon : les textures voyagent dans le .bsp.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont
from srctools.vtf import VTF, ImageFormats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "compile_game", "materials", "givre_noir")
os.makedirs(OUT, exist_ok=True)
FB = "C:/Windows/Fonts/arialbd.ttf"
FR = "C:/Windows/Fonts/arial.ttf"

BG = (34, 40, 52)         # gris-bleu République
LINE = (196, 208, 224)
RED = (220, 60, 50)
GREEN = (70, 210, 110)
BLUE = (110, 170, 255)


def font(path, size):
    return ImageFont.truetype(path, size)


def frame(d, w, h, col=LINE, t=6):
    d.rectangle((t, t, w - t - 1, h - t - 1), outline=col, width=t)


def tuto_piratage():
    w, h = 1024, 512
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    frame(d, w, h)
    d.rectangle((6, 6, w - 7, 78), fill=(60, 90, 150))
    d.text((w // 2, 42), "PIRATAGE DU CENTRE DE DONNÉES", font=font(FB, 44), fill="white", anchor="mm")
    steps = [
        ("1", "TERMINAL 1 : au centre de cette salle.", "Appuyez sur [E] sur le bouton ROUGE."),
        ("2", "Défendez 100 secondes.", "Le bouton du terminal suivant s'allume en ROUGE."),
        ("3", "TERMINAL 2 : plateforme NORD (en haut des rampes).", "[E] puis défendez 100 s."),
        ("4", "TERMINAL 3 : zone SUD, au sol.", "[E] puis défendez 100 s : les portes s'ouvrent."),
    ]
    y = 100
    for num, a, b in steps:
        d.ellipse((30, y, 92, y + 62), fill=(60, 90, 150), outline=LINE, width=3)
        d.text((61, y + 31), num, font=font(FB, 40), fill="white", anchor="mm")
        d.text((112, y + 4), a, font=font(FB, 30), fill="white")
        d.text((112, y + 38), b, font=font(FR, 26), fill=LINE)
        y += 86
    # légende des voyants
    d.ellipse((40, 452, 70, 482), fill=RED)
    d.text((80, 467), "prêt", font=font(FB, 26), fill="white", anchor="lm")
    d.ellipse((190, 452, 220, 482), fill=GREEN)
    d.text((230, 467), "fait", font=font(FB, 26), fill="white", anchor="lm")
    d.text((340, 467), "Éteint = verrouillé.  SENTINELLE ferme des portes au hasard !", font=font(FR, 24), fill=LINE, anchor="lm")
    return im


def terminal(n):
    w = h = 256
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    frame(d, w, h, BLUE, 5)
    d.text((w // 2, 40), "TERMINAL", font=font(FB, 34), fill=LINE, anchor="mm")
    d.text((w // 2, 128), str(n), font=font(FB, 120), fill="white", anchor="mm")
    d.text((w // 2, 214), "[E] bouton rouge", font=font(FB, 26), fill=RED, anchor="mm")
    return im


def trefoil(d, cx, cy, r, col, bg):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    for k in range(3):
        a0 = -90 + 120 * k + 30
        d.pieslice((cx - r, cy - r, cx + r, cy + r), a0, a0 + 60, fill=bg)
    rr = r * 0.22
    d.ellipse((cx - rr * 1.45, cy - rr * 1.45, cx + rr * 1.45, cy + rr * 1.45), fill=bg)
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)


def danger_reacteur():
    w = h = 512
    yel, blk = (238, 196, 40), (22, 22, 24)
    im = Image.new("RGB", (w, h), yel)
    d = ImageDraw.Draw(im)
    d.rectangle((10, 10, w - 11, h - 11), outline=blk, width=14)
    trefoil(d, w // 2, 210, 150, blk, yel)
    d.text((w // 2, 400), "DANGER", font=font(FB, 70), fill=blk, anchor="mm")
    d.text((w // 2, 462), "RADIATIONS - RÉACTEUR", font=font(FB, 34), fill=blk, anchor="mm")
    return im


def save(name, im, selfillum=True):
    v = VTF(im.width, im.height, fmt=ImageFormats.DXT1)
    v.get().copy_from(im.convert("RGB").tobytes(), ImageFormats.RGB888)
    v.compute_mipmaps()
    with open(os.path.join(OUT, name + ".vtf"), "wb") as f:
        v.save(f)
    # LightmappedGeneric : reçoit l'éclairage de la salle ; $selfillum léger via $selfillumtint pour rester lisible
    vmt = ('"LightmappedGeneric"\n{\n\t"$basetexture" "givre_noir/%s"\n\t"$surfaceprop" "metal"\n' % name
           + ('\t"$selfillum" "1"\n\t"$selfillumtint" "[0.55 0.55 0.55]"\n' if selfillum else "") + "}\n")
    with open(os.path.join(OUT, name + ".vmt"), "w", encoding="ascii") as f:
        f.write(vmt)
    return name


def panel(w, h, title, lines, accent=(220, 60, 50)):
    """Panneau de mini-jeu : titre sur bandeau coloré + lignes en gros caractères (lisible sur un petit boîtier)."""
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    frame(d, w, h, accent, 8)
    band = int(h * (0.24 if h <= w else 0.16))
    d.rectangle((8, 8, w - 9, band), fill=accent)
    ft = font(FB, int(band * 0.5))
    while d.textlength(title, font=ft) > w - 40 and ft.size > 12:
        ft = font(FB, ft.size - 2)
    d.text((w // 2, band // 2 + 4), title, font=ft, fill="white", anchor="mm")
    avail = h - band - 24
    size = int(min(avail / (len(lines) * 1.35), w / (11 if w >= h else 6.5)))
    fl = font(FB, size)
    for ln in lines:
        while d.textlength(ln, font=fl) > w - 36 and fl.size > 10:
            fl = font(FB, fl.size - 2)
    y = band + 16 + (avail - len(lines) * fl.size * 1.35) / 2
    for ln in lines:
        d.text((w // 2, y + fl.size * 0.6), ln, font=fl, fill=LINE if not ln.startswith("[") else (255, 210, 120), anchor="mm")
        y += fl.size * 1.35
    return im


MINI = {
    "mj_bouclier": (256, 512, "BOUCLIER", ["Protège les", "3 tourelles AA", "DÉTRUISEZ", "les 2 générateurs"], (60, 120, 220)),
    "mj_generateur": (512, 256, "GÉNÉRATEUR", ["Abaissez les 3 coupe-circuits", "Explosion 6 s plus tard"], RED),
    "mj_chaine": (512, 512, "CHAÎNE", ["DE DROÏDES", "[E] arrêter", "ou relancer"], (200, 120, 40)),
    "mj_armurerie": (512, 256, "VERROU D'ARMURERIE", ["Les 3 consoles (1 par étage)", "à moins de 10 s d'écart"], (60, 120, 220)),
    "mj_disjoncteur": (512, 512, "DISJONCTEUR", ["Coupure pendant", "le piratage :", "[E] pour réarmer"], (220, 160, 40)),
    "mj_champ": (512, 256, "CHAMP DE FORCE", ["Détruisez les 3 batteries", "au sol pour le couper"], RED),
    "mj_champ_batterie": (256, 512, "BATTERIE", ["du champ", "de force", "À DÉTRUIRE"], RED),
    "mj_charge": (512, 512, "CHARGE", ["Gauche : [E] 8 s", "= ARMER", "Droite : [E] 4 s", "= DÉSAMORCER"], RED),
    "mj_reacteur": (512, 512, "VANNE", ["[E] maintenu 5 s", "Les 3 vannes", "en moins de 45 s"], (40, 170, 200)),
}
names = [save("tuto_piratage", tuto_piratage()), save("danger_reacteur", danger_reacteur())]
names += [save(k, panel(*v)) for k, v in MINI.items()]
names += [save(f"terminal_{n}", terminal(n)) for n in (1, 2, 3)]
with open(os.path.join(ROOT, "compile_game", "pack_list.txt"), "w", encoding="ascii") as f:
    for n in names:
        for ext in ("vtf", "vmt"):
            f.write(f"materials/givre_noir/{n}.{ext}\n{os.path.join(OUT, n + '.' + ext)}\n")
# aperçu pour vérification
prev = Image.new("RGB", (1024, 512 + 512), (20, 20, 20))
prev.paste(tuto_piratage(), (0, 0))
prev.paste(danger_reacteur().resize((384, 384)), (0, 560))
for i in (1, 2, 3):
    prev.paste(terminal(i), (400 + (i - 1) * 205, 600))
prev.save(os.path.join(ROOT, "shots", "panneaux_apercu.png"))
mini = Image.new("RGB", (4 * 520, 2 * 520 + 10), (20, 20, 20))
for k, (name, v) in enumerate(MINI.items()):
    im = panel(*v)
    im.thumbnail((512, 512))
    mini.paste(im, ((k % 4) * 520, (k // 4) * 520))
mini.save(os.path.join(ROOT, "shots", "panneaux_minijeux.png"))
print("PANNEAUX", names)
