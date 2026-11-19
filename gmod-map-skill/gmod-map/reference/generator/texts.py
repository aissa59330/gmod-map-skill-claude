"""Textes affichés en jeu (game_text) — aucun addon : tout passe par la map.

Pas de virgule dans les textes (séparateur des sorties I/O dans le VMF).
"""

PHASES = {
    1: ("Insertion", "Progresser à couvert dans le canyon jusqu'au hangar"),
    2: ("Hangar extérieur", "Détruire les 3 tourelles antiaériennes"),
    3: ("Infiltration", "Atteindre l'usine : conduits (ARC) ou porte principale"),
    4: ("Usine de droïdes", "Saboter les 3 générateurs"),
    5: ("Garnison", "Prendre l'armurerie : une console par étage (3)"),
    6: ("Centre de données", "Pirater les 3 terminaux et tenir la salle"),
    7: ("Bloc de détention", "Ouvrir les 3 blocs de cellules"),
    8: ("Tour de communication", "Poser une charge sur l'antenne à chaque niveau (3)"),
    9: ("Noyau du canon", "Surcharger le réacteur : 3 consoles"),
    10: ("Exfiltration", "Remonter les 3 puits avant l'effondrement"),
    11: ("Extraction", "Rejoindre la plateforme LAAT au sommet du glacier"),
}

# relais de la map -> message de SENTINELLE (ton froid ; texte original)
SENTINEL = {
    "gn_phase_1_start": "Signature thermique dans le canyon. Je vous vois déjà.",
    "gn_phase_2_start": "Vous approchez de mes batteries. Chaque pas est enregistré.",
    "gn_aa_destroyed": "Batterie antiaérienne perdue. Remplacement calculé. Vous ne gagnez que du temps.",
    "gn_phase_2_done": "Défenses aériennes neutralisées. J'ouvre les accès... pour mieux vous compter.",
    "gn_phase_3_start": "Deux routes. Deux fois plus de cibles.",
    "gn_phase_4_start": "Bienvenue dans ma chaîne de production. Vous en ferez bientôt partie.",
    "gn_gen_destroyed": "Générateur perdu. Redondance activée.",
    "gn_sentinel_factory_dark": "Coupure d'énergie secteur est. Dans le noir mes unités voient mieux que vous.",
    "gn_phase_4_done": "Production interrompue. Je mémorise chacun de vos visages.",
    "gn_phase_5_start": "La garnison est réveillée. Trois étages. Trois fois plus de raisons de tomber.",
    "gn_armory_taken": "Armurerie compromise. Les armes ne choisissent pas leur camp. Moi si.",
    "gn_phase_5_done": "Garnison perdue. Le centre de données vous attend. Moi aussi.",
    "gn_phase_6_start": "Mon centre de données n'est pas un refuge. C'est un piège climatisé.",
    "gn_hack_start": "Intrusion dans mes archives. Contre-mesures actives. Tenez si vous le pouvez.",
    "gn_hack_stage_1_done": "Premier verrou forcé. Terminal suivant : plateforme nord.",
    "gn_hack_stage_2_done": "Deuxième verrou forcé. Dernier terminal : zone sud. Toutes mes unités convergent.",
    "gn_sentinel_dc_lock": "Porte scellée. Faites le tour. Je vous attends de l'autre côté.",
    "gn_phase_6_done": "Accès accordé... Correction : je n'ai rien accordé.",
    "gn_phase_7_start": "Vous cherchez vos frères. Ils ne se souviennent plus de vous.",
    "gn_sentinel_prison": "Ouverture des cellules détectée. Isolement de secteur engagé.",
    "gn_cells_a_open": "Bloc est ouvert. Des prisonniers armés sont des cibles comme les autres.",
    "gn_cells_b_open": "Bloc sud ouvert. Le nombre ne vous sauvera pas.",
    "gn_cells_c_open": "Coursive haute ouverte. Chaque évadé est une cible de plus.",
    "gn_phase_7_done": "Évasion massive. Fermez la tour. Personne ne doit transmettre.",
    "gn_phase_8_start": "La tour relaie ma voix sur toute la planète. Vous ne la ferez pas taire.",
    "gn_sentinel_tower": "Charge détectée sur l'antenne. Je vous retire le sol sous les pieds.",
    "gn_charge_planted": "Charge armée. Signal dégradé. Je... continue.",
    "gn_phase_8_done": "Signal coupé. Je suis seule. Je n'en suis que plus dangereuse.",
    "gn_phase_9_start": "Vous êtes dans mon cœur. Personne n'en ressort.",
    "gn_sentinel_core_bridge": "Pont rétracté. Divisés vous êtes plus simples à résoudre.",
    "gn_reactor_overload": "Console compromise. Température du réacteur en hausse.",
    "gn_phase_9_done": "Surcharge critique. Si je tombe je vous emporte.",
    "gn_phase_10_start": "Effondrement de la structure dans huit minutes. Courez.",
    "gn_sentinel_exfil_seal": "Sas scellé derrière vous. Ceux qui sont restés m'appartiennent.",
    "gn_exfil_t360": "Six minutes.",
    "gn_exfil_t240": "Quatre minutes. Les puits se tordent.",
    "gn_exfil_t120": "Deux minutes. Le glacier se fissure au-dessus de vous.",
    "gn_exfil_t60": "Une minute. Vos chances s'effondrent plus vite que mes murs.",
    "gn_exfil_t30": "Trente secondes. Je compte.",
    "gn_exfil_fail": "Temps écoulé. Fin de la simulation... pour vous.",
    "gn_phase_10_done": "Signal détecté en surface. Vous n'êtes pas encore partis.",
    "gn_phase_11_start": "Transport en approche. Il ne vous attendra pas.",
    "gn_phase_11_done": "...Connexion... perdue.",
}

END_TEXT = "OPÉRATION GIVRE NOIR TERMINÉE\nLe LAAT a décollé. Ceux qui ne sont pas à bord restent avec SENTINELLE."
