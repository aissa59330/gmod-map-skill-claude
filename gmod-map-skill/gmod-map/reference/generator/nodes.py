"""Réseau de navigation des PNJ (info_node) pour les bots/PNJ de l'event.

Grille sur chaque sol (pas de 320 à l'intérieur, 704 dehors), à 48 u des murs, jamais :
dans un bloc / un prop / un clip, au-dessus du vide, ni dans une zone de trigger_hurt.
Les info_node n'occupent pas d'edict : le jeu construit le graphe (maps/graphs/givre_noir.ain) au premier chargement.
Plafond : 3500 nœuds (limite moteur 4096).
"""
from geom import Block

MAX_NODES = 3500
SKIP = ("ciel", "_d", "doorway", "drop", "crawl")


def _inside(p, b):
    return b[0] <= p[0] <= b[3] and b[1] <= p[1] <= b[4] and b[2] <= p[2] <= b[5]


def _overlap(a, b):
    return a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4] and a[2] < b[5] and b[2] < a[5]


def build(w, prop_boxes):
    M = w.meta
    blocks = [b.box if isinstance(b, Block) else b.bbox for b in w.blocks]
    hurts = [sb.box if isinstance(sb, Block) else sb.bbox for e in w.ents if e["classname"] == "trigger_hurt" for sb in e["solids"]]
    solids_below = blocks + [sl[0] for sl in w.shell_slabs()]
    # index grossier des obstacles
    obst = blocks + list(prop_boxes)
    cell = 512
    grid = {}
    for b in obst:
        for ix in range(int(b[0] // cell), int(b[3] // cell) + 1):
            for iy in range(int(b[1] // cell), int(b[4] // cell) + 1):
                grid.setdefault((ix, iy), []).append(b)
    under = {}
    for b in solids_below:
        for ix in range(int(b[0] // cell), int(b[3] // cell) + 1):
            for iy in range(int(b[1] // cell), int(b[4] // cell) + 1):
                under.setdefault((ix, iy), []).append(b)

    nodes = []
    for s in w.spaces:
        if any(k in s.name for k in SKIP):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        if z1 - z0 < 96 or min(x1 - x0, y1 - y0) < 96:
            continue
        step = 704 if s.sky else 320          # moins de noeuds = recherche de chemin plus légère (600 PNJ)
        floors = [z0] + [f for f in M.get("floors", {}).get(s.name, []) if s.name != "comm_tower"]
        nx = max(1, int((x1 - x0 - 96) // step) + 1)
        ny = max(1, int((y1 - y0 - 96) // step) + 1)
        for f in floors:
            for i in range(nx):
                for j in range(ny):
                    x = x0 + 48 + (i + 0.5) * (x1 - x0 - 96) / nx
                    y = y0 + 48 + (j + 0.5) * (y1 - y0 - 96) / ny
                    hull = (x - 20, y - 20, f + 2, x + 20, y + 20, f + 72)
                    key = (int(x // cell), int(y // cell))
                    if any(_overlap(hull, b) for b in grid.get(key, ())):
                        continue
                    if f > z0 and not any(_inside((x, y, f - 4), b) for b in under.get(key, ())):
                        continue                                # pas de plancher à cet étage ici
                    if any(_inside((x, y, f + 16), h) for h in hurts):
                        continue
                    if z0 < -16 and f == z0 and s.name.endswith("pit"):
                        continue
                    nodes.append((round(x), round(y), f + 16))
    if len(nodes) > MAX_NODES:                                  # éclaircit uniformément
        k = len(nodes) / MAX_NODES
        nodes = [nodes[int(i * k)] for i in range(MAX_NODES)]
    for k, p in enumerate(nodes):
        w.ent("info_node", p, nodeid=k + 1)
    M["nodes"] = len(nodes)
    return len(nodes)
