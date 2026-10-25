"""Phase 5: the application's data files, generated from the normalized model.

    python tools/build-app-data.py          write data/app/*.js
    python tools/build-app-data.py --check  exit 1 unless data/app/ is exactly what the model gives

normalized model -> generated application data -> application. The model is
projected by tools/model_reader.py (the projection M8 compared with today's
files and M9 read side by side with them) and written as page-loadable
files, one per data file the page used to load, with the same globals: the
23 files of the M12 boundary (CONTRACT). The page assets outside the
contract (map geometry, notes, regional vintages, classification prose)
stay in data/ and are not generated.

Records are written in the model's order (by id): the model holds no
display order, and the reordering this causes in the producers list is
accepted, with presentation order on the backlog (docs/PHASE-5-APPLICATION-
SOURCE-SWITCH.md). Nothing here migrates, reconciles or reads the evidence,
the discovery corpus or the raw store; the application never runs it.
"""
import json
import os
import sys

import migration_lib as L
import model_reader as R

OUT = L.ROOT + 'data/app/'
# The page's data files the model projects (tools/app-boundary.py CONTRACT).
CONTRACT = ['batch2.js', 'batch3.js', 'batch4.js', 'cellar.js', 'chateaux.js', 'coords.js', 'cruartisan.js',
            'crubourgeois.js', 'cuvee-url.js', 'cuvees.js', 'fiches-nl.js', 'fiches-url.js', 'fiches.js',
            'graves.js', 'libournais.js', 'overrides.js', 'plantings.js', 'pomerol.js', 'ratings.js',
            'saintemilion.js', 'sauternes.js', 'terroir.js', 'websites.js']
HEADER = ('/* Generated from the normalized model (data/model/) by tools/build-app-data.py.\n'
          '   Do not edit: python tools/build-app-data.py rebuilds it; --check compares. */\n')


def render():
    """{filename: bytes} for every contract file."""
    proj = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
    out = {}
    for f in CONTRACT:
        body = HEADER
        for g, v in sorted(proj[f].items()):
            js = json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            if g == 'BDX_CHATEAUX':
                # The estate files append to one list, as today's files do.
                body += 'window.%s = (window.%s || []).concat(%s);\n' % (g, g, js)
            else:
                body += 'window.%s = %s;\n' % (g, js)
        out[f] = body.encode('utf-8')
    return out


def main():
    files = render()
    if '--check' in sys.argv:
        bad = [f for f, b in files.items()
               if not os.path.exists(OUT + f) or open(OUT + f, 'rb').read() != b]
        extra = sorted(set(os.listdir(OUT)) - set(files)) if os.path.isdir(OUT) else []
        L.out('data/app ' + ('is the model, byte for byte' if not bad and not extra else
                             'differs: %s' % (bad + extra)))
        sys.exit(1 if bad or extra else 0)
    os.makedirs(OUT, exist_ok=True)
    for f, b in files.items():
        with open(OUT + f + '.tmp', 'wb') as h:
            h.write(b)
        os.replace(OUT + f + '.tmp', OUT + f)
    L.out('%d files, %d bytes' % (len(files), sum(len(b) for b in files.values())))


if __name__ == '__main__':
    main()
