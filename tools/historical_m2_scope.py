"""What later phases are allowed to have changed in data/model/, named exactly.

Suites written before M2 assert the model did not change since their own baseline commit. Two
later phases change it, each in a named way, and nothing else may:

M2 (document dates) only adds:

    document/artifact-dates.jsonl   ArtifactDate STATED_IN_TEXT rows
    cross/provenance.jsonl          their DOCUMENT provenance (actor tools/extract-document-dates.py)
    manifest.json                   those files' counts and hashes, one M6 stat

M3.2 (existing-data recovery) gives a figure its own held sheet as source:

    cross/provenance.jsonl          DOCUMENT provenance by tools/m32-recovery.py, added
    canonical/values.jsonl          a row's provenance (to that DOCUMENT) and status (to SOURCED) only
    observation/observations.jsonl  a row's provenance (to that DOCUMENT) only
    manifest.json                   those files' counts and hashes; M7 status counts moved from
                                    LEGACY_RECORD_SOURCE_ONLY to SOURCED, totals unchanged

model_changes_are_m2_only(before) - the name is kept for its callers - holds when every other model
file is byte-identical to `before`, and every difference in the files above is one of these.
"""
import json
import re
import subprocess

import migration_lib as L

M2_FILES = ('cross/provenance.jsonl', 'document/artifact-dates.jsonl', 'manifest.json')
M32_FILES = ('canonical/values.jsonl', 'observation/observations.jsonl',      # M3.2A
             'document/placements.jsonl', 'document/locators.jsonl',        # M3.2B
             'derived/source-documents.json')                               # M3.2B, its index
M32B_STAT = 'M3.2B placements (recovered addresses)'
ALLOWED = set(M2_FILES) | set(M32_FILES)
M2_ACTOR = 'tools/extract-document-dates.py'
M32_ACTOR = 'tools/m32-recovery.py'
M2_STAT = 'document dates (historical M2 audit)'


def _git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode('utf-8')


def _lines(before, rel):
    old = _git('show', '%s:data/model/%s' % (before, rel))
    new = open(L.MODEL + rel, encoding='utf-8').read()
    return old, new


def _m32_document(prov, pid):
    p = prov.get(pid) or {}
    return p.get('kind') == 'DOCUMENT' and p.get('actor') == M32_ACTOR


def _sourced_moved(stats):
    """M7 stats with each '(SOURCED)' count folded back into its '(LEGACY_RECORD_SOURCE_ONLY)' one."""
    out = {}
    for st, kv in stats.items():
        kv = dict(kv)
        b = dict(kv['backfill']) if isinstance(kv.get('backfill'), dict) else None
        if b is not None:
            for k in [k for k in b if k.endswith('(SOURCED)')]:
                base = re.sub(r'\(SOURCED\)$', '(LEGACY_RECORD_SOURCE_ONLY)', k)
                b[base] = b.get(base, 0) + b.pop(k)
            kv['backfill'] = b
        out[st] = kv
    return out


M32_BEFORE = 'eb3772e'           # the state before M3.2
M32_AUDIT = 'data/audit/m32-recovery-candidates.jsonl'


def is_m32_source(p):
    """A provenance row M3.2 wrote: a figure's own held sheet, proven from its labelled text."""
    return (p.get('kind') == 'DOCUMENT' and p.get('actor') == M32_ACTOR
            and str((p.get('code_state') or {}).get('stream', '')).startswith('M3.2') and bool(p.get('derived_from')))


def m32_applied():
    """{(record key, field)} the M3.2 audit applied (its APPLY_PROVENANCE rows)."""
    out = set()
    for line in open(L.ROOT + M32_AUDIT, encoding='utf-8'):
        r = json.loads(line)
        if r['disposition'] == 'APPLY_PROVENANCE':
            out.add((r['target']['record'], r['target']['field']))
    return out


def unpack_figure_sources(text):
    d = json.loads(re.search(r'window\.BDX_FIGURE_SRC = (.*);\n', text).group(1))
    return {k: {f: d['docs'][i] for f, i in r.items()} for k, r in d['rec'].items()}


def m32b_urls():
    """The addresses M3.2B placed (its APPLY_PLACEMENT rows' first-party URLs)."""
    out = set()
    for line in open(L.ROOT + M32_AUDIT, encoding='utf-8'):
        r = json.loads(line)
        if r['disposition'] == 'APPLY_PLACEMENT':
            out.update(f['url'] for f in r['source']['fetched'])
    return out


def figure_sources_change_is_m32_only(before=M32_BEFORE):
    """data/app/figure-sources.js differs from `before` by exactly M3.2's work:
    M3.2A  each recovered figure present with its own source ({n} or {n, u}), where none was;
    M3.2B  a figure whose own file had no address gains one ({n} -> {n, u}, the same n), and that
           address is one M3.2B placed.
    Nothing else added, removed or changed."""
    now = unpack_figure_sources(open(L.ROOT + 'data/app/figure-sources.js', encoding='utf-8').read())
    old = unpack_figure_sources(_git('show', '%s:data/app/figure-sources.js' % before))
    applied = m32_applied()
    placed = m32b_urls()
    for rec, field in applied:
        s = now.get(rec, {}).get(field)
        assert s and set(s) <= {'n', 'u'} and s.get('n'), 'recovered figure without its source: %s %s' % (rec, field)
        assert field not in old.get(rec, {}), 'a recovered figure already had a source: %s %s' % (rec, field)
    rest = {}
    for rec, fs in now.items():
        kept = {}
        for f, s in fs.items():
            if (rec, f) in applied:
                continue
            o = old.get(rec, {}).get(f)
            if o is not None and o != s and set(o) == {'n'} and set(s) == {'n', 'u'} and s['n'] == o['n'] \
                    and s['u'] in placed:
                s = o                                    # M3.2B: the address of exactly these bytes
            kept[f] = s
        if kept:
            rest[rec] = kept
    assert rest == old, 'figure-sources.js changed beyond the M3.2 recovered figures and addresses'
    return True


def app_files_changed_beyond_m32(changed):
    """The changed data/app paths, minus figure-sources.js when its change is exactly M3.2's."""
    rest = [f for f in changed if not f.endswith('data/app/figure-sources.js')]
    if len(rest) < len(changed):
        figure_sources_change_is_m32_only()
    return rest


def model_changes_are_m2_only(before):
    changed = [f[len('data/model/'):] for f in _git('diff', '--name-only', before, '--', 'data/model').split()]
    assert set(changed) <= ALLOWED, 'the model changed beyond M2 and M3.2: %s' % sorted(set(changed) - ALLOWED)
    prov = {json.loads(x)['id']: json.loads(x) for x in open(L.MODEL + 'cross/provenance.jsonl', encoding='utf-8')}
    for rel, check in (('document/artifact-dates.jsonl',
                        lambda r: r['kind'] == 'STATED_IN_TEXT' and r['value']['axis'] == 'CALENDAR'),
                       ('cross/provenance.jsonl',
                        lambda r: r['kind'] == 'DOCUMENT' and r['actor'] in (M2_ACTOR, M32_ACTOR))):
        if rel not in changed:
            continue
        old, new = _lines(before, rel)
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, '%s: %d rows changed or removed' % (rel, len(o - n))
        bad = [r for r in (json.loads(x) for x in n - o) if not check(r)]
        assert not bad, '%s: an added row is not M2\'s or M3.2\'s: %s' % (rel, bad[:1])
    # M3.2B: URL placements (and their locators) added, each with an M3.2B provenance
    for rel in ('document/placements.jsonl', 'document/locators.jsonl'):
        if rel not in changed:
            continue
        old, new = _lines(before, rel)
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, '%s: %d rows changed or removed' % (rel, len(o - n))
        for x in n - o:
            r = json.loads(x)
            if rel.endswith('placements.jsonl'):
                p = prov.get(r['provenance']) or {}
                assert r['locator']['kind'] == 'URL' and p.get('actor') == M32_ACTOR and \
                    (p.get('code_state') or {}).get('stream') == 'M3.2B', ('not an M3.2B placement', r['id'])
            else:
                assert r['kind'] == 'URL', ('not a URL locator', r)
    # M3.2B's derived index: a source may only gain artifacts that M3.2B placed on its host
    if 'derived/source-documents.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'derived/source-documents.json'))
        placed = set()
        for x in open(L.MODEL + 'document/placements.jsonl', encoding='utf-8'):
            r = json.loads(x)
            if (prov.get(r['provenance'], {}).get('code_state') or {}).get('stream') == 'M3.2B':
                placed.add(r['artifact'])
        for k in set(old) | set(new):
            o, n = set(old.get(k, [])), set(new.get(k, []))
            assert o <= n and n - o <= placed, ('derived/source-documents.json', k, sorted(o - n), sorted(n - o - placed))
    for rel, key, fields in (('canonical/values.jsonl', lambda r: (r['subject'], r['field']), {'provenance', 'status'}),
                             ('observation/observations.jsonl', lambda r: r['id'], {'provenance'})):
        if rel not in changed:
            continue
        old, new = _lines(before, rel)
        o = {key(json.loads(x)): json.loads(x) for x in old.splitlines()}
        n = {key(json.loads(x)): json.loads(x) for x in new.splitlines()}
        assert o.keys() == n.keys(), '%s: rows added or removed' % rel
        for k in o:
            if o[k] == n[k]:
                continue
            diff = {f for f in set(o[k]) | set(n[k]) if o[k].get(f) != n[k].get(f)}
            assert diff <= fields, '%s %s: %s changed' % (rel, k, sorted(diff - fields))
            assert _m32_document(prov, n[k]['provenance']), '%s %s: provenance is not an M3.2 DOCUMENT' % (rel, k)
            assert prov[n[k]['provenance']]['derived_from'] == [o[k]['provenance']], '%s %s: history lost' % (rel, k)
            if 'status' in diff:
                assert n[k]['status'] == 'SOURCED', (rel, k, n[k]['status'])
    if 'manifest.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'manifest.json'))
        for k in set(old) | set(new):
            if k == 'files':
                diff = {f for f in set(old[k]) | set(new[k]) if old[k].get(f) != new[k].get(f)}
                assert diff <= ALLOWED - {'manifest.json'}, 'manifest files: %s' % sorted(diff)
            elif k == 'stats':
                a_all, b_all = _sourced_moved(old[k]), _sourced_moved(new[k])
                for st in set(a_all) | set(b_all):
                    a, b = dict(a_all.get(st, {})), dict(b_all.get(st, {}))
                    if st == 'M6':
                        for s in (M2_STAT, M32B_STAT):
                            a.pop(s, None)
                            b.pop(s, None)
                    assert a == b, 'manifest stats %s changed' % st
            else:
                assert old.get(k) == new.get(k), 'manifest %s changed' % k
    return changed
