# Méthode : bench de performance d'une map Gmod sur serveur dédié local

À donner à Claude Code. But : mesurer ce que la **map** coûte au **serveur** avec beaucoup de PNJ
(ex. « 600 PNJ avec 1 joueur, ça freeze »), comparer deux versions (avant / après) et décider.
Fichiers d'exemple dans ce dossier : `bench_server.ps1` (pilote) et `givre_noir_srvbench/` (addon Lua de mesure).
Ils viennent de la map « givre_noir » : remplacer le nom de map, les chemins et les positions des PNJ.

---

## Règles (à respecter absolument)
- **Uniquement en local** : serveur dédié sur le PC (`sv_lan 1`), jamais sur le serveur de l'event ni ses fichiers.
- L'addon de bench est **copié dans le serveur de test seulement**, jamais publié, jamais dans le Gmod du joueur.
- Ne jamais fermer le Gmod du joueur ; ne tuer que le `srcds` lancé par le script.
- Demander avant d'installer (SteamCMD + serveur dédié Gmod, téléchargement anonyme ~ quelques Go).

## 1. Installer le serveur dédié (une seule fois)
- Dossier à **chemin court** (ex. `C:\Users\<nom>\gn_srcds`) : Source ne lit pas les chemins de plus de 260 caractères.
- SteamCMD : `https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip`, puis
  `steamcmd +force_install_dir <dossier>\server +login anonymous +app_update 4020 validate +quit`
  (4020 = Garry's Mod Dedicated Server ; relancer jusqu'à 3 fois, SteamCMD quitte parfois après sa mise à jour).

## 2. Préparer le serveur pour la map
- `garrysmod\cfg\mount.cfg` : monter les **packs Workshop extraits** utilisés par la map (sinon modèles ERROR,
  et le coût mesuré est faux). Format : `"mountcfg" { "<nom>" "<chemin du dossier extrait>" }`.
- Copier le `.bsp` dans `garrysmod\maps\`.
- Copier l'addon de bench dans `garrysmod\addons\` ; vider son dossier `garrysmod\data\<addon>\`.

## 3. L'addon de mesure (Lua serveur, `lua/autorun/server/`)
- Attend 25 s après le chargement, crée **N bots** (`player.CreateNextBot`) : N = 1 pour « 1 joueur », 100 pour un event plein.
- Ajoute des PNJ **par paliers** (ex. 0 / 200 / 400 / 600) à des **positions valides** de la map
  (liste `Vector(...)` prise sur des sols praticables : points de navigation, spawns ; sinon « stuck in wall »).
  Même classe de PNJ d'une version à l'autre (`npc_combine_s` par défaut ; utiliser la classe des staffs si possible,
  ex. VJ Base, pour mesurer le vrai coût).
- Laisse 8 s aux PNJ pour s'installer, puis mesure **60 s** par palier :
  - hook `Tick` : intervalle réel entre deux ticks (`SysTime()`) → moyenne, p99, **max** ;
  - ticks attendus vs ticks réels (`engine.TickCount()`) → **ticks ratés** ;
  - nombre d'entités / edicts.
- Écrit dans `data/<addon>/` : un rapport par palier, `fenetres.txt` (`DEBUT <palier> <unix>` / `FIN <palier> <unix>`),
  puis `done.txt` à la fin.
- ⚠ `engine.ServerFrameTime()` renvoie 0 sur serveur dédié : le temps CPU se mesure **de l'extérieur** (étape 4).

## 4. Lancer et mesurer (script PowerShell)
- Commande :
  `srcds_win64.exe -console -condebug -game garrysmod -tickrate 66 -norestart +sv_lan 1 +sv_hibernate_think 1 +maxplayers 128 +map <map>`
  - `+sv_hibernate_think 1` **obligatoire** : sinon le serveur sans vrai joueur « hiberne » et rien ne tourne.
  - Lancer la fenêtre **réduite** (`-WindowStyle Minimized`) : **un clic dans la console noire met le serveur en pause**
    (mode sélection de Windows) et fausse tout.
- Toutes les 5 s, noter le **temps CPU cumulé** du processus (`$p.TotalProcessorTime.TotalMilliseconds`) avec l'heure unix
  dans `cpu.txt`. S'arrêter quand `done.txt` existe (ou au délai max), tuer le serveur, récupérer `data/` et `console.log`.
- Calcul par palier : `ms CPU par tick = (CPU à FIN − CPU à DEBUT) / (durée en s × 66)` (interpoler dans `cpu.txt`).

## 5. Lire les résultats
| Mesure | Bon | Problème |
|---|---|---|
| ms CPU par tick | bien sous **15,15 ms** (limite à 66 ticks/s) | proche ou au-dessus : le serveur ne suit plus (lag permanent) |
| intervalle de tick max | ~30 ms (normal sous Windows) | **> 50 ms = freeze** visible ; plusieurs centaines = gros freeze |
| ticks ratés | 0 à 2 | dizaines ou plus = freezes |
- p99 vers 30 ms même à vide = granularité du minuteur Windows, **à ignorer**.
- Un message `stuck in wall--level design error` = position de PNJ invalide dans la liste (à corriger, pas un bug de map).

## 6. Conditions pour une comparaison honnête
- **Rien d'autre de lourd sur le PC** pendant le bench (surtout pas une compilation de map : elle crée de faux freezes
  de 200 à 700 ms). Ne pas jouer en même temps.
- **Même** nombre de bots, mêmes paliers, même classe et mêmes positions de PNJ pour les deux versions.
- Une seule différence entre les deux versions testées (ex. avec / sans points de navigation).
- Garder une copie de chaque `.bsp` testé, et installer à la fin celle qui gagne.

## 7. Exemple de résultat (givre_noir, 1 bot, PNJ Combine)
| PNJ | avant | optimisée avec nœuds | optimisée **sans nœuds** |
|---|---|---|---|
| 600 | 2,39 ms (pic 96 ms) | 2,44 ms (pic 31 ms) | **1,62 ms (pic 32 ms)** |
Optimisations testées : brouillard/farz 8000/9000, bloqueurs de visibilité nodraw dans les grands rochers, func_viscluster
dans le ciel des extérieurs, fade des props réduit, effets actifs seulement pendant leur phase, débris non physiques,
suppression des info_node.

## 8. Limites à dire à l'utilisateur
- Le bench mesure le **serveur**, pas les FPS des joueurs (les tester en jeu : `net_graph 1`, `fps_max 0`, points `setpos`).
- Des PNJ Lua (VJ Base…) coûtent plus cher que ceux de HL2 : leur coût Lua ne dépend presque pas de la map.
- Le CPU du PC de test n'est pas celui du serveur de l'event : comparer des versions, pas promettre un chiffre absolu.
