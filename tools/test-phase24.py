# -*- coding: utf-8 -*-
"""Phase 2.4: the evidence store keeps what it was given, and refuses
what would make it lie.

    python tools/test-phase24.py

Two halves. The first builds a store in a temporary directory, from a
sample of the committed evidence, and attacks it: wrong version, a
changed reader, v4 rows without provenance, a duplicate inside one
batch, a part outgrowing its limit, a byte changed after writing. None
of it touches data/evidence/.

The second checks the real store: v1-v3 reproduce the pre-migration
file byte for byte, every part matches its hash, no part nears GitHub's
size limits, and the tools read from it.
"""
import collections
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV
import evidence_store as ST
import importlib.util

spec = importlib.util.spec_from_file_location(
    'migrate', ROOT + 'tools/migrate-evidence-store.py')
MG = importlib.util.module_from_spec(spec)
spec.loader.exec_module(MG)

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-58s %s' % ('ok' if ok else 'FAIL', name[:58], shown))


def refused(fn):
    try:
        fn()
    except ST.RefusedAppend as e:
        return str(e)
    return None


# ======================================================= a store to attack
try:
    raw = MG.source_bytes('a36b35c')
except Exception:
    raw = None
    print('MISSING  git object a36b35c:data/evidence-decisions.jsonl')

real_dir, real_index = ST.DIR, ST.INDEX
tmp = tempfile.mkdtemp(prefix='evstore-')
if raw:
    smp = MG.sample(raw, 300)
    says('a sample migrates losslessly',
         MG.migrate(smp, tmp, 'a36b35c', 'sample') is True)
    bad = bytearray(smp)
    bad[len(bad) // 2] = ord('#') if bad[len(bad) // 2] != ord('#') \
        else ord('%')
    h, by, order = MG.split(smp)
    files = dict((v, b''.join(x + b'\n' for x in ls)) for v, ls in by.items())
    files[2] = files[2].replace(b'"REFUSED"', b'"ACCEPTED"', 1)
    says('...and the proof catches one changed verdict',
         bool(MG.prove(smp, h, by, order, files)))

    ST.DIR, ST.INDEX = os.path.join(tmp, ''), os.path.join(tmp, 'index.json')
    before = dict((v, list(ST.iter_lines(v))) for v in ST.versions())
    v3 = list(ST.iter_rows([3]))
    proto = copy.deepcopy(v3[0])

    def row(**kw):
        r = copy.deepcopy(proto)
        r['artifact'] = kw.pop('artifact', 'TEST-%s.pdf' % len(kw))
        r.update(kw)
        return r

    says('history reads back: v1, v2, v3 present',
         ST.versions() == [1, 2, 3], str(ST.versions()))
    says('a row of v3 cannot go into v2',
         bool(refused(lambda: ST.append([row(artifact='x.pdf')], 2))))
    says('a changed reader cannot add to v3',
         bool(refused(lambda: ST.append(
             [row(artifact='y.pdf', reader='000000000000')], 3))))
    n = ST.append([row(artifact='same-reader.pdf')], 3)
    says('the same reader can add a new question to v3', n == 1, '%d' % n)
    n = ST.append([row(artifact='same-reader.pdf')], 3)
    says('...and asking it again adds nothing', n == 0, '%d' % n)
    n = ST.append([row(artifact='twice.pdf'), row(artifact='twice.pdf')], 3)
    says('a duplicate inside one batch is written once', n == 1, '%d' % n)

    bare = row(artifact='v4.pdf', v=4, reader='abcdefabcdef')
    says('v4 refuses a row without observed path, hash, tree_clean',
         bool(refused(lambda: ST.append([bare], 4))))
    good = copy.deepcopy(bare)
    good['observed'] = {'path': 'fiches/x/v4.pdf', 'sha1': 'f' * 40}
    good['tree_clean'] = True
    says('v4 accepts a row that carries them',
         ST.append([good], 4) == 1)
    says('...in its own file',
         [os.path.basename(p) for p in ST.parts(4)]
         == ['decisions-v4.jsonl'])

    old = ST.PART_LIMIT
    ST.PART_LIMIT = os.path.getsize(ST.parts(4)[0]) + 10
    many = []
    for i in range(5):
        r = copy.deepcopy(good)
        r['artifact'] = 'part-%d.pdf' % i
        many.append(r)
    ST.append(many, 4)
    ST.PART_LIMIT = old
    says('a version past its size limit continues in a second part',
         len(ST.parts(4)) >= 2,
         ', '.join(os.path.basename(p) for p in ST.parts(4)))
    says('...and reads back whole, in order',
         [d['artifact'] for d in ST.iter_rows([4])]
         == ['v4.pdf'] + ['part-%d.pdf' % i for i in range(5)])

    after = dict((v, list(ST.iter_lines(v))) for v in (1, 2, 3))
    says('appending never changed a line of v1, v2 or v3',
         all(after[v][:len(before[v])] == before[v] for v in (1, 2, 3)))
    latest = ST.latest_by_context()
    says('latest_by_context: one answer per question',
         len(latest) == len(set(EV.row_key(d)[:-1]
                                for d in ST.iter_rows())))
    says('the store verifies after all that', ST.verify() == [],
         '; '.join(ST.verify())[:40])
    p = ST.parts(1)[0]
    with open(p, 'r+b') as f:
        f.seek(10)
        c = f.read(1)
        f.seek(10)
        f.write(b'X' if c != b'X' else b'Y')
    says('a byte changed in v1 is caught by verify()', bool(ST.verify()))

ST.DIR, ST.INDEX = real_dir, real_index
shutil.rmtree(tmp, ignore_errors=True)

# ============================================================ the real one
print()
if not os.path.exists(ST.INDEX):
    print('MISSING  data/evidence/index.json')
else:
    ix = json.load(io.open(ST.INDEX, encoding='utf-8'))
    mf = ix.get('migrated_from') or {}
    bad = ST.verify()
    says('every part of the real store matches its hash', not bad,
         '; '.join(bad)[:40])
    rows = collections.Counter(d.get('v') for d in ST.iter_rows())
    says('v1 13,065 / v2 41,259 / v3 41,259 rows',
         (rows[1], rows[2], rows[3]) == (13065, 41259, 41259),
         '%s' % dict(rows))
    if raw:
        header = b''.join(h.encode('utf-8') + b'\n'
                          for h in mf.get('header', []))
        body = b''.join(open(p, 'rb').read()
                        for v in (1, 2, 3) for p in ST.parts(v))
        says('header + v1 + v2 + v3 == the file at a36b35c, byte for byte',
             header + body == raw)
    import hashlib
    says('...and its hash is the one the index recorded',
         hashlib.sha256(header + body).hexdigest() == mf.get('sha256')
         if raw else False)
    big = [(os.path.basename(p), os.path.getsize(p))
           for v in ST.versions() for p in ST.parts(v)
           if os.path.getsize(p) > 45 * 1000 * 1000]
    says('no evidence file over 45 MB (GitHub warns at 50)', not big,
         str(big)[:40])
    says('the single-file store is gone',
         not os.path.exists(ROOT + 'data/evidence-decisions.jsonl'))
    attrs = io.open(ROOT + '.gitattributes', encoding='utf-8').read() \
        if os.path.exists(ROOT + '.gitattributes') else ''
    says('.gitattributes keeps evidence files LF in the working copy',
         'data/evidence/*.jsonl' in attrs and 'eol=lf' in attrs)
    # No tool still opens the old path.
    stale = []
    for f in os.listdir(ROOT + 'tools'):
        if f.endswith('.py') and f not in ('migrate-evidence-store.py',
                                           'evidence_store.py',
                                           'test-phase24.py'):
            t = io.open(ROOT + 'tools/' + f, encoding='utf-8').read()
            if "'data/evidence-decisions.jsonl'" in t \
                    or "read_jsonl('evidence-decisions.jsonl')" in t:
                stale.append(f)
    says('no tool opens data/evidence-decisions.jsonl any more', not stale,
         ', '.join(stale)[:40])

# ================================================== canonical safety
PROTECTED = ('data/sources.json', 'data/fiches.js', 'data/cuvees.js',
             'data/field-src.js', 'data/cuvee-src.js')
try:
    out = subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'] + list(PROTECTED),
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
print()
if out is None:
    print('MISSING  git unavailable')
else:
    says('canonical dataset files unmodified vs HEAD', out == '',
         'clean' if out == '' else out.replace('\n', ' ')[:28])

print('\n%d check(s), %s'
      % (checks, 'all pass' if not fails
         else '%d FAILED: %s' % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
