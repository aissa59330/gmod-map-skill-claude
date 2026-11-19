"""Entités : spawns, portes + areaportals, triggers, lumières, logique des 11 phases.

Phases : 1 canyon, 2 hangar (AA), 3 conduits/porte, 4 usine (générateurs), 5 garnison (consoles),
6 centre de données (hack 3 étapes), 7 bloc de détention (cellules), 8 tour de communication (charges),
9 noyau (réacteur), 10 exfiltration (chrono 8 min), 11 extraction LAAT.
"""
import minigames
import fx
from geom import Block, oct_prism, MAT_DOOR, MAT_PORTAL, MAT_TRIGGER, MAT_HAZARD, MAT_SWITCH, MAT_METAL, MAT_GRATE
import texts

HACK_STAGE = 100       # 3 étapes = 5 min
EXFIL = 480            # 8 min
EXTRACT = 90


def O(output, target, inp, param="", delay=0.0, times=-1):
    return (output, target, inp, param, delay, times)


def relay(w, name, outs, once=False, origin=(-14200, 0, 64)):
    return w.ent("logic_relay", origin, targetname=name, spawnflags=1 if once else 0, outputs=outs)


def door(w, name, axis, pos, lo, hi, z0, z1, portal=True, speed=140, start_open=False):
    if axis == "x":
        box = (pos, lo, z0, pos + 16, hi, z1); pbox = (pos + 4, lo, z0, pos + 12, hi, z1)
    else:
        box = (lo, pos, z0, hi, pos + 16, z1); pbox = (lo, pos + 4, z0, hi, pos + 12, z1)
    # areaportal DANS l'épaisseur de la porte : la porte appartient aux deux zones et reste dessinée
    # quand le portail est fermé (sinon on voit le vide à travers l'ouverture)
    w.ent("func_door", solids=[Block(box, MAT_DOOR)], targetname=name, movedir="-90 0 0",
          speed=speed, lip=8, wait=-1, spawnflags=0, forceclosed=1, dmg=0,
          spawnpos=1 if start_open else 0, rendercolor="255 255 255")
    if portal:
        w.ent("func_areaportal", solids=[Block(pbox, MAT_PORTAL)], target=name,
              StartOpen=1 if start_open else 0, PortalVersion=1)


BTN_CAP = "lordtrilobite/imp_lights02red"


def button(w, name, box, outs, locked=False, housing=None, wait=-1):
    """Vrai bouton : boîtier (console) + champignon rouge qui s'enfonce de 8, voyant rouge (prêt) / vert (fait), clic.
    `box` = boîtier ; le bouton est posé dessus, à hauteur de main."""
    x0, y0, z0, x1, y1, z1 = box
    w.block(box, housing or MAT_SWITCH)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = max(12, min(24, (x1 - x0) / 2 - 6, (y1 - y0) / 2 - 6))
    led = (cx, cy, z1 + 30)
    w.ent("env_sprite", led, targetname=name + "_led_r", model="sprites/glow01.spr", rendermode=9, rendercolor="255 40 30",
          renderamt=255, scale=0.35, GlowProxySize=4, spawnflags=0 if locked else 1)
    w.ent("env_sprite", led, targetname=name + "_led_v", model="sprites/glow01.spr", rendermode=9, rendercolor="40 255 90",
          renderamt=255, scale=0.35, GlowProxySize=4, spawnflags=0)
    w.ent("ambient_generic", (cx, cy, z1 + 8), targetname=name + "_snd", message="buttons/button9.wav", health=10,
          radius=1250, pitch=100, spawnflags=48)
    w.ent("func_button", solids=[oct_prism(cx, cy, r, z1, z1 + 12, BTN_CAP)], targetname=name,
          spawnflags=1024 + (2048 if locked else 0), wait=wait, speed=40, lip=4, movedir="90 0 0",
          outputs=outs + [O("OnPressed", name + "_led_r", "HideSprite"), O("OnPressed", name + "_led_v", "ShowSprite"),
                          O("OnPressed", name + "_snd", "PlaySound")]
          + ([O("OnOut", name + "_led_v", "HideSprite"), O("OnOut", name + "_led_r", "ShowSprite")] if wait > 0 else []))


def booth_button(w, name, gx, gy, gz, outs, locked=False, wait=-1, plinth=MAT_METAL):
    """Pupitre au centre d'un enclos (l'enclos est posé dans zones.py) : socle bas + console, bouton à hauteur de main."""
    w.block((gx - 48, gy - 48, gz, gx + 48, gy + 48, gz + 40), plinth)
    button(w, name, (gx - 32, gy - 32, gz + 40, gx + 32, gy + 32, gz + 64), outs, locked=locked, wait=wait)


def counter(w, name, maxv, outs, origin):
    w.ent("math_counter", origin, targetname=name, min=0, max=maxv, startvalue=0, outputs=outs)


def trig_once(w, name, box, outs):
    w.ent("trigger_once", solids=[Block(box, MAT_TRIGGER)], spawnflags=1, targetname=name, outputs=outs)


def lights_for(w):
    M = w.meta
    dc_panels = []
    for s in w.spaces:
        if s.sky or not s.light:
            continue
        x0, y0, z0, x1, y1, z1 = s.box
        nx = max(1, round((x1 - x0) / s.light_step)); ny = max(1, round((y1 - y0) / s.light_step))
        levels = s.light_levels or [z1 - s.light_drop]
        for z in levels:
            for i in range(nx):
                for j in range(ny):
                    x = x0 + (i + 0.5) * (x1 - x0) / nx
                    y = y0 + (j + 0.5) * (y1 - y0) / ny
                    kv = {"_light": s.light, "_fifty_percent_distance": 384, "_zero_percent_distance": 1400}
                    if s.name == "factory":                  # coupées quand les 3 générateurs ont sauté
                        kv["targetname"] = "gn_factory_light_east" if x > 1536 else "gn_factory_light_west"
                    if s.name == "datacenter":
                        kv["targetname"] = "gn_dc_light"         # coupé pendant le piratage
                    if s.name == "core" or s.name.startswith(("shaft_", "exfil_", "trench_9")):
                        kv["targetname"] = "gn_melt_lights"      # coupées pendant la fusion du réacteur
                    w.ent("light", (x, y, z), **kv)
                    if z >= z1 - 64 and z1 - z0 >= 160:      # luminaire visible sous le plafond
                        fx, fy = int(x) // 16 * 16, int(y) // 16 * 16
                        pb = (fx - 48, fy - 16, z1 - 8, fx + 48, fy + 16, z1)
                        if s.name == "datacenter":
                            dc_panels.append(Block(pb, "lights/fluorescentcool001a"))
                        else:
                            w.block(pb, "lights/fluorescentcool001a")
    for (p, col) in M["lights"]:
        w.ent("light", p, _light=col, _fifty_percent_distance=384, _zero_percent_distance=1400)
    for p in M["core_lights"]:
        w.ent("light", p, targetname="gn_melt_lights", _light="150 200 255 520", _fifty_percent_distance=512, _zero_percent_distance=2000)
    w.ent("light", M["core_light_main"], targetname="gn_melt_lights", _light="120 230 255 800", _fifty_percent_distance=768,
          _zero_percent_distance=3000)
    # salle du hack (fermée par un plafond bas) : éclairage propre, froid
    for (hx, hy) in ((11520, -256), (11520, 256), (12032, -256), (12032, 256)):
        w.ent("light", (hx, hy, 1040), targetname="gn_dc_light", _light="200 225 255 380",
              _fifty_percent_distance=256, _zero_percent_distance=900)
    # luminaires du centre de données : éteints (cachés) pendant le piratage
    if dc_panels:
        w.ent("func_brush", solids=dc_panels, targetname="gn_dc_panels", Solidity=1, StartDisabled=0,
              spawnflags=2, rendermode=0, vrad_brush_cast_shadows=0)
    # alarme du piratage : lumières rouges (éteintes au départ), gyrophares, sirène
    alarm_pts = [(x, y, 1300) for x in (10624, 11776, 12928) for y in (-1024, 0, 1024)] +                 [(11520, 0, 1040), (12032, 0, 1040)]
    for p in alarm_pts:
        # lumière PRÉCALCULÉE qui clignote façon gyrophare (motif de style) : presque gratuit, contrairement aux light_dynamic
        w.ent("light", p, targetname="gn_dc_alarm", _light="255 20 10 520", spawnflags=1, pattern="zzzzmmaaaaaammzz",
              _fifty_percent_distance=256, _zero_percent_distance=900)
        w.ent("env_sprite", (p[0], p[1], p[2] + 20), targetname="gn_dc_alarm_glow", model="sprites/glow01.spr",
              rendermode=9, rendercolor="255 30 20", renderamt=255, renderfx=2, scale=1.6, GlowProxySize=16, spawnflags=0)
    # gyrophares : capot rouge qui tourne (les projecteurs light_dynamic ont été retirés : trop coûteux en FPS)
    beacons = [(x, y, 1408) for x in (10496, 11520, 13056) for y in (-768, 768)] + [(11520, 0, 1088), (12032, 0, 1088)]
    for k, (bx, by, ceil) in enumerate(beacons, 1):
        rn = f"gn_dc_beacon_rot_{k}"
        w.ent("func_rotating", (bx, by, ceil - 20), solids=[oct_prism(bx, by, 12, ceil - 32, ceil - 8, BTN_CAP)],
              targetname=rn, spawnflags=64, maxspeed=200, fanfriction=40, volume=0, angles="0 0 0", dmg=0)
    relay(w, "gn_dc_beacons_on", [O("OnTrigger", f"gn_dc_beacon_rot_{k}", "Start") for k in range(1, len(beacons) + 1)])
    relay(w, "gn_dc_beacons_off", [O("OnTrigger", f"gn_dc_beacon_rot_{k}", "Stop") for k in range(1, len(beacons) + 1)])
    w.ent("logic_timer", (11776, 0, 1190), targetname="gn_dc_voice_timer", RefireTime=30, StartDisabled=1,   # voix de 25,7 s
          UseRandomTime=0, outputs=[O("OnTimer", "gn_dc_voice", "PlaySound")])
    w.ent("logic_auto", (11776, 0, 1180), spawnflags=1,
          outputs=[# sécurité : aucun son du piratage ne doit jouer avant l'appui sur un terminal
                   O("OnMapSpawn", "gn_dc_voice", "StopSound", delay=0.5), O("OnMapSpawn", "gn_dc_voice_fin", "StopSound", delay=0.5),
                   O("OnMapSpawn", "gn_dc_siren", "StopSound", delay=0.5), O("OnMapSpawn", "gn_dc_voice_timer", "Disable")])
    for (sx, sy) in ((11776, 0), (10624, -1024), (10624, 1024), (12928, -1024), (12928, 1024)):
        w.ent("ambient_generic", (sx, sy, 1300), targetname="gn_dc_siren", message="givre_noir/sirene_hack.wav",
              health=8, radius=6000, pitch=100, spawnflags=16)      # 16 = démarre en silence, boucle
    w.ent("ambient_generic", (11776, 0, 1150), targetname="gn_dc_voice", message="givre_noir/sentinelle_alerte.mp3",
          health=10, radius=5200, pitch=100, spawnflags=49)
    w.ent("ambient_generic", (11776, 0, 1160), targetname="gn_dc_voice_fin", message="givre_noir/sentinelle_hack_fin.wav",
          health=10, radius=5200, pitch=100, spawnflags=49)
    # lueur du réacteur (vert-cyan, pulsation lente) + vapeur de refroidissement
    rcx, rcy, rkz = M["reactor_center"]
    for (dx, dy) in ((330, 0), (-330, 0), (0, 330), (0, -330)):
        for dz in (-600, 160, 720):
            w.ent("light", (rcx + dx, rcy + dy, rkz + dz), _light="90 255 190 700", style=2,
                  _fifty_percent_distance=320, _zero_percent_distance=1200)
    for (dx, dy) in ((300, 300), (-300, 300), (300, -300), (-300, -300)):
        w.ent("env_smokestack", (rcx + dx, rcy + dy, rkz - 960), InitialState=1, BaseSpread=40, SpreadSpeed=20, Speed=110,
              StartSize=48, EndSize=180, Rate=12, JetLength=1100, SmokeMaterial="particle/SmokeStack.vmt",
              rendercolor="190 235 225", renderamt=110, twist=0, roll=8, angles="0 0 0", WindAngle="0 0 0", WindSpeed=0)
    # droïdes de l'usine (chaîne de montage + stock) : décor non solide
    # droïde de DÉCOR statique allégé (1500/750/300 triangles, tools/make_static_droid.py) : ni animation ni réseau
    for (mdl, pos, yaw) in M.get("factory_droids", []):
        w.ent("prop_static", (pos[0], pos[1], 16 if pos[2] >= 16 else 0), model="models/givre_noir/droid_b1_debout.mdl",
              angles=f"0 {yaw} 0", solid=0, skin=0)
    w.ent("light_environment", (-13000, 0, 1800), angles="-50 35 0", pitch=-50,
          _light="215 228 255 230", _ambient="120 140 180 60", _lightHDR="-1 -1 -1 1", _ambientHDR="-1 -1 -1 1")
    for (x, y, z) in [(-12000, 0, 512), (-10400, 0, 512), (-7168, 0, 640), (-5632, 0, 600)] + M["glacier_lights"]:
        w.ent("light", (x, y, z), _light="200 215 255 350", _fifty_percent_distance=900, _zero_percent_distance=3000)


def build_entities(w):
    M = w.meta
    # ---- spawns ----
    for (x, y, z) in M["player_starts"]:
        w.ent("info_player_start", (x, y, z), angles="0 0 0")
    for zone, pts in M["def_spawns"].items():
        for (x, y, z) in pts:
            w.ent("info_target", (x, y, z), targetname=f"gn_def_spawn_{zone}", angles="0 180 0")
    for n, pts in M["atk_respawns"].items():
        for (x, y, z) in pts:
            w.ent("info_target", (x, y, z), targetname=f"gn_atk_respawn_{n}", angles="0 0 0")

    for d in M["doors"] + M["dc_doors"]:
        door(w, *d)

    w.ent("env_fog_controller", M["fog_origin"], targetname="gn_fog", fogenable=1, fogblend=0,
          fogcolor="178 194 214", fogcolor2="178 194 214", fogstart=1500, fogend=10000, fogmaxdensity=0.85,
          farz=11000, spawnflags=1, fogdir="1 0 0", angles="0 0 0", use_angles=0)
    w.ent("env_skypaint", (-13000, 0, 1900), targetname="gn_sky", topcolor="0.55 0.64 0.78", bottomcolor="0.82 0.86 0.92",
          fadebias="0.4", duskintensity="0", sunsize="0", starscale="0", drawstars="0", HDRScale="0.66")

    # ---- 1 -> 2 ----
    trig_once(w, "gn_trig_hangar", (-9600, -1536, 0, -9216, 1536, 512), [O("OnStartTouch", "gn_phase_1_done", "Trigger")])

    # ---- 2 : tourelles AA ----
    for i, box in enumerate(M["aa"], 1):
        w.ent("func_breakable", solids=[oct_prism((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, 64, box[2], box[5], MAT_HAZARD)], targetname=f"aa_{i}", health=900, damagefilter="gn_filter_bouclier",
              material=2, spawnflags=0, explosion=1, gibdir="0 0 0", ExplodeDamage=0, ExplodeRadius=0,
              PerformanceMode=0, outputs=[O("OnBreak", "gn_aa_counter", "Add", "1"), O("OnBreak", "gn_aa_destroyed", "Trigger")])
    counter(w, "gn_aa_counter", 3, [O("OnHitMax", "gn_phase_2_done", "Trigger")], (-7000, 0, 64))
    relay(w, "gn_aa_destroyed", [])

    # ---- 3 -> 4 ----
    trig_once(w, "gn_trig_factory", (16, -1520, 0, 3056, 1520, 192), [O("OnStartTouch", "gn_phase_3_done", "Trigger")])

    # ---- 4 : usine ----
    for i, (gx, gy) in enumerate(M["generators"], 1):
        minigames.generator(w, i, gx, gy, [O("OnPressed", "gn_gen_counter", "Add", "1"),
                                           O("OnPressed", "gn_sentinel_factory_dark", "Trigger"),
                                           O("OnPressed", "gn_gen_destroyed", "Trigger")], button)
    relay(w, "gn_gen_destroyed", [])
    counter(w, "gn_gen_counter", 3, [O("OnHitMax", "gn_phase_4_done", "Trigger"),
                                     O("OnHitMax", "gn_factory_blackout", "Trigger", delay=1.5)], (1536, 0, 64))
    # 3 générateurs détruits : plus de courant dans l'usine -> lumières coupées (grésillement), chaîne et presses à l'arrêt
    w.ent("ambient_generic", (1536, 0, 400), targetname="gn_factory_powerdown", message="ambient/energy/powerdown2.wav",
          health=10, radius=5000, pitch=80, spawnflags=48)
    relay(w, "gn_factory_blackout", [O("OnTrigger", "gn_sentinel_factory_dark", "CancelPending"),
                                     O("OnTrigger", "gn_factory_powerdown", "PlaySound")]
          + [o for nm in ("gn_factory_light_east", "gn_factory_light_west") for o in (
              O("OnTrigger", nm, "TurnOff"), O("OnTrigger", nm, "TurnOn", delay=0.25), O("OnTrigger", nm, "TurnOff", delay=0.5),
              O("OnTrigger", nm, "TurnOn", delay=0.9), O("OnTrigger", nm, "TurnOff", delay=1.6))]
          + [O("OnTrigger", f"gn_conveyor_{i}", "SetSpeed", "0") for i in range(1, len(M["conveyors"]) + 1)]
          + [O("OnTrigger", "gn_press_timer", "Disable"), O("OnTrigger", "gn_press_timer", "Kill", delay=0.1),
             O("OnTrigger", "gn_chaine_levier", "Lock"), O("OnTrigger", "gn_chaine_led_r", "HideSprite"),
             O("OnTrigger", "gn_chaine_led_v", "HideSprite")]
          + [O("OnTrigger", f"gn_press_hurt_{i}", "Disable", delay=2.1) for i in range(1, len(M["presses"]) + 1)]
          + [O("OnTrigger", "gn_factory_emerg", "ShowSprite", delay=1.8)])
    for (ex, ey) in ((300, -1300), (300, 1300), (1536, -1300), (1536, 1300), (2800, -1300), (2800, 1300)):
        w.ent("env_sprite", (ex, ey, 600), targetname="gn_factory_emerg", model="sprites/glow01.spr", rendermode=9,
              rendercolor="255 30 20", renderamt=255, renderfx=2, scale=1.5, GlowProxySize=16, spawnflags=0)
    relay(w, "gn_sentinel_factory_dark", [O("OnTrigger", "gn_factory_light_east", "TurnOff"),
                                          O("OnTrigger", "gn_factory_light_east", "TurnOn", delay=30)], once=True)
    for i, box in enumerate(M["conveyors"], 1):
        w.ent("func_conveyor", solids=[Block(box, MAT_GRATE)], targetname=f"gn_conveyor_{i}", speed=120,
              movedir="0 0 0", spawnflags=0, _minlight=0)
    for i, box in enumerate(M["presses"], 1):
        x0, y0, z0, x1, y1, z1 = box
        w.ent("func_door", solids=[Block(box, MAT_HAZARD)], targetname=f"gn_press_{i}", movedir="90 0 0",
              speed=200, lip=-(160 - (z1 - z0)), wait=-1, spawnflags=0, forceclosed=1, dmg=50)
        w.ent("trigger_hurt", solids=[Block((x0, y0, 16, x1, y1, 176), MAT_TRIGGER)], targetname=f"gn_press_hurt_{i}",
              damage=200, damagetype=1, StartDisabled=1, spawnflags=1)
    w.ent("logic_timer", (1536, 0, 96), targetname="gn_press_timer", RefireTime=6, StartDisabled=0, UseRandomTime=0,
          outputs=[o for i in (1, 2) for o in (
              O("OnTimer", f"gn_press_{i}", "Open"), O("OnTimer", f"gn_press_hurt_{i}", "Enable", delay=0.5),
              O("OnTimer", f"gn_press_hurt_{i}", "Disable", delay=2.0), O("OnTimer", f"gn_press_{i}", "Close", delay=2.0))])

    # ---- sas blindés (la seconde porte s'ouvre une fois la première fermée) ----
    for tag, d1, d2, box in (("sas", "gn_sas_door_1", "gn_sas_door_2", (3712, -448, 0, 4480, 448, 128)),
                             ("sas2", "gn_sas2_door_1", "gn_sas2_door_2", (8832, -5504, 768, 9600, -4736, 896))):
        trig_once(w, f"gn_{tag}_trig", box, [O("OnStartTouch", f"gn_{tag}_cycle", "Trigger")])
        # porte 1 fermée à +20 s (1,4 s de course), porte 2 ouverte à +23 s : enchaînement temporisé,
        # plus fiable que OnFullyClosed (observé non déclenché en jeu sur le premier sas)
        relay(w, f"gn_{tag}_cycle", [O("OnTrigger", d1, "Close", delay=20), O("OnTrigger", d1, "Lock", delay=20.1),
                                     O("OnTrigger", f"gn_{tag}_door1_closed", "Trigger", delay=23)], once=True)
        relay(w, f"gn_{tag}_door1_closed", [O("OnTrigger", d2, "Open")])

    # ---- 5 : garnison (3 consoles d'armurerie, une par étage) ----
    for i, (gx, gy, gz) in enumerate(M["garrison_consoles"], 1):
        booth_button(w, f"gn_armory_{i}", gx, gy, gz, [O("OnPressed", "gn_armory_counter", "Add", "1"),
                                                       O("OnPressed", "gn_armory_taken", "Trigger"),
                                                       O("OnPressed", f"gn_armory_window_{i}", "Trigger")],
                     wait=10, plinth="givre_noir/mj_armurerie")
        # fenêtre de 10 s : sans les 2 autres consoles à temps, ce verrou se réarme
        relay(w, f"gn_armory_window_{i}", [O("OnTrigger", "gn_armory_counter", "Subtract", "1", delay=10)])
    relay(w, "gn_armory_taken", [])
    counter(w, "gn_armory_counter", 3, [O("OnHitMax", "gn_phase_5_done", "Trigger")]
            + [o for i in (1, 2, 3) for o in (O("OnHitMax", f"gn_armory_window_{i}", "CancelPending"),
                                              O("OnHitMax", f"gn_armory_{i}", "Lock"),
                                              O("OnHitMax", f"gn_armory_{i}_led_r", "HideSprite", delay=10.5),
                                              O("OnHitMax", f"gn_armory_{i}_led_v", "ShowSprite", delay=10.5))], (6656, 0, 64))

    # ---- 6 : centre de données (hack en 3 étapes de 100 s, portes magnétiques) ----
    for i, box in enumerate(M["hack_buttons"], 1):
        button(w, f"gn_hack_button_{i}", box, [O("OnPressed", f"gn_hack_stage_{i}_start", "Trigger")], locked=(i > 1),
               housing=f"givre_noir/terminal_{i}")
        relay(w, f"gn_hack_stage_{i}_start", [O("OnTrigger", f"gn_hack_timer_{i}", "Enable"),
                                              O("OnTrigger", "gn_hack_fx_on", "Trigger"),
                                              O("OnTrigger", f"gn_hack_txt_etape_{i}", "Display"),
                                              # progression : 1 point par seconde, en pause pendant les coupures
                                              O("OnTrigger", "gn_hack_num", "SetValue", str(i)),
                                              O("OnTrigger", "gn_hack_prog", "SetValue", "0"),
                                              O("OnTrigger", "gn_hack_tick", "Enable"),
                                              O("OnTrigger", "gn_hack_cut_timer", "Enable")]
              + ([O("OnTrigger", "gn_hack_start", "Trigger")] if i == 1 else []), once=True)
        nxt = ([O("OnTimer", f"gn_hack_button_{i + 1}", "Unlock"), O("OnTimer", f"gn_hack_button_{i + 1}_led_r", "ShowSprite")] if i < 3 else
               [O("OnTimer", "gn_phase_6_done", "Trigger"), O("OnTimer", "gn_dc_lock_timer", "Disable")]
               + [O("OnTimer", f"gn_dc_door_{k}", "Open", delay=0.1) for k in range(1, 5)])
        w.ent("logic_timer", (11776, 0, 1000 + 20 * i), targetname=f"gn_hack_timer_{i}", RefireTime=99999, StartDisabled=1,   # fin d'étape : FireTimer par gn_hack_route
              outputs=[O("OnTimer", "!self", "Disable"), O("OnTimer", f"gn_hack_stage_{i}_done", "Trigger")] + nxt)
        relay(w, f"gn_hack_stage_{i}_done", [O("OnTrigger", "gn_hack_fx_off", "Trigger"),
                                             O("OnTrigger", f"gn_hack_txt_fin_{i}", "Display"),
                                             O("OnTrigger", "gn_hack_tick", "Disable"), O("OnTrigger", "gn_hack_cut_timer", "Disable"),
                                             O("OnTrigger", "gn_dc_power_cut", "SetValue", "0"),
                                             O("OnTrigger", "gn_dc_breaker_led_r", "HideSprite"), O("OnTrigger", "gn_dc_breaker_led_v", "ShowSprite")]
              + ([O("OnTrigger", "gn_dc_voice_fin", "PlaySound", delay=1)] if i == 3 else []))
        w.ent("game_text", (11776, 0, 1200 + 10 * i), targetname=f"gn_hack_txt_fin_{i}",
              message=f"PIRATAGE {i}/3 TERMINÉ" + (" - les portes s'ouvrent" if i == 3 else " - terminal suivant déverrouillé"),
              x=-1, y=0.12, channel=3, effect=0, color="80 255 120", color2="80 255 120",
              fadein=0, fadeout=0.5, holdtime=6, fxtime=0, spawnflags=1)
        w.ent("game_text", (11776, 0, 1240 + 10 * i), targetname=f"gn_hack_txt_etape_{i}",
              message=f"TERMINAL {i}/3", x=-1, y=0.08, channel=4, effect=0, color="255 200 190", color2="255 200 190",
              fadein=0, fadeout=0.5, holdtime=HACK_STAGE, fxtime=0, spawnflags=1)
    relay(w, "gn_hack_start", [O("OnTrigger", "gn_dc_lock_timer", "Enable")], once=True)
    # ---- ambiance du piratage : noir + alarme rouge + sirène + voix de SENTINELLE + compte à rebours ----
    # compte à rebours piloté par la progression (gn_hack_prog), donc juste même avec les pauses
    marks = list(range(HACK_STAGE, 10, -10)) + [10, 5, 4, 3, 2, 1]      # secondes restantes affichées (15 cas)
    w.ent("logic_timer", (11776, 96, 1320), targetname="gn_hack_tick", RefireTime=1, StartDisabled=1, UseRandomTime=0,
          outputs=[O("OnTimer", "gn_hack_prog", "Add", "1")])
    w.ent("math_counter", (11776, 96, 1330), targetname="gn_hack_prog", min=0, max=HACK_STAGE, startvalue=0,
          outputs=[O("OnHitMax", "gn_hack_tick", "Disable"), O("OnHitMax", "gn_hack_num", "GetValue"),
                   O("OutValue", "gn_hack_txtcase", "InValue")])
    w.ent("math_counter", (11776, 96, 1340), targetname="gn_hack_num", min=0, max=3, startvalue=0,
          outputs=[O("OnGetValue", "gn_hack_route", "InValue")])
    w.ent("logic_case", (11776, 96, 1350), targetname="gn_hack_route", Case01="1", Case02="2", Case03="3",
          outputs=[O(f"OnCase0{k}", f"gn_hack_timer_{k}", "FireTimer") for k in (1, 2, 3)])
    case_kv = {f"Case{n:02d}": str(HACK_STAGE - r) for n, r in enumerate(marks, 1)}
    w.ent("logic_case", (11776, 96, 1360), targetname="gn_hack_txtcase",
          outputs=[O(f"OnCase{n:02d}", f"gn_hack_txt_{r}", "Display") for n, r in enumerate(marks, 1)], **case_kv)
    for n, r in enumerate(marks):
        nxt = marks[n + 1] if n + 1 < len(marks) else 0
        w.ent("game_text", (11776, 64, 1200 + r), targetname=f"gn_hack_txt_{r}",
              message=f"PIRATAGE EN COURS  -  {r // 60}:{r % 60:02d}", x=-1, y=0.12, channel=3, effect=0,
              color="255 70 60", color2="255 70 60", fadein=0, fadeout=0.1,
              holdtime=(r - nxt) + 0.3, fxtime=0, spawnflags=1)
    # coupures de courant aléatoires pendant chaque étape : pause jusqu'au réarmement du disjoncteur (mur ouest)
    w.ent("logic_timer", (11776, 96, 1370), targetname="gn_hack_cut_timer", StartDisabled=1, UseRandomTime=1,
          LowerRandomBound=25, UpperRandomBound=45, outputs=[O("OnTimer", "gn_hack_cut", "Trigger")])
    relay(w, "gn_hack_cut", [O("OnTrigger", "gn_hack_tick", "Disable"), O("OnTrigger", "gn_hack_cut_timer", "Disable"),
                             O("OnTrigger", "gn_dc_power_cut", "SetValue", "1"), O("OnTrigger", "gn_dc_breaker_led_v", "HideSprite"),
                             O("OnTrigger", "gn_dc_breaker_led_r", "ShowSprite"), O("OnTrigger", "gn_hack_txt_pause", "Display"),
                             O("OnTrigger", "gn_hack_cut_snd", "PlaySound"), O("OnTrigger", "gn_dc_alarm", "TurnOff"),
                             O("OnTrigger", "gn_dc_alarm", "TurnOn", delay=1.5)])
    relay(w, "gn_hack_resume", [O("OnTrigger", "gn_hack_tick", "Enable"), O("OnTrigger", "gn_hack_cut_timer", "Enable"),
                                O("OnTrigger", "gn_dc_breaker_led_r", "HideSprite"), O("OnTrigger", "gn_dc_breaker_led_v", "ShowSprite"),
                                O("OnTrigger", "gn_hack_txt_reprise", "Display")])
    w.ent("ambient_generic", (11776, 0, 1100), targetname="gn_hack_cut_snd", message="ambient/energy/zap1.wav", health=10,
          radius=5000, pitch=80, spawnflags=48)
    w.ent("game_text", (11776, 64, 1100), targetname="gn_hack_txt_pause",
          message="PIRATAGE EN PAUSE  -  coupure de courant : réarmez le disjoncteur (mur ouest)", x=-1, y=0.12, channel=3,
          effect=0, color="255 190 60", color2="255 190 60", fadein=0, fadeout=0.2, holdtime=120, fxtime=0, spawnflags=1)
    w.ent("game_text", (11776, 64, 1110), targetname="gn_hack_txt_reprise", message="PIRATAGE REPRIS", x=-1, y=0.12,
          channel=3, effect=0, color="120 255 140", color2="120 255 140", fadein=0, fadeout=0.2, holdtime=3, fxtime=0, spawnflags=1)
    LOCKDOWN = ["gn_door_gate", "gn_door_conduit", "gn_door_4n", "gn_door_4s", "gn_sas_door_2",
                "gn_door_5a", "gn_door_5n", "gn_door_5s"]      # toutes les portes ouvertes à ce stade de l'event
    relay(w, "gn_hack_fx_on", [O("OnTrigger", d, "Close", delay=3) for d in LOCKDOWN]
          + [O("OnTrigger", "gn_dc_voice_timer", "Enable")] + [O("OnTrigger", "gn_dc_light", "TurnOff"), O("OnTrigger", "gn_dc_panels", "Disable"),
                               O("OnTrigger", "gn_dc_alarm", "TurnOn"), O("OnTrigger", "gn_dc_alarm_glow", "ShowSprite"),
                               O("OnTrigger", "gn_dc_beacons_on", "Trigger"),
                               O("OnTrigger", "gn_dc_siren", "PlaySound"), O("OnTrigger", "gn_dc_voice", "PlaySound", delay=0.5)])
    relay(w, "gn_hack_fx_off", [O("OnTrigger", d, "Open") for d in LOCKDOWN]
          + [O("OnTrigger", "gn_dc_voice_timer", "Disable"), O("OnTrigger", "gn_dc_voice", "StopSound")] + [O("OnTrigger", "gn_dc_light", "TurnOn"), O("OnTrigger", "gn_dc_panels", "Enable"),
                                O("OnTrigger", "gn_dc_alarm", "TurnOff"), O("OnTrigger", "gn_dc_alarm_glow", "HideSprite"),
                                O("OnTrigger", "gn_dc_beacons_off", "Trigger"),
                                O("OnTrigger", "gn_dc_siren", "StopSound")])
    w.ent("logic_timer", (11776, 0, 1300), targetname="gn_dc_lock_timer", RefireTime=45, StartDisabled=1,
          outputs=[O("OnTimer", "gn_dc_case", "PickRandom"), O("OnTimer", "gn_sentinel_dc_lock", "Trigger")])
    w.ent("logic_case", (11776, 0, 1320), targetname="gn_dc_case",
          outputs=[o for i in range(1, 5) for o in (O(f"OnCase0{i}", f"gn_dc_door_{i}", "Close"),
                                                     O(f"OnCase0{i}", f"gn_dc_door_{i}", "Open", delay=20))])
    relay(w, "gn_sentinel_dc_lock", [])

    # ---- 7 : bloc de détention (3 consoles -> 3 groupes de cellules) ----
    for i, ((cx, cy, cz), grp) in enumerate(zip(M["prison_consoles"], ("a", "b", "c")), 1):
        booth_button(w, f"gn_cellblock_{i}", cx, cy, cz, [O("OnPressed", "gn_cell_counter", "Add", "1"),
                                                          O("OnPressed", f"gn_cells_{grp}_open", "Trigger"),
                                                          O("OnPressed", "gn_sentinel_prison", "Trigger")],
                     locked=True, plinth="givre_noir/mj_champ")
        relay(w, f"gn_cells_{grp}_open", [O("OnTrigger", n, "Open") for n in M["cells"][grp]])
    relay(w, "gn_sentinel_prison", [], once=True)
    counter(w, "gn_cell_counter", 3, [O("OnHitMax", "gn_phase_7_done", "Trigger")], (11776, -5120, 1300))

    # ---- 8 : tour de communication (3 charges, une par niveau) ----
    for i, box in enumerate(M["charges"], 1):
        minigames.charge(w, i, box, [O("OnPressed", "gn_charge_counter", "Add", "1"),
                                     O("OnPressed", "gn_charge_planted", "Trigger"),
                                     O("OnPressed", "gn_sentinel_tower", "Trigger")])
    relay(w, "gn_charge_planted", [])
    relay(w, "gn_sentinel_tower", [], once=True)
    counter(w, "gn_charge_counter", 3, [O("OnHitMax", "gn_phase_8_done", "Trigger")], (5376, -5120, 900))

    # ---- 9 : noyau ----
    for i, box in enumerate(M["reactor_buttons"], 1):
        button(w, f"gn_reactor_{i}", box, [O("OnPressed", "gn_reactor_counter", "Add", "1"),
                                           O("OnPressed", "gn_reactor_overload", "Trigger")], locked=True)
    relay(w, "gn_reactor_overload", [])
    counter(w, "gn_reactor_counter", 3, [O("OnHitMax", "gn_phase_9_done", "Trigger")], (2880, -5120, 2400))
    for (name, box, movedir, dist) in M["bridges"]:
        w.ent("func_movelinear", solids=[Block(box, MAT_GRATE)], targetname=name, movedir=movedir,
              movedistance=dist, speed=120, startposition=0, spawnflags=0, blockdamage=0)   # 8 = non solide : interdit
    minigames.build_late(w)
    relay(w, "gn_sentinel_core_bridge", [O("OnTrigger", "gn_core_bridge_1", "Open"),
                                         O("OnTrigger", "gn_core_bridge_1", "Close", delay=45)])
    w.ent("trigger_hurt", solids=[Block(M["core_hurt"], MAT_TRIGGER)], targetname="gn_core_pit",
          damage=1000, damagetype=32, spawnflags=1, StartDisabled=0)

    # ---- 10 : exfiltration (8 min) ----
    marks = [("gn_exfil_t360", 120), ("gn_exfil_t240", 240), ("gn_exfil_t120", 360), ("gn_exfil_t60", 420),
             ("gn_exfil_t30", 450), ("gn_exfil_fail", EXFIL)]
    relay(w, "gn_exfil_clock", [O("OnTrigger", n, "Trigger", delay=d) for n, d in marks])
    for n, _ in marks:
        relay(w, n, [])
    relay(w, "gn_sentinel_exfil_seal", [])
    for i, (box, d) in enumerate(M["seals"], 1):
        trig_once(w, f"gn_exfil_seal_{i}", box, [O("OnStartTouch", d, "Close", delay=12), O("OnStartTouch", d, "Lock", delay=13),
                                                 O("OnStartTouch", "gn_sentinel_exfil_seal", "Trigger")])
    trig_once(w, "gn_trig_glacier", M["glacier_trigger"], [O("OnStartTouch", "gn_phase_10_done", "Trigger"),
                                                            O("OnStartTouch", "gn_exfil_door_5", "Close", delay=15)])

    # ---- 11 : extraction ----
    w.ent("trigger_multiple", solids=[Block(M["extract"], MAT_TRIGGER)], targetname="gn_extract_zone",
          spawnflags=1, wait=1, StartDisabled=1)

    # ---- relais de phase ----
    def opens(*names):
        return [O("OnTrigger", n, "Open") for n in names]
    P = {
        1: ([], [O("OnTrigger", "gn_phase_2_start", "Trigger")]),
        2: ([], opens("gn_door_gate", "gn_door_conduit") + [
                O("OnTrigger", "gn_fog", "SetStartDist", "2500", delay=8), O("OnTrigger", "gn_fog", "SetEndDist", "12000", delay=8),
                O("OnTrigger", "gn_fog", "SetFarZ", "13000", delay=8),
                                                             O("OnTrigger", "gn_phase_3_start", "Trigger")]),
        3: ([], [O("OnTrigger", "gn_phase_4_start", "Trigger")]),
        4: ([], opens("gn_sas_door_1", "gn_door_4n", "gn_door_4s") + [O("OnTrigger", "gn_phase_5_start", "Trigger")]),
        5: ([], opens("gn_door_5a", "gn_door_5n", "gn_door_5s") + [O("OnTrigger", "gn_phase_6_start", "Trigger")]),
        6: (opens(*[f"gn_dc_door_{i}" for i in range(1, 5)]),
            opens("gn_door_6w", "gn_door_6a", "gn_door_6b", "gn_door_6e") + [O("OnTrigger", "gn_phase_7_start", "Trigger")]),
        7: ([], opens("gn_sas2_door_1", "gn_door_7n", "gn_door_7s") + [O("OnTrigger", "gn_phase_8_start", "Trigger")]),
        8: ([], opens("gn_door_8a", "gn_door_8n", "gn_door_8s") + [O("OnTrigger", "gn_phase_9_start", "Trigger")]),
        9: ([O("OnTrigger", "gn_sentinel_core_bridge", "Trigger", delay=60)],
            opens("gn_exfil_door_0") + [O("OnTrigger", "gn_phase_10_start", "Trigger")]),
        10: ([O("OnTrigger", "gn_exfil_clock", "Trigger")] + opens(*[f"gn_exfil_door_{i}" for i in range(1, 6)]),
             [O("OnTrigger", "gn_exfil_clock", "CancelPending"), O("OnTrigger", "gn_phase_11_start", "Trigger")]),
        11: ([O("OnTrigger", "gn_extract_zone", "Enable"), O("OnTrigger", "gn_phase_11_done", "Trigger", delay=EXTRACT)],
             [O("OnTrigger", "gn_extract_zone", "Disable", delay=0.5)]),
    }
    for n, (start, done) in P.items():
        relay(w, f"gn_phase_{n}_start", start, once=True, origin=(-14200 + 48 * n, 600, 64))
        relay(w, f"gn_phase_{n}_done", done, once=True, origin=(-14200 + 48 * n, 700, 64))

    map_only_event(w)
    # ciel 3D
    w.ent("sky_camera", M["sky_camera"], scale=16, fogenable=0, use_angles=0, angles="0 0 0")
    for (model, pos, yaw) in M["sky_props"]:
        w.ent("prop_static", pos, model=model, angles=f"0 {yaw} 0", solid=0, skin=0, fademindist=-1, disableshadows=1)
    lights_for(w)
    fx.build(w)          # animations des 11 étapes (generator/fx.py)


def _find(w, name):
    return [e for e in w.ents if e["kv"].get("targetname") == name]


NL = " : "   # pas de saut de ligne : srctools double les antislashs dans le VMF


def _say(target, text, delay=0.0):
    """AddOutput du texte puis Display (le texte ne doit pas contenir de virgule)."""
    assert "," not in text and '"' not in text, text
    return [O("OnTrigger", target, "AddOutput", "message " + text, delay=delay),
            O("OnTrigger", target, "Display", delay=delay + 0.05)]


def _clock(total, step, label):
    outs = []
    for t in range(0, total, step):
        left = total - t
        outs += _say("gn_txt_timer", f"{label}  {left // 60}:{left % 60:02d}", delay=t)
    return outs


def map_only_event(w):
    """Event sans addon, sans texte affiché et sans téléporteur : démarrage auto + échec de l'exfiltration."""
    M = w.meta
    def add(name, outs):
        ents = _find(w, name)
        assert ents, f"relais introuvable : {name}"
        ents[0]["outputs"].extend(outs)

    # (aucun texte affiché : la narration est faite en direct par l'équipe de l'event,
    #  voir docs/narration.md généré depuis generator/texts.py)

    # la phase 1 démarre au chargement de la map (aucune commande admin nécessaire)
    w.ent("logic_auto", (-14200, -600, 64), spawnflags=1, outputs=[O("OnMapSpawn", "gn_phase_1_start", "Trigger", delay=5)])

    # fin du chrono d'exfiltration : le noyau et les puits deviennent mortels
    w.ent("trigger_hurt", solids=[Block((-8192, -6656, 1280, 3072, -3584, 6896), MAT_TRIGGER)], targetname="gn_exfil_doom",
          damage=500, damagetype=32, spawnflags=1, StartDisabled=1)
    add("gn_exfil_fail", [O("OnTrigger", "gn_exfil_doom", "Enable")])

    # pas de téléporteur : les gérants placent les spawns eux-mêmes sur les repères
    # gn_atk_respawn_<n> (attaquants, phase n) et gn_def_spawn_<zone> (défenseurs)
