"""Tracés de marche pour le test « à pied » de l'addon de dev (aucun téléport dans la map).

Chaque point = (nom, x, y, z_sol). Le joueur de test marche d'un point au suivant ; le point est
validé quand il est à moins de 40 u à l'horizontale ET à moins de 72 u en hauteur (il doit donc
vraiment avoir monté la rampe / pris l'étage).
"""


def spiral(name, x0, y0, z0):
    """Montée d'un puits d'exfiltration (1536 de côté, départ coin sud-ouest)."""
    return [
        (f"{name}_bas", x0 + 128, y0 + 128, z0),
        (f"{name}_r1", x0 + 300, y0 + 128, z0),
        (f"{name}_se", x0 + 1408, y0 + 128, z0 + 384),
        (f"{name}_ne", x0 + 1408, y0 + 1408, z0 + 768),
        (f"{name}_no", x0 + 128, y0 + 1408, z0 + 1152),
        (f"{name}_haut", x0 + 128, y0 + 128, z0 + 1536),
    ]


MAIN = [
    # 1 canyon (voie centrale, contourne le rocher)
    ("plateforme", -13720, 0, 8), ("canyon_a", -13200, 0, 0), ("canyon_b", -12900, -380, 0),
    ("canyon_c", -12200, -300, 0), ("canyon_d", -11400, -300, 0), ("canyon_e", -9900, -300, 0),
    # 2 hangar + rampes d'une plateforme de tourelle
    ("hangar_a", -9100, -300, 0), ("hangar_b", -7000, -450, 0), ("tourelle_rampe_bas", -6500, -1100, 0),
    ("tourelle_haut", -6500, -200, 256), ("tourelle_rampe_nord", -6500, 960, 0),
    ("hangar_c", -5800, 600, 0), ("porte_principale", -5300, 0, 0),
    # 3b hall d'assaut + couloir principal
    ("hall_a", -4950, 0, 0), ("hall_b", -4700, -240, 0), ("hall_c", -2200, -240, 0), ("hall_d", -2150, 0, 0), ("couloir_3b", -1000, 0, 0),
    # 4 usine : rampe -> mezzanine nord -> passerelle +512 -> mezzanine sud -> rampe
    ("usine_a", 200, 0, 0), ("usine_b", 150, 900, 0), ("usine_rampe_bas", 576, 440, 0), ("usine_rampe", 576, 1040, 256),
    ("mezz_nord", 600, 1280, 256), ("mezz_nord_b", 600, 1050, 256), ("mezz_nord_c", 2300, 1050, 256),
    ("pente_512_bas", 2300, 1280, 256), ("passerelle_512", 1536, 1280, 512), ("passerelle_512_sud", 1536, -1280, 512),
    ("mezz_sud", 2300, -1280, 256), ("rampe_sud_haut", 2176, -1040, 256), ("rampe_sud_bas", 2176, -440, 0),
    ("usine_sortie", 3040, 0, 0),
    # sas blindé 4 -> 5
    ("sas1_entree", 3300, 0, 0), ("sas1_chambre", 4096, 0, 0), ("sas1_sortie", 4900, 0, 0),
    # 5 garnison : RDC -> étage 1 -> étage 2
    ("garnison_rdc", 5400, 0, 0), ("garnison_rampe1_bas", 5600, 0, 0), ("garnison_e1", 6500, 0, 384),
    ("garnison_e1_b", 6700, 300, 384), ("garnison_e1_c", 7800, 300, 384), ("garnison_rampe2_bas", 7760, 0, 384),
    ("garnison_e2", 6800, 0, 768), ("garnison_e2_b", 6800, 400, 768), ("garnison_e2_c", 7900, 400, 768),
    ("garnison_sortie", 8000, 0, 768),
    # galerie de glace -> 6 centre de données -> salle du hack -> sortie sud
    ("galerie_a", 8400, 150, 768), ("galerie_b", 9800, 150, 768), ("dc_entree", 10300, 0, 768),
    ("dc_couloir", 11000, 0, 768), ("hack_porte_ouest", 11350, 0, 768), ("salle_hack", 11650, -350, 768),
    ("hack_porte_sud", 11776, -700, 768), ("dc_sud_a", 11776, -760, 768), ("dc_sud_b", 11180, -780, 768),
    ("dc_sud_c", 11180, -1350, 768), ("dc_sud", 11584, -1450, 768),
    # passerelle au-dessus du vide -> 7 prison : mirador (montée nord, descente sud)
    ("passerelle_a", 11584, -1650, 768), ("passerelle_b", 11584, -3500, 768), ("prison_entree", 11584, -3750, 768),
    ("mirador_rampe_bas", 11776, -4050, 768), ("mirador_haut", 11776, -4950, 1152), ("mirador_ouest", 11600, -5000, 1152),
    ("mirador_ouest_b", 11600, -5300, 1152), ("mirador_descente", 11776, -5400, 1152),
    ("mirador_rampe_sud", 11776, -6200, 768), ("prison_b", 11200, -6100, 768), ("prison_c", 11000, -5300, 768),
    # sas 7 -> 8
    ("sas2_entree", 10100, -5120, 768), ("sas2_chambre", 9216, -5120, 768), ("sas2_sortie", 8400, -5120, 768),
    # 8 tour : sol -> niveau 1 -> niveau 2 -> niveau 3
    ("tour_sol", 8000, -5120, 768), ("tour_sol_b", 7300, -6200, 768), ("tour_sol_c", 5500, -6200, 768),
    ("tour_rampe1_bas", 5560, -6528, 768), ("tour_n1", 6700, -6528, 1280), ("tour_n1_b", 7000, -6300, 1280),
    ("tour_n1_c", 8064, -6300, 1280), ("tour_rampe2_bas", 8064, -6170, 1280), ("tour_n2", 8064, -5050, 1792),
    ("tour_n2_b", 7800, -5000, 1792), ("tour_n2_c", 7800, -6300, 1792), ("tour_rampe3_bas", 7720, -6528, 1792),
    ("tour_n3", 6600, -6528, 2304), ("tour_n3_b", 5400, -6528, 2304), ("tour_n3_c", 5400, -5120, 2304),
    # tranchée 8 -> 9 (on descend dans la fosse et on remonte)
    ("tranchee_a", 4950, -5120, 2304), ("tranchee_b", 3200, -5120, 2304),
    # 9 noyau : quai est -> passerelle -> anneau -> pont est -> collier -> pont nord -> anneau -> passerelle ouest
    ("noyau_quai_est", 2900, -5120, 2304), ("noyau_quai_b", 2900, -5760, 2304), ("noyau_passerelle_est", 2300, -5760, 2304),
    ("anneau_est", 2300, -5120, 2304), ("collier_est", 1856, -5120, 2304), ("collier_nord_est", 1856, -4800, 2304),
    ("collier_nord", 1536, -4800, 2304), ("anneau_nord", 1536, -4100, 2304), ("anneau_no", 768, -4100, 2304),
    ("anneau_ouest", 768, -4480, 2304), ("noyau_passerelle_ouest", 450, -4480, 2304), ("noyau_quai_ouest", 128, -4480, 2304),
    ("noyau_sortie", 128, -5120, 2304),
    # 10 exfiltration : couloir -> puits 1 -> couloir -> puits 2 -> couloir -> puits 3
    ("exfil_e0_a", -300, -5120, 2304), ("exfil_e0_b", -768, -5120, 2304), ("exfil_e0_c", -768, -6400, 2304),
    ("exfil_e0_d", -2432, -6400, 2304),
] + spiral("puits1", -2560, -6016, 2304) + [
    ("exfil_e1_a", -2700, -5888, 3840), ("exfil_e1_b", -3328, -5888, 3840), ("exfil_e1_c", -3328, -6400, 3840),
    ("exfil_e1_d", -5248, -6400, 3840),
] + spiral("puits2", -5376, -6016, 3840) + [
    ("exfil_e2_a", -5600, -5888, 5376), ("exfil_e2_b", -6144, -5888, 5376), ("exfil_e2_c", -6144, -6400, 5376),
    ("exfil_e2_d", -8064, -6400, 5376),
] + spiral("puits3", -8192, -6016, 5376) + [
    # 11 glacier -> plateforme LAAT
    ("exfil_e3", -8300, -5888, 6912), ("glacier", -8700, -5888, 6912), ("glacier_b", -9600, -5700, 6912),
    ("laat_rampe_bas", -10000, -5850, 6912), ("laat_plateforme", -10600, -5850, 6976),
]

# route des conduits (3a) : hangar -> tunnels -> collecteur -> usine
CONDUITS = [
    ("c_hangar", -5400, 1920, 0), ("c_porte", -5000, 1920, 0), ("c_vestibule", -4700, 2064, 0),
    ("c_tunnel_a", -4400, 2064, 0), ("c_tunnel_b", -2600, 2064, 0), ("c_tunnel_c", 900, 2064, 0),
    ("c_collecteur", 1300, 2200, 0), ("c_descente", 1536, 1700, 0), ("c_usine", 1536, 1300, 0),
]
