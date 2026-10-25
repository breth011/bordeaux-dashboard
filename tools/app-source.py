"""Phase 5: which data source the application loads, and the rollback.

    python tools/app-source.py              print the current source (model | legacy | mixed)
    python tools/app-source.py --model      load the 23 contract files from data/app/ (generated)
    python tools/app-source.py --legacy     load them from data/ again (the rollback)
    ... --root DIR                          act on a copy of the site instead (tests)

Only index.html's script tags and service-worker.js's precache list change,
plus the service worker's cache name, so installed copies fetch the new
files. Nothing else changes: the legacy files stay in data/ (they are the
protected canonical data and the rollback source), the generated files stay
in data/app/, and the normalized model is never touched.
"""
import os
import re
import sys

import migration_lib as L
from importlib import util as _u

_spec = _u.spec_from_file_location('build_app_data', L.ROOT + 'tools/build-app-data.py')
_b = _u.module_from_spec(_spec)
_spec.loader.exec_module(_b)
CONTRACT = _b.CONTRACT

CACHE_RE = re.compile(r"var CACHE_NAME = 'bordeaux-classified-v(\d+)';")


def paths(root):
    return root + 'index.html', root + 'service-worker.js'


def state(root=L.ROOT):
    idx, sw = (open(p, encoding='utf-8').read() for p in paths(root))
    model = sum(('data/app/%s"' % f) in idx for f in CONTRACT) + \
        sum(("'./data/app/%s'" % f) in sw for f in CONTRACT)
    legacy = sum(('"data/%s"' % f) in idx for f in CONTRACT) + \
        sum(("'./data/%s'" % f) in sw for f in CONTRACT)
    if model == 2 * len(CONTRACT) and not legacy:
        return 'model'
    if legacy == 2 * len(CONTRACT) and not model:
        return 'legacy'
    return 'mixed'


def switch(to, root=L.ROOT):
    cur = state(root)
    if cur == to:
        return False
    if cur == 'mixed':
        raise SystemExit('the source is mixed; refusing to guess')
    idx_p, sw_p = paths(root)
    idx, sw = open(idx_p, encoding='utf-8').read(), open(sw_p, encoding='utf-8').read()
    for f in CONTRACT:
        a, b = ('data/%s' % f, 'data/app/%s' % f) if to == 'model' else ('data/app/%s' % f, 'data/%s' % f)
        assert idx.count('"%s"' % a) == 1 and sw.count("'./%s'" % a) == 1, f
        idx = idx.replace('"%s"' % a, '"%s"' % b)
        sw = sw.replace("'./%s'" % a, "'./%s'" % b)
    # A new cache name, so an installed copy drops the old files and takes these.
    n = int(CACHE_RE.search(sw).group(1))
    sw = CACHE_RE.sub("var CACHE_NAME = 'bordeaux-classified-v%d';" % (n + 1), sw)
    for p, s in ((idx_p, idx), (sw_p, sw)):
        with open(p, 'w', encoding='utf-8', newline='') as h:
            h.write(s)
    return True


def main():
    a = sys.argv[1:]
    root = (a[a.index('--root') + 1].replace('\\', '/').rstrip('/') + '/') if '--root' in a else L.ROOT
    if '--model' in a or '--legacy' in a:
        to = 'model' if '--model' in a else 'legacy'
        L.out('switched to %s' % to if switch(to, root) else 'already %s' % to)
    L.out('application data source: %s' % state(root))


if __name__ == '__main__':
    main()
