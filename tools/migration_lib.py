"""Phase 4: what every migration stage shares.

The legacy data is read exactly as the page reads it (tools/legacy-dump.js
and tools/canonical-view.js under node); the normalized model is a set of
JSON Lines files under data/model/, one file per conceptual responsibility,
each sorted by its key so that a rebuild is byte-identical. Nothing here
writes outside data/model/.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'
# BDX_MODEL_DIR points the migration at another directory (the rollback test).
_md = os.environ.get('BDX_MODEL_DIR')
MODEL = _md.replace('\\', '/').rstrip('/') + '/' if _md else ROOT + 'data/model/'

# The groups whose bytes Phase 4 must not change (docs/PHASE-4-MIGRATION-BASELINE.md).
GROUPS = {
    'canonical': lambda: sorted(glob.glob(ROOT + 'data/*.js')) + [ROOT + 'data/sources.json'],
    'phase_records': lambda: sorted(p for p in glob.glob(ROOT + 'data/*')
                                    if os.path.isfile(p) and not p.endswith('.js')
                                    and not p.endswith('sources.json')),
    'evidence': lambda: sorted(glob.glob(ROOT + 'data/evidence/*')),
    'discovery': lambda: sorted(p for p in glob.glob(ROOT + 'data/discovery/**', recursive=True)
                                if os.path.isfile(p)),
    'scope': lambda: sorted(glob.glob(ROOT + 'data/scope/*')),
    'review': lambda: sorted(glob.glob(ROOT + 'data/review/*')),
    'phase34_model': lambda: [ROOT + 'docs/phase34-model.json', ROOT + 'docs/phase34-fixtures.json',
                              ROOT + 'docs/PHASE-3.4-DOMAIN-MODEL.md',
                              ROOT + 'docs/PHASE-3.4-DOMAIN-MODEL-REVIEW.md'],
}


def rel(p):
    return p.replace('\\', '/').replace(ROOT, '')


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def group_hashes(name):
    files = {rel(p): sha256_file(p) for p in GROUPS[name]()}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'files': files, 'digest': digest}


def node():
    n = shutil.which('node')
    if not n:
        found = glob.glob(os.path.expandvars(
            r'%LOCALAPPDATA%\Microsoft\WinGet\Packages\OpenJS.NodeJS*\node-*\node.exe'))
        n = found[0] if found else None
    if not n:
        sys.exit('node not found: tools/legacy-dump.js needs it')
    return n


_cache = {}


def legacy():
    """{file: {GLOBAL: value}} as the page sees it."""
    if 'legacy' not in _cache:
        out = subprocess.check_output([node(), ROOT + 'tools/legacy-dump.js'], cwd=ROOT)
        _cache['legacy'] = json.loads(out.decode('utf-8'))
    return _cache['legacy']


def canonical_view():
    """The 470 estates as app.js expands them."""
    if 'view' not in _cache:
        out = subprocess.check_output([node(), ROOT + 'tools/canonical-view.js'], cwd=ROOT)
        _cache['view'] = json.loads(out.decode('utf-8'))
    return _cache['view']


def g(name):
    """A legacy global by name, wherever it is defined (estate lists concatenated)."""
    if name == 'BDX_CHATEAUX':
        raise ValueError('use estate_files()')
    for f, gl in legacy().items():
        if name in gl:
            return gl[name]
    return None


ESTATE_FILES = ['chateaux.js', 'sauternes.js', 'saintemilion.js', 'pomerol.js', 'graves.js',
                'libournais.js', 'batch2.js', 'batch3.js', 'batch4.js']


def estate_files():
    """[(file, record)] in the page's load order."""
    L = legacy()
    return [(f, r) for f in ESTATE_FILES for r in L[f].get('BDX_CHATEAUX', [])]


def sources_rows():
    d = json.load(open(ROOT + 'data/sources.json', encoding='utf-8'))
    return d


def jsonl_lines(p):
    with open(p, encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def count_lines(p):
    with open(p, 'rb') as f:
        return sum(1 for x in f if x.strip())


def dumps(o):
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def write_table(relpath, rows, key='id'):
    """One JSON object per line, sorted by key; returns the file's sha256."""
    p = MODEL + relpath
    os.makedirs(os.path.dirname(p), exist_ok=True)
    keyf = key if callable(key) else (lambda r: r[key])
    rows = sorted(rows, key=lambda r: dumps(keyf(r)))
    ids = [dumps(keyf(r)) for r in rows]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})[:5]
        raise SystemExit('%s: duplicate keys %s' % (relpath, dup))
    data = ''.join(dumps(r) + '\n' for r in rows).encode('utf-8')
    tmp = p + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, p)
    return hashlib.sha256(data).hexdigest()


def read_table(relpath):
    p = MODEL + relpath
    return jsonl_lines(p) if os.path.exists(p) else []


def stable_hash(*parts, n=12):
    return hashlib.sha256('\x1f'.join(str(x) for x in parts).encode('utf-8')).hexdigest()[:n]


def out(s=''):
    sys.stdout.write(s + '\n')


sys.stdout.reconfigure(encoding='utf-8')
