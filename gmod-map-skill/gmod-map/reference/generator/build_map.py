"""GÃƒÆ’Ã‚Â©nÃƒÆ’Ã‚Â¨re maps_src/givre_noir.vmf (+ givre_noir.json pour les outils, + points de la tournÃƒÆ’Ã‚Â©e)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from srctools import Vec
from srctools.vmf import VMF, Output

from geom import World, Block, Poly, to_solid, make_box_solid, LIMIT
from theme import retheme
import dataclasses
import zones
import entities
import areaportals
import walk
import props
import kit
import dressing
import optim
from srctools.vmf import UVAxis as _UV
import nodes


def main():
    w = World()
    zones.build(w)
    entities.build_entities(w)
    open_portals = areaportals.build(w)
    props.build(w)
    kit.build(w)
    dressing.build(w)
    M = w.meta
    # la seconde porte du sas ne s'ouvre qu'une fois la premiÃƒÆ’Ã‚Â¨re fermÃƒÆ’Ã‚Â©e
    outs = dict(M.get("door_outputs", []))
    for e in w.ents:
        if e["classname"] == "func_door" and e["kv"].get("targetname") in outs:
            e["outputs"].append(outs[e["kv"]["targetname"]])

    vmf = VMF()
    vmf.spawn["skyname"] = "painted"
    vmf.spawn["mapversion"] = 1
    vmf.spawn["detailvbsp"] = "detail.vbsp"
    vmf.spawn["detailmaterial"] = "detail/detailsprites"

    # AUCUN point de navigation (info_node) : choix de l'organisateur pour les events ÃƒÆ’Ã‚Â  600 PNJ
    # (les PNJ ne cherchent plus de chemin : ils avancent en ligne droite). Mettre True pour les rÃƒÆ’Ã‚Â©activer.
    WITH_NODES = False
    n_nodes = nodes.build(w, [props.world_box(*p) for p in M["props"]]) if WITH_NODES else 0
    # props au-dessus d'une fosse (tranchÃƒÆ’Ã‚Â©es techniques) : posÃƒÆ’Ã‚Â©s au fond si la fosse est assez large, sinon retirÃƒÆ’Ã‚Â©s
    pits = [sp.box for sp in w.spaces if "pit" in sp.name]
    keep = []
    for e in w.ents:
        if e["classname"] == "prop_static" and "origin" in e["kv"]:
            x, y, z = (float(v) for v in str(e["kv"]["origin"]).split())
            pit = next((b for b in pits if b[0] <= x <= b[3] and b[1] <= y <= b[4] and z >= b[5] - 2), None)
            if pit:
                if pit[0] + 36 <= x <= pit[3] - 36 and pit[1] + 36 <= y <= pit[4] - 36:
                    e["kv"]["origin"] = "%g %g %g" % (x, y, pit[2] + 1)
                else:
                    continue
        keep.append(e)
    w.ents[:] = keep
    # func_viscluster sur tout le ciel des extÃƒÆ’Ã‚Â©rieurs (au-dessus de 2560 du sol) : beaucoup moins de zones de visibilitÃƒÆ’Ã‚Â©
    for sp in w.spaces:
        if sp.sky and not sp.name.startswith("ciel"):
            x0, y0, z0, x1, y1, z1 = sp.box
            if z1 - z0 > 3072:
                w.ent("func_viscluster", solids=[Block((x0, y0, z0 + 2560, x1, y1, z1), "tools/toolstrigger")])
    optim_stats = optim.apply(w)
    # anti-grief (sans addon) : Sandbox et ses dÃƒÆ’Ã‚Â©rivÃƒÆ’Ã‚Â©s lisent ces clÃƒÆ’Ã‚Â©s sur les entitÃƒÆ’Ã‚Â©s de la map ->
    # ni physgun, ni toolgun (remover compris), ni menu contextuel sur portes, boutons, objectifs, effets...
    for e in w.ents:
        if e["classname"] not in ("prop_static", "info_player_start", "info_node", "light", "light_spot"):
            e["kv"]["gmod_allowphysgun"] = 0
            e["kv"]["gmod_allowtools"] = "aucun"
    slabs = w.shell_slabs()
    hidden = optim.hidden_face_tester([sl[0] for sl in slabs] + [b.box for b in w.blocks if isinstance(b, Block) and b.kind == "world"])
    n_nodraw = 0
    space_by_name = {s.name: s for s in w.spaces}
    lm_stats = {}
    for box, mat, sky, zone, role, sname in slabs:
        for v in box:
            assert abs(v) <= LIMIT, box
        sol = make_box_solid(vmf, box, retheme(mat, zone, role, "world", sname))
        # ÃƒÆ’Ã‚Â©chelle de lightmap : fine lÃƒÆ’Ã‚Â  oÃƒÆ’Ã‚Â¹ les ombres se voient (sols, murs bas), grossiÃƒÆ’Ã‚Â¨re ailleurs
        sp = space_by_name.get(sname)
        h = (sp.box[5] - sp.box[2]) if sp else 256
        if sky:
            lm = 32 if role == "floor" else 64            # extÃƒÆ’Ã‚Â©rieur : falaises immenses, ÃƒÆ’Ã‚Â©clairage du ciel uniforme
        elif role == "ceil":
            lm = 32
        elif role.startswith("wall") and h >= 512:
            lm = 24
        else:
            lm = 16
        for sd in sol.sides:
            sd.lightmap = lm
            if sd.mat.lower() == "givre_noir/ext_facade":      # texture 1024 : ÃƒÆ’Ã‚Â©chelle doublÃƒÆ’Ã‚Â©e = mÃƒÆ’Ã‚Âªme taille au mur
                sd.uaxis = _UV(sd.uaxis.x, sd.uaxis.y, sd.uaxis.z, offset=sd.uaxis.offset / 2, scale=0.5)
                sd.vaxis = _UV(sd.vaxis.x, sd.vaxis.y, sd.vaxis.z, offset=sd.vaxis.offset / 2, scale=0.5)
        lm_stats[lm] = lm_stats.get(lm, 0) + 1
        vmf.add_brush(sol)

    def themed(b):
        """Copie d'un Block/Poly avec les textures du thÃƒÆ’Ã‚Â¨me de sa zone."""
        bb = b.box if isinstance(b, Block) else b.bbox
        c = ((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2)
        z = w.zone_at(c)
        thin = (bb[5] - bb[2]) <= 32 and (bb[3] - bb[0]) * (bb[4] - bb[1]) >= 128 * 128 and b.top is not None
        role = "floor" if thin else "block"
        # grille ajourÃƒÆ’Ã‚Â©e seulement sur les dalles fines (sinon on verrait l'intÃƒÆ’Ã‚Â©rieur vide du bloc)
        top_kind = b.kind if (bb[5] - bb[2]) <= 32 else "world"
        return dataclasses.replace(b, mat=retheme(b.mat, z, role, b.kind),
                                   top=retheme(b.top, z, "top", top_kind) if b.top else None)

    from srctools import Vec as _V
    FIT = {"lordtrilobite/imp_door01_off": (512, 1024, True), "givre_noir/tuto_piratage": (1024, 512, False),
           "givre_noir/danger_reacteur": (512, 512, False), "givre_noir/terminal_1": (256, 256, False),
           "givre_noir/terminal_2": (256, 256, False), "givre_noir/terminal_3": (256, 256, False),
           "givre_noir/mj_bouclier": (256, 512, False), "givre_noir/mj_generateur": (512, 256, False),
           "givre_noir/mj_chaine": (512, 512, False), "givre_noir/mj_armurerie": (512, 256, False),
           "givre_noir/mj_disjoncteur": (512, 512, False), "givre_noir/mj_champ": (512, 256, False),
           "givre_noir/mj_champ_batterie": (256, 512, False), "givre_noir/mj_charge": (512, 512, False),
           "givre_noir/mj_reacteur": (512, 512, False)}

    def fit(solid):
        """Cale la texture sur la face : lisible (jamais en miroir), une porte = n panneaux entiers."""
        lo, hi = solid.get_bbox()
        for sd in solid.sides:
            spec = FIT.get(sd.mat.lower())
            if not spec:
                continue
            n = -sd.normal()          # srctools : normal() pointe vers l'intÃƒÆ’Ã‚Â©rieur du bloc
            if abs(n.z) > 0.5:
                continue
            right = _V(-n.x, -n.y, 0).cross(_V(0, 0, 1))
            corners = [_V(x, y, 0) for x in (lo.x, hi.x) for y in (lo.y, hi.y)]
            ds = [c.dot(right) for c in corners]
            wd, ht = max(ds) - min(ds), hi.z - lo.z
            if wd < 1 or ht < 1:
                continue
            tw, th, tile = spec
            k = max(1, round(wd / (ht * tw / th))) if tile else 1
            su, sv = wd / (k * tw), ht / th
            sd.uaxis = _UV(right.x, right.y, right.z, offset=-min(ds) / su, scale=su)
            sd.vaxis = _UV(0, 0, -1, offset=hi.z / sv, scale=sv)

    detail = vmf.create_ent("func_detail")
    n_detail = n_world_blocks = 0
    for b in w.blocks:
        s = to_solid(vmf, themed(b))
        fit(s)
        bb = b.box if isinstance(b, Block) else b.bbox
        if max(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2]) >= 768:      # gros rochers, rampes, poutres : lightmap 32
            for sd in s.sides:
                sd.lightmap = 32
        if isinstance(b, Block) and b.kind != "world" and not b.mat.startswith("tools/"):
            lo, hi = b.box[:3], b.box[3:]
            for sd in s.sides:
                n = -sd.normal()
                if hidden(lo, hi, (n.x, n.y, n.z)):
                    sd.mat = "tools/toolsnodraw"
                    n_nodraw += 1
        if b.kind == "world":
            vmf.add_brush(s); n_world_blocks += 1
        else:
            detail.solids.append(s); n_detail += 1

    for e in w.ents:
        kv = {k: (str(v) if not isinstance(v, str) else v) for k, v in e["kv"].items()}
        ent = vmf.create_ent(e["classname"], **kv)
        for b in e["solids"]:
            sol = to_solid(vmf, themed(b))
            fit(sol)
            ent.solids.append(sol)
        for (out, tgt, inp, param, delay, times) in e["outputs"]:
            ent.add_out(Output(out, tgt, inp, param, delay=delay, times=times, comma_sep=True))

    os.makedirs(os.path.join(ROOT, "maps_src"), exist_ok=True)
    path = os.path.join(ROOT, "maps_src", "givre_noir.vmf")
    with open(path, "w", encoding="utf-8") as f:
        vmf.export(f)

    # ---- sidecar pour Blender / validation ----
    side = {
        "spaces": [{"name": s.name, "zone": s.zone, "box": s.box, "sky": s.sky} for s in w.spaces],
        "zones": M["zones"],
        "tour": M["tour"],
        "def_spawns": M["def_spawns"],
        "atk_respawns": M["atk_respawns"],
        "player_starts": M["player_starts"],
        "solids": [list(b) for b in w.solid_boxes()] + [list(props.world_box(*p)) for p in M["props"]],
        "solids_boxes": [list(sl[0]) for sl in slabs] + [list(b.box) for b in w.blocks if isinstance(b, Block)]
                        + [list(props.world_box(*p)) for p in M["props"]],
        "doors": [d[0] for d in M["doors"] + M["dc_doors"]],
        "door_specs": [list(d) for d in M["doors"]],
        "walk": walk.MAIN, "walk_3a": walk.CONDUITS,
    }
    with open(os.path.join(ROOT, "maps_src", "givre_noir.json"), "w", encoding="utf-8") as f:
        json.dump(side, f)

    # ---- points de la tournÃƒÆ’Ã‚Â©e pour l'addon de dev ----
    lua = ["-- gÃƒÆ’Ã‚Â©nÃƒÆ’Ã‚Â©rÃƒÆ’Ã‚Â© par build_map.py : NE PAS ÃƒÆ’Ã¢â‚¬Â°DITER", "GN_TOUR = {"]
    for (name, pos, ang) in M["tour"]:
        lua.append('  { name = "%s", pos = Vector(%d, %d, %d), ang = Angle(%d, %d, %d) },'
                   % (name, *pos, *ang))
    lua.append("}")
    for var, route in (("GN_WALK", walk.MAIN), ("GN_WALK_3A", walk.CONDUITS)):
        lua.append(var + " = {")
        for (name, x, y, z) in route:
            lua.append('  { name = "%s", pos = Vector(%d, %d, %d) },' % (name, x, y, z))
        lua.append("}")
    tp = os.path.join(ROOT, "addons", "givre_noir_devtour", "lua", "givre_noir_devtour")
    os.makedirs(tp, exist_ok=True)
    with open(os.path.join(tp, "points.lua"), "w", encoding="utf-8") as f:
        f.write("\n".join(lua) + "\n")

    n_ents = len(w.ents) + 1
    print(f"VMF : {path}")
    print(f"  noeuds PNJ : {n_nodes}")
    print(f"  areaportals ouverts : {len(open_portals)}  dalles par ÃƒÆ’Ã‚Â©chelle de lightmap : {lm_stats}")
    print(f"  optim : {optim_stats}  faces cachÃƒÆ’Ã‚Â©es -> nodraw : {n_nodraw}  dalles world : {len(slabs)}")
    print(f"  kit : {M.get('kit_stats')}  ambiance : {M.get('dressing_stats')}  props au total : {len(M['props'])}")
    print(f"  refus de placement : {dict(M.get('rejets', {}))}")
    print(f"  espaces={len(w.spaces)} dalles={len(slabs)} blocs_world={n_world_blocks} detail={n_detail} entitÃƒÆ’Ã‚Â©s={n_ents}")


if __name__ == "__main__":
    main()
