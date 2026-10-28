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
import collections
import functools
import hashlib
import json
import os
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
# M3.6E: the historical Cuvée Mongravey evidence decisions corrected, as decider version 7
M36E_MANIFEST = 'data/audit/m3.6e-cuvee-historical-corrections.jsonl'
M36E_EVIDENCE_VERSION = 7
# M3.6H: the one Cuvée Mongravey acceptance M3.6E did not see (found by M3.6G), corrected as decider version 8
M36H_MANIFEST = 'data/audit/m3.6h-cuvee-2015-correction.jsonl'
M36H_EVIDENCE_VERSION = 8
# M3.10B: the four documents M3.10A registered, accepted as evidence (decider version 9) and attributed
M310B_ACTOR = 'tools/m310b-accept.py'
M310B_MANIFEST = 'data/audit/m3.10b-evidence-decisions.jsonl'
M310B_EVIDENCE_VERSION = 9
M310B_STAT = 'M3.10B accepted external documents'
# M3.10C: Durfort-Vivens' nine values from M3.10B's accepted documents (observations, reconciliations, values)
M310C_ACTOR = 'tools/m310c-values.py'
M310C_MANIFEST = 'data/audit/m3.10c-value-application.jsonl'
M310C_STAT = 'M3.10C Durfort-Vivens values'
M310C_FILES = ('canonical/values.jsonl', 'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl',
               'cross/provenance.jsonl', 'manifest.json')
# V1, the vintage-creation mechanism (tools/apply-vintage-creation-manifest.py): one exception for every vintage it
# ever creates - a grand vin's vintage shell (M5) and its existence attributions (M6) on their own provenance. A
# vintage row carries no provenance, so the model manifest's M5 stat, which the mechanism alone writes, names them.
V1_ACTOR = 'tools/apply-vintage-creation-manifest.py'
V1_STREAM = 'vintage-creation'
V1_VINTAGE_STAT = 'vintage-creation manifest vintages'
V1_ATTRIBUTION_STAT = 'vintage-creation manifest attributions'
V1_FILES = ('identity/vintages.jsonl', 'document/attributions.jsonl', 'cross/provenance.jsonl',
            'derived/wine-vintages.json', 'derived/vintage-documents.json', 'manifest.json')
# M3.6D: one canonical wine (Cuvée Mongravey), its names, its estate relationship and its descriptor
M36D_ACTOR = 'tools/m36d-cuvee.py'
M36D_MANIFEST = 'data/audit/m3.6d-cuvee-mongravey.jsonl'
M36D_STAT = 'M3.6D canonical wines'
M36D_FILES = ('identity/wines.jsonl', 'identity/names.jsonl', 'identity/identity-map.jsonl',
              'state/estate-wine.jsonl', 'state/wine-descriptors.jsonl', 'derived/estate-wines.json')
# M3.6F: the wine's vintages from its held technical sheets, and their class-A values (months, new oak)
M36F_ACTOR = 'tools/m36f-vintages.py'
M36F_MANIFEST = 'data/audit/m3.6f-cuvee-vintages.jsonl'
M36F_STATS = ('M3.6F Cuvée vintages', 'M3.6F Cuvée values')
M36F_FILES = ('identity/vintages.jsonl', 'observation/observations.jsonl', 'reconciliation/reconciliations.jsonl',
              'canonical/values.jsonl', 'derived/wine-vintages.json')
CUVEE_ACTORS = {M36D_ACTOR: 'M3.6D', M36F_ACTOR: 'M3.6F'}  # the later Cuvée Mongravey decisions, set aside alike
CUVEE_FILES = M36D_FILES + tuple(f for f in M36F_FILES if f not in M36D_FILES)
# M3.10A: four externally acquired documents registered as artifacts, each with its URL placement - no
# evidence decision, attribution, observation or value
M310A_ACTOR = 'tools/m310a-register.py'
M310A_MANIFEST = 'data/audit/m3.10a-external-artifact-registration.jsonl'
M310A_STAT = 'M3.10A placements (externally acquired documents)'
M310A_ARTIFACT_STAT = 'artifacts (manifest sha1, sha256 only)'      # M2's count, which the registrations raise
M310A_FILES = ('identity/artifacts.jsonl', 'identity/identity-map.jsonl', 'document/placements.jsonl',
               'document/locators.jsonl', 'cross/provenance.jsonl', 'manifest.json')
ALLOWED = set(M2_FILES) | set(M32_FILES) | set(M34B_FILES) | set(M36D_FILES) | set(M36F_FILES) | set(M310A_FILES)
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


def m310b_applied():
    """(attribution id, artifact, estate, wine, vintage) of every APPLIED decision row of the M3.10B manifest."""
    try:
        rows = L.jsonl_lines(L.ROOT + M310B_MANIFEST)
    except FileNotFoundError:
        return set()
    return {(r['attribution'], r['artifact'], r['estate'], r['wine'], r['vintage_id']) for r in rows
            if r['record'] == 'decision' and r['result'] == 'APPLIED'}


def is_m310b_attribution(a, prov):
    p = prov.get(a.get('provenance')) or {}
    return (p.get('kind') == 'DOCUMENT' and p.get('actor') == M310B_ACTOR
            and (p.get('code_state') or {}).get('stream') == 'M3.10B'
            and (a['id'], a['artifact'], a.get('estate'), a.get('wine'), a.get('vintage')) in m310b_applied())


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
        if actor == M310B_ACTOR:
            assert is_m310b_attribution(a, prov), ('an M3.10B attribution not in its manifest', a['id'])
            continue
        if actor == V1_ACTOR:
            assert is_v1_row('document/attributions.jsonl', a, prov), ('a V1 attribution off its stream', a['id'])
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


def is_m36f(p):
    """A provenance row of a value M3.6F added (a Cuvée Mongravey sheet's line, or its reconciliation)."""
    return p.get('actor') == M36F_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.6F'


def is_m36f_observation(o):
    return (o.get('extraction') or {}).get('method') == 'm36f-vintages/1'


def is_m36f_reconciliation(r):
    return r.get('resolver') == M36F_ACTOR and r.get('rule') in ('ONLY_CANDIDATE', 'UNANIMOUS')


def m36f_applied():
    """{(vintage, field): value} the M3.6F manifest's applied value rows added to the model."""
    try:
        rows = L.jsonl_lines(L.ROOT + M36F_MANIFEST)
    except FileNotFoundError:
        return {}
    return {(r['vintage'], r['field']): r['value'] for r in rows if r['record'] == 'value' and r['applied']}


_V1 = {}                         # v1_created()'s set, for this process only: rebuilt when the manifest changes


def v1_created():
    """{(wine, label)} of the vintages the V1 mechanism created, as the model manifest records them (read once per
    process, and again only if the manifest's size or modification time changes)."""
    st = os.stat(L.MODEL + 'manifest.json')
    key = (st.st_size, st.st_mtime_ns)
    if _V1.get('key') != key:
        m = json.load(open(L.MODEL + 'manifest.json', encoding='utf-8'))
        _V1.clear()
        _V1.update(key=key, made=frozenset(tuple(v[3:].rsplit(':', 1))
                                           for v in (m.get('stats') or {}).get('M5', {}).get(V1_VINTAGE_STAT, [])))
    return _V1['made']


def is_v1_row(rel, r, prov):
    """A model row the V1 mechanism added: one of its vintages, an existence attribution on its provenance, or
    that provenance."""
    if rel == 'identity/vintages.jsonl':
        return (r.get('wine'), r.get('label')) in v1_created()
    p = r if rel == 'cross/provenance.jsonl' else (prov.get(r.get('provenance')) or {}) \
        if rel == 'document/attributions.jsonl' else {}
    return p.get('actor') == V1_ACTOR and (p.get('code_state') or {}).get('stream') == V1_STREAM


def v1_links(prov):
    """{(vintage ref, artifact)} the V1 mechanism's existence attributions link."""
    return {(a['vintage'], a['artifact']) for a in L.read_table('document/attributions.jsonl')
            if is_v1_row('document/attributions.jsonl', a, prov)}


def without_v1_vintages(index):
    """derived/wine-vintages.json with the V1 mechanism's vintages taken out."""
    made = collections.defaultdict(set)
    for w, lab in v1_created():
        made[w].add(lab)
    out = {k: [x for x in v if str(x) not in made.get(k, ())] for k, v in index.items()}
    return {k: v for k, v in out.items() if v or k not in made}


def is_m310c(p):
    """A provenance row of a value M3.10C added (a Durfort-Vivens sheet's lines, or its reconciliation)."""
    return p.get('actor') == M310C_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.10C'


def is_m310c_observation(o):
    return (o.get('extraction') or {}).get('method') == 'm310c-values/1'


def is_m310c_reconciliation(r):
    return r.get('resolver') == M310C_ACTOR and r.get('rule') in ('ONLY_CANDIDATE', 'UNANIMOUS')


def m310c_applied():
    """{(vintage, field): value} the M3.10C manifest's value rows added to the model."""
    try:
        rows = L.jsonl_lines(L.ROOT + M310C_MANIFEST)
    except FileNotFoundError:
        return {}
    return {(r['vintage'], r['field']): r['value'] for r in rows if r['record'] == 'value'}


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


@functools.lru_cache(maxsize=None)
def m36d_wine():
    """The wine M3.6D minted (its wine-by-slug key is on M3.6D's provenance), or None."""
    prov = {p['id'] for p in L.read_table('cross/provenance.jsonl') if p.get('actor') == M36D_ACTOR}
    ws = [r['stable_id'] for r in L.read_table('identity/identity-map.jsonl')
          if r['namespace'] == 'wine-by-slug' and r.get('provenance') in prov]
    assert len(ws) <= 1, ('M3.6D mints one wine', ws)
    return ws[0] if ws else None


def is_m36d_row(rel, r, prov):
    """A model row M3.6D or M3.6F added: on their provenance, or the minted wine's own row, identity-map key or
    vintage (a vintage row carries no provenance)."""
    p = prov.get(r.get('provenance')) or {}
    if CUVEE_ACTORS.get(p.get('actor'), '-') == (p.get('code_state') or {}).get('stream'):
        return True
    w = m36d_wine()
    return bool(w) and ((rel == 'identity/wines.jsonl' and r['id'] == w) or
                        (rel == 'identity/identity-map.jsonl' and r.get('stable_id') == w) or
                        (rel == 'identity/vintages.jsonl' and r.get('wine') == w))


def m36d_rows(rel):
    """The rows of `rel` M3.6D added, in file order."""
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    if rel == 'cross/provenance.jsonl':
        return [p for p in prov.values() if p.get('actor') in CUVEE_ACTORS]
    return [r for r in L.read_table(rel) if is_m36d_row(rel, r, prov)]


_M310A = {}                      # the manifest's index, for this process only: rebuilt when the file changes


def _m310a_index():
    """M3.10A's registrations and their sha256 and URL sets, read once per process (and again only if the
    manifest's size or modification time changes); nothing is kept beyond the process."""
    try:
        st = os.stat(L.ROOT + M310A_MANIFEST)
    except FileNotFoundError:
        return {'regs': [], 'shas': frozenset(), 'urls': frozenset()}
    key = (st.st_size, st.st_mtime_ns)
    if _M310A.get('key') != key:
        regs = [r for r in L.jsonl_lines(L.ROOT + M310A_MANIFEST) if r['record'] == 'registration']
        _M310A.clear()
        _M310A.update(key=key, regs=regs, shas=frozenset(g['sha256'] for g in regs),
                      urls=frozenset(g['url'] for g in regs))
    return _M310A


def m310a_registrations():
    """The registration rows of M3.10A's manifest (the migration's fourth artifact input), or []."""
    return list(_m310a_index()['regs'])


def is_m310a_row(rel, r, prov):
    """A model row M3.10A added: on its provenance, or a registered document's artifact, sha256 key or URL locator."""
    p = prov.get(r.get('provenance')) or {}
    if rel == 'cross/provenance.jsonl':
        return r.get('actor') == M310A_ACTOR and (r.get('code_state') or {}).get('stream') == 'M3.10A'
    if p.get('actor') == M310A_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.10A':
        return True
    if rel not in ('identity/artifacts.jsonl', 'identity/identity-map.jsonl', 'document/locators.jsonl'):
        return False                  # the only tables a registered document's key or URL appears in
    idx = _m310a_index()
    shas, urls = idx['shas'], idx['urls']
    return ((rel == 'identity/artifacts.jsonl' and r.get('sha256') in shas and 'sha1' not in r) or
            (rel == 'identity/identity-map.jsonl' and r.get('namespace') == 'artifact-by-sha256' and r.get('legacy_key') in shas) or
            (rel == 'document/locators.jsonl' and r.get('kind') == 'URL' and r.get('value') in urls))


def is_m310b_row(rel, r, prov):
    """A model row M3.10B added: an attribution of a registered document, or its DOCUMENT provenance."""
    if rel == 'cross/provenance.jsonl':
        return r.get('actor') == M310B_ACTOR and (r.get('code_state') or {}).get('stream') == 'M3.10B'
    return rel == 'document/attributions.jsonl' and is_m310b_attribution(r, prov)


M310B_FILES = ('document/attributions.jsonl', 'derived/vintage-documents.json', 'cross/provenance.jsonl', 'manifest.json')


def is_m310c_row(rel, r, prov):
    """A model row M3.10C added: on its provenance (an observation, a canonical value), its reconciliation, or the
    provenance itself."""
    if rel == 'cross/provenance.jsonl':
        return r.get('actor') == M310C_ACTOR and (r.get('code_state') or {}).get('stream') == 'M3.10C'
    if rel == 'reconciliation/reconciliations.jsonl':
        p = prov.get(r.get('provenance')) or {}
        return r.get('resolver') == M310C_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.10C'
    p = prov.get(r.get('provenance')) or {}
    return rel in ('canonical/values.jsonl', 'observation/observations.jsonl') and \
        p.get('actor') == M310C_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.10C'


def _without_m310a_manifest(m):
    """A model manifest with M3.10A's and M3.10B's rows taken out of its counts and their stats set aside."""
    m = json.loads(json.dumps(m))
    regs = m310a_registrations()
    stats = m.get('stats') or {}
    if regs and M310A_STAT in (stats.get('M6') or {}):
        stats['M6'].pop(M310A_STAT)
        a = stats['M2'][M310A_ARTIFACT_STAT]
        stats['M2'][M310A_ARTIFACT_STAT] = [a[0], a[1] - len(regs)]
        for rel in M310A_FILES:
            if rel in m.get('files', {}) and rel != 'manifest.json':
                m['files'][rel] = {'rows': m['files'][rel]['rows'] - len(regs)}
    n = stats.get('M6', {}).pop(M310B_STAT, None)
    if n:
        for rel in ('document/attributions.jsonl', 'cross/provenance.jsonl'):
            m['files'][rel] = {'rows': m['files'][rel]['rows'] - n}
    if stats.get('M7', {}).pop(M310C_STAT, None):
        prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
        for rel in [f for f in M310C_FILES if f.endswith('.jsonl')]:
            k = sum(1 for r in L.read_table(rel) if is_m310c_row(rel, r, prov))
            m['files'][rel] = {'rows': m['files'][rel]['rows'] - k}
    made = stats.get('M5', {}).pop(V1_VINTAGE_STAT, None)
    n = stats.get('M6', {}).pop(V1_ATTRIBUTION_STAT, None)
    if made:
        m['files']['identity/vintages.jsonl'] = {'rows': m['files']['identity/vintages.jsonl']['rows'] - len(made)}
    if n:
        for rel in ('document/attributions.jsonl', 'cross/provenance.jsonl'):
            m['files'][rel] = {'rows': m['files'][rel]['rows'] - n}
    return m


def _decoded(text):
    """(line, its row) for each line of a JSONL text: each line decoded once, however many tests read it."""
    return [(x, json.loads(x)) for x in text.splitlines()]


def unchanged_but_m310a(before, *paths):
    """`git diff before -- paths` (under data/model/) is empty but for M3.10A: only its files differ, and with
    its rows taken out each is exactly as at `before`, line for line and in order (the manifest: its counts and
    stat set aside, every file's hash aside). True, or an assertion error naming what else changed."""
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    later = {(r[4], r[1]) for r in m310b_applied()}            # M3.10B's (vintage, artifact) links
    for f in _git('diff', '--name-only', before, '--', *paths).split():
        rel = f[len('data/model/'):]
        assert rel in set(M310A_FILES) | set(M310B_FILES) | set(M310C_FILES) | set(V1_FILES) and m310a_registrations(), \
            '%s changed, and not by M3.10A' % f
        old = _git('show', '%s:%s' % (before, f))
        new = open(L.ROOT + f, encoding='utf-8').read()
        if rel == 'manifest.json':
            a, b = (_without_m310a_manifest(json.loads(t)) for t in (old, new))
            for d in (a, b):
                d['files'] = {k: {'rows': v['rows']} for k, v in d['files'].items()}
            assert a == b, '%s changed beyond M3.10A and M3.10B' % f
            continue
        if rel == 'derived/vintage-documents.json':
            gone = later | v1_links(prov)                   # and the V1 mechanism's existence links
            a, b = ({k: [x for x in v if (k, x) not in gone] for k, v in json.loads(t).items()} for t in (old, new))
            a, b = ({k: v for k, v in d.items() if v} for d in (a, b))
            assert a == b, '%s changed beyond M3.10B\'s links' % f
            continue
        if rel == 'derived/wine-vintages.json':
            assert without_v1_vintages(json.loads(new)) == without_v1_vintages(json.loads(old)), \
                '%s changed beyond the V1 mechanism\'s vintages' % f
            continue
        kept = [[x for x, r in _decoded(t) if not is_m310a_row(rel, r, prov)
                 and not is_m310b_row(rel, r, prov) and not is_m310c_row(rel, r, prov)
                 and not is_v1_row(rel, r, prov)]
                for t in (new, old)]
        assert kept[0] == kept[1], '%s changed beyond M3.10A\'s and M3.10B\'s rows' % f
    return True


def unchanged_but_m36d(before, *paths):
    """`git diff before -- paths` (paths under data/model/) is empty but for M3.6D: only its files differ, and
    with its rows taken out each is exactly as at `before`, line for line and in order. True, or an assertion
    error naming what else changed."""
    for f in _git('diff', '--name-only', before, '--', *paths).split():
        rel = f[len('data/model/'):]
        if rel in set(M310A_FILES) | set(M310B_FILES) | {'document/attributions.jsonl', 'derived/vintage-documents.json'} \
                and rel not in CUVEE_FILES and rel != 'cross/provenance.jsonl':
            unchanged_but_m310a(before, f)            # M3.10A's and M3.10B's rows, later phases, set aside alike
            continue
        assert (rel in CUVEE_FILES or rel == 'cross/provenance.jsonl') and m36d_wine(), '%s changed, and not by M3.6D' % f
        old = _git('show', '%s:%s' % (before, f))
        new = open(L.ROOT + f, encoding='utf-8').read()
        prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
        if rel == 'cross/provenance.jsonl':
            # `before` may hold M3.6D's rows already (a later phase's check): both sides without them
            kept = [[x for x, r in _decoded(t) if r.get('actor') not in CUVEE_ACTORS
                     and not is_m310a_row(rel, r, prov) and not is_m310b_row(rel, r, prov)
                     and not is_m310c_row(rel, r, prov) and not is_v1_row(rel, r, prov)]
                    for t in (new, old)]
            assert kept[0] == kept[1], '%s changed beyond M3.6D\'s provenance' % f
        elif rel.endswith('.jsonl'):
            kept = [[x for x, r in _decoded(t) if not is_m36d_row(rel, r, prov)
                     and not is_m310a_row(rel, r, prov) and not is_m310c_row(rel, r, prov)
                     and not is_v1_row(rel, r, prov)]
                    for t in (new, old)]
            assert kept[0] == kept[1], '%s changed beyond M3.6D\'s rows' % f
        else:
            w = m36d_wine()
            a, b = json.loads(old), json.loads(new)
            if rel == 'derived/wine-vintages.json':
                a, b = without_v1_vintages(a), without_v1_vintages(b)    # the V1 mechanism's vintages aside
            a, b = ({k: [x for x in v if x != w] for k, v in d.items() if k != w} for d in (a, b))
            assert b == a, '%s changed beyond M3.6D' % f
    return True


def without_m36d(changed, manifest):
    """An earlier phase's report of the model with M3.6D taken out: its files (which only it changes - no earlier
    phase touches identity or state) left off the changed list, and its rows subtracted from the manifest's
    counts. (changed, manifest) unchanged when there is no M3.6D wine."""
    files = dict(manifest['files'])
    if m36d_wine():
        for rel in [f for f in CUVEE_FILES if f.endswith('.jsonl')] + ['cross/provenance.jsonl']:
            files[rel] = dict(files[rel], rows=files[rel]['rows'] - len(m36d_rows(rel)))
        # M3.6F's files besides: the reports that call this read from a state after M3.2, so only M3.6F moved them
        changed = [f for f in changed if f not in CUVEE_FILES]
    # M3.10A's registrations, a later phase, taken out alike: its rows from the counts, and the files only it
    # moved since M3.2 (the artifacts, and the placements and locators M3.2B last moved before these reports)
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    if m310a_registrations():
        for rel in [f for f in M310A_FILES if f.endswith('.jsonl')]:
            n = sum(1 for r in L.read_table(rel) if is_m310a_row(rel, r, prov))
            files[rel] = dict(files[rel], rows=files[rel]['rows'] - n)
        only = ('identity/artifacts.jsonl', 'document/placements.jsonl', 'document/locators.jsonl')
        changed = [f for f in changed if f not in only]
    # M3.10B's attributions and their provenance, a later linking phase: its rows out of the counts (the files
    # stay changed: the reports that call this were written after earlier phases' attributions moved them)
    for rel in ('document/attributions.jsonl', 'cross/provenance.jsonl'):
        n = sum(1 for r in L.read_table(rel) if is_m310b_row(rel, r, prov))
        if n:
            files[rel] = dict(files[rel], rows=files[rel]['rows'] - n)
    # M3.10C's values, observations, reconciliations and their provenance, a later application: its rows out of
    # the counts (its files besides provenance are M3.6F's, already off the list)
    for rel in [f for f in M310C_FILES if f.endswith('.jsonl')]:
        n = sum(1 for r in L.read_table(rel) if is_m310c_row(rel, r, prov))
        if n:
            files[rel] = dict(files[rel], rows=files[rel]['rows'] - n)
    # the V1 mechanism's vintages, existence attributions and their provenance, later population: out of the counts
    for rel in [f for f in V1_FILES if f.endswith('.jsonl')]:
        n = sum(1 for r in L.read_table(rel) if is_v1_row(rel, r, prov))
        if n:
            files[rel] = dict(files[rel], rows=files[rel]['rows'] - n)
    return changed, dict(manifest, files=files)


def model_changes_are_m2_only(before):
    changed = [f[len('data/model/'):] for f in _git('diff', '--name-only', before, '--', 'data/model').split()]
    assert set(changed) <= ALLOWED, 'the model changed beyond M2 and M3.2: %s' % sorted(set(changed) - ALLOWED)
    prov = {r['id']: r for r in map(json.loads, open(L.MODEL + 'cross/provenance.jsonl', encoding='utf-8'))}
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
                        (r['kind'] in ('DOCUMENT', 'DERIVATION') and r['actor'] in CUVEE_ACTORS
                         and (r.get('code_state') or {}).get('stream') == CUVEE_ACTORS[r['actor']]) or
                        (r['kind'] == 'DERIVATION' and r['actor'] == M32_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.2D') or
                        (r['kind'] == 'DOCUMENT' and is_m310a_row('cross/provenance.jsonl', r, {})) or
                        (r['kind'] == 'DOCUMENT' and r['actor'] == M310B_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.10B') or
                        (r['kind'] in ('DOCUMENT', 'DERIVATION') and r['actor'] == M310C_ACTOR
                         and (r.get('code_state') or {}).get('stream') == 'M3.10C') or
                        (r['kind'] == 'DOCUMENT' and is_v1_row('cross/provenance.jsonl', r, {}))),
                       ('reconciliation/reconciliations.jsonl',
                        lambda r: r['resolver'] in (M32_ACTOR, M36F_ACTOR, M310C_ACTOR)
                        and r['rule'] in ('ONLY_CANDIDATE', 'UNANIMOUS')
                        and r['status'] in ('SINGLE', 'AGREED') and 'dispositions' not in r
                        and (r['resolver'] == M32_ACTOR or is_m36d_row('reconciliation/reconciliations.jsonl', r, prov)
                             or is_m310c_row('reconciliation/reconciliations.jsonl', r, prov)))):
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
            assert is_m34b_attribution(a, prov) or is_m35_attribution(a, prov) or is_m36b_attribution(a, prov) or \
                is_m310b_attribution(a, prov) or is_v1_row('document/attributions.jsonl', a, prov),                 ('not an M3.4B, M3.5 or M3.6B attribution', a['id'])
    if 'derived/vintage-documents.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'derived/vintage-documents.json'))
        linked = {(r[4], r[1]) for r in m34b_applied() | m35_applied() | m36b_applied() | m310b_applied()} | \
            v1_links(prov)
        for k in set(old) | set(new):
            o, n = set(old.get(k, [])), set(new.get(k, []))
            assert o <= n and {(k, a) for a in n - o} <= linked, ('derived/vintage-documents.json', k, sorted(o - n))
    # M3.6D: its wine, names, identity keys, relationship and descriptor added, every existing row kept
    for rel in M36D_FILES:
        if rel not in changed or not rel.endswith('.jsonl'):
            continue
        old, new = _lines(before, rel)
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, '%s: %d rows changed or removed' % (rel, len(o - n))
        bad = [r for r in (json.loads(x) for x in n - o) if not is_m36d_row(rel, r, prov)
               and not is_m310a_row(rel, r, prov)]
        assert not bad, '%s: an added row is not M3.6D\'s or M3.10A\'s: %s' % (rel, bad[:1])
    # M3.10A: the registered documents' artifacts added, every existing one kept
    if 'identity/artifacts.jsonl' in changed:
        old, new = _lines(before, 'identity/artifacts.jsonl')
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n, 'identity/artifacts.jsonl: %d rows changed or removed' % len(o - n)
        bad = [r for r in (json.loads(x) for x in n - o) if not is_m310a_row('identity/artifacts.jsonl', r, prov)]
        assert not bad, 'identity/artifacts.jsonl: an added artifact is not M3.10A\'s: %s' % bad[:1]
    if 'derived/estate-wines.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'derived/estate-wines.json'))
        w = m36d_wine()
        moved = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
        assert all(set(new[k]) - set(old.get(k, [])) == {w} and set(old.get(k, [])) <= set(new[k]) for k in moved), \
            ('derived/estate-wines.json changed beyond M3.6D', sorted(moved))
    # M3.6F: the wine's vintages added, every existing one kept; the index gains that wine's key alone
    if 'identity/vintages.jsonl' in changed:
        old, new = _lines(before, 'identity/vintages.jsonl')
        o, n = set(old.splitlines()), set(new.splitlines())
        assert o <= n and all(json.loads(x)['wine'] == m36d_wine() or is_v1_row('identity/vintages.jsonl', json.loads(x), prov)
                              for x in n - o), 'identity/vintages.jsonl beyond M3.6F and the V1 mechanism'
    if 'derived/wine-vintages.json' in changed:
        old, new = (json.loads(x) for x in _lines(before, 'derived/wine-vintages.json'))
        assert {k: v for k, v in without_v1_vintages(new).items() if k != m36d_wine()} == without_v1_vintages(old), \
            'derived/wine-vintages.json beyond M3.6F and the V1 mechanism'
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
                assert r['locator']['kind'] == 'URL' and (
                    (p.get('actor') == M32_ACTOR and (p.get('code_state') or {}).get('stream') == 'M3.2B') or
                    is_m310a_row(rel, r, prov)), ('not an M3.2B or M3.10A placement', r['id'])
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
        o = {key(r): r for r in map(json.loads, old.splitlines())}
        n = {key(r): r for r in map(json.loads, new.splitlines())}
        assert set(o) <= set(n), '%s: rows removed' % rel
        for k in set(n) - set(o):
            # M3.2D: a recovered value or the observation that states it, each with its M3.2D provenance
            # M3.6F: Cuvée Mongravey's vintage value or the observation stating it, on its M3.6F provenance
            p = prov.get(n[k]['provenance']) or {}
            assert (p.get('actor'), (p.get('code_state') or {}).get('stream')) in (
                (M32_ACTOR, 'M3.2D'), (M36F_ACTOR, 'M3.6F'), (M310C_ACTOR, 'M3.10C')), \
                '%s %s: an added row is not M3.2D\'s or M3.6F\'s' % (rel, k)
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
        # M3.10A's registrations, a later phase: its stat and the artifact count it raises set aside
        old, new = (_without_m310a_manifest(json.loads(x)) for x in _lines(before, 'manifest.json'))
        for k in set(old) | set(new):
            if k == 'files':
                diff = {f for f in set(old[k]) | set(new[k]) if old[k].get(f) != new[k].get(f)}
                assert diff <= ALLOWED - {'manifest.json'}, 'manifest files: %s' % sorted(diff)
            elif k == 'stats':
                a_all, b_all = _sourced_moved(old[k]), _sourced_moved(new[k])
                for st in set(a_all) | set(b_all):
                    a, b = dict(a_all.get(st, {})), dict(b_all.get(st, {}))
                    had_m36d = M36D_STAT in a                  # `before` already holds M3.6D (a later phase's check)
                    for s in (M2_STAT, M32B_STAT, M32D_STAT, M34B_STAT, M35_STAT, M36B_STAT, M36D_STAT,
                              M310B_STAT, M310C_STAT) + M36F_STATS:
                        a.pop(s, None)
                        b.pop(s, None)
                    if st == 'M4' and m36d_wine() and 'display names' in b and not had_m36d:
                        # M3.6D's wine resolves one more display name (its own, in its estate)
                        b['display names'] = dict(b['display names'], resolved=b['display names']['resolved'] - 1)
                    assert a == b, 'manifest stats %s changed' % st
            else:
                assert old.get(k) == new.get(k), 'manifest %s changed' % k
    return changed


REGISTER = 'data/audit/data-gap-register.jsonl'
LINKING_PHASES = ('M3.4B', 'M3.5', 'M3.6B', 'M3.10B')


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


def m36e_evidence_rows():
    """v7, verified to be exactly M3.6E's decisions: every superseding row its manifest names, and no other,
    each a REFUSED correction."""
    import evidence_store as ST
    import mig_m6_provenance as M6
    if M36E_EVIDENCE_VERSION not in ST.versions():
        return []
    rows = list(ST.iter_rows([M36E_EVIDENCE_VERSION]))
    keys = [M6.row_key(d) for d in rows]
    want = {r['superseded_by'] for r in L.jsonl_lines(L.ROOT + M36E_MANIFEST) if r['result'] == 'APPLIED'}
    assert len(keys) == len(set(keys)) and set(keys) == want, 'v7 is not exactly M3.6E\'s decisions'
    assert all(d.get('kind') == 'correction' and d.get('decision') == 'REFUSED' for d in rows), 'a v7 row of another kind'
    return rows


def m36h_evidence_rows():
    """v8, verified to be exactly M3.6H's decision: the superseding row its manifest names, and no other, a
    REFUSED correction."""
    import evidence_store as ST
    import mig_m6_provenance as M6
    if M36H_EVIDENCE_VERSION not in ST.versions():
        return []
    rows = list(ST.iter_rows([M36H_EVIDENCE_VERSION]))
    keys = [M6.row_key(d) for d in rows]
    want = {r['superseded_by'] for r in L.jsonl_lines(L.ROOT + M36H_MANIFEST) if r.get('result') == 'APPLIED'}
    assert len(keys) == len(set(keys)) and set(keys) == want, 'v8 is not exactly M3.6H\'s decisions'
    assert all(d.get('kind') == 'correction' and d.get('decision') == 'REFUSED' for d in rows), 'a v8 row of another kind'
    return rows


def m310b_evidence_rows():
    """v9, verified to be exactly M3.10B's decisions: every row its manifest names, and no other, each an ACCEPTED
    `guard` row on the bytes M3.10A registered."""
    import evidence_store as ST
    import mig_m6_provenance as M6
    if M310B_EVIDENCE_VERSION not in ST.versions():
        return []
    rows = list(ST.iter_rows([M310B_EVIDENCE_VERSION]))
    keys = [M6.row_key(d) for d in rows]
    want = {r['evidence_decision'] for r in L.jsonl_lines(L.ROOT + M310B_MANIFEST) if r.get('result') == 'APPLIED'}
    assert len(keys) == len(set(keys)) and set(keys) == want, 'v9 is not exactly M3.10B\'s decisions'
    assert all(d.get('kind') == 'guard' and d.get('decision') == 'ACCEPTED' for d in rows), 'a v9 row of another kind'
    return rows


LATER_EVIDENCE_VERSIONS = {M36B_EVIDENCE_VERSION: m36b_evidence_rows, M36E_EVIDENCE_VERSION: m36e_evidence_rows,
                           M36H_EVIDENCE_VERSION: m36h_evidence_rows, M310B_EVIDENCE_VERSION: m310b_evidence_rows}


def evidence_versions_before_m36b():
    """The store's versions, M3.6B's v6, M3.6E's v7 and M3.6H's v8 verified and set aside."""
    import evidence_store as ST
    for rows in LATER_EVIDENCE_VERSIONS.values():
        rows()
    return [v for v in ST.versions() if v not in LATER_EVIDENCE_VERSIONS]


def latest_before_m36e():
    """evidence_store.latest_by_context() as M3.6B left it: v7 and v8 verified and set aside."""
    import evidence as EV
    import evidence_store as ST
    m36e_evidence_rows()
    m36h_evidence_rows()
    out = {}
    m310b_evidence_rows()
    for d in ST.iter_rows([v for v in ST.versions() if v not in (M36E_EVIDENCE_VERSION, M36H_EVIDENCE_VERSION,
                                                                 M310B_EVIDENCE_VERSION)]):
        k = EV.row_key(d)[:-1]
        if k not in out or (d.get('v') or 0) >= (out[k].get('v') or 0):
            out[k] = d
    return out


def _evidence_unchanged_but(before, versions, phase):
    """data/evidence as at `before` but for `versions`: their decision files and index entries, each verified
    to be exactly its phase's decisions; every other file, and every other index entry, byte for byte."""
    vs = {str(v) for v in versions}
    changed = set(_git('diff', '--name-only', before, '--', 'data/evidence').split())
    untracked = set(_git('ls-files', '--others', '--exclude-standard', '--', 'data/evidence').split())
    assert (changed | untracked) <= {'data/evidence/index.json'} | {'data/evidence/decisions-v%s.jsonl' % v for v in vs}, \
        'the evidence store changed beyond %s: %s' % (phase, sorted(changed | untracked))
    if 'data/evidence/index.json' in changed:
        old = json.loads(_git('show', '%s:data/evidence/index.json' % before))
        new = json.load(open(L.ROOT + 'data/evidence/index.json', encoding='utf-8'))
        assert {k: x for k, x in new.items() if k != 'versions'} == {k: x for k, x in old.items() if k != 'versions'}
        assert {k: x for k, x in new['versions'].items() if k not in vs} == \
            {k: x for k, x in old['versions'].items() if k not in vs}, 'an earlier version changed'
    for v in versions:
        LATER_EVIDENCE_VERSIONS[v]()
    return True


def evidence_unchanged_but_m36e(before):
    """data/evidence as at `before` but for M3.6E: decisions-v7.jsonl and index.json's version 7 entry, v7
    exactly M3.6E's decisions; every other file, and every other index entry, byte for byte. M3.6H's v8, a
    later correction, is verified and set aside alike."""
    return _evidence_unchanged_but(before, (M36E_EVIDENCE_VERSION, M36H_EVIDENCE_VERSION, M310B_EVIDENCE_VERSION), 'M3.6E')


def evidence_unchanged_but_m36h(before):
    """data/evidence as at `before` but for M3.6H: decisions-v8.jsonl and index.json's version 8 entry, v8
    exactly M3.6H's decision; v1-v7 and their index entries byte for byte."""
    return _evidence_unchanged_but(before, (M36H_EVIDENCE_VERSION, M310B_EVIDENCE_VERSION), 'M3.6H')


def evidence_unchanged_but_m310b(before):
    """data/evidence as at `before` but for M3.10B: decisions-v9.jsonl and index.json's version 9 entry, v9
    exactly M3.10B's decisions; v1-v8 and their index entries byte for byte."""
    return _evidence_unchanged_but(before, (M310B_EVIDENCE_VERSION,), 'M3.10B')


def evidence_rows_before_m36b():
    """How many decisions the store holds besides M3.6B's v6."""
    import evidence_store as ST
    return sum(1 for _ in ST.iter_rows(evidence_versions_before_m36b()))


def evidence_changes_are_m36b_only(before):
    """data/evidence as at `before`, but for M3.6B: v1-v5, their files and index entries byte for byte; v6
    exactly M3.6B's decisions; no other file. True, or an assertion error saying what else changed."""
    changed = set(_git('diff', '--name-only', before, '--', 'data/evidence').split())
    untracked = set(_git('ls-files', '--others', '--exclude-standard', '--', 'data/evidence').split())
    later = {'data/evidence/decisions-v%d.jsonl' % v for v in LATER_EVIDENCE_VERSIONS}     # M3.6B's v6, M3.6E's v7, M3.6H's v8
    assert (changed | untracked) <= {'data/evidence/index.json'} | later, \
        'the evidence store changed beyond M3.6B: %s' % sorted(changed | untracked)
    if 'data/evidence/index.json' in changed:
        old = json.loads(_git('show', '%s:data/evidence/index.json' % before))
        new = json.load(open(L.ROOT + 'data/evidence/index.json', encoding='utf-8'))
        skip = {str(v) for v in LATER_EVIDENCE_VERSIONS}
        assert {k: x for k, x in new.items() if k != 'versions'} == {k: x for k, x in old.items() if k != 'versions'}
        assert {k: x for k, x in new['versions'].items() if k not in skip} == \
            {k: x for k, x in old['versions'].items() if k not in skip}, 'a historical version changed in the index'
    for rows in LATER_EVIDENCE_VERSIONS.values():
        rows()
    return True


def protected_group(name):
    """migration_lib.group_hashes(name) for Phase 4's protected groups, with M3.6B's evidence version 6 named
    and set aside: every other group exactly as group_hashes gives it; 'evidence' as v1-v5's files, byte for
    byte, and index.json as the store serialises it without the v6 entry - which reproduces the old index
    only if nothing else in it changed. v6 must be exactly M3.6B's decisions; no v6 failure file may exist."""
    import evidence_store as ST
    if name != 'evidence':
        return L.group_hashes(name)
    files = {}
    for p in L.GROUPS['evidence']():
        r = L.rel(p)
        base = r.rsplit('/', 1)[-1]
        later = False
        for v in LATER_EVIDENCE_VERSIONS:                   # M3.6B's v6, M3.6E's v7, M3.6H's v8, set aside alike
            assert base != 'provenance-failures-v%d.jsonl' % v, 'a v%d provenance failure' % v
            later = later or base == 'decisions-v%d.jsonl' % v or base.startswith('decisions-v%d.part' % v)
        if later:
            continue
        if base == 'index.json':
            ix = json.load(open(p, encoding='utf-8'))
            for v, rows in LATER_EVIDENCE_VERSIONS.items():
                if str(v) in ix.get('versions', {}):
                    rows()
                    del ix['versions'][str(v)]
            b = (json.dumps(ix, ensure_ascii=False, indent=1, sort_keys=True) + '\n').encode('utf-8')
            files[r] = hashlib.sha256(b).hexdigest()
            continue
        files[r] = L.sha256_file(p)
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {'files': files, 'digest': digest}
