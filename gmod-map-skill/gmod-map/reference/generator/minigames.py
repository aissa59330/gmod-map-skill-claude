"""Mini-jeux des objectifs (100 % map : boutons, leviers, vannes à tenir avec [E], cassables, voyants, sons).

Principe : chaque objectif garde son entité finale (gn_gen_i, gn_charge_i, gn_reactor_i...) ; le mini-jeu ne fait
que la DÉBLOQUER. La chaîne des phases et le déblocage manuel (gn_phase_N_done) restent donc intacts.
Les droïdes peuvent défaire ce que font les clones (relever un levier, désamorcer, rouvrir une vanne).

 2 · hangar      bouclier des tourelles AA : 2 générateurs de bouclier à casser, sinon les tourelles sont invulnérables
 4 · usine       générateurs : 3 coupe-circuits (leviers), puis explosion 6 s après ; bonus : levier de la chaîne
 5 · garnison    verrous synchronisés : les 3 consoles en moins de 10 s (géré dans entities.py)
 6 · données     coupures de courant pendant le piratage : chrono en pause jusqu'au réarmement du disjoncteur
 7 · prison      champ de force autour des consoles : 3 batteries à détruire
 8 · tour        charges : tenir [E] 8 s pour armer, 30 s de bips ; [E] 4 s sur l'autre molette pour désamorcer
 9 · noyau       3 vannes de refroidissement à fermer en moins de 45 s, puis les boutons du réacteur
"""
from geom import Block, oct_prism, MAT_METAL, MAT_SWITCH

LT = "lordtrilobite/"
CAP_RED = LT + "imp_lights02red"
WHEEL = LT + "isd_metal06"
CELL = LT + "isd_lights01"              # batteries / générateurs de bouclier (colonnes lumineuses bleues)
SHIELD = "effects/com_shield002a"       # champ d'énergie HL2 (translucide)
SND_OK = "buttons/button9.wav"
SND_NO = "buttons/button10.wav"
SND_ZAP = "ambient/energy/zap1.wav"
SND_BEEP = "buttons/blip1.wav"
SND_BOOM = "ambient/explosions/explode_4.wav"


def O(output, target, inp, param="", delay=0.0, times=-1):
    return (output, target, inp, param, delay, times)


def relay(w, name, outs, origin=(-14200, 0, 96)):
    return w.ent("logic_relay", origin, targetname=name, spawnflags=0, outputs=outs)


def led(w, name, pos, start_red=True, scale=0.3):
    """Voyant : deux sprites superposés, <name>_r (rouge) et <name>_v (vert)."""
    w.ent("env_sprite", pos, targetname=name + "_r", model="sprites/glow01.spr", rendermode=9, rendercolor="255 40 30",
          renderamt=255, scale=scale, GlowProxySize=4, spawnflags=1 if start_red else 0)
    w.ent("env_sprite", pos, targetname=name + "_v", model="sprites/glow01.spr", rendermode=9, rendercolor="40 255 90",
          renderamt=255, scale=scale, GlowProxySize=4, spawnflags=0 if start_red else 1)


def to_green(name):
    return [O("OnTrigger", name + "_r", "HideSprite"), O("OnTrigger", name + "_v", "ShowSprite")]


def snd(w, name, pos, wav, radius=1500, volume=10, everywhere=False):
    w.ent("ambient_generic", pos, targetname=name, message=wav, health=volume, radius=radius, pitch=100,
          spawnflags=48 + (1 if everywhere else 0))


def wheel(w, name, cx, cy, z, r, seconds, back=True, locked=False):
    """Molette / vanne horizontale à tenir avec [E] (momentary_rot_button) : un demi-tour en `seconds` secondes,
    revient d'elle-même si on lâche (back). OnFullyOpen quand elle est au bout."""
    w.ent("momentary_rot_button", (cx, cy, z + 4), solids=[oct_prism(cx, cy, r, z, z + 8, WHEEL),
                                                         Block((cx - r, cy - 3, z + 8, cx + r, cy + 3, z + 14), CAP_RED),
                                                         Block((cx - 3, cy - r, z + 8, cx + 3, cy + r, z + 14), CAP_RED)],
          targetname=name, spawnflags=1024, distance=170, speed=round(170 / seconds, 2),   # < 180 : à 180 pile l'angle bascule en -180 et la position retombe à 0
          returnspeed=180 if back else 0, startposition=0, startdirection=1, solidbsp=0,
          sounds=0, angles="0 0 0")
    if locked:
        w.meta.setdefault("start_locked", []).append(name)


def build_late(w):
    """Appelé après les entités : bouclier, chaîne, disjoncteur, champ de force, vannes du noyau."""
    M = w.meta
    # ---------------- 2 · bouclier des tourelles ----------------
    w.ent("filter_activator_name", (-7000, 0, 96), targetname="gn_filter_bouclier", filtername="gn_personne", Negated=0)
    for k, (gx, gy) in enumerate(((-8900, -1250), (-5560, 1650)), 1):
        w.ent("func_breakable", solids=[Block((gx - 48, gy - 48, 0, gx + 48, gy + 48, 144), "givre_noir/mj_bouclier")],
              targetname=f"gn_shieldgen_{k}", health=700, material=2, spawnflags=0, explosion=1, gibdir="0 0 0",
              ExplodeDamage=0, ExplodeRadius=0, PerformanceMode=0,
              outputs=[O("OnBreak", "gn_shield_counter", "Add", "1"), O("OnBreak", "gn_shield_snd", "PlaySound")])
        w.ent("env_sprite", (gx, gy, 170), targetname="gn_shieldgen_glow", model="sprites/glow01.spr", rendermode=9,
              rendercolor="90 170 255", renderamt=255, renderfx=2, scale=1.2, GlowProxySize=8, spawnflags=1)
    snd(w, "gn_shield_snd", (-7000, 0, 300), SND_BOOM, radius=6000)
    for i, box in enumerate(M["aa"], 1):
        cx, cy = (box[0] + box[3]) / 2, (box[1] + box[4]) / 2
        w.ent("func_brush", solids=[Block((cx - 104, cy - 104, box[2], cx + 104, cy + 104, box[5] + 48), SHIELD)],
              targetname="gn_aa_shield", Solidity=1, StartDisabled=0, spawnflags=2, rendermode=0, rendercolor="120 190 255")
    w.ent("math_counter", (-7000, 0, 120), targetname="gn_shield_counter", min=0, max=2, startvalue=0,
          outputs=[O("OnHitMax", "gn_aa_shield", "Disable"), O("OnHitMax", "gn_shieldgen_glow", "HideSprite")]
          + [O("OnHitMax", f"aa_{i}", "SetDamageFilter", "") for i in range(1, len(M["aa"]) + 1)]
          + [O("OnHitMax", "gn_shield_down", "Trigger")])
    relay(w, "gn_shield_down", [])            # repère narration : « boucliers des tourelles tombés »

    # ---------------- 4 · bonus : saboter la chaîne de droïdes ----------------
    lx, ly, lz = 1640, 1016, 512
    w.block((lx - 16, ly - 16, lz, lx + 16, ly + 16, lz + 40), "givre_noir/mj_chaine")
    w.ent("func_button", solids=[Block((lx - 5, ly - 12, lz + 40, lx + 5, ly + 12, lz + 72), CAP_RED)], targetname="gn_chaine_levier",
          spawnflags=1024 + 32, speed=60, lip=8, movedir="90 0 0", wait=-1,
          outputs=[O("OnIn", "gn_conveyor_1", "SetSpeed", "0"), O("OnIn", "gn_conveyor_2", "SetSpeed", "0"),
                   O("OnIn", "gn_press_timer", "Disable"), O("OnIn", "gn_bonus_chaine", "Trigger"),
                   O("OnIn", "gn_chaine_led_r", "HideSprite"), O("OnIn", "gn_chaine_led_v", "ShowSprite"),
                   O("OnOut", "gn_conveyor_1", "SetSpeed", "120"), O("OnOut", "gn_conveyor_2", "SetSpeed", "120"),
                   O("OnOut", "gn_press_timer", "Enable"), O("OnOut", "gn_bonus_chaine_relancee", "Trigger"),
                   O("OnOut", "gn_chaine_led_v", "HideSprite"), O("OnOut", "gn_chaine_led_r", "ShowSprite"),
                   O("OnPressed", "gn_chaine_snd", "PlaySound")])
    led(w, "gn_chaine_led", (lx, ly, lz + 96))
    snd(w, "gn_chaine_snd", (lx, ly, lz + 48), SND_OK)
    relay(w, "gn_bonus_chaine", [])            # repère narration : production de droïdes stoppée
    relay(w, "gn_bonus_chaine_relancee", [])

    # ---------------- 6 · disjoncteur du centre de données ----------------
    bx, by, bz = 10240, 560, 768
    w.block((bx, by - 40, bz + 40, bx + 24, by + 40, bz + 120), "givre_noir/mj_disjoncteur")
    w.ent("func_button", solids=[oct_prism(bx + 30, by, 12, bz + 64, bz + 96, CAP_RED)], targetname="gn_dc_breaker",
          spawnflags=1024, speed=40, lip=4, movedir="0 180 0", wait=1,
          outputs=[O("OnPressed", "gn_dc_power_cut", "Test")])
    # état « courant coupé » : plus de Lock/Unlock sur le bouton (un bouton verrouillé en mouvement ne se réarmait pas)
    w.ent("logic_branch", (bx, by, bz + 200), targetname="gn_dc_power_cut", InitialValue=0,
          outputs=[O("OnTrue", "!self", "SetValue", "0"), O("OnTrue", "gn_hack_resume", "Trigger"),
                   O("OnFalse", "gn_dc_breaker_no", "PlaySound")])
    snd(w, "gn_dc_breaker_no", (bx, by, bz + 80), SND_NO, radius=800)
    led(w, "gn_dc_breaker_led", (bx + 40, by, bz + 136), start_red=False)

    # ---------------- 7 · champ de force de la prison ----------------
    Z = 768
    for i, (cx, cy, cz) in enumerate(M["prison_consoles"], 1):
        r = 88
        walls = [(cx - r, cy - r, cz, cx + r, cy - r + 4, cz + 128), (cx - r, cy + r - 4, cz, cx + r, cy + r, cz + 128),
                 (cx - r, cy - r, cz, cx - r + 4, cy + r, cz + 128), (cx + r - 4, cy - r, cz, cx + r, cy + r, cz + 128)]
        w.ent("func_brush", solids=[Block(b, SHIELD) for b in walls], targetname="gn_prison_field", Solidity=1,
              StartDisabled=0, spawnflags=2, rendercolor="255 80 60")
        w.ent("trigger_hurt", solids=[Block((cx - r, cy - r, cz, cx + r, cy + r, cz + 128), "tools/toolstrigger")],
              targetname="gn_prison_field_hurt", damage=15, damagetype=1024, StartDisabled=0, spawnflags=1)
    for k, (px, py) in enumerate(((10420, -4180), (10420, -6060), (12920, -3780)), 1):
        w.ent("func_breakable", solids=[Block((px - 28, py - 28, Z, px + 28, py + 28, Z + 96), "givre_noir/mj_champ_batterie")],
              targetname=f"gn_prison_cell_{k}", health=400, material=2, spawnflags=0, explosion=1, gibdir="0 0 0",
              ExplodeDamage=0, ExplodeRadius=0, PerformanceMode=0,
              outputs=[O("OnBreak", "gn_prison_cells", "Add", "1"), O("OnBreak", "gn_prison_zap", "PlaySound")])
        w.ent("env_sprite", (px, py, Z + 116), targetname="gn_prison_cell_glow", model="sprites/glow01.spr", rendermode=9,
              rendercolor="255 80 60", renderamt=255, renderfx=2, scale=0.8, GlowProxySize=8, spawnflags=1)
    snd(w, "gn_prison_zap", (11776, -5120, Z + 300), SND_ZAP, radius=4000)
    w.ent("math_counter", (11776, -5120, Z + 40), targetname="gn_prison_cells", min=0, max=3, startvalue=0,
          outputs=[O("OnHitMax", "gn_prison_field", "Disable"), O("OnHitMax", "gn_prison_field_hurt", "Disable"),
                   O("OnHitMax", "gn_prison_cell_glow", "HideSprite"), O("OnHitMax", "gn_prison_field_down", "Trigger")]
          + [o for i in (1, 2, 3) for o in (O("OnHitMax", f"gn_cellblock_{i}", "Unlock"),
                                            O("OnHitMax", f"gn_cellblock_{i}_led_r", "ShowSprite"))])
    relay(w, "gn_prison_field_down", [])

    # ---------------- 9 · vannes de refroidissement du noyau ----------------
    rcx, rcy, rkz = M["reactor_center"]
    for k, (dx, dy) in enumerate(((-296, -296), (296, -296), (-296, 296)), 1):
        vx, vy = rcx + dx, rcy + dy
        w.block((vx - 20, vy - 20, rkz, vx + 20, vy + 20, rkz + 48), "givre_noir/mj_reacteur")
        wheel(w, f"gn_core_valve_{k}", vx, vy, rkz + 48, 18, 5, back=False)   # reste fermée quand on lâche
        w.ent("logic_branch", (vx, vy, rkz + 120), targetname=f"gn_core_valve_ok_{k}", InitialValue=0)
        led(w, f"gn_core_valve_led_{k}", (vx, vy, rkz + 96))
        # bouton « purge » des droïdes : rouvre la vanne
        w.ent("func_button", solids=[oct_prism(vx + 24, vy, 6, rkz + 20, rkz + 32, CAP_RED)], targetname=f"gn_core_purge_{k}",
              spawnflags=1024, speed=40, lip=2, movedir="0 180 0", wait=1,
              outputs=[O("OnPressed", f"gn_core_valve_ok_{k}", "SetValue", "0"),
                       O("OnPressed", f"gn_core_valve_{k}", "SetPosition", "0"),
                       O("OnPressed", f"gn_core_valve_led_{k}_v", "HideSprite"), O("OnPressed", f"gn_core_valve_led_{k}_r", "ShowSprite")])
        w.ents[-1]["solids"] = w.ents[-1]["solids"]
        for e in w.ents:
            if e["kv"].get("targetname") == f"gn_core_valve_{k}":
                e["outputs"] += [O("OnFullyOpen", f"gn_core_valve_ok_{k}", "SetValue", "1"),
                                 O("OnFullyOpen", f"gn_core_valve_led_{k}_r", "HideSprite"),
                                 O("OnFullyOpen", f"gn_core_valve_led_{k}_v", "ShowSprite"),
                                 O("OnFullyOpen", "gn_core_window", "Trigger"), O("OnFullyOpen", "gn_core_valve_snd", "PlaySound")]
    snd(w, "gn_core_valve_snd", (rcx, rcy, rkz + 200), SND_OK, radius=3000)
    snd(w, "gn_core_fail_snd", (rcx, rcy, rkz + 200), SND_NO, radius=4000)
    w.ent("env_sprite", (rcx, rcy, rkz + 400), targetname="gn_core_heat", model="sprites/glow01.spr", rendermode=9,
          rendercolor="255 60 20", renderamt=255, renderfx=2, scale=6, GlowProxySize=64, spawnflags=0)
    w.ent("logic_branch_listener", (rcx, rcy, rkz + 140), targetname="gn_core_valves",
          Branch01="gn_core_valve_ok_1", Branch02="gn_core_valve_ok_2", Branch03="gn_core_valve_ok_3",
          outputs=[O("OnAllTrue", "gn_core_window", "CancelPending"), O("OnAllTrue", "gn_core_window", "Disable"),
                   O("OnAllTrue", "gn_core_valves_done", "Trigger")])
    relay(w, "gn_core_window", [O("OnTrigger", "!self", "Disable"), O("OnTrigger", "gn_core_heat", "ShowSprite"),
                                O("OnTrigger", "gn_core_fail", "Trigger", delay=45)])
    relay(w, "gn_core_fail", [O("OnTrigger", "gn_core_window", "Enable", delay=0.1), O("OnTrigger", "gn_core_heat", "HideSprite"),
                              O("OnTrigger", "gn_core_fail_snd", "PlaySound")]
          + [o for k in (1, 2, 3) for o in (O("OnTrigger", f"gn_core_valve_ok_{k}", "SetValue", "0"),
                                            O("OnTrigger", f"gn_core_valve_{k}", "SetPosition", "0"),
                                            O("OnTrigger", f"gn_core_valve_led_{k}_v", "HideSprite"),
                                            O("OnTrigger", f"gn_core_valve_led_{k}_r", "ShowSprite"))])
    relay(w, "gn_core_valves_done", [O("OnTrigger", "gn_core_valve_snd", "PlaySound")]
          + [o for k in (1, 2, 3) for o in (O("OnTrigger", f"gn_core_valve_{k}", "Lock"), O("OnTrigger", f"gn_core_purge_{k}", "Lock"))]
          + [o for i in (1, 2, 3) for o in (O("OnTrigger", f"gn_reactor_{i}", "Unlock"),
                                            O("OnTrigger", f"gn_reactor_{i}_led_r", "ShowSprite"))])

    # ---------------- verrous de départ des molettes ----------------
    w.ent("logic_auto", (-14200, 0, 140), spawnflags=1,
          outputs=[O("OnMapSpawn", n, "Lock") for n in M.get("start_locked", [])])
    finalize_wheels(w)


def finalize_wheels(w):
    """Double déclenchement des molettes : OnFullyOpen OU sortie Position > 0,95 (logic_compare).
    Les actions « molette au bout » sont déplacées dans un relais <nom>_full, anti-rebond de 1,5 s."""
    for e in list(w.ents):
        if e["classname"] != "momentary_rot_button":
            continue
        n = e["kv"]["targetname"]
        org = tuple(float(v) for v in e["kv"]["origin"].split())
        full = [o for o in e["outputs"] if o[0] == "OnFullyOpen"]
        e["outputs"] = [o for o in e["outputs"] if o[0] != "OnFullyOpen"]
        e["outputs"] += [O("OnFullyOpen", n + "_full", "Trigger"), O("Position", n + "_cmp", "SetValueCompare")]
        w.ent("logic_compare", (org[0], org[1], org[2] + 200), targetname=n + "_cmp", InitialValue=0, CompareValue=0.95,
              outputs=[O("OnGreaterThan", n + "_full", "Trigger")])
        relay(w, n + "_full", [O("OnTrigger", "!self", "Disable"), O("OnTrigger", "!self", "Enable", delay=1.5)]
              + [("OnTrigger",) + o[1:] for o in full], origin=(org[0], org[1], org[2] + 220))


def generator(w, i, gx, gy, final_outs, button_fn):
    """4 · générateur : 3 coupe-circuits sur 3 coins de l'enclos ; les 3 abaissés -> 6 s de bips -> explosion.
    `button_fn` = entities.button (bouton final caché et verrouillé, garde le nom gn_gen_i)."""
    n = f"gn_gen_{i}"
    w.block((gx - 48, gy - 48, 0, gx + 48, gy + 48, 40), "givre_noir/mj_generateur")
    led(w, n + "_led", (gx, gy, 84))
    # bouton final invisible, dans le pupitre
    w.ent("func_button", solids=[Block((gx - 8, gy - 8, 8, gx + 8, gy + 8, 24), "tools/toolsnodraw")], targetname=n,
          spawnflags=1 + 1024 + 2048, wait=-1, speed=40, movedir="0 0 0", rendermode=10,
          outputs=final_outs + [O("OnPressed", n + "_boom", "PlaySound"), O("OnPressed", n + "_beep_t", "Disable"),
                                O("OnPressed", n + "_fx", "Trigger")]
          + [O("OnPressed", f"{n}_cb_{k}", "Lock") for k in (1, 2, 3)])
    snd(w, n + "_boom", (gx, gy, 96), SND_BOOM, radius=5000)
    # explosion : 3 boules de feu décalées (sans dégâts), secousse, onde de choc sur les props, étincelles + fumée qui restent
    for k, (dx, dy, dz) in enumerate(((0, 0, 60), (-40, 30, 110), (35, -25, 40)), 1):
        w.ent("env_explosion", (gx + dx, gy + dy, dz), targetname=f"{n}_exp_{k}", iMagnitude=220, iRadiusOverride=320,
              spawnflags=1 + 64, rendermode=5)            # 1 = pas de dégâts, 64 = pas de son (le nôtre suffit)
    w.ent("env_shake", (gx, gy, 64), targetname=n + "_shake", amplitude=14, radius=1800, duration=2.5, frequency=40,
          spawnflags=4)                                   # 4 = secoue aussi en l'air
    w.ent("env_physexplosion", (gx, gy, 48), targetname=n + "_push", magnitude=180, radius=400, spawnflags=1 + 2)
    w.ent("env_spark", (gx, gy, 70), targetname=n + "_sparks", MaxDelay=1, Magnitude=5, TrailLength=2,
          spawnflags=0, angles="-90 0 0")
    w.ent("env_smokestack", (gx, gy, 50), targetname=n + "_smoke", InitialState=0, BaseSpread=24, SpreadSpeed=12,
          Speed=60, StartSize=24, EndSize=110, Rate=10, JetLength=320, WindAngle=0, WindSpeed=0,
          SmokeMaterial="particle/SmokeStack.vmt", rendercolor="40 40 40", renderamt=200, twist=6, roll=0)
    snd(w, n + "_boom2", (gx, gy, 96), "ambient/explosions/explode_7.wav", radius=4000)
    relay(w, n + "_fx", [O("OnTrigger", n + "_exp_1", "Explode"), O("OnTrigger", n + "_shake", "StartShake"),
                         O("OnTrigger", n + "_push", "Explode"),
                         O("OnTrigger", n + "_exp_2", "Explode", delay=0.35), O("OnTrigger", n + "_boom2", "PlaySound", delay=0.35),
                         O("OnTrigger", n + "_exp_3", "Explode", delay=0.8),
                         O("OnTrigger", n + "_sparks", "StartSpark", delay=0.5), O("OnTrigger", n + "_smoke", "TurnOn", delay=0.5),
                         O("OnTrigger", n + "_led_v", "HideSprite"), O("OnTrigger", n + "_led_r", "HideSprite")],
          origin=(gx, gy, 220))
    snd(w, n + "_beep", (gx, gy, 96), SND_BEEP, radius=1500)
    w.ent("logic_timer", (gx, gy, 180), targetname=n + "_beep_t", RefireTime=0.5, StartDisabled=1, UseRandomTime=0,
          outputs=[O("OnTimer", n + "_beep", "PlaySound")])
    # 3 leviers abaissés -> surcharge : bips 6 s puis explosion (annulée si un levier est relevé avant)
    relay(w, n + "_surcharge", [O("OnTrigger", n, "Unlock", delay=6), O("OnTrigger", n, "Press", delay=6.1)],
          origin=(gx, gy, 200))
    w.ent("math_counter", (gx, gy, 160), targetname=n + "_cbs", min=0, max=3, startvalue=0,
          outputs=[O("OnHitMax", n + "_surcharge", "Trigger"), O("OnHitMax", n + "_beep_t", "Enable"),
                   O("OnHitMax", n + "_led_r", "HideSprite"), O("OnHitMax", n + "_led_v", "ShowSprite"),
                   O("OnChangedFromMax", n + "_surcharge", "CancelPending"), O("OnChangedFromMax", n + "_beep_t", "Disable"),
                   O("OnChangedFromMax", n + "_led_v", "HideSprite"), O("OnChangedFromMax", n + "_led_r", "ShowSprite")])
    for k, (dx, dy) in enumerate(((-1, -1), (1, -1), (1, 1)), 1):
        cx, cy = gx + dx * 128, gy + dy * 128
        w.block((cx - 12, cy - 12, 64, cx + 12, cy + 12, 92), MAT_SWITCH)
        w.ent("func_button", solids=[Block((cx - 4, cy - 10, 92, cx + 4, cy + 10, 124), CAP_RED)], targetname=f"{n}_cb_{k}",
              spawnflags=1024 + 32, speed=80, lip=8, movedir="90 0 0", wait=-1,
              outputs=[O("OnIn", n + "_cbs", "Add", "1"), O("OnOut", n + "_cbs", "Subtract", "1"),
                       O("OnIn", f"{n}_cb_{k}_led_r", "HideSprite"), O("OnIn", f"{n}_cb_{k}_led_v", "ShowSprite"),
                       O("OnOut", f"{n}_cb_{k}_led_v", "HideSprite"), O("OnOut", f"{n}_cb_{k}_led_r", "ShowSprite")])
        led(w, f"{n}_cb_{k}_led", (cx, cy, 140), scale=0.25)


def charge(w, i, box, final_outs):
    """8 · charge : boîtier + molette d'armement (8 s) + molette de désamorçage (4 s, verrouillée tant que non armée)."""
    n = f"gn_charge_{i}"
    x0, y0, z0, x1, y1, z1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w.block((x0 - 8, y0 - 8, z0, x1 + 8, y1 + 8, z1), "givre_noir/mj_charge")
    wheel(w, n + "_arm", cx - 14, cy, z1, 11, 8)
    wheel(w, n + "_disarm", cx + 14, cy, z1, 11, 4, locked=True)
    led(w, n + "_led", (cx, cy, z1 + 40))
    w.ent("func_button", solids=[Block((cx - 6, cy - 6, z0 + 8, cx + 6, cy + 6, z0 + 20), "tools/toolsnodraw")], targetname=n,
          spawnflags=1 + 1024 + 2048, wait=-1, speed=40, movedir="0 0 0", rendermode=10,
          outputs=final_outs + [O("OnPressed", n + "_arm", "Lock"), O("OnPressed", n + "_disarm", "Lock"),
                                O("OnPressed", n + "_beep_t", "Disable"), O("OnPressed", n + "_boom", "PlaySound")])
    snd(w, n + "_beep", (cx, cy, z1 + 16), SND_BEEP, radius=1500)
    snd(w, n + "_boom", (cx, cy, z1 + 16), SND_OK, radius=2500)
    w.ent("logic_timer", (cx, cy, z1 + 60), targetname=n + "_beep_t", RefireTime=1, StartDisabled=1, UseRandomTime=0,
          outputs=[O("OnTimer", n + "_beep", "PlaySound")])
    relay(w, n + "_count", [O("OnTrigger", n, "Unlock", delay=30), O("OnTrigger", n, "Press", delay=30.1)])
    for e in w.ents:
        tn = e["kv"].get("targetname")
        if tn == n + "_arm":
            e["outputs"] += [O("OnFullyOpen", n + "_arm", "Lock"), O("OnFullyOpen", n + "_disarm", "Unlock"),
                             O("OnFullyOpen", n + "_beep_t", "Enable"), O("OnFullyOpen", n + "_count", "Trigger"),
                             O("OnFullyOpen", n + "_led_r", "HideSprite"), O("OnFullyOpen", n + "_led_v", "ShowSprite")]
        elif tn == n + "_disarm":
            e["outputs"] += [O("OnFullyOpen", n + "_count", "CancelPending"), O("OnFullyOpen", n + "_beep_t", "Disable"),
                             O("OnFullyOpen", n + "_disarm", "SetPosition", "0"), O("OnFullyOpen", n + "_disarm", "Lock", delay=0.2),
                             O("OnFullyOpen", n + "_arm", "Unlock"), O("OnFullyOpen", n + "_arm", "SetPosition", "0"),
                             O("OnFullyOpen", n + "_led_v", "HideSprite"), O("OnFullyOpen", n + "_led_r", "ShowSprite")]
