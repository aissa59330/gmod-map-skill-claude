"""Génère docs/narration.md : script de narration pour l'équipe de l'event (rien n'est affiché par la map).

python tools/narration.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "generator"))
import texts  # noqa: E402
from entities import HACK_STAGE, EXFIL, EXTRACT  # noqa: E402

# ce qui se passe en jeu quand le relais se déclenche
WHEN = {
    "gn_phase_1_start": "Chargement de la map (automatique)",
    "gn_phase_2_start": "Le premier joueur entre dans le hangar",
    "gn_aa_destroyed": "Une tourelle AA est détruite (x3)",
    "gn_phase_2_done": "3e tourelle détruite : la porte principale et l'accès aux conduits s'ouvrent",
    "gn_phase_3_start": "Juste après",
    "gn_phase_4_start": "Le premier joueur entre dans l'usine",
    "gn_gen_destroyed": "Un générateur est saboté (x3)",
    "gn_sentinel_factory_dark": "1er générateur saboté : la moitié est de l'usine est plongée dans le noir 30 s",
    "gn_phase_4_done": "3e générateur saboté : sas + 2 flancs vers la garnison s'ouvrent",
    "gn_phase_5_start": "Juste après",
    "gn_armory_taken": "Une console d'armurerie est prise (x3, une par étage)",
    "gn_phase_5_done": "3e console : les 3 accès vers le centre de données s'ouvrent",
    "gn_phase_6_start": "Juste après (les 4 portes de la salle du hack s'ouvrent)",
    "gn_hack_start": f"Terminal 1 activé (salle centrale) : étape 1 du hack, {HACK_STAGE} s",
    "gn_hack_stage_1_done": f"Étape 1 finie : le terminal 2 (plateforme nord) se déverrouille, {HACK_STAGE} s",
    "gn_hack_stage_2_done": f"Étape 2 finie : le terminal 3 (zone sud) se déverrouille, {HACK_STAGE} s",
    "gn_sentinel_dc_lock": "Toutes les 45 s pendant le hack : une porte de la salle du hack se ferme 20 s",
    "gn_phase_6_done": "Hack terminé : 4 accès vers le bloc de détention s'ouvrent",
    "gn_phase_7_start": "Juste après",
    "gn_sentinel_prison": "1re console de cellules activée",
    "gn_cells_a_open": "Console du mirador : cellules du mur est (bas)",
    "gn_cells_b_open": "Console de la coursive est : cellules du mur sud (bas)",
    "gn_cells_c_open": "Console de la coursive sud : toutes les cellules du haut",
    "gn_phase_7_done": "3 blocs ouverts : sas + 2 flancs vers la tour s'ouvrent",
    "gn_phase_8_start": "Juste après",
    "gn_sentinel_tower": "1re charge posée sur l'antenne",
    "gn_charge_planted": "Une charge est posée (x3, une par niveau)",
    "gn_phase_8_done": "3e charge : les 3 accès vers le noyau s'ouvrent",
    "gn_phase_9_start": "Juste après",
    "gn_sentinel_core_bridge": "60 s après l'ouverture du noyau : le pont est se rétracte 45 s",
    "gn_reactor_overload": "Une console du réacteur est surchargée (x3)",
    "gn_phase_9_done": "3e console : la sortie vers les puits s'ouvre, le chrono démarre",
    "gn_phase_10_start": f"Début du chrono d'exfiltration ({EXFIL // 60} min)",
    "gn_sentinel_exfil_seal": "Les premiers joueurs atteignent un palier : le sas derrière eux se ferme 12 s plus tard",
    "gn_exfil_t360": "Chrono : 6:00 restantes",
    "gn_exfil_t240": "Chrono : 4:00 restantes",
    "gn_exfil_t120": "Chrono : 2:00 restantes",
    "gn_exfil_t60": "Chrono : 1:00 restante",
    "gn_exfil_t30": "Chrono : 0:30 restantes",
    "gn_exfil_fail": "Chrono écoulé : le noyau et les puits deviennent mortels",
    "gn_phase_10_done": "Le premier joueur sort sur le glacier (le chrono s'arrête)",
    "gn_phase_11_start": f"Le LAAT arrive : départ dans {EXTRACT} s",
    "gn_phase_11_done": "Le LAAT décolle : fin de l'event",
}

lines = ["# Opération Givre Noir — script de narration", "",
         "La map n'affiche **aucun texte** et n'a besoin d'**aucun addon** : tout s'enchaîne selon les actions",
         "des joueurs. Ce script donne, phase par phase, ce qui se passe en jeu et une réplique proposée pour",
         "SENTINELLE. Les noms `gn_...` sont ceux des relais de la map (pour Hammer).", "",
         "La map ne téléporte personne : **les gérants posent les spawns** avec leurs outils habituels,",
         "phase par phase, aux coordonnées du tableau en fin de document.", "",
         f"Durées : hack 3 × {HACK_STAGE} s · exfiltration {EXFIL // 60} min · extraction {EXTRACT} s.", ""]
current = 0
for name, text in texts.SENTINEL.items():
    if name.startswith("gn_phase_") and name.endswith("_start"):
        n = int(name.split("_")[2])
        if n != current:
            current = n
            title, obj = texts.PHASES[n]
            lines += ["", f"## Phase {n} — {title}", f"**Objectif :** {obj}", ""]
    lines.append(f"- **{WHEN.get(name, name)}** (`{name}`)  ")
    lines.append(f"  SENTINELLE : *« {text} »*")
lines += ["", "---", "Fin : " + texts.END_TEXT.replace("\n", " ")]

# ---- coordonnées des spawns à poser par les gérants ----
import json  # noqa: E402

side = json.load(open(os.path.join(ROOT, "maps_src", "givre_noir.json"), encoding="utf-8"))


def center(pts):
    return tuple(round(sum(p[i] for p in pts) / len(pts)) for i in range(3))


def extent(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return f"{round(max(xs) - min(xs)) + 32} × {round(max(ys) - min(ys)) + 32}"


def fmt(c):
    return f"{c[0]} {c[1]} {c[2]}"


lines += ["", "## Spawns à poser par les gérants", "",
          "Coordonnées Hammer (= `getpos` en jeu, pieds du joueur). Chaque groupe fait 16 points libres et vérifiés",
          "(aucun dans un mur ni une porte ; aucun spawn défenseur ne voit un spawn attaquant). Les repères existent",
          "aussi dans la map (`info_target` du même nom) pour les retrouver dans Hammer.", "",
          "| Phase | Attaquants (République) : centre | taille | Défenseurs (droïdes) : centre | taille |",
          "|---|---|---|---|---|"]
start = side["player_starts"]
d1 = side["def_spawns"]["1"]
lines.append(f"| 1 — {texts.PHASES[1][0]} | {fmt(center(start))} (plateforme LAAT, 80 `info_player_start`) | "
             f"{extent(start)} | {fmt(center(d1))} (`gn_def_spawn_1`) | {extent(d1)} |")
for n in range(2, len(texts.PHASES) + 1):
    a = side["atk_respawns"][str(n)]
    zones = ["3a", "3b"] if n == 3 else [str(n)]
    ds = [(z, side["def_spawns"][z]) for z in zones]
    dtxt = " / ".join(f"{fmt(center(p))} (`gn_def_spawn_{z}`)" for z, p in ds)
    dext = " / ".join(extent(p) for _, p in ds)
    note = " ⚠ voir note" if n == 10 else ""
    lines.append(f"| {n} — {texts.PHASES[n][0]} | {fmt(center(a))} (`gn_atk_respawn_{n}`){note} | {extent(a)} | {dtxt} | {dext} |")
lines += ["", "⚠ **Phase 10 (exfiltration)** : les sas se referment et se verrouillent derrière les joueurs. Un attaquant qui",
          "réapparaît pendant la course reste bloqué dans le noyau. Conseil : pas de respawn attaquant pendant la phase 10",
          "(mort = hors course), ou spawn directement au point de la phase 11 sur le glacier."]
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
out = os.path.join(ROOT, "docs", "narration.md")
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("narration :", out)
