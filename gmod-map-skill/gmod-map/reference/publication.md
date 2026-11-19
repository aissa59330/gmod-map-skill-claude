# Publication Workshop — Opération Givre Noir

## Contenu de l'addon de la map
`addons/givre_noir_map/` :
- `addon.json` (type `map`)
- `maps/givre_noir.bsp` — copié par `tools/package_map.ps1` depuis `maps_src/` (le script vérifie la taille < 500 Mo)

**Aucun Lua, aucune texture ni aucun modèle d'autres créateurs n'est inclus dans l'addon.** Les contenus
tiers sont des **éléments requis** : le Workshop les fait télécharger automatiquement aux joueurs et au serveur.

## Éléments requis à cocher sur la page Workshop (4 maximum)

Le peu de contenu pris à 4 autres packs (Venator du ciel, caisses, réservoirs, balises, textures des droïdes) est **embarqué dans le .bsp** par `tools/embed_content.py` (≈ 20 Mo, cartes de relief retirées) : ces packs ne sont plus requis.
| Addon | ID Workshop | Auteur | Utilisé pour | Taille |
|---|---|---|---|---|
| Star Wars - Imperial Materials | 1206775008 | Lord Trilobite | Textures de la base (murs, sols, grilles, portes, consoles, lumières, façade) | ~122 Mo |
| Sci-fi Props Megapack | 284266415 | Lt_C | Props (couchettes, casiers, caisses, ordinateurs, générateurs, tuyaux, bureau) | ~297 Mo |
| Star Wars - Misc Prop Pack | 1987994709 | Lord Trilobite | Consoles, panneaux muraux, cuves de bacta, chaises | ~66 Mo |
| SW Modelpack Death Star | 1518614446 | KingPommes | Panneaux muraux, écrans, cellules d'énergie, lampes | ~125 Mo |

Le reste du contenu (neige, roche, conteneurs, transformateur, fûts) vient de HL2 et est déjà livré avec Garry's Mod.

À ajouter aussi à la **collection Workshop du serveur** (sinon textures roses/noires et props « ERROR »).

## Crédits à mettre dans la description (demandés par les auteurs)
- Textures impériales et vaisseaux du ciel : **Lord Trilobite** — « Star Wars - Imperial Materials » et « Star Wars - Skybox Space Props ».
- Props sci-fi : **Lt_C** — « Sci-fi Props Megapack » (avec le soutien de PalmliX).
- Props de base : **Lord Trilobite** — « Star Wars - Misc Prop Pack », « Star Wars Rogue One Prop Pack ».
- Props de base : **KingPommes** — « SW Modelpack Miscellaneous », « SW Modelpack Death Star ».
- Map : régiment 408th Corps Cosmique.

## Vérification avant publication
1. `python generator/build_map.py` puis `python tools/validate.py` → `VALIDATION : OK`
2. `tools/compile.ps1 -Final` → pas de fuite
3. `tools/run_tour.ps1 -Iter <nom>` → logique 18/18, portes 57/57, marche 0 blocage
4. `tools/package_map.ps1` → copie du BSP dans l'addon + contrôle de taille
5. Publier `addons/givre_noir_map/` (gmpublisher ou gmad) et cocher les 4 éléments requis.

⚠ Ne jamais publier `addons/givre_noir_devtour` : c'est l'outil de test local (il téléporte et pilote le joueur).
