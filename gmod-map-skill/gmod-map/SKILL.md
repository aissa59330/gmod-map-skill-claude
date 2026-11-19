---
name: gmod-map
description: Créer de A à Z une map Garry's Mod (Source) d'event multijoueur, générée en Python (srctools), compilée en ligne de commande (vbsp/vvis/vrad), vérifiée en jeu et optimisée pour 100 joueurs, avec logique de phases 100 % map (sans Lua), effets, sons maison et publication Workshop. À utiliser dès que l'utilisateur veut faire, modifier, optimiser ou publier une map Gmod / Source.
---

# Map Garry's Mod d'event — méthode complète

Méthode éprouvée sur « Opération Givre Noir » (map Clone Wars 11 phases, 100 joueurs, ~1 h).
Code de référence complet et fonctionnel : `reference/` (générateur `reference/generator/`, outils `reference/tools/`,
addons de test `reference/addons/`, ancien CLAUDE.md du projet `reference/CLAUDE_givre_noir.md`).
**Ne pas recopier ce design** : réutiliser la MÉTHODE et les outils, le tracé doit être celui que l'utilisateur demande.

## 0. Avant de commencer (demander à l'utilisateur)
- Thème, nombre de joueurs, durée, nombre de phases / objectifs, camps (attaquants / défenseurs).
- Contraintes du serveur : **addons Lua refusés ?** (presque toujours : tout faire en entités de map),
  **nombre max de packs Workshop requis** (Givre Noir : 4 max), **taille max** (souvent 1 Go).
- Ce qui est affiché à l'écran (souvent : rien, la narration est faite en direct ; exceptions demandées explicitement).
- Packs Workshop de contenu autorisés (textures / props) ; le style visuel attendu (captures).
- Règles absolues : ne rien modifier dans le dossier Gmod hors `garrysmod\maps\` (+ addon de test temporaire),
  jamais le serveur de l'event, pas de sv_cheats en ligne, **ne jamais fermer le Gmod de l'utilisateur**,
  demander avant d'installer quoi que ce soit, s'arrêter et expliquer après 3 échecs identiques.
- Créer le projet dans un **dossier durable** (pas un dossier temporaire de session) et l'initialiser en git ;
  commit avant chaque grosse passe.

## 1. Architecture du projet
```
projet/
  generator/   build_map.py (VMF via srctools), zones.py (salles = "spaces" en boîtes), entities.py (logique),
               props.py / dressing.py / kit.py (habillage), fx.py (effets), minigames.py, optim.py, nodes.py, areaportals.py
  tools/       compile.ps1, make_sounds.py, make_signs.py, embed_content.py, extract_workshop.py, diag.py, bench.ps1, package_map.ps1
  addons/      addon de test (tournée, bench) — JAMAIS publié ; addon de la map (bsp + addon.json, zéro Lua)
  compile_game/ profil de compilation (gameinfo + cfg/mount.cfg qui monte les packs extraits)
  maps_src/ logs/ docs/ shots/
```
Principe : **on ne touche jamais le .vmf à la main**, tout vient du générateur (régénérable, versionnable).
Si l'utilisateur veut passer sur Hammer, lui expliquer que la régénération écraserait ses retouches.

## 2. Construction (generator)
- Chaque salle = une boîte d'air ; le générateur fait le CSG (murs de 16 min., tout sur la grille de 16, ±16384 max).
- Échelle : joueur 32×32×72 ; portes ≥ 192×160 ; couloirs 192–320 ; grandes salles 2048–4096 ; marches 8×16.
- Combat de masse : 3 voies par zone, ≥ 3 entrées par objectif, couverts, verticalité ; alterner couloir étroit → grande salle.
- Extérieurs (sky=True) assez grands pour le combat aérien ; plusieurs secteurs reliés par un col si on manque de place
  (la limite ±16384 bloque un axe : s'étendre sur l'autre).
- Décor en `func_detail`, nodraw sur les faces cachées, lightmapscale grossier sur les grandes surfaces extérieures.
- Placement des props : bbox dans la salle, posé sur un sol / bloc / autre prop, jamais au-dessus d'une fosse (le poser au
  fond ou le retirer), jamais dans un mur. Faire un **contrôle automatique** (flotte / dans un mur / dans un bloc) avant livraison.
- Textures : orientation des panneaux = `-face.normal()` de srctools (sinon texte en miroir) ; textures maison en VTF
  (Pillow + srctools, DXT1), embarquées par bspzip.

## 3. Logique 100 % map (aucun Lua)
- Une phase = `logic_relay` `<pfx>_phase_<n>_start` / `_done` (once). Démarrage auto par `logic_auto`.
- Entités utiles : func_door (areaportal DANS l'épaisseur de la porte), func_button (1024 use, 32 toggle → OnIn/OnOut,
  2048 verrouillé), math_counter (OnHitMax / OnChangedFromMax), logic_branch(+listener), logic_case (16 cas max),
  logic_timer (inputs RefireTime, LowerRandomBound…), game_text (seul affichage possible), ambient_generic
  (spawnflags 1 partout, 16 démarre en silence+boucle, 32 non bouclé ; 48 = silence+non bouclé).
- Compte à rebours affiché : relais avec AddOutput « message … » + Display chaque seconde (pas de virgule dans le texte).
- Pièges vécus :
  - `momentary_rot_button` (molettes à tenir) : peu fiable (angle qui bascule à 180°, OnFullyOpen qui ne part pas).
    Préférer leviers/boutons simples + délai ; si molette : course < 180 et déclenchement de secours par la sortie Position.
  - Lock/Unlock sur un bouton en mouvement le casse : garder l'état dans un logic_branch.
  - Un commentaire Python qui avale la fin d'une ligne de kwargs (StartDisabled…) = bug silencieux : relire.
  - Tester chaque mini-jeu avec un vrai maintien de [E] (hook StartCommand IN_USE), pas avec Fire/Use.
- Anti-grief : sur toutes les entités `gmod_allowphysgun 0` + `gmod_allowtools "aucun"` (Sandbox et dérivés).
- Lancer une phase pour tester : `lua_run ents.FindByName("<pfx>_phase_N_done")[1]:Fire("Trigger")` (console serveur).

## 4. Effets et ambiance (sans tuer les FPS)
- Briques réutilisables (voir `reference/generator/fx.py`) : GROS BOUM (env_explosion ×3 décalées sans dégâts,
  light_dynamic flash 0,2 s éteinte au spawn, env_shake, env_physexplosion, env_shooter gibs, env_fire damagescale 0,
  env_smokestack), arcs (point_tesla), vapeur (env_steam), alarme locale (func_rotating + sprite + klaxon),
  porte lourde (OnOpen → son + vapeur + secousse), vaisseaux dans le ciel 3D (func_movelinear + prop_dynamic, échelle 1/16).
- Rythme de chaque objectif : ça monte (tension) → ça pète → ça reste (fumée, feu).
- Final spectaculaire possible : ciel/brouillard qui changent (AddOutput topcolor sur env_skypaint nommé, SetColor sur le fog),
  env_beam depuis le ciel (bombardement), env_fade (flash blanc, assombrissement rouge modulé), explosions en vagues
  de plus en plus grosses (logic_case + logic_timer dont on réduit les bornes).
- Jamais de light_dynamic permanentes (FPS) ; lumières clignotantes = `light` nommée avec `pattern` (précalculé).
  Max 4 styles de lumière par face : peu de lumières nommées qui se recouvrent.
- Sons : uniquement ceux des VPK de Gmod/HL2 (vérifier qu'ils existent en listant les VPK) ou maison (TTS + effet
  droïde, mp3 fourni par l'utilisateur) embarqués dans le .bsp. Voix et alarmes « partout » = spawnflags 1.
- Toute nouvelle entité doit être DANS une salle (sinon leak) : vérifier les origines par script avant de compiler.

## 4 bis. Prévisualisation Blender (AVANT de compiler, à chaque grosse modification du tracé)
- Outils : **Blender** (4.x/5.x) + addon **Plumber** (import VMF/MDL ; demander à l'utilisateur avant d'installer).
- Commande : `blender -b -P tools/preview_blender.py -- maps_src/<map>.vmf shots/iter_N/blender/`
  (référence : `reference/tools/preview_blender.py`). Opérateur d'import : `bpy.ops.import_scene.plumber_vmf`
  (le lister dans `dir(bpy.ops.import_scene)` ; activer l'extension `bl_ext.user_default.plumber` si besoin).
  Plumber refuse le bloc `editor` au niveau du world : en importer une copie nettoyée. Échelle Plumber : 0,01.
- Rendus : 1 vue de dessus orthographique de toute la map + 1 vue par zone. **Regarder les images** :
  proportions, connexions, salles qui se chevauchent, 3 voies par zone, ≥ 3 entrées par objectif.
- Complément rapide sans Blender : plan SVG de dessus (`reference/tools/plan_svg.py`, lit le .json exporté par le générateur).
- Blender sert aussi aux **LOD des props** : import MDL (Plumber) → Decimate → export SMD → studiomdl
  (`reference/tools/make_lod_props.py`, puis `fix_lod_qc.py` pour les $cdmaterials).
- Ensuite seulement : compilation, puis tournée en jeu (les rendus Blender ne remplacent pas la vérification en jeu).

## 5. Compilation (tools/compile.ps1)
- vbsp → vvis (COMPLET, jamais -fast en livraison : sinon on voit tout à travers les murs) → vrad (-final -ldr
  -StaticPropLighting -StaticPropPolys) → bspzip (`-game` en premier) → copie dans garrysmod\maps.
- Packs Workshop : extraits (tools/extract_workshop.py, gère .gma et legacy .bin LZMA) dans un dossier DURABLE à
  chemin court (le Temp de Windows est vidé ; limite de 260 caractères de Source/bspzip/vrad).
- La liste de pack est reconstruite à chaque compilation et VÉRIFIÉE (fichiers maison présents dans le .bsp).
- Un leak = corriger avant tout (lire le .lin / la ligne « Entity … leaked »).

## 6. Optimisation pour 100 joueurs
- Areaportals sur chaque porte, salles fermées, VVIS complet ; brouillard + farz adaptés (extérieur : vue longue
  pour le combat en plaine, ex. fogend 10000 / farz 11000 ; mesurer).
- Props : LOD (Blender + Plumber → Decimate → studiomdl, $cdmaterials du modèle d'origine), fade (plus long dehors),
  collisions bbox ou aucune, prop_static partout où possible ; peu d'entités networkées (edicts).
- Diagnostic (`tools/diag.py`) + bench en jeu (`tools/bench.ps1`, bots qui se battent ; serveur dédié avec
  `sv_hibernate_think 1`). Mesures FPS avec l'utilisateur : `net_graph 1`, `fps_max 0`, points `setpos/setang`.
- Sortir en noclip hors de la map montre tout (normal) : tester la visibilité depuis l'intérieur.

## 7. Vérification en jeu (tournée)
- Addon de test temporaire (téléportation, captures, tests logiques et mini-jeux) copié puis retiré ; Gmod lancé en
  solo fenêtré par nos outils ; ne fermer que les Gmod lancés par nous (ou orphelins sans fenêtre).
- Toujours dire clairement ce qui est vérifié et ce qui ne l'est pas.

## 8. Packs requis et publication
- Mesurer quels packs sont vraiment utilisés (faces + props + matériaux des modèles LOD).
- Moins de packs requis : garder ceux qui portent le gros (textures des murs, props importants), remplacer le reste.
  ⚠ Embarquer dans le .bsp des modèles/textures d'autres auteurs = réupload : risque de retrait Workshop ; prévenir
  l'utilisateur AVANT et préférer le remplacement par du contenu des packs requis / de base.
- Addon de la map : `maps/<map>.bsp` + `addon.json` (type map, tags), zéro Lua (le valider), < 500 Mo.
- Miniature : JPG 512×512 (capture en jeu recadrée + titre) ; description BBCode avec crédits des auteurs des packs.
- gmpublisher : 1re fois « Publish », ensuite **Update** sur l'addon existant (sinon nouvel ID).
  Éléments requis à cocher sur la page Steam. Les serveurs ajoutent l'ID à leur collection.
- Open source possible : licence CC BY 4.0 (attribution), sources (.vmf + générateur) sur GitHub, sans le contenu tiers.

## 9. Façon de travailler avec l'utilisateur
- Il teste en jeu et envoie des captures (+ `getpos`) : corriger exactement ce qui est montré, recompiler, dire quoi tester.
- Réponses courtes, en français simple ; commandes prêtes à copier ; jamais prétendre avoir vérifié en jeu ce qui ne l'a pas été.
- Respecter les limites de quota/budget données par l'utilisateur (vérifier l'usage régulièrement).
- Tenir un journal d'itérations (`logs/iterations.md`) et un document de narration pour les organisateurs.
