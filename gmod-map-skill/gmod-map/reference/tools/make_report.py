"""Rapport d'optimisation (page HTML) : python tools/make_report.py -> docs/rapport_optimisation.html
Le tableau par point est relu dans logs/tableau_fps.md (généré depuis les fichiers de bench)."""
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = []
for l in open(os.path.join(ROOT, "logs", "tableau_fps.md"), encoding="utf-8"):
    if l.startswith("| z") or l.startswith("| v"):
        rows.append([x.strip() for x in l.strip().strip("|").split("|")])


def cell(v):
    m = re.match(r"(\d+) / (\d+)", v)
    a, b = int(m.group(1)), int(m.group(2))
    cls = "ok" if a >= 100 else ("mid" if a >= 60 else "low")
    return f'<td class="num {cls}">{a}<span class="sub"> / {b}</span></td>'


trs = "\n".join(f"<tr><td class='pt'>{html.escape(r[0])}</td>{cell(r[1])}{cell(r[2])}{cell(r[3])}<td class='num dim'>{r[4]}</td></tr>"
                for r in rows)
tpl = open(os.path.join(ROOT, "tools", "report_template.html"), encoding="utf-8").read()
open(os.path.join(ROOT, "docs", "rapport_optimisation.html"), "w", encoding="utf-8").write(tpl.replace("<!--LIGNES-->", trs))
print("rapport :", len(rows), "points")
