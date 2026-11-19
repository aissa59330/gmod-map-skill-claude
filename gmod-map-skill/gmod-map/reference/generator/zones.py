"""Tracé des 11 zones de « Opération Givre Noir » (event ~70 min). Tracé original.

Aile nord (y ~ 0, vers +x) : canyon -> hangar -> conduits / porte -> usine -> garnison (3 étages)
-> centre de données (z 768). Le parcours tourne vers le sud : bloc de détention, puis l'aile
sud repart vers l'ouest : tour de communication -> noyau (z 2304) -> 3 puits d'exfiltration qui
montent jusqu'au glacier (z 6912), au-dessus du canyon.
"""
from geom import (World, Block, box_sub, ramp, slope_slab, frustum, oct_prism, add_chamfers, MAT_TRIGGER, MAT_FLOOR, MAT_WALL, MAT_CEIL, MAT_ICE,
                  MAT_ROCK, MAT_METAL, MAT_GRATE, MAT_CRATE, MAT_HAZARD, MAT_RAIL, MAT_COMPUTER)

ICE_LIGHT = "120 170 255 180"
WARM = "255 236 210 520"


def corridor(w, name, zone, pts, width, height, z0=0, **kw):
    """Couloir polyligne (segments alignés). Les jonctions sont prolongées de width/2."""
    h = width // 2
    out = []
    for i in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        ea = h if i > 0 else 0
        eb = h if i < len(pts) - 2 else 0
        if ay == by:
            x0, x1 = (ax - ea, bx + eb) if bx > ax else (bx - eb, ax + ea)
            box = (x0, ay - h, z0, x1, ay + h, z0 + height)
        else:
            assert ax == bx, "segments alignés seulement"
            y0, y1 = (ay - ea, by + eb) if by > ay else (by - eb, ay + ea)
            box = (ax - h, y0, z0, ax + h, y1, z0 + height)
        out.append(w.space(f"{name}_{i}", zone, box, light_step=512, **kw))
    return out


def rail(w, box, mat=MAT_RAIL):
    w.block(box, mat, "detail")


def crate(w, x, y, z=0, s=64, h=64, mat=MAT_CRATE):
    box = (x - s // 2, y - s // 2, z, x + s // 2, y + s // 2, z + h)
    if mat in (MAT_ROCK, MAT_ICE):          # rocher / bloc de glace irrégulier
        w.add(frustum(box, (s * 0.3, s * 0.2), mat))
    else:                                   # caisse aux arêtes biseautées
        w.add(frustum(box, 8, mat))


def muret(w, x0, y0, x1, y1, z=0, h=56):
    w.add(frustum((x0, y0, z, x1, y1, z + h), 10, MAT_CEIL))


def rock(w, box, rnd=None, mat=MAT_ROCK):
    """Rocher : tronc de pyramide aux pentes irrégulières (au lieu d'un cube)."""
    x0, y0, z0, x1, y1, z1 = box
    k = (rnd.uniform(0.18, 0.35) if rnd else 0.25)
    w.add(frustum(box, ((x1 - x0) * k, (y1 - y0) * k), mat))


def slab_with_holes(w, box, holes, mat=MAT_METAL, kind="detail", top=MAT_GRATE):
    """Dalle horizontale percée de trémies (rampes qui la traversent)."""
    pieces = [box]
    for h in holes:
        pieces = [q for p in pieces for q in box_sub(p, h)]
    for p in pieces:
        w.block(p, mat, kind, top)


def spawn_grid(cx, cy, z, n=16, cols=4, step=96):
    pts = []
    rows = (n + cols - 1) // cols
    for i in range(n):
        r, c = divmod(i, cols)
        pts.append((cx + (c - (cols - 1) / 2) * step, cy + (r - (rows - 1) / 2) * step, z))
    return pts


def closet(w, zone, room, conn, spawn_z=None):
    """Salle de spawn défenseurs + couloir de liaison ; 16 points."""
    w.space(f"closet_{zone}", zone, room, light="255 200 160 300", light_step=512)
    w.space(f"closet_{zone}_link", zone, conn, light=None)
    x0, y0, z0, x1, y1, z1 = room
    w.meta["def_spawns"][zone] = spawn_grid((x0 + x1) / 2, (y0 + y1) / 2, z0 + 4)


def build(w: World):
    w.meta = {"def_spawns": {}, "atk_respawns": {}, "player_starts": [], "tour": [], "zones": {},
              "doors": [], "lights": []}
    M = w.meta

    # =============== ZONE 1 : canyon d'insertion (extérieur, brouillard) ===============
    # vaste vallée : 6900 x 8192, ciel à +6144 => combat aérien possible, longue approche à pied
    CX0, CY, CH = -16128, 4096, 6144
    w.space("canyon", "1", (CX0, -CY, 0, -9216, CY, CH), sky=True,
            floor=MAT_ICE, wall=MAT_ROCK, light=None)
    M["zones"]["1"] = (CX0, -CY, 0, -9216, CY, CH)
    # ---- secteur 1A (nord) : zone d'atterrissage, reliée au canyon (secteur 1B) par un col ----
    NX0, NY0, NX1, NY1 = -16128, 4608, -9472, 12544
    w.space("canyon_nord", "1", (NX0, NY0, 0, NX1, NY1, CH), sky=True, floor=MAT_ICE, wall=MAT_ROCK, light=None)
    COL = (-13312, -11776)
    w.space("canyon_col", "1", (COL[0], CY, 0, COL[1], NY0, CH), sky=True, floor=MAT_ICE, wall=MAT_ROCK, light=None)
    # plateforme d'atterrissage LAAT + 100 départs (10 x 10), au fond du secteur nord
    w.block((-13440, 11264, 0, -12576, 11968, 8), MAT_HAZARD, "detail")
    for i in range(10):
        for j in range(10):
            M["player_starts"].append((-13376 + 80 * i, 11328 + 64 * j, 12))
    import random
    rn = random.Random(1408)
    # falaises du secteur nord (côtés ouest/est), fond nord
    yy = NY0
    while yy < NY1:
        y1 = min(yy + rn.choice([512, 640, 768]), NY1)
        rock(w, (NX0, yy, 0, NX0 + rn.choice([192, 256, 384]), y1, rn.choice([1536, 2048, 2560])), rn)
        for (a, c) in ((yy, min(y1, 4992)), (max(yy, 5504), y1)):    # passage vers le placard défenseurs
            if a < c:
                rock(w, (NX1 - rn.choice([192, 256, 384]), a, 0, NX1, c, rn.choice([1536, 2048, 2560])), rn)
        yy = y1
    xx = NX0 + 384
    while xx < NX1 - 384:
        x1 = min(xx + rn.choice([512, 768]), NX1 - 384)
        if x1 <= -13568 or xx >= -12416:          # laisse la plateforme dégagée
            rock(w, (xx, NY1 - rn.choice([160, 256]), 0, x1, NY1, rn.choice([2048, 3072])), rn)
        xx = x1
    # bord sud du secteur nord : falaise percée par le col
    for (a, b) in ((NX0, COL[0]), (COL[1], NX1)):
        rock(w, (a, NY0, 0, b, NY0 + 256, rn.choice([2048, 2560])), rn)
    # col : 3 passages entre 2 piliers (goulot entre les secteurs)
    rock(w, (-12928, CY, 0, -12672, NY0 + 128, 1536), rn)
    rock(w, (-12416, CY, 0, -12160, NY0 + 128, 1536), rn)
    # secteur nord : crêtes, couverts, aiguilles pour le combat aérien
    for b in ((-14848, 9216, -13824, 9472, 320), (-11776, 9216, -10752, 9472, 320), (-13312, 7680, -12288, 7936, 288),
              (-15104, 6400, -14336, 6656, 320), (-11008, 6400, -10240, 6656, 320)):
        rock(w, (b[0], b[1], 0, b[2], b[3], b[4]))
    for (sx, sy, sh) in ((-15232, 10240, 3072), (-10624, 10496, 2560), (-14080, 7552, 3584), (-11264, 8064, 2816),
                         (-12672, 5632, 2048)):
        rock(w, (sx, sy, 0, sx + 384, sy + 384, sh), rn)
    for (bx, by) in [(-13696, 10240), (-12288, 10240), (-14336, 8448), (-11520, 8448), (-12928, 8704), (-12928, 6784),
                     (-14592, 5632), (-10880, 5632), (-13568, 5248), (-12032, 5248)]:
        crate(w, bx, by, s=160, h=96, mat=MAT_ROCK)
    rnd = random.Random(408)
    # falaises irrégulières le long des deux grands côtés
    x = CX0
    while x < -9216:
        ln = rnd.choice([384, 512, 640, 768])
        x1 = min(x + ln, -9216)
        for side in (-1, 1):
            d = rnd.choice([192, 256, 320, 448])
            hgt = rnd.choice([1024, 1536, 2048, 2560])
            if side < 0:
                rock(w, (x, -CY, 0, x1, -CY + d, hgt), rnd)
            else:   # laisse libre le col vers le secteur nord
                for (a, b) in ((x, min(x1, COL[0])), (max(x, COL[1]), x1)):
                    if a < b:
                        rock(w, (a, CY - d, 0, b, CY, hgt), rnd)
        x = x1
    # fond de vallée (ouest), en laissant la plateforme dégagée
    y = -CY
    while y < CY:
        ln = rnd.choice([512, 768])
        y1 = min(y + ln, CY)
        if True:
            rock(w, (CX0, y, 0, CX0 + rnd.choice([128, 160]), y1, rnd.choice([1536, 2048, 3072])), rnd)
        y = y1
    # crêtes => 3 voies au sol (sud / centre / nord) + rochers de couvert
    rock(w, (-12032, -768, 0, -10624, -448, 320))
    rock(w, (-12032, 448, 0, -10624, 768, 320))
    rock(w, (-12672, -192, 0, -12416, 192, 256))       # casse la ligne de vue centrale
    rock(w, (-13568, -2304, 0, -12416, -1920, 384))
    rock(w, (-13568, 1920, 0, -12416, 2304, 384))
    rock(w, (-11264, -2816, 0, -10368, -2432, 320))
    rock(w, (-11264, 2432, 0, -10368, 2816, 320))
    # aiguilles rocheuses : obstacles pour le combat aérien, couverts au sol
    for (sx, sy, sh) in ((-14592, -2816, 3072), (-13056, 2560, 2560), (-11904, -3328, 3584),
                         (-14336, 2048, 2048), (-10880, -1664, 1792)):
        rock(w, (sx, sy, 0, sx + 384, sy + 384, sh), rnd)
    for (bx, by) in [(-12800, -960), (-12800, 960), (-11264, -1088), (-11264, 1088),
                     (-11392, 0), (-10240, -640), (-10240, 640), (-9856, 0),
                     (-14080, -1600), (-14080, 1600), (-12160, -1600), (-12160, 1600), (-10368, -1856), (-10368, 1856)]:
        crate(w, bx, by, s=160, h=96, mat=MAT_ROCK)
    w.meta["fog_origin"] = (-12800, 11000, 256)
    M["tour"] += [("z1_spawn", (-12900, 11000, 64), (5, -90, 0)), ("z1_col", (-12544, 6000, 64), (5, -90, 0)),
                  ("z1_canyon", (-12900, -1100, 64), (5, 20, 0)), ("z1_ciel", (-15700, -3700, 3200), (22, 35, 0))]
    # placard défenseurs du secteur nord : accès coudé depuis la falaise est (aucune vue directe)
    w.space("closet_1", "1", (-9216, 5632, 0, -8512, 6144, 192), light="255 200 160 300", light_step=512)
    corridor(w, "closet_1_link", "1", [(NX1, 5248), (-9024, 5248), (-9024, 5632)], 192, 160, light=None)
    w.meta["def_spawns"]["1"] = spawn_grid(-8864, 5888, 4)

    # =============== ZONE 2 : hangar extérieur, 3 tourelles AA ===============
    w.space("hangar", "2", (-9216, -2048, 0, -5120, 2048, 6144), sky=True,
            floor=MAT_ICE, wall=MAT_ROCK, light=None)
    M["zones"]["2"] = (-9216, -2048, 0, -5120, 2048, 6144)
    # piliers rocheux à l'embouchure du canyon => 3 voies d'entrée
    rock(w, (-9216, -896, 0, -8960, -576, 1024))
    rock(w, (-9216, 576, 0, -8960, 896, 1024))
    # plateformes des tourelles (+256) avec rampes 256 de large
    w.block((-7936, -1792, 0, -7168, -1024, 256), MAT_METAL, top=MAT_GRATE)
    w.add(ramp(-8448, -1536, -7936, -1280, 0, 256, "+x"))
    w.block((-7168, 1024, 0, -6400, 1792, 256), MAT_METAL, top=MAT_GRATE)
    w.add(ramp(-7680, 1280, -7168, 1536, 0, 256, "+x"))
    w.block((-6656, -384, 0, -6144, 384, 256), MAT_METAL, top=MAT_GRATE)
    w.add(ramp(-6528, -896, -6272, -384, 0, 256, "+y"))
    w.add(ramp(-6528, 384, -6272, 896, 0, 256, "-y"))
    M["aa"] = [(-7616, -1472, 256, -7488, -1344, 448),
               (-6848, 1344, 256, -6720, 1472, 448),
               (-6464, -64, 256, -6336, 64, 448)]
    for (cx, cy) in [(-8448, -512), (-8448, 512), (-7680, 0), (-7296, -640), (-7296, 640),
                     (-5888, -1024), (-5888, 1024), (-5632, -512), (-5632, 512), (-8064, 1536)]:
        crate(w, cx, cy, s=96, h=64)
    for y in (-1536, 1536):
        muret(w, -6016, y - 256, -5952, y + 256)
    M["tour"] += [("z2_hangar", (-8900, -1700, 300), (10, 40, 0)), ("z2_gate", (-6200, 600, 120), (5, -20, 0))]
    closet(w, "2", (-6656, -2816, 0, -5632, -2304, 192), (-6272, -2304, 0, -6016, -2048, 160))

    # =============== ZONE 3b : porte principale + hall d'assaut ===============
    w.space("gate_doorway", "3b", (-5120, -256, 0, -5088, 256, 384), light=None)
    w.space("assault_hall", "3b", (-5088, -768, 0, -2048, 768, 512), light=WARM)
    M["zones"]["3b"] = (-5088, -768, 0, -2048, 768, 512)
    M["doors"].append(("gn_door_gate", "x", -5104, -256, 256, 0, 384))
    # tranchée centrale (fosse de 64) avec rampes aux extrémités
    w.add(ramp(-4608, -160, -4480, 160, -64, 0, "-x", base=-80))
    w.add(ramp(-2688, -160, -2560, 160, -64, 0, "+x", base=-80))
    w.add(ramp(-3648, -160, -3520, 160, -64, 0, "-x", base=-80))
    # couverts au sol : murets et caisses en quinconce
    for i, x in enumerate(range(-4736, -2304, 384)):
        y = 448 if i % 2 else -448
        muret(w, x, y - 128, x + 64, y + 128)
        crate(w, x + 192, -y, s=96, h=64)
    M["tour"] += [("z3b_hall", (-4900, -600, 96), (5, 15, 0))]
    closet(w, "3b", (-3584, -1536, 0, -2816, -1024, 192), (-3296, -1024, 0, -3104, -768, 160))
    # hall -> usine : axe principal + 2 couloirs de service à virages
    w.space("3b_main", "3b", (-2048, -160, 0, 0, 160, 256), light_step=512)
    corridor(w, "3b_south", "3b", [(-2048, -544), (-1536, -544), (-1536, -1088), (-768, -1088),
                                    (-768, -640), (0, -640)], 192, 160)
    corridor(w, "3b_north", "3b", [(-2048, 544), (-1536, 544), (-1536, 1088), (-768, 1088),
                                    (-768, 640), (0, 640)], 192, 160)

    # =============== ZONE 3a : réseau de conduits (192 de large) ===============
    w.space("conduit_doorway", "3a", (-5120, 1792, 0, -5056, 2048, 192), light=None)
    M["doors"].append(("gn_door_conduit", "x", -5088, 1792, 2048, 0, 192))
    w.space("conduit_vestibule", "3a", (-5056, 1792, 0, -4544, 2816, 256), light_step=512)
    w.space("conduit_t1", "3a", (-4544, 1920, 0, 1024, 2112, 128), light_step=512, floor=MAT_GRATE)
    w.space("conduit_t2", "3a", (-4544, 2368, 0, 1024, 2560, 128), light_step=512, floor=MAT_GRATE)
    for i, cx in enumerate((-4000, -2560, -1120)):
        w.space(f"conduit_x{i}", "3a", (cx - 96, 2112, 0, cx + 96, 2368, 128), light=None)
    for i, cx in enumerate((-3328, -1888)):   # passages accroupis courts (256 de long, 48 de haut)
        w.space(f"conduit_crawl{i}", "3a", (cx - 64, 2112, 0, cx + 64, 2368, 48), light=None)
    # cloisons basses dans les tunnels (couverts)
    for x in (-3712, -2176, -704):
        w.block((x, 1920, 0, x + 32, 2016, 56), MAT_METAL)
        w.block((x + 256, 2464, 0, x + 288, 2560, 56), MAT_METAL)
    w.space("conduit_collector", "3a", (1024, 1920, 0, 2048, 2560, 256), light_step=512)
    for i, cx in enumerate((1184, 1536, 1888)):
        w.space(f"conduit_drop{i}", "3a", (cx - 96, 1536, 0, cx + 96, 1920, 192), light=None)
    M["zones"]["3a"] = (-5056, 1536, 0, 2048, 2816, 256)
    M["tour"] += [("z3a_conduits", (-4300, 2016, 40), (0, 0, 0)), ("z3a_collector", (1100, 2240, 64), (10, -30, 0))]
    closet(w, "3a", (-2944, 2816, 0, -2176, 3328, 192), (-2656, 2560, 0, -2464, 2816, 128))

    # =============== ZONE 4 : usine de droïdes ===============
    w.space("factory", "4", (0, -1536, 0, 3072, 1536, 768), light=WARM, light_step=768, light_levels=[192, 720])
    M["zones"]["4"] = (0, -1536, 0, 3072, 1536, 768)
    # mezzanines +256 (dalles suspendues) avec piliers
    for sy in (1, -1):
        y0, y1 = (960, 1536) if sy > 0 else (-1536, -960)
        w.block((384, y0, 224, 2688, y1, 256), MAT_METAL, top=MAT_GRATE)
        for px in (384, 1024, 1664, 2304):
            py = y0 if sy > 0 else y1 - 64
            w.add(oct_prism(px + 32, py + 32, 32, 0, 224, MAT_METAL))
        rail(w, (704, (y0 - 16) if sy > 0 else y1, 256, 1408, y0 if sy > 0 else y1 + 16, 304))
        rail(w, (2304, (y0 - 16) if sy > 0 else y1, 256, 2688, y0 if sy > 0 else y1 + 16, 304))
        ry0, ry1 = (1152, 1408) if sy > 0 else (-1408, -1152)
        # rampes d'accès (256 de large) : du sol de l'usine jusqu'au bord de la mezzanine
        for (ra, rb) in ((448, 704), (2048, 2304)):
            if sy > 0:
                w.add(ramp(ra, 512, rb, 960, 0, 256, "+y"))
            else:
                w.add(ramp(ra, -960, rb, -512, 0, 256, "-y"))
        # rampe mezzanine -> passerelle +512
        w.add(slope_slab(1664, ry0, 2176, ry1, 256, 512, "-x"))
    # passerelle centrale +512 (nord-sud)
    w.block((1408, -1408, 480, 1664, 1408, 512), MAT_METAL, top=MAT_GRATE)
    rail(w, (1392, -1408, 512, 1408, 1408, 560))
    rail(w, (1664, -1152, 512, 1680, 1152, 560))
    # tapis roulants + presses
    M["conveyors"] = [(1024, -448, 0, 2048, -320, 16), (1024, 320, 0, 2048, 448, 16)]
    M["presses"] = [(1472, -448, 176, 1600, -320, 240), (1472, 320, 176, 1600, 448, 240)]
    for (x0, y0, z0, x1, y1, z1) in M["presses"]:
        w.block((x0 - 32, y0 - 32, 240, x0, y1 + 32, 480), MAT_HAZARD)   # montants (sous la passerelle)
        w.block((x1, y0 - 32, 240, x1 + 32, y1 + 32, 480), MAT_HAZARD)
    # générateurs : enclos bas avec 4 ouvertures (>= 3 entrées)
    M["generators"] = [(640, 0), (2496, -640), (2496, 640)]
    for (gx, gy) in M["generators"]:
        for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            w.add(frustum((gx + dx * 128 - 64, gy + dy * 128 - 64, 0, gx + dx * 128 + 64, gy + dy * 128 + 64, 64), 14, MAT_CEIL))
    for (cx, cy) in [(256, -640), (256, 640), (1280, 0), (2048, 0), (2816, 0), (1024, -1344), (2560, 1344)]:
        crate(w, cx, cy, s=96, h=64)
    B1 = "models/tfa/comm/gg/npc_comb_sw_droid_b1.mdl"
    M["factory_droids"] = ([(B1, (x, y, 16), 0) for x in range(1088, 2048, 128) for y in (-384, 384)]
                           + [(B1, (x, y, 2), 90) for x in range(2240, 2561, 80) for y in (-1280, -1200, -1120)])
    M["tour"] += [("z4_factory", (120, -800, 360), (15, 25, 0)), ("z4_mezz", (2900, 1250, 320), (15, -160, 0)),
                  ("z4_chaine", (900, -100, 160), (18, 0, 0))]
    closet(w, "4", (1280, -2304, 0, 2048, -1792, 192), (1568, -1792, 0, 1760, -1536, 160))

    # =============== Transitions 4 -> 5 : sas blindé + tranchée + service ===============
    w.space("sas_in", "4-5", (3072, -128, 0, 3584, 128, 192), light=None)
    w.space("sas_chamber", "4-5", (3584, -512, 0, 4608, 512, 320), light_step=512)
    w.space("sas_out", "4-5", (4608, -128, 0, 5120, 128, 192), light=None)
    M["doors"].append(("gn_sas_door_1", "x", 3552, -128, 128, 0, 192))
    M["doors"].append(("gn_sas_door_2", "x", 4624, -128, 128, 0, 192))
    w.space("trench_n", "4-5", (3072, 704, 0, 5120, 1024, 224), light_step=512)
    w.space("trench_n_pit", "4-5", (3328, 784, -64, 4864, 944, 0), light=None, floor=MAT_GRATE)
    w.add(ramp(3328, 784, 3456, 944, -64, 0, "-x", base=-80))
    w.add(ramp(4736, 784, 4864, 944, -64, 0, "+x", base=-80))
    M["doors"].append(("gn_door_4n", "x", 3104, 704, 1024, 0, 224))
    corridor(w, "service_s", "4-5", [(3072, -864), (3584, -864), (3584, -1376), (4352, -1376),
                                      (4352, -864), (5120, -864)], 192, 160)
    M["doors"].append(("gn_door_4s", "x", 3104, -960, -768, 0, 160))
    M["tour"] += [("z45_sas", (3632, 240, 64), (5, -20, 0))]

    # =============== ZONE 5 : GARNISON (3 étages) ===============
    GX0, GY0, GX1, GY1 = 5120, -1536, 8192, 1536
    w.space("garrison", "5", (GX0, GY0, 0, GX1, GY1, 1152), light="255 230 200 420", light_step=768,
            light_levels=[300, 684, 1068], wall=MAT_METAL)
    M["zones"]["5"] = (GX0, GY0, 0, GX1, GY1, 1152)
    strips = ((-1280, -1024), (-128, 128), (1024, 1280))
    holes1 = [(5632, a, 352, 6400, b, 384) for a, b in strips]      # rampes RDC -> étage 1 (+x)
    holes2 = [(6912, a, 736, 7680, b, 768) for a, b in strips]      # rampes étage 1 -> étage 2 (-x)
    slab_with_holes(w, (GX0, GY0, 352, GX1, GY1, 384), holes1, kind="world")
    slab_with_holes(w, (GX0, GY0, 736, GX1, GY1, 768), holes2, kind="world")
    for a, b in strips:
        w.add(ramp(5632, a, 6400, b, 0, 384, "+x"))
        w.add(ramp(6912, a, 7680, b, 384, 768, "-x", base=368))
        for (x0, x1, z) in ((5632, 6400, 384), (6912, 7680, 768)):   # garde-corps des trémies
            rail(w, (x0, a - 16, z, x1, a, z + 48)); rail(w, (x0, b, z, x1, b + 16, z + 48))
        rail(w, (5616, a, 384, 5632, b, 432))
        rail(w, (7680, a, 768, 7696, b, 816))
    # consoles de l'armurerie : une par étage, enclos avec 4 ouvertures
    M["garrison_consoles"] = [(7168, 640, 0), (7936, -640, 384), (5888, 640, 768)]
    for (gx, gy, gz) in M["garrison_consoles"]:
        for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            w.add(frustum((gx + dx * 128 - 64, gy + dy * 128 - 64, gz, gx + dx * 128 + 64, gy + dy * 128 + 64, gz + 64), 14, MAT_CEIL))
    for z in (0, 384, 768):     # couverts et piliers par étage (pas au-dessus d'une trémie)
        for (cx, cy) in [(5440, -640), (5440, 640), (6656, -640), (6656, 640), (7424, 0), (6144, 0)]:
            if (z == 384 and (cx, cy) == (6144, 0)) or (z == 768 and (cx, cy) == (7424, 0)):
                continue
            crate(w, cx, cy, z=z, s=96, h=64)
        if z < 768:
            for (px, py) in [(6656, -1408), (6656, 1344), (7872, 1344), (7872, -1408)]:
                w.add(oct_prism(px + 32, py + 32, 32, z, z + 352, MAT_METAL))
    M["tour"] += [("z5_garnison_rdc", (5300, -1300, 40), (5, 40, 0)), ("z5_garnison_e2", (5300, 1300, 808), (8, -35, 0))]
    closet(w, "5", (6272, 1792, 768, 7040, 2304, 960), (6560, 1536, 768, 6752, 1792, 928))

    # =============== Transitions 5 -> 6 (z 768) : galerie de glace + service + tranchée ===============
    Z = 768
    for i, (x0, h) in enumerate([(8192, 256), (8704, 384), (9216, 320), (9728, 288)]):
        w.space(f"ice_gallery_{i}", "5-6", (x0, -224, Z, x0 + 512, 224, Z + h), floor=MAT_ICE, wall=MAT_ICE,
                ceil=MAT_ICE, light=ICE_LIGHT, light_step=512)
    for x in (8576, 9472):
        rock(w, (x, -96, Z, x + 64, 96, Z + 64), mat=MAT_ICE)
    M["doors"].append(("gn_door_5a", "x", 8224, -224, 224, Z, Z + 256))
    corridor(w, "service_n", "5-6", [(8192, 864), (8704, 864), (8704, 1376), (9600, 1376),
                                      (9600, 864), (10240, 864)], 192, 160, z0=Z)
    M["doors"].append(("gn_door_5n", "x", 8224, 768, 960, Z, Z + 160))
    w.space("trench_s", "5-6", (8192, -1024, Z, 10240, -704, Z + 224), light_step=512)
    w.space("trench_s_pit", "5-6", (8448, -944, Z - 64, 9984, -784, Z), light=None, floor=MAT_GRATE)
    w.add(ramp(8448, -944, 8576, -784, Z - 64, Z, "-x", base=Z - 80))
    w.add(ramp(9856, -944, 9984, -784, Z - 64, Z, "+x", base=Z - 80))
    M["doors"].append(("gn_door_5s", "x", 8224, -1024, -704, Z, Z + 224))
    M["tour"] += [("z56_glace", (8300, 0, Z + 64), (5, 0, 0))]

    # =============== ZONE 6 : centre de données (salle de serveurs, hack en 3 étapes) ===============
    OX, OZ = 5120, 768          # ancien centre de données décalé
    def D(b):
        return (b[0] + OX, b[1], b[2] + OZ, b[3] + OX, b[4], b[5] + OZ)
    w.space("datacenter", "6", D((5120, -1536, 0, 8192, 1536, 640)), light="210 230 255 480", light_step=768)
    M["zones"]["6"] = D((5120, -1536, 0, 8192, 1536, 640))
    hx0, hy0, hx1, hy1, hz = 6144, -512, 7168, 512, 320
    T = 32
    def wall_with_door(axis, fixed, lo, hi, d0, d1):
        if axis == "x":
            parts = [(fixed, lo, 0, fixed + T, d0, hz), (fixed, d1, 0, fixed + T, hi, hz), (fixed, d0, 192, fixed + T, d1, hz)]
        else:
            parts = [(lo, fixed, 0, d0, fixed + T, hz), (d1, fixed, 0, hi, fixed + T, hz), (d0, fixed, 192, d1, fixed + T, hz)]
        for p in parts:
            w.block(D(p), MAT_WALL, "world")
    wall_with_door("x", hx0 - T, hy0 - T, hy1 + T, -128, 128)
    wall_with_door("x", hx1, hy0 - T, hy1 + T, -128, 128)
    wall_with_door("y", hy0 - T, hx0, hx1, 6528, 6784)
    wall_with_door("y", hy1, hx0, hx1, 6528, 6784)
    w.block(D((hx0 - T, hy0 - T, hz, hx1 + T, hy1 + T, hz + T)), MAT_CEIL, "world")
    M["dc_doors"] = [("gn_dc_door_1", "x", hx0 - T + 16 + OX, -128, 128, OZ, OZ + 192),
                     ("gn_dc_door_2", "x", hx1 + 16 + OX, -128, 128, OZ, OZ + 192),
                     ("gn_dc_door_3", "y", hy0 - T + 16, 6528 + OX, 6784 + OX, OZ, OZ + 192),
                     ("gn_dc_door_4", "y", hy1 + 16, 6528 + OX, 6784 + OX, OZ, OZ + 192)]
    # 3 terminaux : salle du hack (centre), plateforme nord (+256), zone sud
    M["hack_buttons"] = [D((6624, -32, 0, 6688, 32, 64)), D((6624, 1312, 256, 6688, 1376, 320)),
                         D((6624, -1120, 0, 6688, -1056, 64))]     # terminal 3 reculé : dégage les passerelles
    # panneaux « mode d'emploi » du piratage : dans la salle et sur ses façades
    for sb in ((6208, 504, 72, 6464, 512, 200), (6848, -512, 72, 7104, -504, 200),
               (6208, 544, 72, 6464, 552, 200), (6848, -552, 72, 7104, -544, 200),
               (6104, 192, 72, 6112, 448, 200), (7200, -448, 72, 7208, -192, 200)):
        w.block(D(sb), "givre_noir/tuto_piratage")
    for (dx, dy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        w.block(D((6656 + dx * 160 - 48, -1088 + dy * 160 - 48, 0, 6656 + dx * 160 + 48, -1088 + dy * 160 + 48, 56)), MAT_COMPUTER)
    for (lx, ly) in ((6400, -256), (6912, 256), (6400, 256), (6912, -256)):
        w.block(D((lx - 32, ly - 32, 0, lx + 32, ly + 32, 48)), MAT_COMPUTER)
    RACK_H = 224
    for x in list(range(5248, 5953, 192)) + list(range(7328, 8001, 192)):
        for (y0, y1) in ((224, 704), (-704, -224), (1024, 1120), (-1120, -1024)):
            if abs(y0) >= 1024 and 5696 < x < 7700:
                continue
            w.block(D((x, y0, 0, x + 64, y1, RACK_H)), MAT_COMPUTER)
    for sy in (1, -1):
        for (x0, x1) in ((6112, 6464), (6848, 7200)):
            for yy in (640, 1024):
                y0 = yy if sy > 0 else -yy - 64
                w.block(D((x0, y0, 0, x1, y0 + 64, RACK_H)), MAT_COMPUTER)
        for x in (5888, 7424):
            w.block(D((x, sy * 864 - 48, 0, x + 128, sy * 864 + 48, 56)), MAT_COMPUTER)
        w.block(D((6560, sy * 864 - 32, 0, 6752, sy * 864 + 32, 56)), MAT_COMPUTER)
    # plateforme +256 côté nord seulement (le sud mène aux sorties vers la prison)
    w.block(D((5760, 1152, 0, 7680, 1536, 256)), MAT_METAL, top=MAT_GRATE)
    w.add(ramp(7680 + OX, 1152, 8192 + OX, 1408, OZ, OZ + 256, "-x", base=OZ - 16))
    w.add(ramp(5248 + OX, 1152, 5760 + OX, 1408, OZ, OZ + 256, "+x", base=OZ - 16))
    rail(w, D((5760, 1136, 256, 7680, 1152, 304)))
    M["tour"] += [("z6_dc", (10400, 0, OZ + 64), (5, 20, 0)), ("z6_hack", (11370, -400, OZ + 64), (5, 35, 0))]
    closet(w, "6", D((6272, 1792, 256, 7040, 2304, 448)), D((6560, 1536, 256, 6752, 1792, 416)))

    # =============== Transitions 6 -> 7 (vers le sud, z 768) ===============
    corridor(w, "service_w", "6-7", [(10752, -1536), (10752, -2048), (10368, -2048), (10368, -2816),
                                      (10752, -2816), (10752, -3584)], 192, 160, z0=Z)
    M["doors"].append(("gn_door_6w", "y", -1600, 10656, 10848, Z, Z + 160))
    # salle des passerelles : 2 passerelles parallèles au-dessus d'un vide de 640
    w.space("catwalk_hall", "6-7", (11392, -3456, 128, 12160, -1664, 1152), light_step=512, wall=MAT_METAL)
    w.ent("trigger_hurt", solids=[Block((11392, -3456, 128, 12160, -1664, 256), MAT_TRIGGER)], targetname="gn_catwalk_pit",
          damage=1000, damagetype=32, spawnflags=1, StartDisabled=0)
    for i, (x0, x1) in enumerate(((11456, 11712), (11840, 12096))):
        w.space(f"catwalk_n{i}", "6-7", (x0, -1664, Z, x1, -1536, Z + 192), light=None)
        w.space(f"catwalk_s{i}", "6-7", (x0, -3584, Z, x1, -3456, Z + 192), light=None)
        w.block((x0, -3456, Z - 32, x1, -1664, Z), MAT_METAL, top=MAT_GRATE)
        rail(w, (x0, -3456, Z, x0 + 16, -1664, Z + 48)); rail(w, (x1 - 16, -3456, Z, x1, -1664, Z + 48))
        M["doors"].append((f"gn_door_6{'ab'[i]}", "y", -1600, x0, x1, Z, Z + 192))
    w.space("trench_e", "6-7", (12640, -3584, Z, 12960, -1536, Z + 224), light_step=512)
    w.space("trench_e_pit", "6-7", (12720, -3328, Z - 64, 12880, -1792, Z), light=None, floor=MAT_GRATE)
    w.add(ramp(12720, -1920, 12880, -1792, Z - 64, Z, "+y", base=Z - 80))
    w.add(ramp(12720, -3328, 12880, -3200, Z - 64, Z, "-y", base=Z - 80))
    M["doors"].append(("gn_door_6e", "y", -1600, 12640, 12960, Z, Z + 224))
    M["tour"] += [("z67_passerelles", (11776, -1750, Z + 64), (15, -90, 0))]

    # =============== ZONE 7 : bloc de détention (libérer les prisonniers) ===============
    PX0, PY0, PX1, PY1 = 10240, -6656, 13312, -3584
    w.space("prison", "7", (PX0, PY0, Z, PX1, PY1, Z + 896), light="235 225 255 450", light_step=768,
            light_levels=[Z + 300, Z + 840], wall=MAT_METAL)
    M["zones"]["7"] = (PX0, PY0, Z, PX1, PY1, Z + 896)
    cells = {"a": [], "b": [], "c": []}
    for tier, zc in ((0, Z), (1, Z + 384)):
        for yc in (-3968, -4416, -4864, -5312, -5760, -6208):          # cellules mur est
            if tier == 0 and yc == -5312:
                continue                                                # emplacement du placard
            w.space(f"cell_e{tier}_{yc}", "7", (13344, yc - 160, zc, 13728, yc + 160, zc + 192), light="200 200 255 120",
                    light_step=512)
            w.space(f"cell_e{tier}_{yc}_d", "7", (13312, yc - 96, zc, 13344, yc + 96, zc + 160), light=None)
            cells["a" if tier == 0 else "c"].append(("x", 13328, yc - 96, yc + 96, zc, zc + 160))
        for xc in (10624, 11072, 11520, 11968, 12416, 12864):          # cellules mur sud
            w.space(f"cell_s{tier}_{xc}", "7", (xc - 160, -7072, zc, xc + 160, -6688, zc + 192), light="200 200 255 120",
                    light_step=512)
            w.space(f"cell_s{tier}_{xc}_d", "7", (xc - 96, -6688, zc, xc + 96, -6656, zc + 160), light=None)
            cells["b" if tier == 0 else "c"].append(("y", -6672, xc - 96, xc + 96, zc, zc + 160))
    M["cells"] = {}
    for g, lst in cells.items():
        M["cells"][g] = []
        for i, (axis, pos, lo, hi, z0, z1) in enumerate(lst, 1):
            name = f"gn_cell_{g}_{i}"
            M["cells"][g].append(name)
            M["doors"].append((name, axis, pos, lo, hi, z0, z1))
    # coursive haute (+384) le long des murs est et sud
    w.block((12928, -6272, Z + 352, 13312, -3584, Z + 384), MAT_METAL, top=MAT_GRATE)
    w.block((10240, -6656, Z + 352, 13312, -6272, Z + 384), MAT_METAL, top=MAT_GRATE)
    rail(w, (12912, -6272, Z + 384, 12928, -4096, Z + 432))
    rail(w, (10752, -6272, Z + 384, 12928, -6256, Z + 432))
    w.add(ramp(12160, -4096, 12928, -3840, Z, Z + 384, "+x", base=Z - 16))
    w.add(ramp(10496, -6272, 10752, -5504, Z, Z + 384, "-y", base=Z - 16))
    # mirador central (+384) avec 3 rampes
    w.block((11520, -5376, Z, 12032, -4864, Z + 384), MAT_METAL, top=MAT_GRATE)
    w.add(ramp(11648, -4864, 11904, -4096, Z, Z + 384, "-y", base=Z - 16))
    w.add(ramp(12032, -5248, 12800, -4992, Z, Z + 384, "-x", base=Z - 16))
    w.add(ramp(11648, -6144, 11904, -5376, Z, Z + 384, "+y", base=Z - 16))
    M["prison_consoles"] = [(11776, -5120, Z + 384), (13120, -4480, Z + 384), (11264, -6464, Z + 384)]
    for (cx, cy) in [(10752, -4224), (10880, -5120), (12544, -5760), (12544, -4352), (11136, -5760), (12288, -6016)]:
        crate(w, cx, cy, z=Z, s=96, h=64)
    for (x0, y0, x1, y1) in [(10624, -4736, 10688, -4480), (12416, -5504, 12672, -5440), (11200, -4096, 11456, -4032)]:
        muret(w, x0, y0, x1, y1, z=Z)
    M["tour"] += [("z7_prison", (10400, -3750, Z + 300), (20, -40, 0)), ("z7_cellules", (12700, -6300, Z + 450), (10, 20, 0))]
    closet(w, "7", (13824, -5696, Z, 14592, -4928, Z + 192), (13312, -5408, Z, 13824, -5216, Z + 160))

    # =============== Transitions 7 -> 8 (vers l'ouest, z 768) : sas + service + galerie ===============
    w.space("sas2_in", "7-8", (9728, -5248, Z, 10240, -4992, Z + 192), light=None)
    w.space("sas2_chamber", "7-8", (8704, -5632, Z, 9728, -4608, Z + 320), light_step=512)
    w.space("sas2_out", "7-8", (8192, -5248, Z, 8704, -4992, Z + 192), light=None)
    M["doors"].append(("gn_sas2_door_1", "x", 9744, -5248, -4992, Z, Z + 192))
    M["doors"].append(("gn_sas2_door_2", "x", 8672, -5248, -4992, Z, Z + 192))
    corridor(w, "service_7n", "7-8", [(10240, -4096), (9728, -4096), (9728, -3712), (8704, -3712),
                                       (8704, -4096), (8192, -4096)], 192, 160, z0=Z)
    M["doors"].append(("gn_door_7n", "x", 10192, -4192, -4000, Z, Z + 160))
    for i, (x0, h) in enumerate([(9728, 256), (9216, 384), (8704, 320), (8192, 288)]):
        w.space(f"ice_gallery2_{i}", "7-8", (x0, -6368, Z, x0 + 512, -5920, Z + h), floor=MAT_ICE, wall=MAT_ICE,
                ceil=MAT_ICE, light=ICE_LIGHT, light_step=512)
    rock(w, (9024, -6240, Z, 9088, -6048, Z + 64), mat=MAT_ICE)
    M["doors"].append(("gn_door_7s", "x", 10192, -6368, -5920, Z, Z + 256))
    M["tour"] += [("z78_sas", (9664, -5120, Z + 64), (5, 180, 0))]

    # =============== ZONE 8 : tour de communication (salle verticale, 3 charges) ===============
    TX0, TY0, TX1, TY1 = 5120, -6656, 8192, -3584
    w.space("comm_tower", "8", (TX0, TY0, Z, TX1, TY1, Z + 2048), light="190 220 255 520", light_step=1024,
            light_levels=[Z + 400, Z + 900, Z + 1400, Z + 1950], wall=MAT_METAL)
    M["zones"]["8"] = (TX0, TY0, Z, TX1, TY1, Z + 2048)
    lv = [Z + 512, Z + 1024, Z + 1536]                     # 1280 / 1792 / 2304
    ramps = {  # niveau d'arrivée -> [(empreinte, z_bas, z_haut, sens)]
        0: [((5632, -6656, 6656, -6400), "+x"), ((6656, -3840, 7680, -3584), "-x")],
        1: [((7936, -6144, 8192, -5120), "+y"), ((5120, -5120, 5376, -4096), "-y")],
        2: [((6656, -6656, 7680, -6400), "-x"), ((5632, -3840, 6656, -3584), "+x")],
    }
    for k, zt in enumerate(lv):
        holes = [(f[0], f[1], zt - 32, f[2], f[3], zt) for f, _ in ramps[k]]
        for strip in ((TX0, TY0, TX1, -6144), (TX0, -4096, TX1, TY1), (TX0, -6144, 5632, -4096), (7680, -6144, TX1, -4096)):
            slab_with_holes(w, (strip[0], strip[1], zt - 32, strip[2], strip[3], zt), holes, kind="detail")
        zb = Z if k == 0 else lv[k - 1]
        for (f, d) in ramps[k]:
            w.add(ramp(f[0], f[1], f[2], f[3], zb, zt, d, base=zb - 16))
        # collier de l'antenne + 4 ponts
        w.block((6272, -5504, zt - 32, 7040, -4736, zt), MAT_METAL, top=MAT_GRATE)
        for b in ((6528, -4736, 6784, -4096), (6528, -6144, 6784, -5504), (7040, -5248, 7680, -4992), (5632, -5248, 6272, -4992)):
            w.block((b[0], b[1], zt - 32, b[2], b[3], zt), MAT_METAL, top=MAT_GRATE)
            if b[2] - b[0] == 256:
                rail(w, (b[0], b[1], zt, b[0] + 16, b[3], zt + 48)); rail(w, (b[2] - 16, b[1], zt, b[2], b[3], zt + 48))
            else:
                rail(w, (b[0], b[1], zt, b[2], b[1] + 16, zt + 48)); rail(w, (b[0], b[3] - 16, zt, b[2], b[3], zt + 48))
        # garde-corps du bord intérieur des coursives (ouvertures aux ponts)
        for (a, c) in ((5632, 6528), (6784, 7680)):
            rail(w, (a, -4112, zt, c, -4096, zt + 48)); rail(w, (a, -6144, zt, c, -6128, zt + 48))
        for (a, c) in ((-6144, -5248), (-4992, -4096)):
            rail(w, (5632, a, zt, 5648, c, zt + 48)); rail(w, (7664, a, zt, 7680, c, zt + 48))
    w.add(oct_prism(6656, -5120, 256, Z, Z + 2048, MAT_HAZARD, "world"))           # antenne
    M["charges"] = [(6928, -4848, zt, 6976, -4800, zt + 64) for zt in lv]
    for (cx, cy) in [(5632, -5632), (7552, -4608), (6144, -4352), (7296, -5888), (5760, -4480)]:
        crate(w, cx, cy, z=Z, s=96, h=64)
    M["tour"] += [("z8_tour_bas", (7900, -6450, Z + 64), (-20, 135, 0)), ("z8_tour_haut", (5300, -3800, lv[2] + 64), (20, -45, 0))]
    closet(w, "8", (6912, -3328, lv[1], 7680, -2816, lv[1] + 192), (7200, -3584, lv[1], 7392, -3328, lv[1] + 160))

    # =============== Transitions 8 -> 9 (z 2304, vers l'ouest) ===============
    Z9 = lv[2]
    w.space("trench_9", "8-9", (3072, -5280, Z9, 5120, -4960, Z9 + 224), light_step=512)
    w.space("trench_9_pit", "8-9", (3328, -5200, Z9 - 64, 4864, -5040, Z9), light=None, floor=MAT_GRATE)
    w.add(ramp(3328, -5200, 3456, -5040, Z9 - 64, Z9, "-x", base=Z9 - 80))
    w.add(ramp(4736, -5200, 4864, -5040, Z9 - 64, Z9, "+x", base=Z9 - 80))
    M["doors"].append(("gn_door_8a", "x", 5072, -5280, -4960, Z9, Z9 + 224))
    corridor(w, "service_9n", "8-9", [(5120, -4224), (4608, -4224), (4608, -3840), (3584, -3840),
                                       (3584, -4224), (3072, -4224)], 192, 160, z0=Z9)
    M["doors"].append(("gn_door_8n", "x", 5072, -4320, -4128, Z9, Z9 + 160))
    for i, (x0, h) in enumerate([(4608, 288), (4096, 352), (3584, 256), (3072, 320)]):
        w.space(f"ice_gallery3_{i}", "8-9", (x0, -6112, Z9, x0 + 512, -5664, Z9 + h), floor=MAT_ICE, wall=MAT_ICE,
                ceil=MAT_ICE, light=ICE_LIGHT, light_step=512)
    M["doors"].append(("gn_door_8s", "x", 5072, -6112, -5664, Z9, Z9 + 288))
    M["tour"] += [("z89_tranchee", (5000, -5120, Z9 + 64), (5, 180, 0))]

    # =============== ZONE 9 : noyau du canon ===============
    KX, KY, KZ = -10240, -5120, Z9          # ancien noyau décalé (entrée à l'est, sortie à l'ouest)
    def K(b):
        return (b[0] + KX, b[1] + KY, b[2] + KZ, b[3] + KX, b[4] + KY, b[5] + KZ)
    def KB(b, mat=MAT_METAL, kind="detail", top=None):
        w.block(K(b), mat, kind, top)
    w.space("core", "9", K((10240, -1536, -1024, 13312, 1536, 1024)), light=None, wall=MAT_METAL)
    M["zones"]["9"] = K((10240, -1536, -1024, 13312, 1536, 1024))
    G = MAT_GRATE
    KB((10240, -1024, -32, 10496, 1024, 0), top=G)
    KB((12928, -1024, -32, 13312, 1024, 0), top=G)
    for (y0, y1) in ((-768, -512), (512, 768)):
        KB((10496, y0, -32, 10880, y1, 0), top=G)
        KB((10496, y0 - 16, 0, 10880, y0, 48), MAT_RAIL); KB((10496, y1, 0, 10880, y1 + 16, 48), MAT_RAIL)
        KB((12672, y0, -32, 12928, y1, 0), top=G)
        KB((12672, y0 - 16, 0, 12928, y0, 48), MAT_RAIL); KB((12672, y1, 0, 12928, y1 + 16, 48), MAT_RAIL)
    rx0, ry0, rx1, ry1 = 10880, -1152, 12672, 1152
    ix0, iy0, ix1, iy1 = 11136, -896, 12416, 896
    KB((rx0, ry0, -32, rx1, iy0, 0), top=G); KB((rx0, iy1, -32, rx1, ry1, 0), top=G)
    KB((rx0, iy0, -32, ix0, iy1, 0), top=G); KB((ix1, iy0, -32, rx1, iy1, 0), top=G)
    KB((rx0, ry0 - 16, 0, rx1, ry0, 48), MAT_RAIL); KB((rx0, ry1, 0, rx1, ry1 + 16, 48), MAT_RAIL)
    for (a, b) in ((iy0 + 16, -128), (128, iy1 - 16)):
        KB((ix0 - 16, a, 0, ix0, b, 48), MAT_RAIL); KB((ix1, a, 0, ix1 + 16, b, 48), MAT_RAIL)
    for (a, b) in ((ix0, 11648), (11904, ix1)):
        KB((a, iy0, 0, b, iy0 + 16, 48), MAT_RAIL); KB((a, iy1 - 16, 0, b, iy1, 48), MAT_RAIL)
    w.add(oct_prism(11776 + KX, 0 + KY, 256, -1024 + KZ, 1024 + KZ, MAT_HAZARD, "world"))      # réacteur
    RCX, RCY = 11776 + KX, 0 + KY
    M["reactor_center"] = (RCX, RCY, KZ)
    for rz in (-896, -640, -384, 320, 640, 896):            # bagues de confinement
        w.add(oct_prism(RCX, RCY, 300, rz + KZ, rz + KZ + 40, MAT_METAL, "detail"))
    for (dx, dy) in ((352, 352), (-352, 352), (352, -352), (-352, -352)):   # conduites de refroidissement
        w.add(oct_prism(RCX + dx, RCY + dy, 28, -1024 + KZ, 1024 + KZ, MAT_RAIL, "detail"))
    for sb in ((10240, -704, 96, 10248, -448, 352), (10240, 448, 96, 10248, 704, 352),
               (13304, -704, 96, 13312, -448, 352), (13304, 448, 96, 13312, 704, 352)):
        KB(sb, "givre_noir/danger_reacteur")
    KB((11392, -384, -32, 12160, 384, 0), top=G)
    M["reactor_buttons"] = [K((11480, -24, 0, 11528, 24, 64)), K((12024, -24, 0, 12072, 24, 64)),
                            K((11752, 248, 0, 11800, 296, 64))]
    M["bridges"] = [("gn_core_bridge_1", K((12160, -128, -32, ix1, 128, 0)), "0 0 0", 256),
                    ("gn_core_bridge_2", K((ix0, -128, -32, 11392, 128, 0)), "0 180 0", 256),
                    ("gn_core_bridge_3", K((11648, 384, -32, 11904, iy1, 0)), "0 90 0", 512),
                    ("gn_core_bridge_4", K((11648, iy0, -32, 11904, -384, 0)), "0 270 0", 512)]
    for sy in (1, -1):
        y0, y1 = (1280, 1536) if sy > 0 else (-1536, -1280)
        KB((12928, y0, -32, 13312, y1, 0), top=G)
        KB((12928, (1024 if sy > 0 else -1280), -32, 13312, (1280 if sy > 0 else -1024), 0), top=G)
        kb = K((12160, y0, 0, 12928, y1, 0))
        w.add(slope_slab(kb[0], kb[1], kb[3], kb[4], KZ, KZ + 384, "-x"))
        KB((10880, y0, 352, 12160, y1, 384), top=G)
        KB((10880, (y0 - 16) if sy > 0 else y1, 384, 12160, y0 if sy > 0 else y1 + 16, 432), MAT_RAIL)
        KB((12160, (y0 - 16) if sy > 0 else y1, 0, 12928, y0 if sy > 0 else y1 + 16, 432), MAT_RAIL)
    KB((11648, 1152, -32, 11904, 1280, 0), top=G)
    KB((11648, 1280, -32, 11904, 1536, 0), top=G)
    M["core_hurt"] = K((10240, -1536, -1024, 13312, 1536, -896))
    M["core_lights"] = [(x + KX, y + KY, z + KZ) for x in (10560, 11776, 12992) for y in (-1024, 0, 1024)
                        for z in (192, 768) if not (x == 11776 and y == 0)]
    M["core_light_main"] = (11776 + KX, 640 + KY, 900 + KZ)
    M["tour"] += [("z9_noyau", (2900, -6000, KZ + 128), (10, 150, 0)), ("z9_reacteur", (1200, -4100, KZ + 500), (25, -40, 0))]
    closet(w, "9", K((11392, 1792, 0, 12160, 2304, 192)), K((11680, 1536, 0, 11872, 1792, 160)))

    # =============== ZONE 10 : exfiltration (3 puits, chrono 8 min) ===============
    def shaft(name, x0, y0, z0):
        S = 1536
        w.space(name, "10", (x0, y0, z0, x0 + S, y0 + S, z0 + 1536 + 256), light=None, wall=MAT_METAL)
        a, b = 256, S - 256
        w.add(ramp(x0 + a, y0, x0 + b, y0 + a, z0, z0 + 384, "+x", base=z0 - 16))
        w.block((x0 + b, y0, z0, x0 + S, y0 + a, z0 + 384), MAT_METAL, top=MAT_GRATE)
        w.add(slope_slab(x0 + b, y0 + a, x0 + S, y0 + b, z0 + 384, z0 + 768, "+y"))
        w.block((x0 + b, y0 + b, z0 + 736, x0 + S, y0 + S, z0 + 768), MAT_METAL, top=MAT_GRATE)
        w.add(slope_slab(x0 + a, y0 + b, x0 + b, y0 + S, z0 + 768, z0 + 1152, "-x"))
        w.block((x0, y0 + b, z0 + 1120, x0 + a, y0 + S, z0 + 1152), MAT_METAL, top=MAT_GRATE)
        w.add(slope_slab(x0, y0 + a, x0 + a, y0 + b, z0 + 1152, z0 + 1536, "-y"))
        w.block((x0, y0, z0 + 1504, x0 + a, y0 + a, z0 + 1536), MAT_METAL, top=MAT_GRATE)
        w.add(slope_slab(x0 + a, y0 + a, x0 + b, y0 + a + 16, z0 + 48, z0 + 432, "+x", thick=48, mat=MAT_RAIL))
        w.add(slope_slab(x0 + b - 16, y0 + a, x0 + b, y0 + b, z0 + 432, z0 + 816, "+y", thick=48, mat=MAT_RAIL))
        w.add(slope_slab(x0 + a, y0 + b - 16, x0 + b, y0 + b, z0 + 816, z0 + 1200, "-x", thick=48, mat=MAT_RAIL))
        w.add(slope_slab(x0 + a, y0 + a, x0 + a + 16, y0 + b, z0 + 1200, z0 + 1584, "-y", thick=48, mat=MAT_RAIL))
        z_l = [z0 + 256, z0 + 640, z0 + 1024, z0 + 1408, z0 + 1700]
        for i, (lx, ly) in enumerate([(x0 + S // 2, y0 + 128), (x0 + S - 128, y0 + S // 2),
                                       (x0 + S // 2, y0 + S - 128), (x0 + 128, y0 + S // 2), (x0 + 128, y0 + 128)]):
            M["lights"].append(((lx, ly, z_l[i]), "255 120 90 420"))
        return (x0, y0, z0)
    corridor(w, "exfil_e0", "10", [(0, -5120), (-768, -5120), (-768, -6400), (-2432, -6400), (-2432, -6016)], 256, 192, z0=Z9)
    M["doors"].append(("gn_exfil_door_0", "x", -48, -5248, -4992, Z9, Z9 + 192))
    s1 = shaft("shaft_1", -2560, -6016, Z9)
    z2 = Z9 + 1536
    corridor(w, "exfil_e1", "10", [(-2560, -5888), (-3328, -5888), (-3328, -6400), (-5248, -6400), (-5248, -6016)], 256, 192, z0=z2)
    M["doors"].append(("gn_exfil_door_1", "x", -2624, -6016, -5760, z2, z2 + 192))
    M["doors"].append(("gn_exfil_door_2", "y", -6064, -5376, -5120, z2, z2 + 192))
    s2 = shaft("shaft_2", -5376, -6016, z2)
    z3 = z2 + 1536
    corridor(w, "exfil_e2", "10", [(-5376, -5888), (-6144, -5888), (-6144, -6400), (-8064, -6400), (-8064, -6016)], 256, 192, z0=z3)
    M["doors"].append(("gn_exfil_door_3", "x", -5440, -6016, -5760, z3, z3 + 192))
    M["doors"].append(("gn_exfil_door_4", "y", -6064, -8192, -7936, z3, z3 + 192))
    s3 = shaft("shaft_3", -8192, -6016, z3)
    z4 = z3 + 1536
    corridor(w, "exfil_e3", "10", [(-8192, -5888), (-8448, -5888)], 256, 192, z0=z4)
    M["doors"].append(("gn_exfil_door_5", "x", -8432, -6016, -5760, z4, z4 + 192))
    # scellements : sommet puits 1, bas puits 2, sommet puits 2, bas puits 3, sommet puits 3
    M["seals"] = [((-2560, -6016, Z9 + 1536, -2304, -5760, Z9 + 1664), "gn_exfil_door_0"),
                  ((-5376, -6016, z2, -5120, -5760, z2 + 128), "gn_exfil_door_1"),
                  ((-5376, -6016, z3, -5120, -5760, z3 + 128), "gn_exfil_door_2"),
                  ((-8192, -6016, z3, -7936, -5760, z3 + 128), "gn_exfil_door_3"),
                  ((-8192, -6016, z4, -7936, -5760, z4 + 128), "gn_exfil_door_4")]
    M["zones"]["10"] = (-8192, -6528, Z9, -640, -4480, z4 + 256)
    M["tour"] += [("z10_puits1", (-2430, -5900, Z9 + 64), (-20, 20, 0)), ("z10_puits3", (-8050, -5900, z3 + 300), (-15, 30, 0))]
    closet(w, "10", (-4736, -7168, z2, -3840, -6656, z2 + 192), (-4352, -6656, z2, -4160, -6528, z2 + 160))

    # =============== ZONE 11 : sommet du glacier, extraction LAAT ===============
    GLX0, GLY0, GLX1, GLY1 = -13312, -8192, -8448, -3840
    w.space("glacier", "11", (GLX0, GLY0, z4, GLX1, GLY1, z4 + 1536), sky=True, floor=MAT_ICE, wall=MAT_ICE, light=None)
    M["zones"]["11"] = (GLX0, GLY0, z4, GLX1, GLY1, z4 + 1536)
    px, py = -10880, -6016
    w.block((px - 512, py - 512, z4, px + 512, py + 512, z4 + 64), MAT_HAZARD, top=MAT_HAZARD)
    w.add(ramp(px + 512, py - 256, px + 768, py + 256, z4, z4 + 64, "-x", base=z4 - 16))
    w.add(ramp(px - 768, py - 256, px - 512, py + 256, z4, z4 + 64, "+x", base=z4 - 16))
    w.add(ramp(px - 256, py + 512, px + 256, py + 768, z4, z4 + 64, "-y", base=z4 - 16))
    w.add(ramp(px - 256, py - 768, px + 256, py - 512, z4, z4 + 64, "+y", base=z4 - 16))
    M["extract"] = (px - 512, py - 512, z4 + 64, px + 512, py + 512, z4 + 256)
    M["glacier_trigger"] = (-8960, -6016, z4, -8464, -5760, z4 + 192)
    for (bx, by) in [(-9472, -5248), (-9472, -6784), (-9856, -6016), (-12160, -5120), (-12160, -6912),
                     (-11648, -4608), (-11648, -7424), (-9984, -4480), (-9984, -7552)]:
        crate(w, bx, by, z=z4, s=192, h=128, mat=MAT_ICE)
    for i, x in enumerate(range(GLX0, GLX1, 512)):
        d = (128, 256, 192, 320)[i % 4]
        x1 = min(x + 512, GLX1)
        rock(w, (x, GLY0, z4, x1, GLY0 + d, z4 + 256 + d), mat=MAT_ICE)
        rock(w, (x, GLY1 - d, z4, x1, GLY1, z4 + 256 + d), mat=MAT_ICE)
    M["glacier_lights"] = [(-9216, -6016, z4 + 500), (-11008, -6016, z4 + 500), (-12544, -6016, z4 + 500)]
    M["tour"] += [("z11_glacier", (-8700, -4300, z4 + 128), (8, -150, 0)), ("z11_laat", (-9600, -7600, z4 + 260), (12, 135, 0))]
    w.space("closet_11", "11", (-14080, -6400, z4, -13568, -5632, z4 + 192), light="255 200 160 300", light_step=512)
    corridor(w, "closet_11_link", "11", [(-13312, -4864), (-13824, -4864), (-13824, -5632)], 192, 160, z0=z4, light=None)
    M["def_spawns"]["11"] = spawn_grid(-13824, -6016, z4 + 4)

    # =============== ciel 3D (inaccessible) : vaisseaux au 1/16 ===============
    # « Star Wars - Skybox Space Props » (Lord Trilobite, Workshop 1708099047, élément requis)
    from geom import MAT_SKY
    w.space("ciel_3d", "ciel", (-6144, 4352, 0, 6144, 14336, 4096), sky=True,
            floor=MAT_SKY, wall=MAT_SKY, ceil=MAT_SKY, light=None)
    cam = (0, 9344, 512)
    M["sky_camera"] = cam
    M["sky_props"] = [
        ("models/lordtrilobite/starwars/props/venator_16.mdl", (cam[0] - 1600, cam[1] + 2200, cam[2] + 1300), 200),
        ("models/lordtrilobite/starwars/props/venator_16.mdl", (cam[0] + 2600, cam[1] + 1200, cam[2] + 1900), 160),
    ]

    # points de vue supplémentaires (revue de l'habillage)
    M["tour"] += [
        ("v1_largage", (-13300, 0, 120), (10, 180, 0)), ("v2_hangar_sud", (-8000, -800, 200), (10, 30, 0)),
        ("v2_hangar_facade", (-7600, 900, 120), (5, -10, 0)), ("v3b_hall", (-3000, 400, 180), (10, -150, 0)),
        ("v3a_tunnel", (-1500, 2064, 8), (0, 180, 0)), ("v4_usine_sud", (300, -1200, 300), (10, 40, 0)),
        ("v4_usine_est", (2800, 0, 150), (5, 180, 0)), ("v5_garnison_e1", (7400, -900, 450), (5, 160, 0)),
        ("v6_dc_sud", (10400, -1300, 832), (5, 45, 0)), ("v6_dc_nord", (12900, 900, 1100), (15, -150, 0)),
        ("v7_prison_cellules", (12500, -4400, 1200), (10, -30, 0)), ("v8_tour_n1", (5400, -6400, 1340), (10, 45, 0)),
        ("v8_tour_n3", (7900, -3800, 2370), (15, -135, 0)), ("v9_noyau_ouest", (128, -4600, 2370), (5, -30, 0)),
        ("v10_couloir", (-3328, -6100, 3880), (5, -90, 0)), ("v11_glacier_feux", (-11000, -5000, 7050), (10, -120, 0)),
    ]

    # planchers supplémentaires à habiller (étages, mezzanines, coursives)
    M["floors"] = {"garrison": [384, 768], "factory": [256], "prison": [Z + 384], "comm_tower": lv}

    # chanfreins mur/plafond partout où ça ne bouche pas un passage
    add_chamfers(w, skip=("_d", "doorway", "catwalk_n", "catwalk_s", "pit", "ciel", "drop", "crawl", "link"))

    # ---------- points de réapparition progressifs (attaquants), un groupe par phase ----------
    M["atk_respawns"] = {
        "2": spawn_grid(-10560, 0, 4, step=80),            # fin du canyon
        "3": spawn_grid(-8704, 0, 4, step=80),             # entrée du hangar
        "4": spawn_grid(-4928, -448, 4, step=80),          # début du hall d'assaut
        "5": spawn_grid(4096, 0, 4, step=96),              # sas 4 -> 5
        "6": spawn_grid(9216, 0, Z + 4, step=64),          # galerie de glace 5 -> 6
        "7": spawn_grid(11776, -320, Z + 4, step=80),      # salle du hack (fermée)
        "8": spawn_grid(9216, -5120, Z + 4, step=96),      # chambre du sas 7 -> 8
        "9": spawn_grid(4096, -5888, Z9 + 4, step=64),     # galerie de glace 8 -> 9
        "10": spawn_grid(128, -5120, Z9 + 4, step=56),     # quai ouest du noyau
        "11": spawn_grid(-9216, -5888, z4 + 4, step=80),   # sur le glacier (devant la porte qui se referme)
    }
    return w
