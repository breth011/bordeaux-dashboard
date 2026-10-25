"""What historical model M2 (document dates) is allowed to have changed in data/model/.

Suites written before M2 assert the model did not change since their own
baseline commit. M2 adds to exactly three files, and only adds:

    document/artifact-dates.jsonl   ArtifactDate STATED_IN_TEXT rows
    cross/provenance.jsonl          their DOCUMENT provenance
    manifest.json                   those two files' counts and hashes, one stat

model_changes_are_m2_only(before) holds when every other model file is
byte-identical to `before`, every row there before is still there byte for
byte, every added row is M2's, and the manifest differs only as above.
"""
import json
import subprocess

import migration_lib as L

M2_FILES = ('cross/provenance.jsonl', 'document/artifact-dates.jsonl', 'manifest.json')
M2_ACTOR = 'tools/extract-document-dates.py'
M2_STAT = 'document dates (historical M2 audit)'


def _git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def _lines(before, rel):
    old = _git('show', '%s:data/model/%s' % (before, rel))
    new = open(L.MODEL + rel, encoding='utf-8').read()
    return old, new


def model_changes_are_m2_only(before):
    changed = [f[len('data/model/'):] for f in _git('diff', '--name-only', before, '--', 'data/model').split()]
    assert set(changed) <= set(M2_FILES), 'the model changed beyond M2: %s' % sorted(set(changed) - set(M2_FILES))
    for rel, check in (('document/artifact-dates.jsonl',
                        lambda r: r['kind'] == 'STATED_IN_TEXT' and r['value']['axis'] == 'CALENDAR'),
                       ('cross/provenance.jsonl',
                        lambda r: r['kind'] == 'DOCUMENT' and r['actor'] == M2_ACTOR)):
        if rel not in changed:
            continue
        old, new = _lines(before, rel)
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, '%s: %d rows changed or removed' % (rel, len(o - n))
        bad = [r for r in (json.loads(x) for x in n - o) if not check(r)]
        assert not bad, '%s: an added row is not M2\'s: %s' % (rel, bad[:1])
    if 'manifest.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'manifest.json'))
        for k in set(old) | set(new):
            if k == 'files':
                diff = {f for f in set(old[k]) | set(new[k]) if old[k].get(f) != new[k].get(f)}
                assert diff <= set(M2_FILES[:2]), 'manifest files: %s' % sorted(diff)
            elif k == 'stats':
                for st in set(old[k]) | set(new[k]):
                    a, b = dict(old[k].get(st, {})), dict(new[k].get(st, {}))
                    b.pop(M2_STAT, None) if st == 'M6' else None
                    assert a == b, 'manifest stats %s changed' % st
            else:
                assert old.get(k) == new.get(k), 'manifest %s changed' % k
    return changed
