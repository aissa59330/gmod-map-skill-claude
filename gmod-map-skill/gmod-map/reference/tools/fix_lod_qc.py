"""À lancer après tools/make_lod_props.py : remplace les $cdmaterials des QC par ceux du modèle d'origine.

Plumber renomme parfois les matériaux introuvables ('~hash/dossier/nom') : les dossiers déduits de ces noms
sont faux (props violets en jeu). Les vrais dossiers sont lus dans le .mdl d'origine (srctools).
python tools/fix_lod_qc.py [dossier_qc]
"""
import os
import re
import sys

from srctools.filesys import RawFileSystem
from srctools.mdl import Model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QC_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "lod_props")
roots = [l.strip() for l in open(os.path.join(ROOT, "tools", "content_paths.txt"), encoding="utf-8")
         if l.strip() and not l.startswith("#")]
report = open(os.path.join(QC_DIR, "lod_report.txt"), encoding="utf-8").read()
for m in re.finditer(r"^OK (models/\S+\.mdl)", report, re.M):
    rel = m.group(1)
    name = os.path.splitext(os.path.basename(rel))[0]
    root = next((r for r in roots if os.path.exists(os.path.join(r, rel))), None)
    if not root:
        print("introuvable", rel)
        continue
    fs = RawFileSystem(root)
    cds = [c.replace("\\", "/").strip("/") for c in Model(fs, fs[rel]).cdmaterials]
    qp = os.path.join(QC_DIR, name + ".qc")
    q = re.sub(r'^\$cdmaterials .*\n', '', open(qp, encoding="ascii").read(), flags=re.M)
    q = q.replace('$surfaceprop "metal"\n', '$surfaceprop "metal"\n' + "".join(f'$cdmaterials "{c + "/" if c else ""}"\n' for c in cds))
    open(qp, "w", encoding="ascii").write(q)
    print(name, cds)
