"""Animations / effets des 11 étapes (100 % entités de map, déclenchés par les événements, rien en continu de coûteux).

Rythme de chaque objectif : ça monte (tension) -> ça pète (flash, détonation, secousse, débris) -> ça reste (fumée, feu).
Aucune lumière dynamique permanente : light_dynamic éteintes au démarrage, allumées 0,2 s pour les flashs.
"""
from geom import Block, oct_prism, MAT_METAL

LT = "lordtrilobite/"
RED = LT + "imp_lights02red"
_off_at_spawn = []          # light_dynamic à éteindre au chargement


def O(output, target, inp, param="", delay=0.0, times=-1):
    return (output, target, inp, param, delay, times)


def relay(w, name, outs, origin=(-14200, -900, 64)):
    return w.ent("logic_relay", origin, targetname=name, spawnflags=0, outputs=outs)


def add(w, name, outs):
    ents = [e for e in w.ents if e["kv"].get("targetname") == name]
    assert ents, f"entité introuvable : {name}"
    for e in ents:
        e["outputs"].extend(outs)


def snd(w, name, pos, wav, radius=2500, vol=10, pitch=100, loop=False, everywhere=False):
    w.ent("ambient_generic", pos, targetname=name, message=wav, health=vol, radius=radius, pitch=pitch,
          spawnflags=(16 if loop else 48) + (1 if everywhere else 0))


def T(name, inp="Trigger", param="", d=0.0):
    return O("OnTrigger", name, inp, param, d)


# ------------------------------------------------------------------ briques réutilisables
def boom(w, n, pos, size=1.0, fire=True, gibs=True, shake_r=2000):
    """GROS BOUM -> relais <n>_boom."""
    x, y, z = pos
    for k, (dx, dy, dz, dt) in enumerate(((0, 0, 20, 0), (-40, 30, 70, 0.3), (35, -25, 0, 0.7)), 1):
        w.ent("env_explosion", (x + dx * size, y + dy * size, z + dz * size), targetname=f"{n}_x{k}",
              iMagnitude=int(220 * size), iRadiusOverride=int(320 * size), spawnflags=1 + 64, rendermode=5)
    w.ent("light_dynamic", (x, y, z + 60), targetname=n + "_flash", _light="255 170 90 255", brightness=7,
          distance=int(900 * size), _inner_cone=0, _cone=0, spawnflags=0, style=0)
    _off_at_spawn.append(n + "_flash")
    w.ent("env_shake", (x, y, z), targetname=n + "_shake", amplitude=16, radius=shake_r, duration=2.5, frequency=60, spawnflags=4)
    w.ent("env_physexplosion", (x, y, z), targetname=n + "_push", magnitude=int(220 * size), radius=int(420 * size), spawnflags=1 + 2)
    snd(w, n + "_s1", (x, y, z + 40), "ambient/levels/labs/electric_explosion1.wav", radius=5000)
    snd(w, n + "_s2", (x, y, z + 40), "weapons/mortar/mortar_explode2.wav", radius=7000)
    snd(w, n + "_s3", (x, y, z + 40), "physics/metal/metal_box_break1.wav", radius=3000)
    outs = [T(n + "_x1", "Explode"), T(n + "_x2", "Explode", d=0.3), T(n + "_x3", "Explode", d=0.7),
            T(n + "_flash", "TurnOn"), T(n + "_flash", "TurnOff", d=0.18), T(n + "_flash", "TurnOn", d=0.3),
            T(n + "_flash", "TurnOff", d=0.42), T(n + "_shake", "StartShake"), T(n + "_push", "Explode"),
            T(n + "_s1", "PlaySound"), T(n + "_s2", "PlaySound", d=0.05), T(n + "_s3", "PlaySound", d=0.35)]
    if gibs:
        for k, mdl in enumerate(("models/gibs/metal_gib2.mdl", "models/gibs/metal_gib4.mdl"), 1):
            w.ent("env_shooter", (x, y, z + 30), targetname=f"{n}_gib{k}", angles="-80 0 0", m_iGibs=6, delay=0,
                  gibangles="0 0 0", gibanglevelocity=400, m_flVelocity=int(420 * size), m_flVariance=0.9, m_flGibLife=7,
                  shootmodel=mdl, shootsounds=2, simulation=0, nogibshadows=1, gibgravityscale=1, massoverride=0, spawnflags=0)
            outs.append(T(f"{n}_gib{k}", "Shoot", d=0.05))
    if fire:
        w.ent("env_fire", (x, y, z), targetname=n + "_fire", health=14, firesize=int(110 * size), fireattack=1, firetype=0,
              spawnflags=128 + 256, ignitionpoint=999, damagescale=0)
        w.ent("env_smokestack", (x, y, z + 20), targetname=n + "_smoke", InitialState=0, BaseSpread=24, SpreadSpeed=14,
              Speed=70, StartSize=30, EndSize=int(140 * size), Rate=9, JetLength=int(500 * size), WindAngle=0, WindSpeed=0,
              SmokeMaterial="particle/SmokeStack.vmt", rendercolor="35 35 35", renderamt=210, twist=6, roll=0)
        outs += [T(n + "_fire", "StartFire", d=0.4), T(n + "_smoke", "TurnOn", d=0.5)]
    relay(w, n + "_boom", outs, origin=(x, y, z + 300))
    return n + "_boom"


def arcs(w, n, pos, radius=220, start_on=False):
    """ARC : arcs électriques bleus (TurnOn / TurnOff / DoSpark)."""
    w.ent("point_tesla", pos, targetname=n, m_SoundName="DoSpark", texture="sprites/physbeam.vmt", m_Color="140 190 255",
          m_flRadius=radius, beamcount_min=4, beamcount_max=8, thick_min=3, thick_max=7, lifetime_min=0.1, lifetime_max=0.25,
          interval_min=0.3, interval_max=1.4)
    if start_on:
        _off_at_spawn.append(("on", n))
    return n


def steam(w, n, pos, angles="-90 0 0", length=140, size=1.0, start_on=False, hiss=True):
    """VAPEUR : jet qui siffle (TurnOn / TurnOff sur <n>, son <n>_s)."""
    w.ent("env_steam", pos, targetname=n, InitialState=1 if start_on else 0, type=0, SpreadSpeed=int(18 * size),
          Speed=int(140 * size), StartSize=int(10 * size), EndSize=int(34 * size), Rate=28, JetLength=int(length),
          rendercolor="225 230 235", renderamt=200, rollspeed=8, angles=angles, spawnflags=0)
    if hiss:
        snd(w, n + "_s", pos, "ambient/machines/steam_release_2.wav", radius=1600)
    return [T(n, "TurnOn")] + ([T(n + "_s", "PlaySound")] if hiss else [])


def spinner(w, n, cx, cy, z, r, mat=MAT_METAL, speed=40, start=True, thick=24):
    """Anneau / pièce tournante non solide (Start, Stop = ralentit jusqu'à l'arrêt, SetSpeed 0..1)."""
    w.ent("func_rotating", (cx, cy, z), solids=[oct_prism(cx, cy, r, z, z + thick, mat)], targetname=n,
          spawnflags=64 + (1 if start else 0), maxspeed=speed, fanfriction=8, volume=0, angles="0 0 0", dmg=0)


def beacon(w, n, pos):
    """ALARME LOCALE : capot rouge qui tourne + halo + klaxon (relais <n>_on / <n>_off)."""
    x, y, z = pos
    w.ent("func_rotating", (x, y, z), solids=[oct_prism(x, y, 10, z - 12, z + 12, RED)], targetname=n + "_rot",
          spawnflags=64, maxspeed=260, fanfriction=60, volume=0, angles="0 0 0", dmg=0)
    w.ent("env_sprite", (x, y, z), targetname=n + "_glow", model="sprites/glow01.spr", rendermode=9, rendercolor="255 30 20",
          renderamt=255, renderfx=10, scale=1.1, GlowProxySize=12, spawnflags=0)
    snd(w, n + "_k", (x, y, z), "ambient/alarms/klaxon1.wav", radius=2200, loop=True)
    relay(w, n + "_on", [T(n + "_rot", "Start"), T(n + "_glow", "ShowSprite"), T(n + "_k", "PlaySound")], origin=(x, y, z + 40))
    relay(w, n + "_off", [T(n + "_rot", "Stop"), T(n + "_glow", "HideSprite"), T(n + "_k", "StopSound")], origin=(x, y, z + 60))


def door_center(w, name):
    e = next(e for e in w.ents if e["kv"].get("targetname") == name and e["classname"] == "func_door")
    b = e["solids"][0].box
    return ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, b[2]), b


def heavy_door(w, name):
    """PORTE LOURDE : à l'ouverture, secousse locale + vapeur au pied + grondement."""
    (x, y, z), b = door_center(w, name)
    n = "fx_" + name
    w.ent("env_shake", (x, y, z), targetname=n + "_sh", amplitude=5, radius=900, duration=1.6, frequency=30, spawnflags=0)
    w.ent("env_steam", (x, y, b[5] - 8), targetname=n + "_st", InitialState=0, type=0, SpreadSpeed=30, Speed=90,
          StartSize=20, EndSize=60, Rate=30, JetLength=140, rendercolor="200 205 210", renderamt=150, rollspeed=6,
          angles="90 0 0", spawnflags=0)
    snd(w, n + "_s", (x, y, z + 64), "doors/heavy_metal_stop1.wav", radius=2500)
    add(w, name, [O("OnOpen", n + "_sh", "StartShake"), O("OnOpen", n + "_st", "TurnOn"), O("OnOpen", n + "_st", "TurnOff", delay=1.8),
                  O("OnOpen", n + "_s", "PlaySound")])


# ------------------------------------------------------------------ les 11 étapes
def build(w):
    M = w.meta
    # sons de mouvement sur toutes les portes (presque gratuit : joués par la porte elle-même)
    for e in w.ents:
        if e["classname"] == "func_door" and e["kv"].get("targetname", "").startswith(("gn_door", "gn_cell", "gn_dc_door",
                                                                                         "gn_sas", "gn_exfil")):
            e["kv"].setdefault("noise1", "doors/heavy_metal_move1.wav")
            e["kv"].setdefault("noise2", "doors/heavy_metal_stop1.wav")
    for d in ("gn_door_gate", "gn_door_conduit", "gn_door_4n", "gn_door_4s", "gn_sas_door_1", "gn_door_5a", "gn_door_5n",
              "gn_door_5s", "gn_door_6w", "gn_door_6a", "gn_door_6b", "gn_door_6e", "gn_sas2_door_1", "gn_door_7n", "gn_door_7s",
              "gn_door_8a", "gn_door_8n", "gn_door_8s", "gn_exfil_door_0"):
        heavy_door(w, d)

    phase1_2(w, M)
    phase3(w)
    phase4(w, M)
    phase5(w, M)
    phase6(w)
    phase7(w, M)
    phase8(w, M)
    phase9(w, M)
    phase10_11(w, M)
    core_countdown(w, M)
    meltdown_escalation(w, M)
    finale(w, M)

    outs = []
    for it in _off_at_spawn:
        outs.append(O("OnMapSpawn", it[1], "TurnOn", delay=1) if isinstance(it, tuple) else O("OnMapSpawn", it, "TurnOff"))
    w.ent("logic_auto", (-14200, -900, 140), spawnflags=1, outputs=outs)


def sky(x, y, z):
    """Point du monde -> point du ciel 3D (sky_camera en (0, 9344, 512), échelle 1/16)."""
    return (x / 16, 9344 + y / 16, 512 + z / 16)


def phase1_2(w, M):
    # 1 · vaisseaux qui traversent le ciel (ciel 3D, échelle 1/16) pendant l'assaut, avec grondement au passage
    for k, (yw, zw, mdl) in enumerate(((-2500, 9500, "venator_16"),), 1):
        x0, y0, z0 = sky(-19000, yw, zw)
        n = f"fx_ship_{k}"
        w.ent("func_movelinear", solids=[Block((x0 - 4, y0 - 4, z0 - 4, x0 + 4, y0 + 4, z0 + 4), "tools/toolsnodraw")],
              targetname=n, movedir="0 0 0", movedistance=2100, speed=110, startposition=0, spawnflags=8, blockdamage=0)
        w.ent("prop_dynamic", (x0, y0, z0), targetname=n + "_mdl", parentname=n, solid=0, DisableShadows=1,
              model=f"models/lordtrilobite/starwars/props/{mdl}.mdl", angles="0 0 0", StartDisabled=1)
        snd(w, n + "_s", (-9000, max(-1800, min(1800, yw)), 1200), "ambient/overhead/plane2.wav", radius=14000, pitch=70)
        relay(w, n + "_pass", [T(n + "_mdl", "Enable"), T(n, "Open"), T(n + "_s", "PlaySound", d=6),
                               T(n + "_mdl", "Disable", d=19.5), T(n, "SetSpeed", "3000", d=19.6), T(n, "Close", d=19.7),
                               T(n, "SetSpeed", "110", d=21.5)], origin=(-14200, -1000 - 40 * k, 64))
    w.ent("logic_timer", (-14200, -1100, 64), targetname="fx_ships_t", RefireTime=40, StartDisabled=1, UseRandomTime=0,
          outputs=[O("OnTimer", "fx_ship_1_pass", "Trigger")])
    # vent du canyon (rafales aléatoires)
    for k, p in enumerate(((-14000, -2000, 400), (-12000, 2000, 400), (-10000, 0, 600)), 1):
        snd(w, f"fx_wind_{k}", p, "ambient/wind/windgust_strong.wav", radius=5000)
    w.ent("logic_timer", (-14200, -1150, 64), targetname="fx_wind_t", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=6, UpperRandomBound=14, outputs=[O("OnTimer", "fx_wind_1", "PlaySound"),
                                                         O("OnTimer", "fx_wind_2", "PlaySound", delay=2.5),
                                                         O("OnTimer", "fx_wind_3", "PlaySound", delay=4)])
    # projecteurs fixés sur la façade de la base (mur est du hangar), allumés un par un au début
    proj = []
    for k, y in enumerate(range(-1600, 1601, 640)):
        w.ent("env_sprite", (-5140, y, 900), targetname=f"fx_proj_{k}", model="sprites/glow01.spr", rendermode=9,
              rendercolor="220 235 255", renderamt=255, scale=3, GlowProxySize=24, spawnflags=0)
        snd(w, f"fx_proj_{k}_s", (-5140, y, 900), "ambient/machines/machine1_hit1.wav", radius=6000)
        proj += [T(f"fx_proj_{k}", "ShowSprite", d=2 + 0.6 * k), T(f"fx_proj_{k}_s", "PlaySound", d=2 + 0.6 * k)]
    add(w, "gn_phase_1_start", [T("fx_ships_t", "Enable"), T("fx_ship_1_pass", d=3), T("fx_wind_t", "Enable")] + proj)

    # 2 · tourelles AA : tête qui pivote + tirs de flak tant qu'elles vivent ; bouclier qui vacille ; GROS BOUM
    for i, box in enumerate(M["aa"], 1):
        cx, cy = (box[0] + box[3]) / 2, (box[1] + box[4]) / 2
        top = box[5]
        n = f"fx_aa_{i}"
        w.ent("func_rotating", (cx, cy, top), solids=[oct_prism(cx, cy, 48, top, top + 40, MAT_METAL),
                                                       Block((cx, cy - 10, top + 20, cx + 150, cy + 10, top + 36), MAT_METAL)],
              targetname=n + "_head", spawnflags=64 + 1, maxspeed=14, fanfriction=20, volume=0, angles="0 0 0", dmg=0)
        fx, fy, fz = cx + 600, cy + (900 if i % 2 else -900), 2600
        w.ent("env_explosion", (fx, fy, fz), targetname=n + "_flak", iMagnitude=90, iRadiusOverride=200,
              spawnflags=1 + 2 + 64 + 16, rendermode=5)
        snd(w, n + "_fire", (cx, cy, top + 40), "weapons/mortar/mortar_fire1.wav", radius=6000)
        w.ent("logic_timer", (cx, cy, top + 200), targetname=n + "_t", StartDisabled=1, UseRandomTime=1, LowerRandomBound=2,
              UpperRandomBound=5, outputs=[O("OnTimer", n + "_fire", "PlaySound"), O("OnTimer", n + "_flak", "Explode", delay=1.2)])
        b = boom(w, n, (cx, cy, top), size=1.3, shake_r=3000)
        add(w, f"aa_{i}", [O("OnBreak", b, "Trigger"), O("OnBreak", n + "_t", "Kill"), O("OnBreak", n + "_head", "Kill")])
        add(w, "gn_phase_2_start", [T(n + "_t", "Enable")])
    flick = [T("gn_aa_shield", "Enable", d=0.15), T("gn_aa_shield", "Disable", d=0.3), T("gn_aa_shield", "Enable", d=0.5),
             T("gn_aa_shield", "Disable", d=0.8)]
    add(w, "gn_shield_down", flick)
    for k, (gx, gy) in enumerate(((-8900, -1250), (-5560, 1650)), 1):
        a = arcs(w, f"fx_shieldgen_{k}", (gx, gy, 80), radius=260, start_on=True)
        snd(w, a + "_z", (gx, gy, 80), "ambient/levels/labs/electric_explosion3.wav", radius=4000)
        add(w, f"gn_shieldgen_{k}", [O("OnBreak", a, "DoSpark"), O("OnBreak", a, "TurnOff", delay=0.6), O("OnBreak", a + "_z", "PlaySound"),
                                     O("OnHealthChanged", a, "DoSpark")])
    add(w, "gn_phase_2_done", [T("fx_ships_t", "Disable", d=40)])


def phase3(w):
    # porte principale qui se coince à mi-course puis cède ; fuites de vapeur et étincelles dans les conduits
    w.ent("env_spark", (-5110, 0, 300), targetname="fx_gate_sp", MaxDelay=0.3, Magnitude=8, TrailLength=3, spawnflags=0,
          angles="0 180 0")
    snd(w, "fx_gate_grind", (-5110, 0, 200), "ambient/materials/metal_stress1.wav", radius=4000)
    snd(w, "fx_gate_bang", (-5110, 0, 200), "ambient/machines/wall_crash1.wav", radius=5000)
    add(w, "gn_door_gate", [O("OnOpen", "!self", "SetSpeed", "12"), O("OnOpen", "fx_gate_sp", "StartSpark"),
                            O("OnOpen", "fx_gate_grind", "PlaySound"), O("OnOpen", "!self", "SetSpeed", "220", delay=3),
                            O("OnOpen", "fx_gate_bang", "PlaySound", delay=3), O("OnOpen", "fx_gate_sp", "StopSpark", delay=4)])
    for k, x in enumerate((-4000, -2560, -1120), 1):
        steam(w, f"fx_cond_st_{k}", (x, 2125, 110), angles="45 90 0", length=110, start_on=True, hiss=False)
        snd(w, f"fx_cond_hiss_{k}", (x, 2125, 100), "ambient/gas/steam_loop1.wav", radius=900, vol=6, loop=True)
        w.ent("env_spark", (x, 2350, 120), MaxDelay=4, Magnitude=2, TrailLength=1, spawnflags=64, angles="90 0 0")
    add(w, "gn_phase_1_start", [T(f"fx_cond_hiss_{k}", "PlaySound", d=6) for k in (1, 2, 3)])


def phase4(w, M):
    # usine : bras de soudure qui montent et descendent au-dessus de la chaîne, étincelles, bruit de machines
    arms = []
    for k, (ax, ay) in enumerate(((1250, -384), (1800, -384), (1250, 384), (1800, 384)), 1):
        n = f"fx_arm_{k}"
        w.ent("func_movelinear", solids=[Block((ax - 14, ay - 14, 420, ax + 14, ay + 14, 768), MAT_METAL),
                                          Block((ax - 30, ay - 30, 400, ax + 30, ay + 30, 420), RED)],
              targetname=n, movedir="90 0 0", movedistance=230, speed=160, startposition=0, spawnflags=8, blockdamage=0)
        w.ent("env_spark", (ax, ay, 170), targetname=n + "_sp", MaxDelay=0.2, Magnitude=4, TrailLength=2, spawnflags=0,
              angles="-60 0 0")
        snd(w, n + "_s", (ax, ay, 300), "ambient/levels/citadel/stalk_spark_01.wav", radius=1600)
        d = 0.8 * (k - 1)
        arms += [O("OnTimer", n, "Open", delay=d), O("OnTimer", n + "_sp", "StartSpark", delay=d + 1.4),
                 O("OnTimer", n + "_s", "PlaySound", delay=d + 1.4), O("OnTimer", n + "_sp", "StopSpark", delay=d + 2.6),
                 O("OnTimer", n, "Close", delay=d + 2.8)]
    w.ent("logic_timer", (1536, 0, 400), targetname="fx_arms_t", RefireTime=6, StartDisabled=1, UseRandomTime=0, outputs=arms)
    snd(w, "fx_factory_hum", (1536, 0, 300), "ambient/levels/labs/machine_moving_loop3.wav", radius=3500, vol=7, loop=True)
    snd(w, "fx_factory_stop", (1536, 0, 300), "ambient/levels/labs/machine_stop1.wav", radius=6000)
    snd(w, "fx_factory_down", (1536, 0, 300), "ambient/machines/thumper_shutdown1.wav", radius=6000)
    add(w, "gn_phase_4_start", [T("fx_factory_hum", "PlaySound"), T("fx_arms_t", "Enable")])
    add(w, "gn_phase_5_done", [T("fx_arms_t", "Disable"), T("fx_factory_hum", "StopSound")])
    add(w, "gn_factory_blackout", [T("fx_arms_t", "Disable"), T("fx_factory_hum", "StopSound"), T("fx_factory_stop", "PlaySound"),
                                   T("fx_factory_down", "PlaySound", d=0.6)]
        + [T(f"fx_arm_{k}", "Close", d=0.3) for k in range(1, 5)] + [T(f"fx_arm_{k}_sp", "StopSpark") for k in range(1, 5)])
    add(w, "gn_chaine_levier", [O("OnIn", "fx_arms_t", "Disable"), O("OnIn", "fx_factory_hum", "StopSound"),
                                O("OnIn", "fx_factory_stop", "PlaySound"), O("OnOut", "fx_arms_t", "Enable"),
                                O("OnOut", "fx_factory_hum", "PlaySound")])
    # générateurs : montée en tension pendant les 6 s, puis GROS BOUM + capot arraché
    for i, (gx, gy) in enumerate(M["generators"], 1):
        n = f"gn_gen_{i}"
        a = arcs(w, f"fx_gen_{i}_arc", (gx, gy, 60), radius=200)
        st = steam(w, f"fx_gen_{i}_st", (gx + 40, gy, 40), angles="-60 0 0", length=160)
        snd(w, f"fx_gen_{i}_wind", (gx, gy, 80), "ambient/levels/citadel/zapper_warmup1.wav", radius=2500)
        w.ent("func_breakable", solids=[Block((gx - 40, gy - 40, 40, gx + 40, gy + 40, 52), MAT_METAL)],
              targetname=f"fx_gen_{i}_cover", health=0, material=2, spawnflags=1, explosion=1, gibdir="0 0 0",
              ExplodeDamage=0, ExplodeRadius=0, PerformanceMode=0, propdata=0)
        b = boom(w, f"fx_gen_{i}", (gx, gy, 40))
        add(w, n + "_surcharge", [T(a, "TurnOn"), T(f"fx_gen_{i}_wind", "PlaySound")] + st
            + [T(n + "_beep_t", "RefireTime", "0.25", d=3), T(n + "_beep_t", "RefireTime", "0.1", d=4.8)])
        add(w, n + "_cbs", [O("OnChangedFromMax", a, "TurnOff"), O("OnChangedFromMax", f"fx_gen_{i}_st", "TurnOff"),
                            O("OnChangedFromMax", n + "_beep_t", "RefireTime", "0.5")])
        add(w, n, [O("OnPressed", b, "Trigger"), O("OnPressed", f"fx_gen_{i}_cover", "Break"),
                   O("OnPressed", f"fx_gen_{i}_st", "TurnOff", delay=8), O("OnPressed", a, "TurnOff", delay=12)])


def phase5(w, M):
    # garnison : alarme locale sur l'étage de chaque console tant que les 3 ne sont pas prises
    for i, (gx, gy, gz) in enumerate(M["garrison_consoles"], 1):
        n = f"fx_armory_{i}"
        beacon(w, n, (gx, gy, gz + 220))
        snd(w, n + "_clac", (gx, gy, gz + 60), "plats/rackstop1.wav", radius=2000)
        add(w, f"gn_armory_{i}", [O("OnPressed", n + "_on", "Trigger"), O("OnPressed", n + "_clac", "PlaySound")])
        add(w, f"gn_armory_window_{i}", [T(n + "_off", d=10)])
        add(w, "gn_armory_counter", [O("OnHitMax", n + "_off", "Trigger"), O("OnHitMax", f"gn_armory_window_{i}", "CancelPending")])
    snd(w, "fx_armory_win", (6656, 0, 600), "ambient/machines/wall_move4.wav", radius=6000)
    add(w, "gn_armory_counter", [O("OnHitMax", "fx_armory_win", "PlaySound")])


def phase6(w):
    # centre de données : voyants des baies (plus rapides pendant le hack), ventilateurs, coupure / réarmement
    leds = []
    for x in range(10500, 13200, 384):
        for y in (-1528, 1528):
            leds.append((x, y, 960))
    for (x, y, z) in leds:
        w.ent("env_sprite", (x, y, z), targetname="fx_dc_led", model="sprites/glow01.spr", rendermode=9,
              rendercolor="60 200 255", renderamt=255, renderfx=1, scale=0.35, GlowProxySize=4, spawnflags=1)
    for k, (x, y) in enumerate(((10880, -768), (12672, -768), (10880, 768), (12672, 768)), 1):
        spinner(w, f"fx_dc_fan_{k}", x, y, 1360, 90, mat=MAT_METAL, speed=90, thick=12, start=False)
    snd(w, "fx_dc_fans", (11776, 0, 1300), "ambient/machines/turbine_loop_1.wav", radius=4000, vol=6, loop=True)
    snd(w, "fx_dc_off", (11776, 0, 1100), "ambient/levels/citadel/stalk_poweroff_on_17_10.wav", radius=6000)
    snd(w, "fx_dc_clonk", (10240, 560, 860), "plats/bigstop1.wav", radius=4000)
    a = arcs(w, "fx_dc_breaker_arc", (10250, 560, 860), radius=160)
    fans = lambda inp, p="": [T(f"fx_dc_fan_{k}", inp, p) for k in range(1, 5)]
    add(w, "gn_phase_6_start", [T("fx_dc_fans", "PlaySound")] + [T(f"fx_dc_fan_{k}", "Start") for k in range(1, 5)])
    add(w, "gn_phase_7_done", [T("fx_dc_fans", "StopSound")] + [T(f"fx_dc_fan_{k}", "Stop") for k in range(1, 5)])
    add(w, "gn_hack_fx_on", [T("fx_dc_led", "AddOutput", "renderfx 10")] + fans("SetSpeed", "1"))
    add(w, "gn_hack_fx_off", [T("fx_dc_led", "AddOutput", "renderfx 1")] + fans("SetSpeed", "0.4"))
    add(w, "gn_hack_cut", [T("fx_dc_led", "HideSprite"), T("fx_dc_fans", "StopSound"), T("fx_dc_off", "PlaySound"), T(a, "TurnOn")]
        + fans("Stop"))
    add(w, "gn_hack_resume", [T("fx_dc_clonk", "PlaySound"), T(a, "TurnOff"), T("fx_dc_fans", "PlaySound", d=0.5)]
        + fans("Start") + [T("fx_dc_led", "ShowSprite", d=0.4 + 0.25 * k) for k in range(1)])
    for i in (1, 2, 3):
        n = f"fx_dc_rack_{i}"
        x, y = (11000, -1400) if i == 1 else (12500, 1400) if i == 2 else (12500, -1400)
        w.ent("env_spark", (x, y, 900), targetname=n, MaxDelay=0.15, Magnitude=8, TrailLength=3, spawnflags=0, angles="0 90 0")
        snd(w, n + "_s", (x, y, 900), "ambient/levels/labs/electric_explosion4.wav", radius=4000)
        add(w, f"gn_hack_stage_{i}_done", [T(n, "StartSpark"), T(n + "_s", "PlaySound"), T(n, "StopSpark", d=2.5)])


def phase7(w, M):
    # prison : le champ vacille quand on touche une batterie, batteries qui claquent, cellules en cascade + alarme
    for k in (1, 2, 3):
        add(w, f"gn_prison_cell_{k}", [O("OnHealthChanged", "gn_prison_field", "Alpha", "60"),
                                       O("OnHealthChanged", "gn_prison_field", "Alpha", "255", delay=0.12)])
    for k, (px, py) in enumerate(((10420, -4180), (10420, -6060), (12920, -3780)), 1):
        a = arcs(w, f"fx_pcell_{k}", (px, py, 820), radius=240)
        add(w, f"gn_prison_cell_{k}", [O("OnBreak", a, "DoSpark"), O("OnBreak", a, "DoSpark", delay=0.3),
                                       O("OnBreak", a, "DoSpark", delay=0.7)])
    add(w, "gn_prison_field_down", [T("gn_prison_field", "Enable", d=0.15), T("gn_prison_field", "Disable", d=0.3),
                                    T("gn_prison_field", "Enable", d=0.5), T("gn_prison_field", "Disable", d=0.8)])
    beacon(w, "fx_prison_alarm", (11776, -5120, 1600))
    for grp in ("a", "b", "c"):
        rel = next(e for e in w.ents if e["kv"].get("targetname") == f"gn_cells_{grp}_open")
        rel["outputs"] = [(o[0], o[1], o[2], o[3], 0.35 * j, o[5]) for j, o in enumerate(rel["outputs"])]
        rel["outputs"] += [T("fx_prison_alarm_on"), T("fx_prison_alarm_off", d=12)]


def phase8(w, M):
    # tour : anneaux qui tournent autour de l'antenne + éclairs ; charges qui bipent de plus en plus vite ; GROS BOUM
    for k, z in enumerate((1580, 2092, 2604), 1):
        spinner(w, f"fx_ant_ring_{k}", 6656, -5120, z, 330, speed=25 + 10 * k, thick=20, start=False)
    a = arcs(w, "fx_ant_arc", (6656, -5120, 2700), radius=420)
    snd(w, "fx_ant_hum", (6656, -5120, 1800), "ambient/levels/citadel/zapper_ambient_loop1.wav", radius=3500, vol=6, loop=True)
    snd(w, "fx_ant_die", (6656, -5120, 1800), "ambient/levels/labs/teleport_winddown1.wav", radius=8000)
    add(w, "gn_phase_8_start", [T("fx_ant_hum", "PlaySound"), T(a, "TurnOn")] + [T(f"fx_ant_ring_{k}", "Start") for k in (1, 2, 3)])
    for i, box in enumerate(M["charges"], 1):
        n = f"gn_charge_{i}"
        cx, cy = (box[0] + box[3]) / 2, (box[1] + box[4]) / 2
        b = boom(w, f"fx_charge_{i}", (cx, cy, box[5]), size=1.4, shake_r=3500)
        add(w, n + "_count", [T(n + "_beep_t", "RefireTime", "0.5", d=15), T(n + "_beep_t", "RefireTime", "0.2", d=25),
                              T(n + "_beep_t", "RefireTime", "0.08", d=28)])
        add(w, n, [O("OnPressed", b, "Trigger")])
        add(w, n + "_disarm_full", [T(n + "_beep_t", "RefireTime", "1")])
    add(w, "gn_phase_8_done", [T(a, "TurnOff"), T("fx_ant_hum", "StopSound"), T("fx_ant_die", "PlaySound")]
        + [T(f"fx_ant_ring_{k}", "Stop") for k in (1, 2, 3)])


def phase9(w, M):
    # noyau : anneaux tournants, vapeur aux vannes, cœur bleu -> rouge, arcs, flash final
    rcx, rcy, kz = M["reactor_center"]
    spinner(w, "fx_core_ring_1", rcx, rcy, kz + 480, 380, speed=30, thick=28, start=False)
    spinner(w, "fx_core_ring_2", rcx, rcy, kz - 480, 380, speed=22, thick=28, start=False)
    for (dx, dy) in ((310, 0), (-310, 0), (0, 310), (0, -310)):
        w.ent("env_sprite", (rcx + dx, rcy + dy, kz + 700), targetname="fx_core_blue", model="sprites/glow01.spr", rendermode=9,
              rendercolor="80 200 255", renderamt=255, renderfx=1, scale=4, GlowProxySize=48, spawnflags=1)
    a = arcs(w, "fx_core_arc", (rcx, rcy, kz + 300), radius=520)
    w.ent("env_shake", (rcx, rcy, kz), targetname="fx_core_shake", amplitude=4, radius=4000, duration=2, frequency=25, spawnflags=4)
    snd(w, "fx_core_zap", (rcx, rcy, kz + 300), "ambient/levels/labs/electric_explosion2.wav", radius=6000)
    for k, (dx, dy) in enumerate(((-296, -296), (296, -296), (-296, 296)), 1):
        n = f"fx_core_valve_st_{k}"
        st = steam(w, n, (rcx + dx, rcy + dy, kz + 60), angles="-90 0 0", length=260, size=1.5)
        add(w, f"gn_core_valve_{k}_full", st + [T(n, "TurnOff", d=3)])
    add(w, "gn_core_valves_done", [T("fx_core_blue", "HideSprite"), T("fx_core_ring_1", "SetSpeed", "1"),
                                   T("fx_core_ring_2", "SetSpeed", "1"), T(a, "TurnOn")])
    add(w, "gn_reactor_overload", [T(a, "DoSpark"), T("fx_core_zap", "PlaySound"), T("fx_core_shake", "StartShake"),
                                   T("fx_core_shake", "Amplitude", "9", d=0.1)])
    b = boom(w, "fx_core", (rcx, rcy, kz + 200), size=2.0, fire=False, gibs=False, shake_r=6000)
    add(w, "gn_phase_9_done", [T(b)])
    add(w, "gn_phase_9_start", [T("fx_core_ring_1", "Start"), T("fx_core_ring_2", "Start"), T("fx_core_ring_1", "SetSpeed", "0.4", d=1), T("fx_core_ring_2", "SetSpeed", "0.4", d=1)])


def phase10_11(w, M):
    # exfiltration : la base tremble par vagues, tuyaux qui pètent, sirène à 30 s ; sortie : explosion géante
    for k, (tag, amp) in enumerate((("gn_exfil_t360", 4), ("gn_exfil_t240", 6), ("gn_exfil_t120", 9), ("gn_exfil_t60", 12),
                                    ("gn_exfil_t30", 15)), 1):
        w.ent("env_shake", (-4000, -5500, 4500), targetname=f"fx_exq_{k}", amplitude=amp, radius=20000, duration=4,
              frequency=20, spawnflags=1 + 4)
        add(w, tag, [T(f"fx_exq_{k}", "StartShake"), T("fx_ex_rumble", "PlaySound")])
    snd(w, "fx_ex_rumble", (-4000, -5500, 4500), "ambient/atmosphere/terrain_rumble1.wav", everywhere=True)
    add(w, "gn_phase_10_start", [T("fx_exq_1", "StartShake"), T("fx_ex_rumble", "PlaySound")])
    pipes = []
    for k, (x, y, z) in enumerate(((-1800, -4500, 3200), (-4600, -4500, 4700), (-7400, -4500, 6200),
                                    (-1100, -5900, 2700), (-3900, -5900, 4300), (-6700, -5900, 5800)), 1):
        n = f"fx_ex_pipe_{k}"
        steam(w, n, (x, y, z), angles="20 90 0", length=220, size=1.3)
        w.ent("env_shooter", (x, y, z + 400), targetname=n + "_deb", angles="90 0 0", m_iGibs=5, delay=0, gibangles="0 0 0",
              gibanglevelocity=200, m_flVelocity=60, m_flVariance=1, m_flGibLife=4, shootmodel="models/gibs/metal_gib1.mdl",
              shootsounds=2, simulation=0, nogibshadows=1, gibgravityscale=1, massoverride=0, spawnflags=0)
        pipes += [O("OnCase0" + str(k), n, "TurnOn"), O("OnCase0" + str(k), n + "_s", "PlaySound"),
                  O("OnCase0" + str(k), n, "TurnOff", delay=3.5), O("OnCase0" + str(k), n + "_deb", "Shoot")]
    w.ent("logic_case", (-4000, -5500, 4400), targetname="fx_ex_case", outputs=pipes)
    w.ent("logic_timer", (-4000, -5500, 4300), targetname="fx_ex_t", StartDisabled=1, UseRandomTime=1, LowerRandomBound=3,
          UpperRandomBound=7, outputs=[O("OnTimer", "fx_ex_case", "PickRandom")])
    snd(w, "fx_ex_siren", (-4000, -5500, 4500), "ambient/alarms/citadel_alert_loop2.wav", everywhere=True, loop=True, vol=7)
    add(w, "gn_phase_10_start", [T("fx_ex_t", "Enable")])
    add(w, "gn_exfil_t30", [T("fx_ex_siren", "PlaySound")])
    b = boom(w, "fx_ex_final", (-8800, -4300, 6950), size=3.0, gibs=False, shake_r=9000)
    w.ent("env_smokestack", (-8800, -4300, 6950), targetname="fx_ex_column", InitialState=0, BaseSpread=120, SpreadSpeed=40,
          Speed=220, StartSize=200, EndSize=700, Rate=8, JetLength=3500, WindAngle=0, WindSpeed=0,
          SmokeMaterial="particle/SmokeStack.vmt", rendercolor="30 30 30", renderamt=230, twist=4, roll=0)
    add(w, "gn_phase_10_done", [T("fx_ex_t", "Disable"), T("fx_ex_siren", "StopSound"), T(b, d=4), T("fx_ex_column", "TurnOn", d=4.5)])
    # extraction : balises de la plateforme, vaisseaux, explosions lointaines sur la base
    x0, y0, z0, x1, y1, z1 = M["extract"]
    for (x, y) in ((x0, y0), (x0, y1), (x1, y0), (x1, y1)):
        w.ent("env_sprite", (x, y, z0 + 24), targetname="fx_pad_led", model="sprites/glow01.spr", rendermode=9,
              rendercolor="255 200 60", renderamt=255, renderfx=10, scale=1.2, GlowProxySize=10, spawnflags=0)
    for k, p in enumerate(((-8600, -4300, 6960), (-8600, -7800, 6960), (-8600, -6900, 6960)), 1):
        boom(w, f"fx_far_{k}", p, size=2.0, gibs=False, fire=False, shake_r=7000)
    w.ent("logic_timer", (-10000, -6000, 7300), targetname="fx_far_t", StartDisabled=1, UseRandomTime=1, LowerRandomBound=9,
          UpperRandomBound=18, outputs=[O("OnTimer", "fx_far_case", "PickRandom")])
    w.ent("logic_case", (-10000, -6000, 7250), targetname="fx_far_case",
          outputs=[O(f"OnCase0{k}", f"fx_far_{k}_boom", "Trigger") for k in (1, 2, 3)])
    add(w, "gn_phase_11_start", [T("fx_pad_led", "ShowSprite"), T("fx_far_t", "Enable"), T("fx_ships_t", "Enable"),
                                 T("fx_ship_1_pass")])
    add(w, "gn_phase_11_done", [T("fx_far_t", "Disable", d=5)])


# ------------------------------------------------------------------ noyau : compte à rebours, réussite / fusion
CORE_TIME = 300          # 5 min pour surcharger les 3 consoles


def core_countdown(w, M):
    """Phase 9 : compte à rebours affiché. Réussite -> suite normale. Échec -> fusion : tout part en vrille, il faut fuir."""
    rcx, rcy, kz = M["reactor_center"]
    def txt(name, msg, color, hold):
        w.ent("game_text", (rcx, rcy, kz + 900), targetname=name, message=msg, x=-1, y=0.05, channel=2, effect=0,
              color=color, color2=color, fadein=0, fadeout=0.3, holdtime=hold, fxtime=0, spawnflags=1)
    txt("gn_core_txt", "NOYAU", "255 170 90", 1.2)
    txt("gn_core_txt_ok", "SURCHARGE RÉUSSIE - le noyau est hors service : évacuez par les puits", "90 255 140", 8)
    txt("gn_core_txt_fail", "ÉCHEC - FUSION DU RÉACTEUR : FUYEZ PAR LES PUITS", "255 60 40", 10)
    outs = []
    for t in range(CORE_TIME):
        left = CORE_TIME - t
        outs += [T("gn_core_txt", "AddOutput", f"message SURCHARGEZ LE RÉACTEUR  {left // 60}:{left % 60:02d}", d=t),
                 T("gn_core_txt", "Display", d=t + 0.05)]
    outs.append(T("gn_core_meltdown", d=CORE_TIME))
    relay(w, "gn_core_clock", outs, origin=(rcx, rcy, kz + 940))
    add(w, "gn_phase_9_start", [T("gn_core_clock")])
    add(w, "gn_phase_9_done", [T("gn_core_clock", "CancelPending"), T("gn_core_ok_check", "Test")])
    w.ent("logic_branch", (rcx, rcy, kz + 960), targetname="gn_core_ok_check", InitialValue=1,
          outputs=[O("OnTrue", "gn_core_txt_ok", "Display")])
    # fusion : alarme générale, explosions en série dans le noyau, secousses, noyau mortel au bout de 45 s
    snd(w, "fx_melt_siren", (rcx, rcy, kz + 600), "ambient/alarms/citadel_alert_loop2.wav", everywhere=True, loop=True, vol=8)
    w.ent("env_shake", (rcx, rcy, kz), targetname="fx_melt_shake", amplitude=10, radius=30000, duration=5, frequency=30,
          spawnflags=1 + 4)
    w.ent("logic_timer", (rcx, rcy, kz + 980), targetname="fx_melt_t", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=2, UpperRandomBound=5, outputs=[O("OnTimer", "fx_melt_case", "PickRandom"),
                                                         O("OnTimer", "fx_melt_shake", "StartShake")])
    bs = []
    for k, (dx, dy, dz) in enumerate(((400, 400, 300), (-400, -400, 600), (-450, 380, -200), (420, -420, 650)), 1):
        bs.append(boom(w, f"fx_melt_{k}", (rcx + dx, rcy + dy, kz + dz), size=1.5, gibs=False, shake_r=5000))
    w.ent("logic_case", (rcx, rcy, kz + 1000), targetname="fx_melt_case",
          outputs=[O(f"OnCase0{k}", b, "Trigger") for k, b in enumerate(bs, 1)])
    w.ent("trigger_hurt", solids=[Block(M["zones"]["9"], "tools/toolstrigger")], targetname="gn_core_melt_hurt",
          damage=25, damagetype=262144, spawnflags=1, StartDisabled=1)
    relay(w, "gn_core_meltdown", [T("gn_core_ok_check", "SetValue", "0"), T("gn_core_txt_fail", "Display"),
                                  T("fx_melt_siren", "PlaySound"), T("fx_melt_t", "Enable"), T("fx_melt_shake", "StartShake"),
                                  T(bs[0]), T("fx_core_boom", d=1), T("fx_core_blue", "HideSprite"),
                                  T("gn_core_heat", "ShowSprite"), T("fx_core_arc", "TurnOn"),
                                  T("gn_phase_9_done", d=2),                     # la sortie s'ouvre : il faut fuir
                                  T("gn_core_melt_hurt", "Enable", d=45),        # 45 s pour quitter le noyau
                                  T("gn_exfil_fail", d=300),                     # 5 min (au lieu de 8) avant l'effondrement
                                  T("fx_melt_siren", "StopSound", d=320), T("fx_melt_t", "Disable", d=320)],
          origin=(rcx, rcy, kz + 1020))
    add(w, "gn_phase_10_done", [T("fx_melt_siren", "StopSound"), T("fx_melt_t", "Disable"), T("gn_core_melt_hurt", "Disable")])


FLEE = 300               # fusion : 5 min pour fuir


def meltdown_escalation(w, M):
    """Fusion : chrono FUYEZ de 5 min affiché, explosions de plus en plus fréquentes et fortes (noyau puis puits),
    vacarme sur toute la map, annonces de SENTINELLE recalées sur 5 min (au lieu des 8 min de l'exfiltration normale)."""
    rcx, rcy, kz = M["reactor_center"]
    w.ent("game_text", (rcx, rcy, kz + 880), targetname="gn_melt_txt", message="FUYEZ", x=-1, y=0.05, channel=2, effect=0,
          color="255 50 30", color2="255 50 30", fadein=0, fadeout=0.3, holdtime=1.2, fxtime=0, spawnflags=1)
    outs = []
    for t in range(12, FLEE):                     # le message d'échec reste affiché les 10 premières secondes
        left = FLEE - t
        outs += [T("gn_melt_txt", "AddOutput", f"message FUSION DU RÉACTEUR - FUYEZ  {left // 60}:{left % 60:02d}", d=t),
                 T("gn_melt_txt", "Display", d=t + 0.05)]
    # explosions dans les puits (le chemin de fuite) : à partir de 1 min
    far = []
    for k, p in enumerate(((-1800, -5200, 3000), (-4600, -5200, 4600), (-7400, -5200, 6200), (-1300, -5800, 2600),
                           (-4100, -5800, 4100), (-6900, -5800, 5700)), 1):
        far.append(boom(w, f"fx_flee_{k}", p, size=1.8, gibs=(k <= 3), shake_r=6000))
    w.ent("logic_case", (rcx, rcy, kz + 860), targetname="fx_flee_case",
          outputs=[O(f"OnCase0{k}", b, "Trigger") for k, b in enumerate(far, 1)])
    w.ent("logic_timer", (rcx, rcy, kz + 840), targetname="fx_flee_t", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=7, UpperRandomBound=11, outputs=[O("OnTimer", "fx_flee_case", "PickRandom")])
    # vacarme sur toute la map (sons entendus partout)
    noise = ["ambient/explosions/explode_1.wav", "ambient/explosions/explode_3.wav", "ambient/explosions/explode_5.wav",
             "ambient/levels/streetwar/building_rubble1.wav", "ambient/levels/streetwar/building_rubble3.wav",
             "ambient/atmosphere/hole_hit3.wav", "ambient/materials/metal_stress3.wav", "ambient/explosions/explode_8.wav"]
    for k, wav in enumerate(noise, 1):
        snd(w, f"fx_noise_{k}", (rcx, rcy, kz + 200), wav, everywhere=True, vol=8, pitch=85)
    w.ent("logic_case", (rcx, rcy, kz + 820), targetname="fx_noise_case",
          outputs=[O(f"OnCase0{k}", f"fx_noise_{k}", "PlaySound") for k in range(1, len(noise) + 1)])
    w.ent("logic_timer", (rcx, rcy, kz + 800), targetname="fx_noise_t", StartDisabled=1, RefireTime=6, UseRandomTime=0,
          outputs=[O("OnTimer", "fx_noise_case", "PickRandom")])
    w.ent("env_shake", (rcx, rcy, kz), targetname="fx_melt_quake", amplitude=16, radius=30000, duration=31, frequency=40,
          spawnflags=1 + 4)
    snd(w, "fx_melt_rumble", (rcx, rcy, kz + 200), "ambient/atmosphere/terrain_rumble1.wav", everywhere=True, vol=10)
    ramp = [  # (seconde, actions)
        (3, [T("gn_exfil_clock", "CancelPending")]),              # plus d'annonces calées sur 8 min
        (60, [T("gn_exfil_t240"), T("fx_flee_t", "Enable"), T("fx_noise_t", "Enable"),
              T("fx_melt_t", "LowerRandomBound", "1.5"), T("fx_melt_t", "UpperRandomBound", "3"),
              T("fx_melt_shake", "Amplitude", "12")]),
        (120, [T("fx_noise_t", "RefireTime", "3"), T("fx_flee_t", "LowerRandomBound", "4"), T("fx_flee_t", "UpperRandomBound", "7")]),
        (180, [T("gn_exfil_t120"), T("fx_noise_t", "RefireTime", "1.6"), T("fx_melt_t", "LowerRandomBound", "0.8"),
               T("fx_melt_t", "UpperRandomBound", "1.6"), T("fx_flee_t", "LowerRandomBound", "2"),
               T("fx_flee_t", "UpperRandomBound", "4"), T("fx_melt_shake", "Amplitude", "15")]),
        (240, [T("gn_exfil_t60"), T("fx_noise_t", "RefireTime", "0.9"), T("fx_flee_t", "LowerRandomBound", "1"),
               T("fx_flee_t", "UpperRandomBound", "2")]),
        (270, [T("gn_exfil_t30"), T("fx_melt_quake", "StartShake"), T("fx_melt_rumble", "PlaySound"),
               T("fx_noise_t", "RefireTime", "0.5")]),
        (FLEE, [T("fx_ex_final_boom"), T("fx_core_boom"), T("gn_base_collapse")]),
    ]
    for t, acts in ramp:
        outs += [(o[0], o[1], o[2], o[3], t + o[4], o[5]) for o in acts]
    add(w, "gn_core_meltdown", outs)
    add(w, "gn_phase_10_done", [T("gn_core_meltdown", "CancelPending"), T("gn_melt_flag", "Test"),
                                 T("gn_melt_txt", "AddOutput", "holdtime 0")])
    base_collapse(w, M)


def base_collapse(w, M):
    """Fusion : la base plonge dans le noir, puis (à 5 min, ou dès que les survivants sortent) elle explose de partout,
    de plus en plus fort, jusqu'à la fin de l'event."""
    rcx, rcy, kz = M["reactor_center"]
    w.ent("logic_branch", (rcx, rcy, kz + 780), targetname="gn_melt_flag", InitialValue=0,
          outputs=[O("OnTrue", "gn_base_collapse", "Trigger")])
    # noir : lumières du noyau et des puits coupées (grésillement) + assombrissement rouge de l'écran pour tous
    w.ent("env_fade", (rcx, rcy, kz + 760), targetname="fx_dark", rendercolor="70 25 20", renderamt=170, duration=4,
          holdtime=1200, spawnflags=2 + 8)
    w.ent("env_fade", (rcx, rcy, kz + 740), targetname="fx_dark_off", rendercolor="70 25 20", renderamt=170, duration=3,
          holdtime=0, spawnflags=1 + 2)
    dark = [T("gn_melt_flag", "SetValue", "1"), T("fx_dark", "Fade", d=1)]
    for k, dt in enumerate((0, 0.2, 0.5, 0.9, 1.6)):
        dark.append(T("gn_melt_lights", "TurnOff" if k % 2 == 0 else "TurnOn", d=dt))
    add(w, "gn_core_meltdown", dark)
    # balises rouges de secours dans les puits (seule lumière qui reste)
    for (x, y, z) in ((-1800, -4600, 3300), (-4600, -4600, 4900), (-7400, -4600, 6500), (-1800, -5900, 2700),
                      (-4600, -5900, 4300), (-7400, -5900, 5900), (1536, -4200, 2900), (1536, -6000, 2900)):
        w.ent("env_sprite", (x, y, z), targetname="fx_melt_beacon", model="sprites/glow01.spr", rendermode=9,
              rendercolor="255 30 20", renderamt=255, renderfx=10, scale=2, GlowProxySize=16, spawnflags=0)
    add(w, "gn_core_meltdown", [T("fx_melt_beacon", "ShowSprite", d=1.7)])
    add(w, "gn_phase_10_done", [T("fx_dark_off", "Fade")])
    # destruction de toute la base : 3 vagues d'explosions de plus en plus grosses
    waves = [
        (1.6, [(11776, -5120, 900), (6656, -4400, 1500), (9200, -5120, 780), (6656, -5900, 2100)]),         # prison, tour, sas
        (2.6, [(11776, -900, 950), (12800, 900, 950), (6656, 0, 300), (1536, 0, 250), (1536, 900, 250)]),  # données, garnison, usine
        (3.6, [(-7200, 0, 700), (-12800, -2000, 700), (-12800, 8000, 700), (-9300, -5000, 7000),          # hangar, canyon, nord,
               (-11800, -7200, 7000), (-12500, -4400, 7000)]),                                              # glacier (visibles)
    ]
    for wi, (size, pts) in enumerate(waves, 1):
        names = [boom(w, f"fx_col{wi}_{k}", p, size=size, gibs=False, shake_r=int(5000 * size)) for k, p in enumerate(pts, 1)]
        w.ent("logic_case", (rcx, rcy, kz + 700 - 20 * wi), targetname=f"fx_col{wi}_case",
              outputs=[O(f"OnCase0{k}", n, "Trigger") for k, n in enumerate(names, 1)])
        w.ent("logic_timer", (rcx, rcy, kz + 600 - 20 * wi), targetname=f"fx_col{wi}_t", StartDisabled=1, UseRandomTime=1,
              LowerRandomBound=2 + wi, UpperRandomBound=4 + 2 * wi, outputs=[O("OnTimer", f"fx_col{wi}_case", "PickRandom")])
    w.ent("logic_timer", (rcx, rcy, kz + 520), targetname="fx_col_quake_t", StartDisabled=1, RefireTime=8, UseRandomTime=0,
          outputs=[O("OnTimer", "fx_melt_quake", "StartShake"), O("OnTimer", "fx_melt_rumble", "PlaySound")])
    relay(w, "gn_base_collapse", [T("fx_col1_t", "Enable"), T("fx_noise_t", "Enable"), T("fx_noise_t", "RefireTime", "1.2"),
                                  T("fx_col_quake_t", "Enable"), T("fx_flee_t", "Enable"),
                                  T("fx_col2_t", "Enable", d=25), T("fx_col3_t", "Enable", d=50),
                                  T("fx_col1_t", "LowerRandomBound", "1", d=60), T("fx_col1_t", "UpperRandomBound", "2", d=60),
                                  T("fx_col2_t", "LowerRandomBound", "1.5", d=80), T("fx_col2_t", "UpperRandomBound", "3", d=80),
                                  T("fx_col3_t", "LowerRandomBound", "2", d=100), T("fx_col3_t", "UpperRandomBound", "4", d=100)],
          origin=(rcx, rcy, kz + 500))
    add(w, "gn_phase_11_done", [T(f"fx_col{i}_t", "Disable", d=20) for i in (1, 2, 3)]
        + [T("fx_noise_t", "Disable", d=20), T("fx_flee_t", "Disable", d=20), T("fx_col_quake_t", "Disable", d=20)])


def finale(w, M):
    """Fusion, final de film : ciel et brouillard rouges, bombardement orbital des Venator, débris qui tombent du ciel,
    glacier qui se fissure, colonnes de fumée, dernières paroles de SENTINELLE, explosion finale au départ du LAAT."""
    rcx, rcy, kz = M["reactor_center"]
    # 1 · ciel et brouillard qui virent au rouge (4 paliers sur 2 min)
    steps = [("0.55 0.40 0.45", "0.80 0.60 0.55", "150 120 120"), ("0.55 0.25 0.20", "0.85 0.45 0.30", "140 90 70"),
             ("0.50 0.15 0.08", "0.90 0.35 0.15", "130 65 40"), ("0.40 0.08 0.04", "0.95 0.30 0.08", "120 50 25")]
    sky = []
    for i, (top, bot, fog) in enumerate(steps):
        d = 2 + 30 * i
        sky += [T("gn_sky", "AddOutput", f"topcolor {top}", d=d), T("gn_sky", "AddOutput", f"bottomcolor {bot}", d=d),
                T("gn_fog", "SetColor", fog, d=d), T("gn_fog", "SetColorSecondary", fog, d=d)]
    add(w, "gn_core_meltdown", sky)
    # 2 · bombardement orbital : rayons depuis le ciel + impact
    strikes = []
    for k, (x, y, z, top) in enumerate(((-9000, -4300, 6930, 8380), (-9000, -7700, 6930, 8380), (-12900, -7700, 6930, 8380),
                                        (-7000, 1500, 20, 6080), (-12000, 2200, 20, 6080), (-13000, 9500, 20, 6080)), 1):
        n = f"fx_orb_{k}"
        w.ent("info_target", (x - 400 if x - 400 > -13250 else x + 300, y + 300, top), targetname=n + "_a")
        w.ent("info_target", (x, y, z + 8), targetname=n + "_b")
        w.ent("env_beam", (x, y, z + 40), targetname=n, LightningStart=n + "_a", LightningEnd=n + "_b",
              texture="sprites/laserbeam.spr", rendercolor="255 40 30" if k % 2 else "80 160 255", renderamt=255,
              BoltWidth=60, NoiseAmplitude=1.5, life=0, damage=0, spawnflags=0, TextureScroll=35, framerate=0)
        b = boom(w, n, (x, y, z), size=2.2, gibs=False, shake_r=9000)
        snd(w, n + "_zap", (x, y, z + 200), "ambient/levels/labs/electric_explosion5.wav", radius=12000)
        strikes.append([T(n, "TurnOn"), T(n + "_zap", "PlaySound"), T(n, "TurnOff", d=0.7), T(b, d=0.5)])
    w.ent("logic_case", (rcx, rcy, kz + 480), targetname="fx_orb_case",
          outputs=[(f"OnCase0{k}",) + o[1:] for k, outs in enumerate(strikes, 1) for o in outs])
    w.ent("logic_timer", (rcx, rcy, kz + 460), targetname="fx_orb_t", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=3, UpperRandomBound=7, outputs=[O("OnTimer", "fx_orb_case", "PickRandom")])
    # 4 · débris qui tombent du ciel sur le glacier (sans dégâts) + 6 · glacier qui se fissure + 7 · colonnes de fumée
    for k, (x, y) in enumerate(((-9800, -5000), (-11200, -4400), (-12400, -6800), (-10000, -7600)), 1):
        w.ent("env_shooter", (x, y, 8350), targetname=f"fx_sky_deb_{k}", angles="90 0 0", m_iGibs=8, delay=0,
              gibangles="0 0 0", gibanglevelocity=300, m_flVelocity=200, m_flVariance=1, m_flGibLife=6,
              shootmodel=f"models/gibs/metal_gib{k}.mdl", shootsounds=2, simulation=0, nogibshadows=1, gibgravityscale=1,
              massoverride=0, spawnflags=0)
    w.ent("logic_timer", (rcx, rcy, kz + 440), targetname="fx_sky_deb_t", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=2, UpperRandomBound=5,
          outputs=[O("OnTimer", f"fx_sky_deb_{k}", "Shoot", delay=0.4 * k) for k in range(1, 5)])
    cracks = []
    for k, (x0, y0) in enumerate(((-8960, -4600), (-8960, -6000), (-8960, -7400)), 1):
        n = f"fx_ice_{k}"
        # fissure : grondement + projection de neige + secousse locale (aucun bloc mobile : personne ne peut rester coincé)
        w.ent("env_steam", (x0 + 220, y0 + 250, 6916), targetname=n, InitialState=0, type=0, SpreadSpeed=80, Speed=260,
              StartSize=60, EndSize=220, Rate=40, JetLength=500, rendercolor="235 240 250", renderamt=220, rollspeed=10,
              angles="-90 0 0", spawnflags=0)
        w.ent("env_shake", (x0 + 220, y0 + 250, 6930), targetname=n + "_sh", amplitude=10, radius=2500, duration=3,
              frequency=40, spawnflags=4)
        snd(w, n + "_s", (x0 + 220, y0 + 250, 7000), "ambient/levels/streetwar/building_rubble2.wav", radius=9000)
        cracks += [T(n + "_s", "PlaySound", d=20 * k), T(n, "TurnOn", d=20 * k), T(n + "_sh", "StartShake", d=20 * k),
                   T(n, "TurnOff", d=20 * k + 4)]
    smokes = []
    for k, (x, y, z) in enumerate(((-8700, -4100, 6930), (-8700, -6500, 6930), (-8700, -8000, 6930), (-7000, 0, 20),
                                   (-12500, 0, 20)), 1):
        w.ent("env_smokestack", (x, y, z), targetname=f"fx_col_smoke_{k}", InitialState=0, BaseSpread=150, SpreadSpeed=50,
              Speed=200, StartSize=220, EndSize=800, Rate=6, JetLength=4500, WindAngle=0, WindSpeed=0,
              SmokeMaterial="particle/SmokeStack.vmt", rendercolor="25 22 22", renderamt=230, twist=4, roll=0)
        smokes.append(T(f"fx_col_smoke_{k}", "TurnOn", d=12 * k))
    add(w, "gn_base_collapse", [T("fx_orb_t", "Enable"), T("fx_sky_deb_t", "Enable")] + cracks + smokes)
    # 5 + 3 · dernières paroles de SENTINELLE puis explosion finale géante au départ du LAAT
    w.ent("ambient_generic", (rcx, rcy, kz + 420), targetname="fx_sent_fin", message="givre_noir/sentinelle_fin.wav",
          health=10, radius=20000, pitch=100, spawnflags=49)
    big = boom(w, "fx_final", (-8700, -5600, 6930), size=5.0, gibs=False, shake_r=30000)
    w.ent("env_fade", (rcx, rcy, kz + 400), targetname="fx_white", rendercolor="255 245 230", renderamt=255, duration=3,
          holdtime=0.6, spawnflags=1)
    w.ent("env_shake", (rcx, rcy, kz), targetname="fx_final_quake", amplitude=16, radius=40000, duration=6, frequency=60,
          spawnflags=1 + 4)
    snd(w, "fx_final_s", (rcx, rcy, kz + 300), "ambient/explosions/citadel_end_explosion1.wav", everywhere=True, vol=10)
    add(w, "gn_phase_11_done", [T("gn_final_flag", "Test", d=0.1)])
    add(w, "gn_core_meltdown", [T("gn_final_flag", "SetValue", "1")])
    w.ent("logic_branch", (rcx, rcy, kz + 380), targetname="gn_final_flag", InitialValue=0,
          outputs=[O("OnTrue", "gn_finale", "Trigger")])
    relay(w, "gn_finale", [T("fx_sent_fin", "PlaySound"), T(big, d=9), T("fx_white", "Fade", d=9), T("fx_final_quake", "StartShake", d=9),
                           T("fx_final_s", "PlaySound", d=9), T("fx_ex_column", "TurnOn", d=10), T("fx_orb_t", "Disable", d=9),
                           T("gn_sky", "AddOutput", "topcolor 0.9 0.6 0.3", d=9), T("gn_sky", "AddOutput", "topcolor 0.40 0.08 0.04", d=12)],
          origin=(rcx, rcy, kz + 360))
