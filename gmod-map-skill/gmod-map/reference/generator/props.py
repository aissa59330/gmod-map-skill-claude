"""Props statiques posés hors des passages : contenu HL2 de base + « Sci-fi Props Megapack »
(Lt_C, Workshop 284266415, élément requis).

Chaque prop : (modèle, (x, y, z), lacet). z = origine du modèle (déjà décalée selon ses bornes).
BOUNDS = bornes lues dans les .mdl (tools : srctools.mdl), servent au validateur.
"""

BOUNDS = {
    "models/props_wasteland/cargo_container01.mdl": ((-66, -192, -61), (66, 195, 68)),
    "models/props_c17/substation_transformer01a.mdl": ((-78, -120, -76), (79, 120, 76)),
    "models/items/ammocrate_smg1.mdl": ((-16, -28, -16), (17, 28, 18)),
    "models/items/ammocrate_ar2.mdl": ((-16, -28, -16), (17, 28, 18)),
    "models/props_wasteland/prison_bedframe001a.mdl": ((-46, -20, -15), (46, 20, 15)),
    "models/props_wasteland/controlroom_storagecloset001a.mdl": ((-17, -25, -44), (18, 25, 44)),
    "models/props_wasteland/controlroom_filecabinet002a.mdl": ((-16, -12, -35), (15, 12, 35)),
    "models/props_combine/combine_intmonitor001.mdl": ((-10, -46, 0), (6, 37, 65)),
    "models/props_lab/reciever01a.mdl": ((-8, -11, -3), (7, 11, 3)),
    "models/props_lab/monitor01a.mdl": ((-14, -13, -13), (14, 12, 14)),
    "models/props_wasteland/rockcliff01b.mdl": ((-52, -41, -87), (52, 41, 87)),
    "models/props_borealis/bluebarrel001.mdl": ((-14, -14, -26), (14, 14, 26)),
    "models/props_c17/oildrum001.mdl": ((-14, -14, 0), (15, 14, 45)),
    # Sci-fi Props Megapack (Lt_C)
    "models/lt_c/sci_fi/bed_bunk.mdl": ((-24, -49, 0), (24, 48, 96)),
    "models/lt_c/sci_fi/ground_locker_small.mdl": ((-1, -10, 0), (30, 10, 54)),
    "models/lt_c/sci_fi/box_crate.mdl": ((-25, -25, 0), (25, 25, 43)),
    "models/lt_c/holo_laptop.mdl": ((-13, -6, 0), (13, 11, 9)),
    "models/lt_c/sci_fi/generator_portable.mdl": ((-12, -14, 0), (12, 14, 24)),
    "models/lt_c/sci_fi/pipe_large_512.mdl": ((-32, -258, -32), (32, 256, 32)),
    "models/lt_c/desk_officer.mdl": ((-20, -53, 0), (20, 53, 60)),
}


def world_box(model, pos, yaw):
    (a, b) = BOUNDS[model]
    x0, y0, z0 = a
    x1, y1, z1 = b
    y = yaw % 360
    if y == 90:
        x0, y0, x1, y1 = -y1, x0, -y0, x1
    elif y == 180:
        x0, y0, x1, y1 = -x1, -y1, -x0, -y0
    elif y == 270:
        x0, y0, x1, y1 = y0, -x1, y1, -x0
    return (pos[0] + x0, pos[1] + y0, pos[2] + z0, pos[0] + x1, pos[1] + y1, pos[2] + z1)


def build(w):
    M = w.meta
    P = []

    def add(model, x, y, zfloor, yaw=0):
        """Pose le modèle sur un sol à zfloor (décale l'origine de -min.z)."""
        zmin = BOUNDS[model][0][2]
        P.append((model, (x, y, zfloor - zmin + 2), yaw))      # +2 : point d'éclairage hors du sol

    C = "models/props_wasteland/cargo_container01.mdl"
    # hangar : conteneurs de ravitaillement contre les murs
    add(C, -8200, 1800, 0); add(C, -8600, -1800, 0); add(C, -5500, -1750, 0)
    # usine : transformateur sous la mezzanine nord
    add("models/props_c17/substation_transformer01a.mdl", 2400, 1416, 0)
    # garnison : caisses de munitions de l'armurerie, une rangée par étage contre les murs
    for (x, y, z, yaw) in [(7100, 1500, 0, 90), (7240, 1500, 0, 90), (7880, -1500, 384, 90), (8020, -1500, 384, 90),
                           (5820, 1500, 768, 90), (5960, 1500, 768, 90)]:
        add("models/lt_c/sci_fi/box_crate.mdl", x, y, z, yaw)
    add("models/lt_c/desk_officer.mdl", 6400, 1470, 768, 90)          # poste de l'officier (étage 2)
    add("models/lt_c/holo_laptop.mdl", 6400, 1470, 768 + 60, 0)
    # usine : générateurs portables sur les socles des générateurs, tuyaux au plafond
    for (gx, gy) in M["generators"]:
        add("models/lt_c/sci_fi/generator_portable.mdl", gx + 76, gy - 76, 0, 0)     # au sol, à côté du pupitre
    for k in range(6):
        for y in (-700, 700):
            P.append(("models/lt_c/sci_fi/pipe_large_512.mdl", (256 + 512 * k, y, 712), 90))
    # centre de données : écrans sur le pupitre du terminal central, équipements sur les baies
    OX, OZ = 5120, 768
    for (lx, ly, lyaw) in ((6596 + OX, 64, 180), (6716 + OX, -64, 0)):
        w.block((lx - 20, ly - 16, OZ, lx + 20, ly + 16, OZ + 48), "lordtrilobite/isd_metal06")   # petit bureau sous l'écran
        add("models/lt_c/holo_laptop.mdl", lx, ly, OZ + 48, lyaw)
    # (rien sur le dessus des baies serveurs : illogique)
    # prison : un lit dans chaque cellule
    for s in w.spaces:
        if s.name.startswith("cell_") and not s.name.endswith("_d"):
            x0, y0, z0, x1, y1, z1 = s.box
            if s.name.startswith("cell_e"):
                add("models/lt_c/sci_fi/bed_bunk.mdl", x1 - 32, (y0 + y1) / 2, z0, 0)
            else:
                add("models/lt_c/sci_fi/bed_bunk.mdl", (x0 + x1) / 2, y0 + 32, z0, 90)
    # salles de spawn défenseurs : casiers contre les deux murs latéraux (hors de la grille de spawn)
    for s in w.spaces:
        if s.name.startswith("closet_") and "_link" not in s.name:
            x0, y0, z0, x1, y1, z1 = s.box
            links = [l.box for l in w.spaces if l.name.startswith(s.name + "_link")]
            west_used = any(l[3] == x0 for l in links)      # le couloir arrive par ce mur : on le laisse libre
            east_used = any(l[0] == x1 for l in links)
            cy = (y0 + y1) / 2
            for dy in (-120, -60, 0, 60, 120):
                if not west_used:
                    add("models/lt_c/sci_fi/ground_locker_small.mdl", x0 + 2, cy + dy, z0, 0)
                if not east_used:
                    add("models/lt_c/sci_fi/ground_locker_small.mdl", x1 - 2, cy + dy, z0, 180)
    # glacier : conteneur de ravitaillement et fûts près de la plateforme
    z4 = M["zones"]["11"][2]
    add(C, -11600, -6800, z4)
    for (x, y) in [(-11470, -6560), (-11530, -6500), (-11700, -6540)]:     # caisses (les fûts HL2 ne peuvent pas être statiques)
        add("models/lt_c/sci_fi/box_crate.mdl", x, y, z4)
    # canyon : éboulis contre les parois
    for (x, y) in [(-13000, 1300), (-12100, -1300), (-11000, 1300), (-10000, -1300)]:
        add("models/props_wasteland/rockcliff01b.mdl", x, y, 0)

    M["props"] = P
    for (model, pos, yaw) in P:
        w.ent("prop_static", pos, model=model, angles=f"0 {yaw} 0", solid=6, skin=0, fademindist=-1, fadescale=1)
    return P
