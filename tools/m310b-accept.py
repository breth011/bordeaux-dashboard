"""M3.10B: accept the four Durfort-Vivens documents M3.10A registered as evidence for their exact wine and
vintage - the evidence decisions, and the manifest the migration reads for their attributions.

    python tools/m310b-accept.py --apply    preflight; the four ACCEPTED decisions (decider version 9) and the
                                            manifest and report
    python tools/m310b-accept.py --check    recompute what is written and compare (see VERIFYING)

THE ALLOW-LIST is M3.10A's registration manifest and nothing else: its four artifacts, each one of M3.9's
SAFE_TO_MAP documents of Château Durfort-Vivens. Before anything is written, M3.9's review is recomputed with
the existing reader (tools/m39-evidence-review.py, unchanged) and each of the four rows must equal the
committed audit's: the same disposition, wine, vintage and basis. Any other artifact, count or verdict stops
the run.

THE REPRESENTATION is M3.6B's, for a sheet: one ACCEPTED row (kind `guard`, the evidence store's reader
accepting a sheet, as v1-v5's acceptances) per document, asking its estate's grand-vin question for its
vintage; its `read` the held bytes (sources/acquisition/m3.8/blobs/<sha256>), its `folder` the store and
the digest (`acquisition:<sha256>`, as M3.6B's `discovery:<sha256>`); its evidence the reader's basis and
veto as M3.9 recorded them. Decider version 9: the rules that decide are unchanged (tools/m35_rubric.py,
tools/web_evidence.py, the same fingerprint as v6-v8). v1-v8 stay byte for byte.

THE ATTRIBUTION is the model's, through the migration (tools/mig_m6_provenance.m310b_attributions), as
M3.6B's: one Attribution per document (method DOCUMENT_TEXT, status ACCEPTED, role FIRST), its DOCUMENT
provenance naming the decision. The 2014 English and French sheets are two accepted artifacts of one claim,
2014: two decisions and two attributions, no observation, no reconciliation. No value is applied - not the
2014 blend, ageing or new oak, not the 2021 alcohol, not the 2024 blend, oak, picking, yield or ageing; the
2024 oak discrepancy stays where M3.9 recorded it.

VERIFYING. A v9 row carries the git state it was written in. --check recomputes every row, the manifest and
the report, and compares all of it except that git stamp, which must name a commit in HEAD's history.
"""
import collections
import importlib.util
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402
import provenance as PV  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

VERSION = 9
ACTOR = 'tools/m310b-accept.py'
M310A = L.ROOT + 'data/audit/m3.10a-external-artifact-registration.jsonl'
M39 = L.ROOT + 'data/audit/m3.9-evidence-review.jsonl'
MANIFEST = L.ROOT + 'data/audit/m3.10b-evidence-decisions.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.10B-EVIDENCE-DECISIONS.md'
ESTATE, WINE = 'es_00263', 'wn_00263'
NOT_YET = 'NONE: value application is M3.10C'

_r = importlib.util.spec_from_file_location('m39', L.ROOT + 'tools/m39-evidence-review.py')
R = importlib.util.module_from_spec(_r)
_r.loader.exec_module(R)
_e = importlib.util.spec_from_file_location('m36e', L.ROOT + 'tools/m36e-apply.py')
E = importlib.util.module_from_spec(_e)
_e.loader.exec_module(E)


class Stop(Exception):
    pass


def allow_list():
    """M3.10A's four registrations and their results, each with its M3.9 review row - verified unchanged."""
    regs = [r for r in L.jsonl_lines(M310A) if r['record'] == 'registration']
    res = {r['candidate']: r for r in L.jsonl_lines(M310A) if r['record'] == 'result'}
    audit = {'m3.9:%d' % r['n']: r for r in L.jsonl_lines(M39) if r['record'] == 'review'}
    if len(regs) != 4 or set(res) != {g['candidate'] for g in regs}:
        raise Stop('M3.10A registers %d documents (%d results), expected 4' % (len(regs), len(res)))
    fresh = {'m3.9:%d' % r['n']: r for r in R.build() if r['record'] == 'review'}
    out = []
    for g in regs:
        a, now = audit.get(g['candidate']), fresh.get(g['candidate'])
        if not a or a['disposition'] != 'SAFE_TO_MAP' or a['estate'] != ESTATE or a['wine'] != WINE:
            raise Stop('%s is not an M3.9 SAFE_TO_MAP document of %s' % (g['candidate'], WINE))
        if a['sha256'] != g['sha256'] or a['url'] != g['url']:
            raise Stop('%s: M3.10A registered other bytes than M3.9 reviewed' % g['candidate'])
        keep = ('disposition', 'wine', 'vintage', 'reason', 'identity_source', 'claims')
        if {k: now[k] for k in keep} != {k: a[k] for k in keep}:
            raise Stop('%s: the reader no longer judges it as M3.9 recorded' % g['candidate'])
        out.append((g, res[g['candidate']], a))
    return out


def rows():
    cx = R.V.Ctx()
    est = R.X.legacy_estates()
    vints = {'vt:%s:%s' % (v['wine'], v['label']) for v in L.read_table('identity/vintages.jsonl')}
    slug, e = est[ESTATE]
    if e.get('name') != cx.nm.get(WINE):
        raise Stop('%s is not the grand vin of the legacy estate record %s' % (WINE, slug))
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    gitstate = PV.git_state(L.ROOT)
    fp = E.decider_fingerprint()
    out = []
    for g, res, a in allow_list():
        aid, sha, y = res['artifact'], g['sha256'], a['vintage']
        vt = 'vt:%s:%d' % (WINE, y)
        if arts.get(aid, {}).get('sha256') != sha:
            raise Stop('%s is not the model artifact of %s' % (aid, g['candidate']))
        if vt not in vints:
            raise Stop('%s does not exist in the model' % vt)
        [claim] = [c for c in a['claims'] if c['wine'] == WINE]
        ev, rd = claim['evidence_of_document'], claim['reader']
        d = {'artifact': os.path.basename(g['url']), 'kind': 'guard',
             'ctx': {'estate': slug, 'folder': 'acquisition:' + sha, 'wine': None, 'vintage': y,
                     'target_wine': cx.nm.get(WINE), 'target_role': 'grand', 'target_vintage': y,
                     'evaluated_as': '%s, vintage %d' % (cx.nm.get(WINE), y)},
             'decision': 'ACCEPTED', 'code': 'ACCEPTED', 'raw': '',
             'evidence': ['%s rule: %s' % (ev['rule'], ev['basis']),
                          'whose_sheet with year=%d, is_second=False: %s' % (y, rd['decision']),
                          'M3.9 evidence review (de365eb) %s: SAFE_TO_MAP; M3.10A artifact %s' % (g['candidate'], aid)],
             'points_at': {'role': None, 'wine': None},
             'read': {'path': g['acquisition_path'][len('sources/'):], 'sha256': sha, 'bytes': g['bytes'],
                      'extraction': 'acquisition/m3.8/extracted/%s.json' % sha},
             'git': gitstate, 'reader': fp, 'v': VERSION, 're_evaluable': True}
        rk = M6.row_key(d)
        man = {'record': 'decision', 'candidate': g['candidate'], 'artifact': aid, 'sha256': sha, 'url': g['url'],
               'estate': ESTATE, 'wine': WINE, 'wine_name': cx.nm.get(WINE), 'vintage': y, 'vintage_id': vt,
               'document_type': a['m38_genre'], 'language': a['language'], 'identity_source': ev['rule'],
               'identity_region': 'the document\'s opening text', 'vintage_source': a['vintage_evidence'],
               'supporting_evidence': ev['basis'], 'reader_decision': rd['decision'], 'decider': fp,
               'evidence_decision': rk, 'evidence_version': VERSION,
               'attribution': S.hid('Attribution', aid, 'm310b', vt), 'role': 'FIRST',
               'same_claim_as': None,
               'stages': {'artifact_registered': 'M3.10A', 'evidence_accepted': 'M3.10B (v%d)' % VERSION,
                          'attribution_applied': 'M3.10B (migration)', 'value_applied': NOT_YET},
               'result': 'APPLIED'}
        out.append({'manifest': man, 'decision': d})
    by_claim = collections.defaultdict(list)
    for x in out:
        by_claim[x['manifest']['vintage_id']].append(x['manifest'])
    for ms in by_claim.values():
        for m in ms:
            others = [o['artifact'] for o in ms if o is not m]
            m['same_claim_as'] = others or None          # 2014: two artifacts of one claim, not two claims
    out.sort(key=lambda x: (x['manifest']['vintage'], x['manifest']['artifact']))
    return out


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def report(ms):
    out = []
    w = out.append
    w('# Phase M3.10B — Durfort-Vivens evidence decisions\n')
    w('Generated by `python tools/m310b-accept.py` (`data/audit/m3.10b-evidence-decisions.jsonl`); never edited by '
      'hand. **M3.10B stops before canonical value application.** Four documents become accepted evidence for their '
      'exact wine and vintage, and are attributed in the model; no observation, reconciliation or canonical value is '
      'created. M3.10C applies the values.\n')
    w('## 1. The four decisions\n')
    w('Evidence decider version %d, appended; v1-v8 byte for byte. Each is an ACCEPTED `guard` row - the evidence '
      'store\'s reader accepting a sheet, as v1-v5\'s acceptances - asking the grand-vin question of Château '
      'Durfort-Vivens (`%s`) for its vintage, read from the bytes M3.8 acquired and M3.10A registered.\n' % (VERSION, WINE))
    w('| Candidate | Artifact | Document | Vintage | Type | Language | Identity | Vintage stated as | Attribution |')
    w('|---|---|---|---:|---|---|---|---|---|')
    for m in ms:
        w('| %s | `%s` | %s | %d | %s | %s | %s | %s | `%s` |' % (
            m['candidate'], m['artifact'], m['url'].rsplit('/', 1)[-1], m['vintage'], m['document_type'],
            m['language'] or '—', m['identity_source'], m['vintage_source'].replace('|', '/'), m['attribution']))
    w('\nThe basis of each, as M3.9 recorded it and as the existing reader gives it again: "%s"; `whose_sheet` raised no '
      'objection. The decider fingerprint is `%s`, as v6-v8\'s.\n' % (ms[0]['supporting_evidence'], ms[0]['decider']))
    w('## 2. Stages\n')
    w('| Stage | Status |')
    w('|---|---|')
    for k, v in ms[0]['stages'].items():
        w('| %s | %s |' % (k.replace('_', ' '), v))
    w('')
    w('## 3. The 2014 English and French sheets\n')
    w('Two accepted artifacts of one claim, Château Durfort-Vivens 2014: two decisions and two attributions, because '
      'both documents are real evidence; no observation, no reconciliation, no conflict. M3.10C treats their matching '
      'statements as one observation.\n')
    w('## 4. Not applied\n')
    w('- 2014: blend, ageing, new oak. 2021: alcohol. 2024: blend, oak, picking, yield, ageing.')
    w('- The 2024 oak discrepancy (the reader read 30; the document states "70% in new barrels and 30% in TAVA '
      'amphorae") stays where M3.9 recorded it; no oak value is created.')
    w('- The data-gap register is unchanged: M3.10B\'s attributions are a later linking phase, set aside as M3.4B\'s, '
      'M3.5\'s and M3.6B\'s are. That they document Durfort-Vivens 2014 and 2024 is recorded on the register\'s '
      '"no document" gap once this phase\'s commit exists, as for M3.6B.')
    w('- 2021 already had two documents in the model; the certificate is a third, not a first.\n')
    return ('\n'.join(out) + '\n').encode('utf-8')


def in_head(commit):
    return subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=L.ROOT).returncode == 0


def stored():
    return list(ST.iter_rows([VERSION])) if VERSION in ST.versions() else []


def main():
    try:
        if '--check' in sys.argv:
            got = rows()
            ms = [x['manifest'] for x in got]
            bad = []
            if body(ms) != open(MANIFEST, 'rb').read():
                bad.append('the manifest')
            if report(ms) != open(REPORT, 'rb').read():
                bad.append('the report')
            have = {M6.row_key(d): d for d in stored()}
            want = {x['manifest']['evidence_decision']: x['decision'] for x in got}
            if set(have) != set(want):
                bad.append('v%d is not exactly the manifest\'s decisions' % VERSION)
            for k in sorted(set(want) & set(have)):
                a, b = dict(want[k]), dict(have[k])
                ga, gb = a.pop('git'), b.pop('git')
                if a != b or not gb.get('commit') or not in_head(gb['commit']):
                    bad.append('v%d decision %s' % (VERSION, k[:50]))
            print('M3.10B ' + ('is current' if not bad else 'differs: %s' % bad))
            sys.exit(1 if bad else 0)
        if '--apply' in sys.argv:
            if VERSION in ST.versions():
                raise Stop('v%d already exists' % VERSION)
            if ST.versions()[-1] != VERSION - 1:
                raise Stop('the store\'s last version is %d, not %d' % (ST.versions()[-1], VERSION - 1))
            got = rows()
            n = ST.append([x['decision'] for x in got], VERSION)
            ms = [x['manifest'] for x in got]
            open(MANIFEST, 'wb').write(body(ms))
            open(REPORT, 'wb').write(report(ms))
            print('%d decision(s) appended to v%d; manifest and report written' % (n, VERSION))
            return
        print(__doc__)
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)


if __name__ == '__main__':
    main()
