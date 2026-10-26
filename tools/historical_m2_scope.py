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

M3.4B (audited existing-evidence mappings) links an accepted document to its vintage:

    document/attributions.jsonl     Attribution rows added, method DOCUMENT_TEXT, status ACCEPTED, each
                                    exactly an APPLIED row of data/audit/m3.4b-mapping-application.jsonl
    cross/provenance.jsonl          their DOCUMENT provenance (actor tools/m34b-apply.py, stream M3.4B)
    derived/vintage-documents.json  a vintage gains only the artifacts those attributions link to it
    manifest.json                   those files' counts and hashes, one M6 stat

M3.5 (held-document review) links a reviewed held document to the vintage its own title establishes:

    document/attributions.jsonl     Attribution rows added, method DOCUMENT_TEXT, status ACCEPTED, each
                                    exactly an eligible row of data/audit/m3.5-held-document-review.jsonl
    cross/provenance.jsonl          their DOCUMENT provenance (actor tools/m35-review.py, stream M3.5)
    derived/vintage-documents.json  a vintage gains only the artifacts those attributions link to it
    manifest.json                   those files' counts and hashes, one M6 stat

model_changes_are_m2_only(before) - the name is kept for its callers - holds when every other model
file is byte-identical to `before`, and every difference in the files above is one of these.
"""
import hashlib
import json
import re
import subprocess

import migration_lib as L

M2_FILES = ('cross/provenance.jsonl', 'document/artifact-dates.jsonl', 'manifest.json')
M32_FILES = ('canonical/values.jsonl', 'observation/observations.jsonl',      # M3.2A
             'document/placements.jsonl', 'document/locators.jsonl',        # M3.2B
             'derived/source-documents.json',                               # M3.2B, its index
             'reconciliation/reconciliations.jsonl')                        # M3.2D
M32B_STAT = 'M3.2B placements (recovered addresses)'
M32D_STAT = 'M3.2D recovered values'
M34B_FILES = ('document/attributions.jsonl', 'derived/vintage-documents.json')
M34B_STAT = 'M3.4B audited mappings'
M35_STAT = 'M3.5 held-document attributions'
M35_ACTOR = 'tools/m35-review.py'
M35_REVIEW = 'data/audit/m3.5-held-document-review.jsonl'
M36B_STAT = 'M3.6B audited web-page mappings'
M36B_ACTOR = 'tools/m36b-apply.py'
M36B_MAPPINGS = 'data/audit/m3.6b-mapping-application.jsonl'
M36B_CORRECTIONS = 'data/audit/m3.6b-correction-application.jsonl'
M36B_EVIDENCE_VERSION = 6
ALLOWED = set(M2_FILES) | set(M32_FILES) | set(M34B_FILES)
M2_ACTOR = 'tools/extract-document-dates.py'
M32_ACTOR = 'tools/m32-recovery.py'
M34B_ACTOR = 'tools/m34b-apply.py'
M34B_MANIFEST = 'data/audit/m3.4b-mapping-application.jsonl'
M2_STAT = 'document dates (historical M2 audit)'


def m34b_applied():
    """(attribution id, artifact, estate, wine, vintage) of every APPLIED row of the M3.4B manifest."""
    try:
        rows = L.jsonl_lines(L.ROOT + M34B_MANIFEST)
    except FileNotFoundError:
        return set()
    return {(r['attribution'], r['artifact'], r['estate'], r['wine'], r['vintage_id']) for r in rows
            if r['result'] == 'APPLIED'}


def m35_applied():
    """(attribution id, artifact, estate, wine, vintage) of every eligible row of the M3.5 review."""
    try:
        rows = L.jsonl_lines(L.ROOT + M35_REVIEW)
    except FileNotFoundError:
        return set()
    return {(r['attribution'], r['artifact'], r['estate'], r['wine'], r['vintage_id']) for r in rows if r['eligible']}


def m36b_applied():
    """(attribution id, artifact, estate, wine, vintage) of every APPLIED row of the M3.6B mapping manifest."""
    try:
        rows = L.jsonl_lines(L.ROOT + M36B_MAPPINGS)
    except FileNotFoundError:
        return set()
    return {(r['attribution'], r['artifact'], r['estate'], r['wine'], r['vintage_id']) for r in rows
            if r['result'] == 'APPLIED'}


def is_m36b_attribution(a, prov):
    p = prov.get(a.get('provenance')) or {}
    return (a.get('method') == 'DOCUMENT_TEXT' and a.get('status') == 'ACCEPTED' and a.get('role') == 'FIRST'
            and p.get('kind') == 'DOCUMENT' and p.get('actor') == M36B_ACTOR
            and (p.get('code_state') or {}).get('stream') == 'M3.6B'
            and (a['id'], a['artifact'], a.get('estate'), a.get('wine'), a.get('vintage')) in m36b_applied())


def is_m35_attribution(a, prov):
    p = prov.get(a.get('provenance')) or {}
    return (a.get('method') == 'DOCUMENT_TEXT' and a.get('status') == 'ACCEPTED' and a.get('role') in ('FIRST', 'SECOND')
            and p.get('kind') == 'DOCUMENT' and p.get('actor') == M35_ACTOR
            and (p.get('code_state') or {}).get('stream') == 'M3.5'
            and (a['id'], a['artifact'], a.get('estate'), a.get('wine'), a.get('vintage')) in m35_applied())


def is_m34b_attribution(a, prov):
    p = prov.get(a.get('provenance')) or {}
    return (a.get('method') == 'DOCUMENT_TEXT' and a.get('status') == 'ACCEPTED' and a.get('role') == 'FIRST'
            and p.get('kind') == 'DOCUMENT' and p.get('actor') == M34B_ACTOR
            and (p.get('code_state') or {}).get('stream') == 'M3.4B'
            and (a['id'], a['artifact'], a.get('estate'), a.get('wine'), a.get('vintage')) in m34b_applied())


def legacy_attributions(rows, prov):
    """The manifest's attributions: every row but M3.4B's, which must each be exactly an applied mapping."""
    out = []
    for a in rows:
        actor = (prov.get(a['provenance']) or {}).get('actor')
        if actor == M34B_ACTOR:
            assert is_m34b_attribution(a, prov), ('an M3.4B attribution not in its manifest', a['id'])
            continue
        if actor == M35_ACTOR:
            assert is_m35_attribution(a, prov), ('an M3.5 attribution not in its review', a['id'])
            continue
        if actor == M36B_ACTOR:
            assert is_m36b_attribution(a, prov), ('an M3.6B attribution not in its manifest', a['id'])
            continue
        out.append(a)
    return out


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


def is_m32d(p):
    """A provenance row of a value M3.2D added (a recovered harvested figure, or its reconciliation)."""
    return p.get('actor') == M32_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.2D'


def is_m32d_observation(o):
    return (o.get('extraction') or {}).get('mapping') == 'm32-recovery/1'


def is_m32d_reconciliation(r):
    return r.get('resolver') == M32_ACTOR and r.get('rule') in ('ONLY_CANDIDATE', 'UNANIMOUS')


def m32d_applied():
    """{(vintage, field)} the M3.2 audit's APPLY_VALUE rows added to the model."""
    out = set()
    for line in open(L.ROOT + M32_AUDIT, encoding='utf-8'):
        r = json.loads(line)
        if r['disposition'] == 'APPLY_VALUE':
            out.add((r['target']['subject'], r['target']['field']))
    return out


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
                        lambda r: (r['kind'] == 'DOCUMENT' and r['actor'] in (M2_ACTOR, M32_ACTOR)) or
                        (r['kind'] == 'DOCUMENT' and r['actor'] == M34B_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.4B') or
                        (r['kind'] == 'DOCUMENT' and r['actor'] == M35_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.5') or
                        (r['kind'] == 'DOCUMENT' and r['actor'] == M36B_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.6B') or
                        (r['kind'] == 'DERIVATION' and r['actor'] == M32_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.2D')),
                       ('reconciliation/reconciliations.jsonl',
                        lambda r: r['resolver'] == M32_ACTOR and r['rule'] in ('ONLY_CANDIDATE', 'UNANIMOUS')
                        and r['status'] in ('SINGLE', 'AGREED') and 'dispositions' not in r)):
        if rel not in changed:
            continue
        old, new = _lines(before, rel)
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, '%s: %d rows changed or removed' % (rel, len(o - n))
        bad = [r for r in (json.loads(x) for x in n - o) if not check(r)]
        assert not bad, '%s: an added row is not M2\'s or M3.2\'s: %s' % (rel, bad[:1])
    # M3.4B: attributions added, each exactly an applied mapping; a vintage gains only their artifacts
    if 'document/attributions.jsonl' in changed:
        old, new = _lines(before, 'document/attributions.jsonl')
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, 'document/attributions.jsonl: %d rows changed or removed' % len(o - n)
        for x in n - o:
            a = json.loads(x)
            assert is_m34b_attribution(a, prov) or is_m35_attribution(a, prov) or is_m36b_attribution(a, prov),                 ('not an M3.4B, M3.5 or M3.6B attribution', a['id'])
    if 'derived/vintage-documents.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'derived/vintage-documents.json'))
        linked = {(r[4], r[1]) for r in m34b_applied() | m35_applied() | m36b_applied()}
        for k in set(old) | set(new):
            o, n = set(old.get(k, [])), set(new.get(k, []))
            assert o <= n and {(k, a) for a in n - o} <= linked, ('derived/vintage-documents.json', k, sorted(o - n))
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
        assert set(o) <= set(n), '%s: rows removed' % rel
        for k in set(n) - set(o):
            # M3.2D: a recovered value or the observation that states it, each with its M3.2D provenance
            p = prov.get(n[k]['provenance']) or {}
            assert p.get('actor') == M32_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.2D', \
                '%s %s: an added row is not M3.2D\'s' % (rel, k)
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
                    for s in (M2_STAT, M32B_STAT, M32D_STAT, M34B_STAT, M35_STAT, M36B_STAT):
                        a.pop(s, None)
                        b.pop(s, None)
                    assert a == b, 'manifest stats %s changed' % st
            else:
                assert old.get(k) == new.get(k), 'manifest %s changed' % k
    return changed


REGISTER = 'data/audit/data-gap-register.jsonl'
LINKING_PHASES = ('M3.4B', 'M3.5', 'M3.6B')


def register_changes_are_m34b_only(before):
    """The gap register as at `before`, but for the resolution records of the later document-linking
    phases (M3.4B, M3.5): every gap kept with its id and every field, a gap's `resolution` gaining only
    `by` entries of those phases (its counts moved by those entries' items), the ranks M3.1 gave unchanged."""
    old = {r['gap_id']: r for r in (json.loads(x) for x in _git('show', '%s:%s' % (before, REGISTER)).splitlines())}
    new = {r['gap_id']: r for r in L.jsonl_lines(L.ROOT + REGISTER)}
    assert set(old) == set(new), 'a gap was added or removed'
    for g, n in new.items():
        o = old[g]
        assert {k: v for k, v in o.items() if k != 'resolution'} == {k: v for k, v in n.items() if k != 'resolution'}, g
        if o.get('resolution') == n.get('resolution'):
            continue
        ob = (o.get('resolution') or {}).get('by', [])
        nb = n['resolution']['by']
        added = [b for b in nb if b not in ob]
        assert all(b in nb for b in ob) and added and all(b['phase'] in LINKING_PHASES for b in added), (g, added)
        res = n['resolution']
        assert res['affected_before'] == n['affected_count'] and \
            res['recovered'] == sum(b['items'] for b in nb) and res['affected_after'] == res['affected_before'] - res['recovered'], g
    return True


# -- the evidence store: M3.6B's decider version --------------------------------------------------
# Suites written before M3.6B assert the store holds v1-v5 only, 177,127 decisions, unchanged since their
# baseline. M3.6B adds decider version 6 beside them (the store grows by design: a new version and its
# index entry). These name that addition exactly; every assertion about v1-v5 stands unchanged.

def m36b_evidence_keys():
    """The row keys M3.6B's manifests say it wrote to v6: the mappings' decisions and the corrections'."""
    out = set()
    for path, field in ((M36B_MAPPINGS, 'evidence_decision'), (M36B_CORRECTIONS, 'superseded_by')):
        try:
            rows = L.jsonl_lines(L.ROOT + path)
        except FileNotFoundError:
            continue
        out |= {r[field] for r in rows if r['result'] == 'APPLIED'}
    return out


def m36b_evidence_rows():
    """v6, verified to be exactly M3.6B's decisions: every row its manifests name, and no other."""
    import evidence_store as ST
    import mig_m6_provenance as M6
    if M36B_EVIDENCE_VERSION not in ST.versions():
        return []
    rows = list(ST.iter_rows([M36B_EVIDENCE_VERSION]))
    keys = [M6.row_key(d) for d in rows]
    assert len(keys) == len(set(keys)) and set(keys) == m36b_evidence_keys(), 'v6 is not exactly M3.6B\'s decisions'
    assert all(d.get('kind') in ('web_page_review', 'correction') for d in rows), 'a v6 row of another kind'
    return rows


def evidence_versions_before_m36b():
    """The store's versions, M3.6B's v6 verified and set aside."""
    import evidence_store as ST
    m36b_evidence_rows()
    return [v for v in ST.versions() if v != M36B_EVIDENCE_VERSION]


def evidence_rows_before_m36b():
    """How many decisions the store holds besides M3.6B's v6."""
    import evidence_store as ST
    return sum(1 for _ in ST.iter_rows(evidence_versions_before_m36b()))


def evidence_changes_are_m36b_only(before):
    """data/evidence as at `before`, but for M3.6B: v1-v5, their files and index entries byte for byte; v6
    exactly M3.6B's decisions; no other file. True, or an assertion error saying what else changed."""
    changed = set(_git('diff', '--name-only', before, '--', 'data/evidence').split())
    untracked = set(_git('ls-files', '--others', '--exclude-standard', '--', 'data/evidence').split())
    assert (changed | untracked) <= {'data/evidence/index.json', 'data/evidence/decisions-v6.jsonl'}, \
        'the evidence store changed beyond M3.6B: %s' % sorted(changed | untracked)
    if 'data/evidence/index.json' in changed:
        old = json.loads(_git('show', '%s:data/evidence/index.json' % before))
        new = json.load(open(L.ROOT + 'data/evidence/index.json', encoding='utf-8'))
        v = str(M36B_EVIDENCE_VERSION)
        assert {k: x for k, x in new.items() if k != 'versions'} == {k: x for k, x in old.items() if k != 'versions'}
        assert {k: x for k, x in new['versions'].items() if k != v} == \
            {k: x for k, x in old['versions'].items() if k != v}, 'a historical version changed in the index'
    m36b_evidence_rows()
    return True


def protected_group(name):
    """migration_lib.group_hashes(name) for Phase 4's protected groups, with M3.6B's evidence version 6 named
    and set aside: every other group exactly as group_hashes gives it; 'evidence' as v1-v5's files, byte for
    byte, and index.json as the store serialises it without the v6 entry - which reproduces the old index
    only if nothing else in it changed. v6 must be exactly M3.6B's decisions; no v6 failure file may exist."""
    import evidence_store as ST
    if name != 'evidence':
        return L.group_hashes(name)
    v = M36B_EVIDENCE_VERSION
    files = {}
    for p in L.GROUPS['evidence']():
        r = L.rel(p)
        base = r.rsplit('/', 1)[-1]
        assert base != 'provenance-failures-v%d.jsonl' % v, 'a v6 provenance failure'
        if base == 'decisions-v%d.jsonl' % v or base.startswith('decisions-v%d.part' % v):
            continue
        if base == 'index.json':
            ix = json.load(open(p, encoding='utf-8'))
            if str(v) in ix.get('versions', {}):
                m36b_evidence_rows()
                del ix['versions'][str(v)]
            b = (json.dumps(ix, ensure_ascii=False, indent=1, sort_keys=True) + '\n').encode('utf-8')
            files[r] = hashlib.sha256(b).hexdigest()
            continue
        files[r] = L.sha256_file(p)
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'files': files, 'digest': digest}
