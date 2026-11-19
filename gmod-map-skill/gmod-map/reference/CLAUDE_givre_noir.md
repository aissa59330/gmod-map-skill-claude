# CLAUDE.md — Map Gmod « Opération Givre Noir »

## Objectif
Générer, compiler et vérifier visuellement une map Garry's Mod originale (`givre_noir`) pour un event Clone Wars du régiment 408th Corps Cosmique.
Tu travailles en boucle autonome : **générer → compiler → regarder → corriger**, jusqu'à ce que chaque zone soit correcte.

Le design est **original**. Ne reproduis jamais le plan ou les assets d'un autre jeu (GTA, etc.) : on s'inspire uniquement du rythme d'une mission en plusieurs phases.

## Environnement
- OS : Windows 10/11, Claude Code lancé en local.
- Garry's Mod : `<GMOD>` = dossier d'installation (ex. `C:\Program Files (x86)\Steam\steamapps\common\GarrysMod`). **Vérifie le chemin au démarrage.**
- Outils de compilation : `<GMOD>\bin\vbsp.exe`, `vvis.exe`, `vrad.exe` (vérifier s'ils sont dans `bin\` ou `bin\win64\`).
- Python 3.10+ avec `srctools`.
- Blender 4.x avec l'addon **Plumber** (import VMF).
- Si quelque chose manque : **demande-moi avant d'installer quoi que ce soit.**

## Structure du projet
```
givre_noir/
├── CLAUDE.md
├── generator/
│   ├── build_map.py        # génère maps_src/givre_noir.vmf avec srctools
│   ├── zones.py            # définition des zones (dimensions, positions, connexions)
│   └── entities.py         # spawns, portes, triggers, logique
├── maps_src/givre_noir.vmf
├── tools/
│   ├── compile.ps1         # vbsp → vvis → vrad → copie du .bsp
│   ├── preview_blender.py  # rendus Blender en ligne de commande
│   └── run_tour.ps1        # lance Gmod, attend les captures, ferme le jeu
├── addons/
│   └── givre_noir_devtour/ # addon de DEV uniquement (tournée caméra) — jamais sur le serveur
├── shots/                  # captures Blender + Gmod copiées ici, une sous-dossier par itération
└── logs/                   # logs de compilation
```

## Échelle Source (unités Hammer)
- Joueur : 32 × 32 × 72, vue à 64.
- **Map de combat pour 70 joueurs** : tout est dimensionné pour ça.
- Portes et passages : **192 × 160 minimum**, 256 × 192 pour les axes principaux.
- Couloirs : **192 à 320 de large**, 160 à 256 de haut. Rien en dessous de 128 de large, sauf passages de flanc courts (≤ 256 de long).
- Grandes salles (hangar, usine, centre de données, noyau) : **2048 à 4096 de côté**, 512 à 1024 de haut.
- Marches : 8 de haut, 16 de profondeur. Pente max franchissable : 45°.
- Murs : 16 d'épaisseur minimum. Grille : tout aligné sur 16.
- Map entièrement scellée (aucun leak), carrés de construction à l'intérieur de ±16384.

## Les zones (ordre de progression) — version 11 phases (~70 min, validée le 2026-11-15)
L'event doit durer environ 1 h : la base est un grand complexe sur deux ailes et plusieurs étages.
Numéro de zone = numéro de phase (`gn_phase_<n>_start/done`, `gn_def_spawn_<n>`, `gn_atk_respawn_<n>`).

| # | Zone | Rôle gameplay | Notes de construction |
|---|------|---------------|------------------------|
| 1 | Canyon d'insertion | Largage LAAT, approche à couvert | Extérieur, `env_fog_controller` dense, rochers en brushes, skybox `toolsskybox` |
| 2 | Hangar extérieur | Détruire 3 tourelles AA | 3 `func_breakable` `aa_1..3`, `logic_counter` → ouverture des 2 routes |
| 3a / 3b | Conduits / porte principale | Deux routes de 35 joueurs | Réseau de tunnels 192 de large (128 de haut) / `func_door` massive + hall à tranchée |
| 4 | Usine de droïdes | Saboter 3 générateurs | Tapis roulants, presses (`func_door` + `trigger_hurt`), lumière coupée par SENTINELLE |
| 5 | Garnison (3 étages) | Prendre l'armurerie : 1 console par étage | Étages à 0 / +384 / +768, 3 rampes par étage |
| 6 | Centre de données | Hack en 3 étapes de 100 s sur 3 terminaux | Salle remplie de baies serveurs, salle du hack centrale, portes magnétiques (`logic_case`) |
| 7 | Bloc de détention | Ouvrir 3 blocs de cellules | 23 cellules sur 2 niveaux, mirador central, coursive haute |
| 8 | Tour de communication | 3 charges sur l'antenne (une par niveau) | Salle verticale +768 → +2304, coursives et 4 ponts par niveau |
| 9 | Noyau du canon | Surcharger le réacteur, IA SENTINELLE | Anneau de passerelles, ponts mobiles (`func_movelinear`), balcons |
| 10 | Exfiltration | Chrono 8 min | 3 puits en spirale (+2304 → +6912), sas qui se ferment derrière les joueurs |
| 11 | Extraction LAAT | Fin de l'event | Plateforme au sommet du glacier, `trigger_multiple` de fin |

Connexions : 1 → 2 → (3a ou 3b) → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11. Les joueurs ne repassent jamais par le même chemin.
Les chronos (hack, exfiltration, extraction) sont réglés en tête de `generator/entities.py` ; les textes dans `generator/texts.py`.

## Sensations recherchées (inspiration de rythme uniquement)
La map s'inspire de l'**ambiance** des grosses missions de casse en plusieurs phases : tension qui monte, IA ennemie omniprésente, final sous chrono. **Aucun plan, tracé ou asset d'un autre jeu n'est repris** : tout le tracé ci-dessous est original.

### Courbe de tension
1. Zone 1-2 : calme, discrétion, visibilité réduite → les joueurs se mettent en place.
2. Zone 3-4 : premiers vrais combats, l'escouade est séparée en deux routes puis se regroupe.
3. Zone 5 : pression maximale tenue dans la durée (défense du hack).
4. Zone 6 : climax, SENTINELLE au plus fort.
5. Zone 7-8 : course contre la montre, tout s'effondre derrière les joueurs.

### Types de couloirs (à mélanger, jamais deux fois le même d'affilée)
- **Couloir de service** : 192-256 de large, 160 de haut, virages à 90° tous les 512-768 unités → combats à courte distance.
- **Galerie de glace** : 384-512 de large, plafond irrégulier 256-384 (brushes en escalier), éclairage bleu faible.
- **Passerelle** : 192-256 de large au-dessus d'un vide de 512+, garde-corps 48 de haut, `trigger_hurt` au fond. Toujours au moins 2 passerelles parallèles.
- **Sas blindé** : chambre de 768 × 768 minimum entre deux `func_door` larges (256) ; la seconde ne s'ouvre qu'une fois la première fermée → regroupe l'armée.
- **Tranchée technique** : couloir de 320 de large avec une fosse centrale de 64 de profondeur (couverts bas).
- Règle de rythme : toujours **couloir étroit → grande salle → couloir étroit** pour créer des respirations.

### Moments scriptés de SENTINELLE
- Usine : coupe la lumière d'une moitié de salle (`light` nommées + `logic_relay`) pendant 30 s.
- Centre de données : verrouille une porte au hasard toutes les 45 s, force une partie de l'escouade à faire le tour.
- Noyau : rétracte un pont mobile, sépare l'escouade sur deux passerelles le temps d'une vague.
- Exfiltration : ferme les sas derrière les joueurs, annonce le temps restant à 4:00, 2:00, 1:00, 0:30.
- Chaque moment déclenche un message texte de SENTINELLE via l'addon Lua (ton froid, menaçant, original).

## Combat à 70 joueurs
### Flux et lignes de combat
- **Jamais un seul chemin** : chaque zone de combat a **3 voies** (une principale large + deux flancs), qui se rejoignent aux objectifs. Un goulot unique = 70 joueurs bloqués dans une porte.
- Les deux routes de la zone 3 (conduits / porte principale) doivent chacune pouvoir accueillir **35 joueurs** : les « conduits » deviennent un réseau de tunnels de maintenance de 192 de large, pas des gaines étroites.
- Objectifs à défendre (générateurs, hack, réacteur) : **au moins 3 entrées** chacun, et des couverts répartis (caisses, murets en brushes de 48-64 de haut, piliers).
- Lignes de vue : alterner zones à longue portée (hangar, galerie) et combats rapprochés (couloirs de service). Pas de ligne droite dégagée de plus de 3072 unités.
- Verticalité dans les grandes salles : niveaux à +256 / +512 avec escaliers et rampes larges (256), pour étaler les joueurs.

### Camps et spawns
- **Attaquants (République)** : **80 `info_player_start`** dans la zone 1, répartis sur une grande plateforme d'atterrissage (pas plus de 8 par rangée, espacés de 64).
- **Défenseurs (Séparatistes)** : zones de spawn `info_target` nommées `gn_def_spawn_<zone>` dans chaque zone (au moins 16 points par zone), pour que l'addon y place les joueurs droïdes ou des PNJ selon l'event.
- **Points de réapparition progressifs** pour les attaquants : `info_target` nommées `gn_atk_respawn_<n>`, activés par l'addon quand une phase est validée (évite de refaire tout le trajet à pied à 70).
- Aucun spawn visible depuis un spawn ennemi (pas de spawn-kill).

### Performances (critique à 70 joueurs)
- Tout le décor non structurel en **`func_detail`**.
- **`areaportal`** sur chaque porte et chaque sas ; **`hint`/`skip`** pour bien découper les visleafs entre les zones.
- Les grandes salles sont fermées par des murs pleins : aucune zone ne doit voir plus de 2 zones voisines.
- Rester très loin des limites Source : édicts < 4000 au total, brushes entités raisonnables, pas de `func_physbox` en masse.
- Compilation finale **sans `-fast`** pour vvis et vrad.

## Entités et nommage
- Préfixes : `gn_` pour tout ce qui est nommé (ex. `gn_hack_timer`, `gn_door_core`).
- Spawns : voir « Camps et spawns » (vérifier qu'aucun n'est dans un mur ni dans le sol).
- Chaque phase se déclenche via un `logic_relay` nommé `gn_phase_<n>_start` / `gn_phase_<n>_done`.
- **Aucun addon sur le serveur** (refusé par les gérants) et **aucun texte affiché par la map** (la narration est faite en direct) :
  toute la mécanique de l'event est dans la map. Seule exception au « rien d'affiché » (demandée le 2026-11-16) : le compte à rebours du piratage (`game_text`) + noir/alarme rouge/sirène/voix de SENTINELLE (sons maison `tools/make_sounds.py`, panneaux `tools/make_signs.py`, embarqués dans le .bsp par bspzip). La phase 1 démarre au chargement (`logic_auto`), les suivantes s'enchaînent seules.
  **Aucun téléporteur** : les gérants posent les spawns eux-mêmes, phase par phase, sur les repères `gn_atk_respawn_<n>`
  (attaquants) et `gn_def_spawn_<zone>` (défenseurs) ; coordonnées dans `docs/narration.md`.
  Échec de l'exfiltration = `trigger_hurt` `gn_exfil_doom`.
  Script de narration (répliques de SENTINELLE + déclencheurs) : `docs/narration.md`, généré par `tools/narration.py` depuis `generator/texts.py`.
- Éclairage de base : `light_environment` + `light` dans chaque salle (sinon les captures sont noires).
- Textures et props : voir `docs/direction_artistique.md` (palette Imperial Materials + packs Workshop en éléments requis, liste dans `docs/publication.md`). Plus aucune texture `dev/` ni bande noir/jaune.

## Boucle de travail (obligatoire à chaque itération)
1. **Générer** : `python generator/build_map.py` → `maps_src/givre_noir.vmf`.
2. **Preview Blender** : `blender -b -P tools/preview_blender.py -- maps_src/givre_noir.vmf shots/iter_<n>/blender/`
   - Trouve d'abord le nom exact de l'opérateur d'import Plumber (le lister dans `bpy.ops`).
   - Rendus : 1 vue de dessus orthographique de toute la map + 1 vue par zone.
   - **Regarde les images** : proportions, connexions, salles qui se chevauchent.
3. **Compiler** : `tools/compile.ps1`
   - `vbsp -game "<GMOD>\garrysmod" maps_src\givre_noir.vmf`
   - `vvis -game "<GMOD>\garrysmod" maps_src\givre_noir` (`-fast` pendant les itérations)
   - `vrad -game "<GMOD>\garrysmod" maps_src\givre_noir` (`-fast` pendant les itérations)
   - Copier le `.bsp` dans `<GMOD>\garrysmod\maps\`. Logs dans `logs/`.
   - **Un leak = on corrige avant de continuer** (lire le `.lin` / le log).
4. **Tournée caméra Gmod** : `tools/run_tour.ps1`
   - Copie temporaire de `addons/givre_noir_devtour` dans `<GMOD>\garrysmod\addons\`.
   - Lance le jeu en solo, fenêtré : `-windowed -w 1280 -h 720 +map givre_noir` (vérifier si l'exécutable est `gmod.exe` ou `hl2.exe`).
   - L'addon : côté serveur, téléporte le joueur à chaque point (`SetPos` / `SetEyeAngles`) ; côté client, capture via `render.Capture` dans un hook `PostRender`, écrit `data/givre_noir_shots/<zone>.png`. Attendre ~2 s entre chaque point.
   - Le script attend que toutes les images existent (timeout 3 min), ferme le jeu, copie les images dans `shots/iter_<n>/gmod/`, puis **retire l'addon de dev** du dossier addons.
5. **Analyser** les captures Gmod : zones noires (lumière), joueur coincé, salles vides ou trop petites, portes fermées par erreur.
6. **Corriger** le générateur (jamais le `.vmf` à la main) et recommencer.
7. Écris un résumé court de chaque itération dans `logs/iterations.md` (ce qui a changé, ce qui reste).

## Règles
- Ne modifie rien dans `<GMOD>` en dehors de `garrysmod\maps\` et de l'addon de dev temporaire.
- Ne touche jamais au serveur de l'event ni à ses fichiers.
- Pas de `sv_cheats` sur un serveur en ligne : la tournée se fait uniquement en solo local.
- Pas de contenu tiré d'autres jeux. Les props Clone Wars viendront du Workshop, ajoutés à la main plus tard.
- Si une étape échoue 3 fois de suite de la même façon, arrête-toi et explique-moi le problème.

## Définition de « terminé »
- Compilation sans leak ni erreur bloquante.
- Les 8 zones sont visibles, éclairées et accessibles sur les captures Gmod.
- Le parcours complet est faisable à pied (aucun saut impossible, aucune porte bloquée).
- Chaque zone de combat a 3 voies et chaque objectif au moins 3 entrées (vérifiable sur la vue de dessus Blender).
- 80 spawns attaquants + spawns défenseurs + points de réapparition présents et valides.
- Test perf en jeu : `r_drawportals`/`mat_wireframe` sur les captures de la tournée pour vérifier que les areaportals coupent bien la visibilité ; noter le FPS (`net_graph 1`) à chaque point de la tournée dans `logs/iterations.md`.
- Les relais `gn_phase_*` existent et toute la chaîne des 11 phases fonctionne sans addon (vérifiée par le test logique de la tournée) ; `docs/narration.md` est à jour.
