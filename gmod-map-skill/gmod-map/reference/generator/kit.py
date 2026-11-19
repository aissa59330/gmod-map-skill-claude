"""Kit architectural : ce qui transforme des « boîtes » en architecture.

Pour chaque salle intérieure :
- soubassement bicolore (lambris sombre 0-96 u) + moulure ;
- nervures verticales (piliers engagés) à intervalle régulier ;
- poutres de plafond dans les grandes salles ;
Pour chaque porte : encadrement (montants + linteau) des deux côtés.
Tout s'interrompt au droit des ouvertures (couloirs, portes, cellules).
"""
from geom import Block

# matériaux « logiques » du kit (remplacés par theme.KIT selon le thème de la zone)
KIT_DADO = "kit/dado"
KIT_TRIM = "kit/trim"
KIT_RIB = "kit/rib"
KIT_BEAM = "kit/beam"
KIT_FRAME = "kit/frame"
KIT_LIGHT = "kit/light"

SKIP = ("_d", "doorway", "pit", "ciel", "crawl", "drop", "catwalk_n", "catwalk_s", "shaft", "glacier", "canyon",
        "hangar", "closet_1_link", "closet_11_link")


OBST = []      # boîtes des obstacles posés contre les murs (rampes, piliers, plateformes...), remplies dans build()


def openings(w, s, side):
    """Ouvertures d'un mur : (u0, u1, z_bas, z_haut) des volumes voisins qui le traversent."""
    x0, y0, z0, x1, y1, z1 = s.box
    out = []
    for o in w.spaces:
        if o is s:
            continue
        bx = o.box
        if bx[5] <= z0 or bx[2] >= z1:
            continue
        if side == "x0" and bx[3] >= x0 and bx[0] < x0 and bx[1] < y1 and bx[4] > y0:
            out.append((max(bx[1], y0), min(bx[4], y1), max(bx[2], z0), min(bx[5], z1)))
        elif side == "x1" and bx[0] <= x1 and bx[3] > x1 and bx[1] < y1 and bx[4] > y0:
            out.append((max(bx[1], y0), min(bx[4], y1), max(bx[2], z0), min(bx[5], z1)))
        elif side == "y0" and bx[4] >= y0 and bx[1] < y0 and bx[0] < x1 and bx[3] > x0:
            out.append((max(bx[0], x0), min(bx[3], x1), max(bx[2], z0), min(bx[5], z1)))
        elif side == "y1" and bx[1] <= y1 and bx[4] > y1 and bx[0] < x1 and bx[3] > x0:
            out.append((max(bx[0], x0), min(bx[3], x1), max(bx[2], z0), min(bx[5], z1)))
    return out


def free_intervals(w, s, side, zlo, zhi, margin=24):
    """Intervalles (u0, u1) le long d'un mur, hors ouvertures et hors obstacles collés au mur, entre zlo et zhi."""
    x0, y0, z0, x1, y1, z1 = s.box
    if side in ("x0", "x1"):
        a, b = y0, y1
    else:
        a, b = x0, x1
    cuts = []
    band = strip(side, s.box, a, b, zlo, zhi, 40)
    for ob in OBST:
        if ob[0] < band[3] and band[0] < ob[3] and ob[1] < band[4] and band[1] < ob[4] and ob[2] < band[5] and band[2] < ob[5]:
            cuts.append((ob[1], ob[4]) if side in ("x0", "x1") else (ob[0], ob[3]))
    for o in w.spaces:
        if o is s:
            continue
        bx = o.box
        if bx[5] <= zlo or bx[2] >= zhi:
            continue
        if side == "x0" and bx[3] >= x0 and bx[0] < x0 and bx[1] < y1 and bx[4] > y0:
            cuts.append((bx[1], bx[4]))
        elif side == "x1" and bx[0] <= x1 and bx[3] > x1 and bx[1] < y1 and bx[4] > y0:
            cuts.append((bx[1], bx[4]))
        elif side == "y0" and bx[4] >= y0 and bx[1] < y0 and bx[0] < x1 and bx[3] > x0:
            cuts.append((bx[0], bx[3]))
        elif side == "y1" and bx[1] <= y1 and bx[4] > y1 and bx[0] < x1 and bx[3] > x0:
            cuts.append((bx[0], bx[3]))
    cuts = sorted((max(a, c0 - margin), min(b, c1 + margin)) for c0, c1 in cuts)
    out, cur = [], a
    for c0, c1 in cuts:
        if c0 > cur:
            out.append((cur, c0))
        cur = max(cur, c1)
    if cur < b:
        out.append((cur, b))
    return [(u0, u1) for (u0, u1) in out if u1 - u0 >= 48]


def strip(side, box, u0, u1, zlo, zhi, depth):
    """Boîte collée au mur `side` de la salle `box`, entre u0 et u1, de profondeur `depth`."""
    x0, y0, z0, x1, y1, z1 = box
    if side == "x0":
        return (x0, u0, zlo, x0 + depth, u1, zhi)
    if side == "x1":
        return (x1 - depth, u0, zlo, x1, u1, zhi)
    if side == "y0":
        return (u0, y0, zlo, u1, y0 + depth, zhi)
    return (u0, y1 - depth, zlo, u1, y1, zhi)


def g16(v):
    return int(round(v / 16.0)) * 16


def build(w):
    M = w.meta
    n = {"dado": 0, "rib": 0, "beam": 0, "frame": 0}
    OBST.clear()
    for b in w.blocks:
        OBST.append(b.box if isinstance(b, Block) else b.bbox)
    for e in w.ents:
        if e["classname"] in ("func_door", "func_button", "func_breakable", "func_movelinear", "func_conveyor"):
            OBST.extend(sb.box if isinstance(sb, Block) else sb.bbox for sb in e["solids"])
    for s in w.spaces:
        if s.sky or any(k in s.name for k in SKIP):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        h, wx, wy = z1 - z0, x1 - x0, y1 - y0
        if h < 160 or min(wx, wy) < 128:
            continue
        big = min(wx, wy) >= 1024
        narrow = min(wx, wy) <= 448
        dado_h = 96 if h >= 224 else 64
        d_dado = 4 if narrow else 6
        rib_step = 512                       # (256 dans les couloirs avant : 2x plus de brushes et de jonctions)
        rib_w = 32 if narrow else 48
        d_rib = 8 if narrow else 16
        top_rib = z1 - (32 if h < 256 else (64 if h < 512 else 128))      # sous le chanfrein
        floors = [z0] + [f for f in M.get("floors", {}).get(s.name, []) if s.name != "comm_tower"]
        for side in ("x0", "x1", "y0", "y1"):
            for zf in floors:
                zt = (floors[floors.index(zf) + 1] - 32) if zf != floors[-1] else top_rib
                for (u0, u1) in free_intervals(w, s, side, zf, zf + dado_h + 8):
                    w.block(strip(side, s.box, u0, u1, zf, zf + dado_h, d_dado), KIT_DADO)
                    w.block(strip(side, s.box, u0, u1, zf + dado_h, zf + dado_h + 8, d_dado + 4), KIT_TRIM)
                    # clip joueurs/PNJ lisse devant le soubassement, les nervures et la moulure :
                    # les collisions se font contre UN plan au lieu de dizaines de petites brushes
                    w.block(strip(side, s.box, u0, u1, zf, min(zf + 160, zt), max(d_rib, d_dado + 4)), "tools/toolsclip")
                    n["dado"] += 1
                    n["clip"] = n.get("clip", 0) + 1
                # nervures + travées (espaces entre deux nervures, pour l'ambiance)
                for (u0, u1) in free_intervals(w, s, side, zf, zt, margin=48):
                    k = int((u1 - u0) // rib_step)
                    ribs = []
                    for i in range(1, k + 1):
                        u = g16(u0 + i * (u1 - u0) / (k + 1))
                        if u - rib_w // 2 < u0 + 16 or u + rib_w // 2 > u1 - 16:
                            continue
                        w.block(strip(side, s.box, u - rib_w // 2, u + rib_w // 2, zf, zt, d_rib), KIT_RIB)
                        ribs.append(u)
                        n["rib"] += 1
                    edges = [u0] + [r for r in ribs] + [u1]
                    for j in range(len(edges) - 1):
                        b0 = edges[j] + (rib_w // 2 + 8 if j > 0 else 8)
                        b1 = edges[j + 1] - (rib_w // 2 + 8 if j < len(edges) - 2 else 8)
                        if b1 - b0 >= 96:
                            M.setdefault("bays", []).append((s.name, side, b0, b1, zf, s.box, d_rib))
        # poutres de plafond (grandes salles) : en travers de la petite dimension, tous les 512
        if big and h >= 320:
            zb = z1 - 40
            if wx >= wy:
                for x in range(x0 + 512, x1 - 255, 512):
                    w.block((x - 24, y0, zb, x + 24, y1, z1), KIT_BEAM)
                    n["beam"] += 1
            else:
                for y in range(y0 + 512, y1 - 255, 512):
                    w.block((x0, y - 24, zb, x1, y + 24, z1), KIT_BEAM)
                    n["beam"] += 1
    # encadrements des ouvertures, côté salle : montants + linteau autour de chaque couloir qui débouche
    for s in w.spaces:
        if s.name != "hangar" and (s.sky or any(k in s.name for k in SKIP)):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        if min(x1 - x0, y1 - y0) < 448 or z1 - z0 < 224:
            continue
        for side in ("x0", "x1", "y0", "y1"):
            wall_len = (y1 - y0) if side in ("x0", "x1") else (x1 - x0)
            for (c0, c1, oz0, oz1) in openings(w, s, side):
                if c1 - c0 > 0.7 * wall_len or oz1 + 40 > z1 or oz0 > z0 + 8:
                    continue                      # grande ouverture, ou passage en hauteur : pas de cadre
                for p in (strip(side, s.box, c0 - 32, c0, oz0, oz1 + 32, 20),
                          strip(side, s.box, c1, c1 + 32, oz0, oz1 + 32, 20),
                          strip(side, s.box, c0 - 32, c1 + 32, oz1, oz1 + 32, 20)):
                    if not any(_overlap(p, ob) for ob in OBST):
                        w.block(p, KIT_FRAME)
                        n["frame"] += 1
    M["kit_stats"] = n
    return n


def _overlap(a, b):
    return a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4] and a[2] < b[5] and b[2] < a[5]


def _in_air(w, p):
    """Le morceau d'encadrement est-il dans un volume d'air (sinon il est déjà dans le mur) ?"""
    cx, cy, cz = (p[0] + p[3]) / 2, (p[1] + p[4]) / 2, (p[2] + p[5]) / 2
    return any(s.box[0] < cx < s.box[3] and s.box[1] < cy < s.box[4] and s.box[2] < cz < s.box[5] for s in w.spaces)
