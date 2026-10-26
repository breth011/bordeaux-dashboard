"""M3.4B: apply the audited existing-evidence mappings - the fail-closed preflight and its manifest.

    python tools/m34b-apply.py             preflight; write data/audit/m3.4b-mapping-application.jsonl
    python tools/m34b-apply.py --check     recompute and compare, byte for byte
    python tools/m34b-apply.py --check-all recompute once; compare the output and the report, byte for byte
    python tools/m34b-apply.py --report    write docs/PHASE-M3.4B-MAPPING-APPLICATION.md (also --check)

The allow-list is M3.4A's SAFE_TO_MAP rows (data/audit/m3.4a-mapping-proposals.jsonl) and nothing
else. Each is checked again, against the model as it stood before M3.4B, before anything changes:

  allow-list  a fresh M3.4A run reproduces every SAFE row byte for byte; the counts match its report
  artifact    exists, same id and sha256, bytes held and re-hashed, its manifest provenance present
  evidence    each referenced v5 decision exists, is ACCEPTED, read exactly these bytes, and names
              this estate, this wine and this vintage; its evidence link carries the model ids
  estate      exists; the decision's estate
  wine        exists, belongs to the estate, is the decision's wine; no open decision governs it
  vintage     exists; the decision's vintage, stated in the document's own opening (not its name)
  role/colour as M3.4A recorded them; the wine's colour in the model unchanged
  conflicts   no other attribution of the artifact names another wine or vintage; two proposals
              for one artifact agree

A row that fails is REJECTED_PREFLIGHT, with every failure named; nothing replaces it.

The migration (tools/mig_m6_provenance.audited_mappings) reads this manifest's APPLIED rows and adds
one Attribution per row - method DOCUMENT_TEXT, status ACCEPTED, role FIRST - whose DOCUMENT
provenance names the decision, the audit row and the manifest provenance it rests on. It means only:
this accepted document is evidence for this estate + wine + vintage. No value, figure, name, date or
classification changes. No clock, no network; the evidence store and the sources are only read.
"""
import collections
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

AUDIT = L.ROOT + 'data/audit/m3.4a-mapping-proposals.jsonl'
AUDIT_REPORT = L.ROOT + 'docs/PHASE-M3.4A-MAPPING-AUDIT.md'
OUT = L.ROOT + 'data/audit/m3.4b-mapping-application.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.4B-MAPPING-APPLICATION.md'
ROLE = {'GRAND_VIN': 'FIRST'}                       # the only role M3.4A proposed; anything else fails

_s = importlib.util.spec_from_file_location('m34a', L.ROOT + 'tools/m34a-mapping-audit.py')
M34A = importlib.util.module_from_spec(_s)
_s.loader.exec_module(M34A)


def allow_list():
    return [r for r in L.jsonl_lines(AUDIT) if r['disposition'] == 'SAFE_TO_MAP']


def recorded_counts():
    """The counts M3.4A's report states for its SAFE mappings: (documents, vintages, wines)."""
    m = re.search(r'^(\d+) documents for (\d+) vintages of (\d+) wines', open(AUDIT_REPORT, encoding='utf-8').read(), re.M)
    return tuple(int(x) for x in m.groups()) if m else None


def v5_decisions():
    """row_key (as the evidence links carry it) -> the v5 decision."""
    return {M6.row_key(d): d for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl')}


def attribution_id(r):
    return S.hid('Attribution', r['artifact'], 'm34b', r['vintage_id'])


def preflight(rows, fresh):
    arts = A.by_id('identity/artifacts.jsonl')
    estates = A.by_id('identity/estates.jsonl')
    wines = A.by_id('identity/wines.jsonl')
    vintages = {'vt:%s:%s' % (v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    ew = {(x['estate'], x['wine']) for x in A.table('state/estate-wine.jsonl')}
    pv = A.by_id('cross/provenance.jsonl')
    links = {e['row_key']: e for e in A.table('observation/evidence-links.jsonl') if e['evidence_version'] == 5}
    decs = v5_decisions()
    nm = M34A.P.names()
    blocked = M34A.open_decision_wines(nm)
    vdocs = A.vintage_documents()
    legacy_att = A.legacy_attr_by_artifact()
    findings = [f for f in A.table('cross/findings.jsonl') if f['status'] == 'OPEN']
    fresh_by_key = {(r['estate'], r['wine'], r['vintage'], r['artifact']): json.loads(json.dumps(r)) for r in fresh}
    by_artifact = collections.defaultdict(set)
    for r in rows:
        by_artifact[r['artifact']].add((r['estate'], r['wine'], r['vintage_id']))
    out = []
    for r in rows:
        k = (r['estate'], r['wine'], r['vintage'], r['artifact'])
        fail, notes = [], []
        # the allow-list: the audit, run again now, decides this row exactly as recorded
        if fresh_by_key.get(k) != r:
            fail.append('allow-list: a fresh M3.4A run does not reproduce this SAFE row')
        # artifact
        a = arts.get(r['artifact'])
        if not a:
            fail.append('artifact: %s does not exist' % r['artifact'])
            a = {}
        if a.get('sha256') != r['sha256'] or not a.get('bytes_available'):
            fail.append('artifact: sha256 or held bytes differ from the audit')
        hashed = 0
        for pl in A.placements_of(r['artifact']):
            q = L.ROOT + 'sources/' + pl['locator']['value']
            if pl['locator']['kind'] == 'LOCAL_PATH' and os.path.exists(q):
                hashed += 1
                if hashlib.sha256(open(q, 'rb').read()).hexdigest() != r['sha256']:
                    fail.append('artifact: the held file %s does not hash to the recorded sha256' % pl['locator']['value'])
        if not hashed:
            fail.append('artifact: no held file to re-hash')
        legacy_prov = sorted({x['provenance'] for x in legacy_att.get(r['artifact'], [])
                              if (pv.get(x['provenance']) or {}).get('kind') == 'LEGACY_MANIFEST'})
        if not legacy_prov:
            fail.append('provenance: no manifest provenance for the artifact')
        # evidence: the referenced decisions on these bytes. The mapping rests on the ACCEPTED ones, each
        # for exactly this estate, wine, vintage and role. A decision that refused these bytes for
        # another target (the guard keeping a 2019 sheet off 1984) agrees with the mapping and is kept
        # beside it; one that accepted them for another target is a conflict.
        accepted, other = [], []
        for rk in r['evidence_refs']:
            d, ln = decs.get(rk), links.get(rk)
            if not d or not ln:
                fail.append('evidence: decision %s not found' % rk[:60])
                continue
            c = d.get('ctx') or {}
            if (d.get('read') or {}).get('sha256') != r['sha256'] or ln.get('artifact') != r['artifact']:
                fail.append('evidence: a referenced decision read other bytes')
            target = (ln.get('estate'), ln.get('wine'), c.get('target_vintage') or c.get('vintage'), c.get('target_role'))
            if d['decision'] == 'ACCEPTED':
                accepted.append(rk)
                if target[0] != r['estate']:
                    fail.append('estate: the accepted decision\'s estate is %s' % target[0])
                if target[1] != r['wine']:
                    fail.append('wine: the accepted decision\'s wine is %s' % target[1])
                if target[2] != r['vintage']:
                    fail.append('vintage: the accepted decision\'s vintage is %s' % target[2])
                if target[3] != 'grand':
                    fail.append('role: the accepted decision\'s role is %s' % target[3])
            else:
                other.append({'decision': rk, 'result': d['decision'], 'code': d['code'], 'vintage': target[2]})
                if target[:3] == (r['estate'], r['wine'], r['vintage']):
                    fail.append('evidence: a decision for exactly this target is %s' % d['decision'])
        if not accepted:
            fail.append('evidence: no accepted decision for this target')
        # estate, wine, vintage in the model
        if r['estate'] not in estates:
            fail.append('estate: %s does not exist' % r['estate'])
        if r['wine'] not in wines:
            fail.append('wine: %s does not exist' % r['wine'])
        if (r['estate'], r['wine']) not in ew:
            fail.append('wine: not a wine of the estate in the model')
        if r['vintage_id'] != 'vt:%s:%d' % (r['wine'], r['vintage']) or r['vintage_id'] not in vintages:
            fail.append('vintage: %s does not exist' % r['vintage_id'])
        if vdocs.get(r['vintage_id']):
            fail.append('vintage: already has a document (the audit found none)')
        # the vintage from the document's text: its opening states the year
        text, _ = M34A.document_text(r['artifact'])
        if not text or not re.search(r'(?<!\d)%d(?!\d)' % r['vintage'], text[:M34A.OPENING]):
            fail.append('vintage: the document\'s opening does not state it')
        # role and colour, as recorded
        p = r.get('proposal') or {}
        if p.get('role') not in ROLE:
            fail.append('role: %s is not one this phase applies' % p.get('role'))
        if p.get('colour') != (wines.get(r['wine']) or {}).get('type'):
            fail.append('colour: the wine\'s colour changed since the audit')
        # open decisions
        if r['wine'] in blocked:
            fail.append('open decision: %s governs the wine' % blocked[r['wine']])
        for s, d in sorted(blocked.items()):
            if text and A.fold(nm.get(s, '')) in text:
                fail.append('open decision: the document names %s (%s)' % (nm.get(s), d))
        for f in findings:
            if f['target'] in (r['wine'], r['vintage_id'], r['artifact']):
                fail.append('open decision: finding %s (%s) on the target' % (f['id'], f['kind']))
            elif f['target'] == r['estate']:
                notes.append('open %s finding %s on the estate is not touched: the mapping is the grand vin\'s, '
                             'and the document names no other wine' % (f['kind'], f['id']))
        # conflicts: another attribution naming another wine or vintage; proposals that disagree
        for x in legacy_att.get(r['artifact'], []):
            if (x.get('wine') and x['wine'] != r['wine']) or (x.get('vintage') and x['vintage'] != r['vintage_id']):
                fail.append('conflict: attribution %s names %s %s' % (x['id'], x.get('wine'), x.get('vintage')))
        if len(by_artifact[r['artifact']]) > 1:
            fail.append('conflict: proposals for this artifact name several targets')
        out.append({'gap_id': r['gap_id'], 'estate': r['estate'], 'estate_name': r['estate_name'],
                    'wine': r['wine'], 'wine_name': r['wine_name'], 'vintage': r['vintage'], 'vintage_id': r['vintage_id'],
                    'artifact': r['artifact'], 'sha256': r['sha256'], 'files': r['files'],
                    'evidence_decisions': sorted(accepted), 'other_decisions': other, 'manifest_provenance': legacy_prov,
                    'attribution': attribution_id(r), 'role': 'FIRST', 'audit_role': p.get('role'),
                    'colour': p.get('colour'), 'basis': r['basis'],
                    'result': 'REJECTED_PREFLIGHT' if fail else 'APPLIED',
                    'failures': sorted(set(fail)), 'notes': sorted(set(notes))})
    out.sort(key=lambda x: (x['estate'], x['wine'], x['vintage'], x['artifact']))
    return out


def build():
    rows = allow_list()
    fresh = [r for r in M34A.build() if r['disposition'] == 'SAFE_TO_MAP']
    return preflight(rows, fresh), rows


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def main():
    rows, allow = build()
    counts = (len(allow), len({r['vintage_id'] for r in allow}), len({r['wine'] for r in allow}))
    if counts != recorded_counts():
        print('STOP: the allow-list (%d mappings, %d vintages, %d wines) differs from M3.4A\'s report %s'
              % (counts + (recorded_counts(),)))
        sys.exit(2)
    if '--report' in sys.argv or '--check-all' in sys.argv:
        import m34b_report
        text = m34b_report.report(rows, allow)
        if '--check' in sys.argv or '--check-all' in sys.argv:
            same = os.path.exists(REPORT) and open(REPORT, encoding='utf-8').read() == text
            print('docs/PHASE-M3.4B-MAPPING-APPLICATION.md ' + ('is current' if same else 'differs from a fresh run'))
            if not same or '--check-all' not in sys.argv:
                sys.exit(0 if same else 1)
        else:
            open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
            print('wrote docs/PHASE-M3.4B-MAPPING-APPLICATION.md')
            return
    b = body(rows)
    if '--check' in sys.argv or '--check-all' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == b
        print('data/audit/m3.4b-mapping-application.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    res = collections.Counter(r['result'] for r in rows)
    print('allow-list %d mappings, %d vintages, %d wines (as M3.4A recorded); %s' % (counts + (dict(res),)))
    for r in rows:
        if r['failures']:
            print('  REJECTED %s %s %d %s: %s' % (r['estate_name'], r['wine_name'], r['vintage'], r['artifact'],
                                                  '; '.join(r['failures'])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(b)
    print('wrote data/audit/m3.4b-mapping-application.jsonl')


if __name__ == '__main__':
    main()
