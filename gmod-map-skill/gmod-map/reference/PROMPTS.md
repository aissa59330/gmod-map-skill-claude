# Prompts prêts à l'emploi

À coller dans une nouvelle conversation Claude Code ouverte dans le dossier de la map.
Remplacer `<UTILISATEUR>` par le nom du dossier utilisateur Windows.

---

## 1. Optimiser une map au maximum

```
Je veux optimiser ma map Gmod au maximum, pour un event avec 70 à 100 joueurs et beaucoup de droïdes (PNJ).

Utilise la compétence gmod-map (section 6 « Optimisation » et 6 bis « Mesurer ») et suis cette méthode :

1. DIAGNOSTIC D'ABORD, sans rien modifier :
   - lis la map (le générateur et le .vmf, ou le .bsp avec srctools) : distance de vue (fog/farz), nombre de zones de visibilité, areaportals, lumières dynamiques, props (types, triangles, fade, collisions), nombre de points de navigation (info_node), effets permanents, herbe automatique, contenu embarqué ;
   - montre-moi la liste des problèmes, classés par impact, avec ce que tu proposes pour chacun.

2. MESURE « AVANT » :
   - FPS : donne-moi les commandes setpos/setang de 5 à 8 points fixes (spawn, extérieur, en l'air, grandes salles, effets lourds) ; je mesure avec net_graph 1 et fps_max 0, et je te donne les chiffres ;
   - serveur : bench sur serveur dédié local (méthode de la compétence : 1 bot + 0/200/400/600 PNJ, ms de CPU par tick, pics, ticks ratés). Le serveur est déjà installé dans C:\Users\<UTILISATEUR>\gn_srcds.

3. OPTIMISE, dans l'ordre d'impact : visibilité (VVIS complet, bloqueurs nodraw, func_viscluster, areaportals si c'est une map intérieure), éclairage précalculé, distance de vue, props (prop_static, LOD, barème de fade, collisions), points de navigation (demande-moi avant de les supprimer), effets actifs seulement pendant leur phase, terrain et herbe, contenu embarqué.

4. MESURE « APRÈS » aux mêmes points et avec le même bench, puis donne-moi un tableau avant / après.

Règles :
- Sauvegarde git avant chaque grosse modification.
- Uniquement en local, jamais sur le serveur de l'event.
- Ne ferme jamais mon Gmod ; ne tue que ce que tes outils ont lancé, et vérifie qu'aucun vbsp/vvis/vrad/srcds ne reste en arrière-plan à la fin.
- Préviens-moi avant chaque bench pour que je ne compile rien et ne joue pas pendant la mesure ; serveur lancé en fenêtre réduite.
- Demande-moi avant d'installer quoi que ce soit, et avant tout changement de gameplay (portes, points de navigation, distance de vue très réduite).
- Dis toujours ce qui a été mesuré et ce qui ne l'a pas été.
```

---

## 2. Bench serveur seul (mesurer une map avec beaucoup de PNJ)

```
Je veux mesurer les performances SERVEUR de ma map Gmod avec beaucoup de PNJ.

Utilise la compétence gmod-map : section 6 bis, et les fichiers reference/METHODE_BENCH_SERVEUR.md,
reference/tools/bench_server.ps1 et reference/addons/givre_noir_srvbench/.

1. Adapte le script et l'addon de mesure à MA map : nom de la map, chemins, packs Workshop à monter, et une liste de positions de PNJ valides prises sur des sols praticables.
2. Réutilise le serveur dédié déjà installé dans C:\Users\<UTILISATEUR>\gn_srcds (ne réinstalle pas s'il est là).
3. Lance le bench avec 1 bot et des paliers de 0 / 200 / 400 / 600 PNJ (classe npc_combine_s), 60 s par palier.
4. Donne-moi un tableau : ms de CPU par tick, intervalle de tick max (pics) et ticks ratés pour chaque palier, puis ton analyse.
5. Si tu proposes des optimisations, refais exactement le même bench après et compare avant / après.

Règles :
- Uniquement en local, jamais sur le serveur de l'event ni ses fichiers.
- Ne ferme jamais mon Gmod ; ne tue que le serveur lancé par le script.
- Lance la fenêtre du serveur réduite et préviens-moi de ne pas cliquer dedans.
- Préviens-moi avant de lancer le bench pour que je ne compile rien et ne joue pas pendant la mesure.
- Demande-moi avant d'installer quoi que ce soit.
- Dis toujours clairement ce qui a été mesuré et ce qui ne l'a pas été.
```

---

## 3. Créer une nouvelle map

```
Je veux créer une nouvelle map Gmod d'event avec la compétence gmod-map.
Pose-moi d'abord les questions de la section 0 (thème, joueurs, durée, phases, règles du serveur, packs autorisés, ce qui est affiché),
puis propose un plan des zones avant de générer quoi que ce soit. Commence petit (2-3 zones, 1 objectif) pour valider l'installation.
```
