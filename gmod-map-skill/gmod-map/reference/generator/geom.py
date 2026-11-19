"""Géométrie de base : volumes d'air (Space), CSG par boîtes, rampes, export VMF.

Principe : chaque Space est un volume d'air entouré de 6 dalles de 16 u.
Toutes les dalles sont ensuite privées de TOUS les volumes d'air : là où deux
volumes se touchent ou se chevauchent, le mur disparaît (ouverture). La frontière
de l'union des volumes d'air reste toujours couverte de matière -> map scellée.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from srctools import Vec
from srctools.vmf import VMF, Side, Solid

WALL = 16
LIMIT = 16384

MAT_FLOOR = "dev/dev_measuregeneric01b"
MAT_WALL = "dev/dev_measurewall01a"
MAT_CEIL = "dev/dev_measurewall01d"
MAT_ICE = "dev/dev_measureice01"
MAT_ROCK = "dev/dev_concretewall020a"
MAT_METAL = "dev/dev_lowerwallmetal01a"
MAT_GRATE = "dev/dev_interiorfloorgrate03b"
MAT_CRATE = "dev/dev_measurecrate01"
MAT_HAZARD = "dev/dev_hazzardstripe01a"
MAT_DOOR = "dev/dev_lowermetaldoor01"
MAT_SWITCH = "dev/dev_measureswitch01"
MAT_COMPUTER = "dev/dev_measurecomputer01"
MAT_RAIL = "dev/dev_measurerails01"
MAT_SKY = "tools/toolsskybox"
MAT_NODRAW = "tools/toolsnodraw"
MAT_TRIGGER = "tools/toolstrigger"
MAT_PORTAL = "tools/toolsareaportal"
MAT_CLIP = "tools/toolsplayerclip"

Box = tuple  # (x0, y0, z0, x1, y1, z1)


def norm(b: Box) -> Box:
    x0, y0, z0, x1, y1, z1 = b
    return (min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1))


def overlap(a: Box, b: Box) -> bool:
    return (a[0] < b[3] and b[0] < a[3] and a[1] < b[4] and b[1] < a[4]
            and a[2] < b[5] and b[2] < a[5])


def contains_pt(b: Box, p, eps=0.0) -> bool:
    return (b[0] - eps <= p[0] <= b[3] + eps and b[1] - eps <= p[1] <= b[4] + eps
            and b[2] - eps <= p[2] <= b[5] + eps)


def merge_slabs(items):
    """Fusionne les morceaux de dalle qui partagent une face entière (même matériau / rôle / volume) :
    moins de brushes world, moins de faces et de jonctions en T (triangles en éventail)."""
    changed = True
    items = list(items)
    while changed:
        changed = False
        for ax in range(3):
            o = [i for i in range(3) if i != ax]
            idx = {}
            for k, it in enumerate(items):
                b = it[0]
                key = (it[1:], b[o[0]], b[o[0] + 3], b[o[1]], b[o[1] + 3])
                idx.setdefault(key, []).append(k)
            dead = set()
            new = []
            for key, ks in idx.items():
                ks = sorted(ks, key=lambda k: items[k][0][ax])
                cur = None
                for k in ks:
                    b = items[k][0]
                    if cur is not None and abs(cur[0][ax + 3] - b[ax]) < 1e-6:
                        nb = list(cur[0]); nb[ax + 3] = b[ax + 3]
                        cur = (tuple(nb),) + cur[1:]
                        dead.add(k); changed = True
                    else:
                        if cur is not None:
                            new.append(cur)
                        cur = items[k]
                        dead.add(k)
                if cur is not None:
                    new.append(cur)
            items = new
    return items


def box_sub(a: Box, b: Box) -> list[Box]:
    """a - b, en boîtes alignées (au plus 6 morceaux)."""
    if not overlap(a, b):
        return [a]
    x0, y0, z0, x1, y1, z1 = a
    out = []
    if b[0] > x0:
        out.append((x0, y0, z0, b[0], y1, z1)); x0 = b[0]
    if b[3] < x1:
        out.append((b[3], y0, z0, x1, y1, z1)); x1 = b[3]
    if b[1] > y0:
        out.append((x0, y0, z0, x1, b[1], z1)); y0 = b[1]
    if b[4] < y1:
        out.append((x0, b[4], z0, x1, y1, z1)); y1 = b[4]
    if b[2] > z0:
        out.append((x0, y0, z0, x1, y1, b[2])); z0 = b[2]
    if b[5] < z1:
        out.append((x0, y0, b[5], x1, y1, z1))
    return out


@dataclass
class Space:
    name: str
    zone: str
    box: Box
    sky: bool = False
    floor: str = MAT_FLOOR
    wall: str = MAT_WALL
    ceil: str = MAT_CEIL
    light: str | None = "255 244 228 450"   # None = pas de lumières auto
    light_step: int = 768
    light_drop: int = 48
    light_levels: list | None = None   # hauteurs absolues des lumières (salles à étages)

    def __post_init__(self):
        self.box = norm(self.box)
        for v in self.box:
            assert v % 16 == 0, f"{self.name}: hors grille {self.box}"
            assert abs(v) < LIMIT - 64, f"{self.name}: hors limites {self.box}"


@dataclass
class Block:
    """Brush plein (décor / structure). kind = world | detail."""
    box: Box
    mat: str = MAT_METAL
    kind: str = "detail"
    top: str | None = None

    def __post_init__(self):
        self.box = norm(self.box)


@dataclass
class Poly:
    """Brush convexe quelconque défini par ses plans (point, normale sortante)."""
    planes: list
    mat: str = MAT_METAL
    kind: str = "detail"
    bbox: Box = (0, 0, 0, 0, 0, 0)
    top: str | None = None


def ramp(x0, y0, x1, y1, z_lo, z_hi, rise_dir: str, base=None, mat=MAT_FLOOR, kind="detail") -> Poly:
    """Rampe pleine : surface inclinée de z_lo à z_hi dans la direction rise_dir
    (+x, -x, +y, -y), fond plat à `base` (défaut : z_lo - 16)."""
    x0, y0, x1, y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    if base is None:
        base = z_lo - 16
    dz = z_hi - z_lo
    if rise_dir in ("+x", "-x"):
        run = x1 - x0
    else:
        run = y1 - y0
    assert dz / run <= 1.0, "pente > 45°"
    # normale du plan incliné
    if rise_dir == "+x":
        n = Vec(-dz, 0, run); p = Vec(x0, y0, z_lo)
    elif rise_dir == "-x":
        n = Vec(dz, 0, run); p = Vec(x1, y0, z_lo)
    elif rise_dir == "+y":
        n = Vec(0, -dz, run); p = Vec(x0, y0, z_lo)
    else:
        n = Vec(0, dz, run); p = Vec(x0, y1, z_lo)
    planes = [
        (p, n.norm()),
        (Vec(x0, y0, base), Vec(0, 0, -1)),
        (Vec(x0, y0, base), Vec(-1, 0, 0)),
        (Vec(x1, y1, base), Vec(1, 0, 0)),
        (Vec(x0, y0, base), Vec(0, -1, 0)),
        (Vec(x1, y1, base), Vec(0, 1, 0)),
    ]
    return Poly(planes, mat, kind, (x0, y0, base, x1, y1, z_hi))


def slope_slab(x0, y0, x1, y1, z_lo, z_hi, rise_dir: str, thick=32, mat=MAT_FLOOR, kind="detail") -> Poly:
    """Dalle inclinée d'épaisseur verticale `thick` (rampe suspendue)."""
    x0, y0, x1, y1 = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    dz = z_hi - z_lo
    run = (x1 - x0) if rise_dir in ("+x", "-x") else (y1 - y0)
    assert dz / run <= 1.0, "pente > 45°"
    if rise_dir == "+x":
        n = Vec(-dz, 0, run); p = Vec(x0, y0, z_lo)
    elif rise_dir == "-x":
        n = Vec(dz, 0, run); p = Vec(x1, y0, z_lo)
    elif rise_dir == "+y":
        n = Vec(0, -dz, run); p = Vec(x0, y0, z_lo)
    else:
        n = Vec(0, dz, run); p = Vec(x0, y1, z_lo)
    n = n.norm()
    planes = [
        (p, n),
        (p - Vec(0, 0, thick), -n),
        (Vec(x0, y0, 0), Vec(-1, 0, 0)),
        (Vec(x1, y1, 0), Vec(1, 0, 0)),
        (Vec(x0, y0, 0), Vec(0, -1, 0)),
        (Vec(x1, y1, 0), Vec(0, 1, 0)),
    ]
    return Poly(planes, mat, kind, (x0, y0, z_lo - thick, x1, y1, z_hi))


class World:
    def __init__(self):
        self.spaces: list[Space] = []
        self.blocks: list = []          # Block | Poly (dans l'air, non soustraits)
        self.ents: list[dict] = []      # entités ponctuelles / brush
        self.carve: list[Box] = []      # volumes d'air supplémentaires (fosses, trous)

    # ---- construction ----
    def space(self, *a, **k) -> Space:
        s = Space(*a, **k)
        self.spaces.append(s)
        return s

    def block(self, box, mat=MAT_METAL, kind="detail", top=None):
        b = Block(box, mat, kind, top)
        self.blocks.append(b)
        return b

    def add(self, poly):
        self.blocks.append(poly)
        return poly

    def zone_at(self, p):
        """Zone du plus petit volume d'air contenant p (sinon du plus proche)."""
        best, bv = None, None
        for s in self.spaces:
            if contains_pt(s.box, p):
                v = (s.box[3] - s.box[0]) * (s.box[4] - s.box[1]) * (s.box[5] - s.box[2])
                if bv is None or v < bv:
                    best, bv = s.zone, v
        if best is None:
            def d2(s):
                b = s.box
                c = ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)
                return sum((c[i] - p[i]) ** 2 for i in range(3))
            best = min(self.spaces, key=d2).zone
        return best

    def ent(self, classname, origin=None, solids=None, outputs=None, **kv):
        e = {"classname": classname, "kv": kv, "solids": solids or [], "outputs": outputs or []}
        if origin is not None:
            e["kv"]["origin"] = "%g %g %g" % tuple(origin)
        self.ents.append(e)
        return e

    # ---- CSG ----
    def shell_slabs(self):
        """Dalles des murs après soustraction de tout l'air. -> [(box, mat, sky, zone, rôle, nom du volume)]"""
        airs = [s.box for s in self.spaces] + list(self.carve)
        out = []
        for s in self.spaces:
            x0, y0, z0, x1, y1, z1 = s.box
            W = WALL
            slabs = [
                ((x0 - W, y0 - W, z0 - W, x1 + W, y1 + W, z0), s.floor, False, "floor"),
                ((x0 - W, y0 - W, z1, x1 + W, y1 + W, z1 + W), MAT_SKY if s.sky else s.ceil, s.sky, "ceil"),
                ((x0 - W, y0 - W, z0, x0, y1 + W, z1), s.wall, False, "wall_x0"),
                ((x1, y0 - W, z0, x1 + W, y1 + W, z1), s.wall, False, "wall_x1"),
                ((x0, y0 - W, z0, x1, y0, z1), s.wall, False, "wall_y0"),
                ((x0, y1, z0, x1, y1 + W, z1), s.wall, False, "wall_y1"),
            ]
            for box, mat, sky, role in slabs:
                pieces = [box]
                for a in airs:
                    nxt = []
                    for p in pieces:
                        nxt.extend(box_sub(p, a))
                    pieces = nxt
                    if not pieces:
                        break
                for p in pieces:
                    if p[0] < p[3] and p[1] < p[4] and p[2] < p[5]:
                        out.append((p, mat, sky, s.zone, role, s.name))
        return merge_slabs(out)

    def solid_boxes(self):
        """Toutes les boîtes pleines statiques (murs + blocs) pour les tests de visibilité/collision."""
        boxes = [sl[0] for sl in self.shell_slabs()]
        for b in self.blocks:
            boxes.append(b.box if isinstance(b, Block) else b.bbox)
        return boxes


# ---------------- export srctools ----------------

def make_box_solid(vmf: VMF, box: Box, mat: str, top: str | None = None) -> Solid:
    x0, y0, z0, x1, y1, z1 = box
    pr = vmf.make_prism(Vec(x0, y0, z0), Vec(x1, y1, z1), mat)
    if top:
        pr.top.mat = top
    return pr.solid


def make_poly_solid(vmf: VMF, poly: Poly) -> Solid:
    sides = []
    for i, (p, n) in enumerate(poly.planes):
        mat = poly.top if (poly.top and i == 0) else poly.mat
        # from_plane produit l'orientation inverse de make_prism : on passe -n
        sides.append(Side.from_plane(vmf, p, -n, mat))
    return Solid(vmf, sides=sides)


def to_solid(vmf, item):
    if isinstance(item, Block):
        return make_box_solid(vmf, item.box, item.mat, item.top)
    if isinstance(item, Poly):
        return make_poly_solid(vmf, item)
    box, mat = item
    return make_box_solid(vmf, box, mat)


# ---------------- formes non cubiques ----------------
import math as _m


def frustum(box, inset, mat=MAT_METAL, kind="detail", top=None):
    """Tronc de pyramide : base = box, sommet rentré de `inset` (ou (ix, iy)) de chaque côté."""
    x0, y0, z0, x1, y1, z1 = norm(box)
    ix, iy = (inset, inset) if not isinstance(inset, tuple) else inset
    ix = min(ix, (x1 - x0) / 2 - 2); iy = min(iy, (y1 - y0) / 2 - 2)
    h = z1 - z0
    planes = [
        (Vec(x0, y0, z1), Vec(0, 0, 1)),
        (Vec(x0, y0, z0), Vec(0, 0, -1)),
        (Vec(x0, y0, z0), Vec(-h, 0, ix).norm()),
        (Vec(x1, y0, z0), Vec(h, 0, ix).norm()),
        (Vec(x0, y0, z0), Vec(0, -h, iy).norm()),
        (Vec(x0, y1, z0), Vec(0, h, iy).norm()),
    ]
    return Poly(planes, mat, kind, (x0, y0, z0, x1, y1, z1), top)


def oct_prism(cx, cy, r, z0, z1, mat=MAT_METAL, kind="detail"):
    """Prisme octogonal d'apothème r (piliers, réacteur, antenne)."""
    planes = [(Vec(cx, cy, z1), Vec(0, 0, 1)), (Vec(cx, cy, z0), Vec(0, 0, -1))]
    for k in range(8):
        a = _m.radians(45 * k)
        n = Vec(_m.cos(a), _m.sin(a), 0)
        planes.append((Vec(cx + r * n.x, cy + r * n.y, z0), n))
    return Poly(planes, mat, kind, (cx - r, cy - r, z0, cx + r, cy + r, z1))


def chamfer(x0, y0, x1, y1, z1, c, side, mat=MAT_CEIL, kind="detail"):
    """Chanfrein à 45° le long d'une arête haute d'une salle (side : x0 | x1 | y0 | y1)."""
    s2 = 1 / _m.sqrt(2)
    if side == "y0":
        planes = [(Vec(x0, y0, z1), Vec(0, 0, 1)), (Vec(x0, y0, z1), Vec(0, -1, 0)),
                  (Vec(x0, y0 + c, z1), Vec(0, s2, -s2)), (Vec(x0, y0, z1), Vec(-1, 0, 0)), (Vec(x1, y0, z1), Vec(1, 0, 0))]
        bb = (x0, y0, z1 - c, x1, y0 + c, z1)
    elif side == "y1":
        planes = [(Vec(x0, y1, z1), Vec(0, 0, 1)), (Vec(x0, y1, z1), Vec(0, 1, 0)),
                  (Vec(x0, y1 - c, z1), Vec(0, -s2, -s2)), (Vec(x0, y1, z1), Vec(-1, 0, 0)), (Vec(x1, y1, z1), Vec(1, 0, 0))]
        bb = (x0, y1 - c, z1 - c, x1, y1, z1)
    elif side == "x0":
        planes = [(Vec(x0, y0, z1), Vec(0, 0, 1)), (Vec(x0, y0, z1), Vec(-1, 0, 0)),
                  (Vec(x0 + c, y0, z1), Vec(s2, 0, -s2)), (Vec(x0, y0, z1), Vec(0, -1, 0)), (Vec(x0, y1, z1), Vec(0, 1, 0))]
        bb = (x0, y0, z1 - c, x0 + c, y1, z1)
    else:
        planes = [(Vec(x1, y0, z1), Vec(0, 0, 1)), (Vec(x1, y0, z1), Vec(1, 0, 0)),
                  (Vec(x1 - c, y0, z1), Vec(-s2, 0, -s2)), (Vec(x1, y0, z1), Vec(0, -1, 0)), (Vec(x1, y1, z1), Vec(0, 1, 0))]
        bb = (x1 - c, y0, z1 - c, x1, y1, z1)
    return Poly(planes, mat, kind, bb)


def add_chamfers(w, skip=()):
    """Chanfreins mur/plafond dans les salles intérieures, sauf sur un côté ouvert vers un volume
    qui monte jusqu'à la zone du chanfrein (sinon on boucherait le haut du passage)."""
    for s in w.spaces:
        if s.sky or any(k in s.name for k in skip):
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        h, wx, wy = z1 - z0, x1 - x0, y1 - y0
        if h < 160 or min(wx, wy) < 128:
            continue
        c = 128 if (h >= 512 and min(wx, wy) >= 1024) else (64 if h >= 256 and min(wx, wy) >= 256 else 32)
        for side in ("x0", "x1", "y0", "y1"):
            blocked = False
            for o in w.spaces:
                if o is s:
                    continue
                b = o.box
                if b[5] <= z1 - c or b[2] >= z1:
                    continue              # le voisin ne monte pas jusqu'au chanfrein
                if side == "x0":
                    touch = b[3] >= x0 - 32 and b[0] < x0 and b[1] < y1 and b[4] > y0
                elif side == "x1":
                    touch = b[0] <= x1 + 32 and b[3] > x1 and b[1] < y1 and b[4] > y0
                elif side == "y0":
                    touch = b[4] >= y0 - 32 and b[1] < y0 and b[0] < x1 and b[3] > x0
                else:
                    touch = b[1] <= y1 + 32 and b[4] > y1 and b[0] < x1 and b[3] > x0
                if touch:
                    blocked = True
                    break
            if not blocked:
                w.add(chamfer(x0, y0, x1, y1, z1, c, side, mat=s.wall))
