# -*- coding: utf-8 -*-
"""Phase 2.5: a decision can be tied to the bytes it read and the code
that read them.

    python tools/test-phase25.py

Everything that can be tested on fixtures is: a small sources/ tree and
a throwaway git repository in a temporary directory, and a temporary
evidence store. Nothing here writes to data/ or reads a real document,
except the last section, which checks the known same-name cases against
sources/ where it is present and prints MISSING where it is not.
"""
import hashlib
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
import provenance as PV

fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-60s %s' % ('ok' if ok else 'FAIL', name[:60], shown))


def failure(fn):
    try:
        fn()
    except PV.ProvenanceFailure as f:
        return f.code
    return None


def put(root, rel, data):
    p = os.path.join(root, *rel.split('/'))
    if not os.path.isdir(os.path.dirname(p)):
        os.makedirs(os.path.dirname(p))
    with open(p, 'wb') as f:
        f.write(data)
    return p


def sha(b):
    return hashlib.sha256(b).hexdigest()


def git(args, cwd):
    return subprocess.check_output(['git'] + args, cwd=cwd,
                                   stderr=subprocess.DEVNULL).decode().strip()


tmp = tempfile.mkdtemp(prefix='prov-')
try:
    # ======================================================= resolution
    print('RESOLUTION')
    A, B = b'%PDF estate A sheet', b'%PDF estate B sheet, other bytes'
    put(tmp, 'sources/fiches/estate-a/sheet.pdf', A)
    put(tmp, 'sources/fiches/estate-b/sheet.pdf', B)
    put(tmp, 'sources/fiches/estate-c/same.pdf', A)
    put(tmp, 'sources/fiches/estate-d/same.pdf', A)
    put(tmp, 'sources/pages/estate-e/2020__page.txt', b'page')
    put(tmp, 'sources/fiches/pages/estate-f/both.txt', b'one')
    put(tmp, 'sources/pages/estate-f/both.txt', b'two')
    put(tmp, 'sources/fiches/estate-g/Upper-Case.pdf', b'case')

    a = PV.resolve('estate-a', 'sheet.pdf', tmp)
    says('1. exact folder: the row\'s own file',
         a.rel == 'fiches/estate-a/sheet.pdf', a.rel)
    b = PV.resolve('estate-b', 'sheet.pdf', tmp)
    says('2. same filename, other folder: that folder\'s file',
         b.rel == 'fiches/estate-b/sheet.pdf', b.rel)
    says('3. same filename, different bytes: different hashes',
         a.sha256 == sha(A) and b.sha256 == sha(B) and a.sha256 != b.sha256)
    c = PV.resolve('estate-c', 'same.pdf', tmp)
    d = PV.resolve('estate-d', 'same.pdf', tmp)
    says('4. same filename, same bytes: own paths, one hash',
         c.rel != d.rel and c.sha256 == d.sha256, '%s | %s' % (c.rel, d.rel))
    e = PV.resolve('pages/estate-e', '2020__page.txt', tmp)
    says('5. a crawled page resolves under sources/pages/',
         e.rel == 'pages/estate-e/2020__page.txt', e.rel)
    says('6. a name in two places is ARTIFACT_AMBIGUOUS, not first-found',
         failure(lambda: PV.resolve('pages/estate-f', 'both.txt', tmp))
         == 'ARTIFACT_AMBIGUOUS')
    says('7. a file in no folder of its own is ARTIFACT_NOT_FOUND, even '
         'when the name exists elsewhere',
         failure(lambda: PV.resolve('estate-z', 'sheet.pdf', tmp))
         == 'ARTIFACT_NOT_FOUND')
    says('8. another letter case is ARTIFACT_NAME_MISMATCH, on any OS',
         failure(lambda: PV.resolve('estate-g', 'upper-case.pdf', tmp))
         == 'ARTIFACT_NAME_MISMATCH')
    says('9. a trailing dot is ARTIFACT_NAME_MISMATCH',
         failure(lambda: PV.resolve('estate-g', 'Upper-Case.pdf.', tmp))
         == 'ARTIFACT_NAME_MISMATCH')
    says('10. a folder that climbs out of sources/ is refused',
         failure(lambda: PV.resolve('../..', 'x.pdf', tmp))
         == 'ARTIFACT_OUTSIDE_SOURCES')

    # ================================================= hash semantics
    print()
    print('HASH')
    says('11. read.sha256 is SHA-256 of the bytes on disk',
         a.sha256 == hashlib.sha256(open(a.path, 'rb').read()).hexdigest()
         and a.size == len(A))

    # A run in a throwaway repository, with the fixture tree in it.
    git(['init', '-q'], tmp)
    git(['config', 'user.email', 't@t'], tmp)
    git(['config', 'user.name', 't'], tmp)
    with open(os.path.join(tmp, '.gitignore'), 'w') as f:
        f.write('sources/\nevidence/\n')
    put(tmp, 'code.py', b'print(1)\n')
    git(['add', '.gitignore', 'code.py'], tmp)
    git(['commit', '-q', '-m', 'one'], tmp)

    run = PV.Run(4, tmp)
    stale = {'file': 'sheet.pdf', 'folder': 'estate-a',
             'sha1': 'deadbeef' * 5}
    st = run.stamp(stale, a)
    says('12. a stale manifest hash does not become the recorded hash',
         st['read']['sha256'] == sha(A) and st['manifest_sha1'] == stale['sha1'],
         'read %s, claim %s' % (st['read']['sha256'][:8],
                                st['manifest_sha1'][:8]))
    says('13. v4 rows carry no `observed` and no `commit` (v1-v3 meanings)',
         'observed' not in st and 'commit' not in st)
    leg = PV.Run(3, tmp).stamp(stale, a)
    says('14. below v4 the stamp is exactly the v1-v3 one',
         leg == {'commit': git(['rev-parse', '--short', 'HEAD'], tmp),
                 'observed': {'sha1': stale['sha1']}}, str(leg)[:40])

    art = PV.resolve('estate-b', 'sheet.pdf', tmp)
    put(tmp, 'sources/fiches/estate-b/sheet.pdf', B + b' rewritten')
    says('15. bytes changed under the reader: ARTIFACT_CHANGED_DURING_READ',
         failure(lambda: PV.confirm(art)) == 'ARTIFACT_CHANGED_DURING_READ')
    says('16. ...and Run.confirm records it and keeps nothing',
         run.confirm(art, {'file': 'sheet.pdf', 'folder': 'estate-b'}, {})
         is False and run.failures[-1]['code']
         == 'ARTIFACT_CHANGED_DURING_READ')

    # ========================================================= git
    print()
    print('GIT')
    head = git(['rev-parse', 'HEAD'], tmp)
    g = PV.git_state(tmp)
    says('17. clean tree: the full HEAD sha, dirty false, no status hash',
         g == {'commit': head, 'dirty': False, 'status_hash': None},
         head[:12])
    put(tmp, 'code.py', b'print(2)\n')
    g2 = PV.git_state(tmp)
    says('18. a modified tracked file: dirty, with a status hash',
         g2['dirty'] is True and g2['commit'] == head
         and len(g2['status_hash'] or '') == 64)
    put(tmp, 'code.py', b'print(3)\n')
    g3 = PV.git_state(tmp)
    says('19. different uncommitted code, different status hash',
         g3['status_hash'] != g2['status_hash'])
    put(tmp, 'code.py', b'print(2)\n')
    says('20. the same uncommitted code, the same status hash',
         PV.git_state(tmp)['status_hash'] == g2['status_hash'])
    put(tmp, 'code.py', b'print(1)\n')
    put(tmp, 'new_tool.py', b'x = 1\n')
    g4 = PV.git_state(tmp)
    says('21. an untracked file alone makes the tree dirty',
         g4['dirty'] is True)
    os.remove(os.path.join(tmp, 'new_tool.py'))
    put(tmp, 'code.py', b'print(4)\n')
    git(['commit', '-q', '-am', 'two'], tmp)
    g5 = PV.git_state(tmp)
    says('22. after a commit: the new commit, clean',
         g5['commit'] == git(['rev-parse', 'HEAD'], tmp)
         and g5['commit'] != head and g5['dirty'] is False)
    says('23. the recorded commit is the code that ran, not its parent',
         g5['commit'] != git(['rev-parse', 'HEAD~1'], tmp))
    # Phase 2.7: the evidence store is a run's output. One writer of a
    # pass must not make the tree dirty for the next.
    put(tmp, 'data/evidence/decisions-v4.jsonl', b'{}\n')
    says('23b. evidence written under data/evidence/ leaves the tree clean',
         PV.git_state(tmp)['dirty'] is False)
    put(tmp, 'code.py', b'print(7)\n')
    says('23c. ...while a code change beside it still makes it dirty',
         PV.git_state(tmp)['dirty'] is True)
    git(['checkout', '-q', '--', 'code.py'], tmp)
    os.remove(os.path.join(tmp, 'data', 'evidence', 'decisions-v4.jsonl'))

    # ================================================= the store, v4
    print()
    print('STORE')
    real_dir, real_index = ST.DIR, ST.INDEX
    ST.DIR = os.path.join(tmp, 'evidence', '')
    ST.INDEX = ST.DIR + 'index.json'
    try:
        run = PV.Run(4, tmp)
        sheet = {'file': 'sheet.pdf', 'folder': 'estate-a',
                 'sha1': 'deadbeef' * 5, 'estate': 'estate-a'}
        a = PV.resolve('estate-a', 'sheet.pdf', tmp)

        def decision(**over):
            r = {'artifact': 'sheet.pdf', 'kind': 'guard',
                 'ctx': {'estate': 'estate-a', 'wine': None,
                         'vintage': 2020, 'folder': 'estate-a',
                         'target_wine': 'Chateau A', 'target_role': 'grand',
                         'target_vintage': 2020},
                 'decision': 'ACCEPTED', 'code': 'ACCEPTED', 'raw': '',
                 'v': 4, 'reader': 'r' * 12, 'at': '2026-10-24'}
            r.update(run.stamp(sheet, a))
            r.update(over)
            return r

        n, f = PV.write(run, [decision()])
        says('24. a clean v4 run writes its decision', (n, f) == (1, 0))
        row = list(ST.iter_rows([4]))[0]
        says('25. ...with read.sha256 = the bytes, and the full commit',
             row['read']['sha256'] == sha(A)
             and row['git']['commit'] == git(['rev-parse', 'HEAD'], tmp))

        other = decision()
        other['git'] = {'commit': 'b' * 40, 'dirty': True,
                        'status_hash': 'c' * 64}
        other['read'] = dict(other['read'], sha256='d' * 64)
        other['at'] = '2030-01-01'
        says('26. identity ignores commit, hash and date',
             EV.row_key(other) == EV.row_key(decision()))
        says('27. ...so the same question rerun appends nothing',
             ST.append([other], 4) == 0)

        legacy = decision()
        legacy['observed'] = {'sha1': 'f' * 40}
        refusal = None
        try:
            ST.append([dict(legacy, artifact='legacy.pdf')], 4)
        except ST.RefusedAppend as e:
            refusal = str(e)
        says('28. v4 refuses a row carrying v1-v3 `observed`',
             bool(refusal), (refusal or '')[:30])

        run.fail(sheet, {'folder': 'estate-a'},
                 PV.ProvenanceFailure('ARTIFACT_NOT_FOUND', 'x'))
        fr = run.failures[-1]
        says('29. a provenance failure has no `decision` and no reader code',
             'decision' not in fr and fr['code'] in PV.FAILURES
             and fr['code'] not in set(c for _, c in EV.CODES))
        refusal = None
        try:
            ST.append([dict(fr, reader='r' * 12, v=4)], 4)
        except ST.RefusedAppend as e:
            refusal = str(e)
        says('30. the store will not take a failure as a decision',
             bool(refusal))
        bad = dict(fr, decision='REFUSED')
        refusal = None
        try:
            ST.append_failures([bad], 4)
        except ST.RefusedAppend as e:
            refusal = str(e)
        says('31. ...nor a "failure" that carries a verdict', bool(refusal))
        says('32. failures go to their own file',
             ST.append_failures([fr], 4) == 1
             and os.path.exists(ST.failures_path(4)))
        says('33. ...which iter_rows never returns',
             all(d.get('kind') != 'provenance_failure'
                 for d in ST.iter_rows()))
        says('34. a failure recorded twice is written once',
             ST.append_failures([fr], 4) == 0)

        put(tmp, 'code.py', b'print(5)\n')
        dirty = PV.Run(4, tmp)
        refusal = None
        try:
            PV.write(dirty, [decision(artifact='dirty.pdf',
                                      git=dirty.git)])
        except SystemExit as e:
            refusal = str(e)
        says('35. a dirty v4 run is refused without --allow-dirty',
             bool(refusal) and 'differs' in refusal)
        n, _ = PV.write(dirty, [decision(artifact='dirty.pdf',
                                         git=dirty.git)], allow_dirty=True)
        got = [d for d in ST.iter_rows([4]) if d['artifact'] == 'dirty.pdf']
        says('36. ...and with it, recorded as dirty with its status hash',
             n == 1 and got and got[0]['git']['dirty'] is True
             and len(got[0]['git']['status_hash']) == 64)
        put(tmp, 'code.py', b'print(6)\n')
        refusal = None
        try:
            PV.write(dirty, [decision(artifact='late.pdf', git=dirty.git)],
                     allow_dirty=True)
        except SystemExit as e:
            refusal = str(e)
        says('37. code changed during the run: nothing written',
             bool(refusal) and 'changed during the run' in refusal)
        says('38. the store verifies', ST.verify() == [])
    finally:
        ST.DIR, ST.INDEX = real_dir, real_index
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ================================================ the real evidence
print()
print('HISTORY')
says('39. v1/v2/v3 parts match their recorded hashes', ST.verify() == [],
     '; '.join(ST.verify())[:40])
try:
    out = subprocess.check_output(
        # The historical files, not the whole store: a new version is
        # appended beside them (v4, Phase 2.7) and must not count.
        ['git', 'diff', '--name-only', 'HEAD', '--',
         'data/evidence/decisions-v1.jsonl',
         'data/evidence/decisions-v2.jsonl',
         'data/evidence/decisions-v3.jsonl'],
        cwd=ROOT, stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    out = None
if out is None:
    print('MISSING  git unavailable')
else:
    says('40. the v1-v3 evidence files are unchanged from HEAD', out == '',
         out.replace('\n', ' ')[:40])
ix = json.load(io.open(ST.INDEX, encoding='utf-8'))
# Phase 2.5 wrote no v4; Phase 2.7 did. What has to hold for good is that
# writing v4 left v1-v3 exactly as Phase 2.5 found them.
try:
    old = json.loads(subprocess.check_output(
        ['git', 'show', '4370382:data/evidence/index.json'], cwd=ROOT,
        stderr=subprocess.DEVNULL))
    same = all(old['versions'][v]['parts'] == ix['versions'][v]['parts']
               for v in ('1', '2', '3'))
except Exception:
    same = False
says('41. v1/v2/v3 parts identical to Phase 2.5 (4370382)', same)

# ================================== the known same-name cases, for real
print()
print('THE SAME-NAME CASES (sources/)')
audit = ROOT + 'data/provenance-audit.jsonl'
rows = []
if os.path.exists(audit):
    with io.open(audit, encoding='utf-8') as f:
        f.readline()
        rows = [json.loads(l) for l in f]
if not os.path.isdir(ROOT + 'sources/fiches'):
    print('MISSING  sources/ (not in the repository)')
elif not rows:
    print('MISSING  data/provenance-audit.jsonl')
else:
    diff = [r for r in rows if r['bytes_differ']]
    same = [r for r in rows if r['class'] == 'old read another folder, '
                                             'same bytes']
    ok = 0
    for r in diff:
        art = PV.resolve(r['folder'], r['artifact'])
        ok += (art.sha256 == r['actual_sha256']
               and art.sha256 != r['old_sha256']
               and art.rel == r['new_path'])
    says('42. all %d different-bytes cases now read their own bytes'
         % len(diff), len(diff) == 48 and ok == 48, '%d/%d' % (ok, len(diff)))
    ok = sum(1 for r in same
             if PV.resolve(r['folder'], r['artifact']).rel == r['new_path'])
    says('43. the %d same-bytes cases resolve to their own folder'
         % len(same), len(same) == 869 and ok == 869)
    says('44. none of the 917 is ambiguous', not any(
        r['new_failure'] == 'ARTIFACT_AMBIGUOUS' for r in rows))
    says('45. no decision identity changes', not any(
        r['identity_changes'] for r in rows))

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
