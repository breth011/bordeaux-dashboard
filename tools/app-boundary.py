"""Phase 4 M12: the application boundary (D7).

    python tools/app-boundary.py          write data/model/checks/app-boundary.json
    python tools/app-boundary.py --check  exit 1 if the app reaches past the boundary

D7, decided after the migration gate's evidence (M8 zero unexplained
differences, M9 dual read PASS): the application reads page-loadable data
files generated from the model's projection (tools/model_reader.py):
canonical values, observations and provenance where the page shows them
(class B text such as tasting and cellar notes), and the derived indexes
(M13). It never reads scraper output, the discovery data, the evidence
logs, the manifest, migration files or the raw store. The switch from
today's hand-maintained files to the generated ones is a separate,
controlled step after Phase 4; today the page still reads data/*.js,
which the dual read shows the model reproduces.

This tool lists what the page loads (index.html, the service worker's
cache list, fetch calls in assets/) and classifies each file:
  CONTRACT     projected from the normalized model (M8, M9)
  PAGE_ASSET   outside the contract (map geometry, editorial notes); the
               page keeps reading it as it is
  FORBIDDEN    must never be read by the page
"""
import json
import os
import re
import sys

import migration_lib as L
import model_reader  # noqa: F401  (the projection this boundary names)
import reconstruct

OUT = L.MODEL + 'checks/app-boundary.json'
FORBIDDEN = ('data/discovery', 'data/evidence', 'data/sources.json', 'data/model', 'data/scope',
             'data/review', 'data/audit', 'data/proposals', 'data/attribution-candidates', 'sources/',
             'tools/', '.jsonl')
APP_FILES = ['index.html', 'service-worker.js'] + sorted(
    'assets/' + f for f in os.listdir(L.ROOT + 'assets') if f.endswith(('.js', '.html')))


def loaded():
    refs = {}
    for f in APP_FILES:
        s = open(L.ROOT + f, encoding='utf-8').read()
        for m in re.finditer(r'''(?:src=|href=|fetch\(|importScripts\(|['"])\.?/?((?:data|sources|tools)/[^'"\s)]+)''', s):
            refs.setdefault(m.group(1), set()).add(f)
    return {k: sorted(v) for k, v in refs.items()}


def classify(path):
    if any(x in path for x in FORBIDDEN):
        return 'FORBIDDEN'
    name = path.split('/')[-1]
    if name in reconstruct.OUT_OF_SCOPE or name == 'classifications.js':
        return 'PAGE_ASSET'
    return 'CONTRACT'


def build():
    refs = loaded()
    rows = {p: {'class': classify(p), 'referenced_by': by} for p, by in sorted(refs.items())
            if not ('assets/app.js' in by and len(by) == 1 and p.endswith('.js') and
                    not re.search(r'fetch|src=', p))}
    # comments in app.js name files in prose ("data/chateaux.js carries ..."): only loads count
    loads = {p: r for p, r in rows.items() if any(b in ('index.html', 'service-worker.js')
                                                    for b in r['referenced_by'])}
    return {'_': 'Phase 4 M12: what the page loads, classified against the D7 boundary '
                 '(tools/app-boundary.py).',
            'decision_D7': 'the page reads files generated from the model projection (canonical values, '
                           'observations and provenance where shown, derived indexes); switched in a '
                           'separate controlled step after Phase 4',
            'loads': loads,
            'forbidden': sorted(p for p, r in loads.items() if r['class'] == 'FORBIDDEN')}


def main():
    r = build()
    if '--check' not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
    c = {}
    for p, x in r['loads'].items():
        c[x['class']] = c.get(x['class'], 0) + 1
    L.out('page loads: %s; forbidden: %s' % (json.dumps(c), r['forbidden'] or 'none'))
    sys.exit(1 if r['forbidden'] else 0)


if __name__ == '__main__':
    main()
