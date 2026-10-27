"""M3.6H: correct the one Cuvée Mongravey acceptance M3.6E did not see - append-only.

    python tools/m36h-apply.py --apply     preflight; the superseding v8 decision and the manifest
    python tools/m36h-apply.py --check     recompute what is written and compare (see VERIFYING)

THE ALLOW-LIST is M3.6G's committed audit (data/audit/m3.6g-cuvee-acquisition.jsonl) and nothing else: its
one `finding`, ar_010314 (FT-Cuvee-Mongravey-2015.pdf, the 2023/09 FR sheet), whose latest answer to
"is this Château Mongravey, vintage 2015?" is still the v5 acceptance. M3.6C never saw it: the model held no
text for it, so it is not on the list M3.6E corrected. The same sheet's other question, "...vintage 1999?",
is already REFUSED (WRONG_VINTAGE) and stays as it is, as M3.6E left every such refusal. A finding, a
question or a latest answer that differs stops the run.

THE READING, THE REPRESENTATION AND VERIFYING are M3.6E's (tools/m36e-apply.py), used from that tool, not
copied: the document is judged again by tools/m35_rubric.judge() and must be WRONG_EXISTING_ATTRIBUTION with
a title that folds to a name M3.6D recorded for wn_00640; the correction is one REFUSED row (kind
correction, code WRONG_WINE) asking exactly the superseded decision's question, so latest_by_context() reads
it, with `document_is` naming wn_00640 and the 2015 title. Decider version 8 has the same rules as v6 and v7
(tools/m35_rubric.py, tools/web_evidence.py), so the same reader fingerprint. v1-v7 stay byte for byte.

The model is not changed: it reads evidence links from v4-v5 only (mig_m6_provenance.evidence_links). No
attribution is made: vt:wn_00640:2015 and its values are M3.6F's and stay as they are; wn_00158, wn_00640,
their names, ranks and estate stand.
"""
import collections
import copy
import importlib.util
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import evidence as EV  # noqa: E402
import evidence_store as ST  # noqa: E402
import migration_lib as L  # noqa: E402
import mig_m6_provenance as M6  # noqa: E402

_e = importlib.util.spec_from_file_location('m36e', L.ROOT + 'tools/m36e-apply.py')
E = importlib.util.module_from_spec(_e)
_e.loader.exec_module(E)
Stop = E.Stop

VERSION = 8
M36G = 'data/audit/m3.6g-cuvee-acquisition.jsonl'
MANIFEST = L.ROOT + 'data/audit/m3.6h-cuvee-2015-correction.jsonl'
WINE, GRAND_VIN = E.WINE, E.GRAND_VIN
EXPECT = {('Château Mongravey', 2015): ('ACCEPTED', 'ACCEPTED', 5),
          ('Château Mongravey', 1999): ('REFUSED', 'WRONG_VINTAGE', 5)}
NOTE = ('the document is Cuvée Mongravey (wn_00640), its %s vintage; this correction refuses the grand-vin '
        'reading and attributes nothing: vt:wn_00640:2015 and its values are M3.6F\'s and stay as they are')


def latest_before():
    """evidence_store.latest_by_context() over the versions before this one: the answers M3.6H corrects."""
    out = {}
    for d in ST.iter_rows([v for v in ST.versions() if v < VERSION]):
        k = EV.row_key(d)[:-1]
        if k not in out or (d.get('v') or 0) >= (out[k].get('v') or 0):
            out[k] = d
    return out


def allow_list():
    """M3.6G's one finding, and the latest answers to every question asked of its bytes."""
    found = [r for r in L.jsonl_lines(L.ROOT + M36G) if r['record'] == 'finding']
    if len(found) != 1:
        raise Stop('M3.6G records %d findings, expected 1' % len(found))
    f = found[0]
    arts = [a for a in L.read_table('identity/artifacts.jsonl') if a['id'] == f['artifact']]
    if len(arts) != 1 or not arts[0].get('sha256'):
        raise Stop('%s is not one artifact with bytes' % f['artifact'])
    sha = arts[0]['sha256']
    asked = {}
    for d in latest_before().values():
        if (d.get('read') or {}).get('sha256') == sha:
            c = d.get('ctx') or {}
            asked[(c.get('target_wine'), c.get('target_vintage'))] = d
    got = {k: (d['decision'], d.get('code'), d['v']) for k, d in asked.items()}
    if got != EXPECT:
        raise Stop('the questions asked of %s differ: %s, expected %s' % (f['artifact'], got, EXPECT))
    cur = asked[('Château Mongravey', 2015)]
    if f['asked'] != cur['ctx']['evaluated_as']:
        raise Stop('M3.6G\'s finding asks "%s", the decision "%s"' % (f['asked'], cur['ctx']['evaluated_as']))
    return f, arts[0], cur, asked[('Château Mongravey', 1999)]


def rows(k):
    f, art, cur, kept = allow_list()
    rk = M6.row_key(cur)
    r = {'id': rk, 'artifact': art['id'], 'sha256': art['sha256'], 'claimed': {'vintage': cur['ctx']['target_vintage']}}
    j, name, fail = E.read(k, r, cur)
    ctx = cur.get('ctx') or {}
    title = j['title'] if j else None
    ln = k.cx.ln.get(rk) or {}
    man = {'record': 'correction', 'decision': rk, 'artifact': art['id'], 'sha256': art['sha256'],
           'path': cur['read']['path'], 'found_by': 'M3.6G finding',
           'asked': {'estate': ctx.get('estate'), 'wine': ctx.get('target_wine'), 'vintage': ctx.get('target_vintage')},
           'linked_to': {'estate': ln.get('estate'), 'wine': ln.get('wine')},
           'superseding': {'row_key': rk, 'v': cur['v'], 'decision': cur['decision'], 'code': cur.get('code')},
           'document_title': title, 'judged': j['disposition'] if j else None,
           'outcome': 'CUVEE_MONGRAVEY' if name and not fail else 'UNRESOLVED',
           'wine': WINE if name and not fail else None, 'name_kind': name['kind'] if name else None,
           'vintage_stated': title[1] if title else None, 'vintage_created': False, 'attributed': False,
           'failures': sorted(set(fail))}
    if ln.get('wine') != GRAND_VIN:
        raise Stop('the v5 link of %s names %s, not %s' % (rk[:60], ln.get('wine'), GRAND_VIN))
    same = {'record': 'unchanged', 'decision': M6.row_key(kept), 'artifact': art['id'],
            'asked': {'estate': kept['ctx'].get('estate'), 'wine': kept['ctx'].get('target_wine'),
                      'vintage': kept['ctx'].get('target_vintage')},
            'latest': {'v': kept['v'], 'decision': kept['decision'], 'code': kept.get('code')},
            'why': 'already REFUSED; M3.6E superseded acceptances and no-wine refusals only, and left every '
                   'WRONG_VINTAGE refusal as it stands'}
    if man['outcome'] != 'CUVEE_MONGRAVEY':
        return [{'manifest': dict(man, superseded_by=None, result='UNRESOLVED'), 'decision': None},
                {'manifest': same, 'decision': None}]
    new ={'artifact': cur.get('artifact'), 'kind': 'correction', 'ctx': copy.deepcopy(ctx),
           'decision': 'REFUSED', 'code': 'WRONG_WINE',
           'raw': 'the title is "%s", %s of %s (Cuvée Mongravey); not %s' % (
               title[0], name['kind'], WINE, ctx.get('target_wine')),
           'evidence': ['the document\'s title reads "%s"' % ' '.join(str(x) for x in title if x),
                        'm35_rubric.judge: WRONG_EXISTING_ATTRIBUTION: %s' % j['basis'],
                        'M3.6G acquisition audit: finding (latest answer still the v5 acceptance)',
                        'M3.6D: "%s" is the %s name of %s' % (name['name'], name['kind'], WINE)],
           'points_at': {'role': None, 'wine': WINE},
           'supersedes': {'row_key': rk, 'v': cur['v'], 'decision': cur['decision'], 'code': cur.get('code')},
           'replacement': {'decision': None, 'attribution': None, 'note': NOTE % title[1]},
           'document_is': {'title': title, 'model_wines': [WINE], 'unlisted': False},
           'read': copy.deepcopy(cur['read']), 'git': k.git, 'reader': k.fp, 'v': VERSION, 're_evaluable': True}
    nk = M6.row_key(new)
    if json.loads(nk)[:-1] != json.loads(rk)[:-1]:
        raise Stop('the superseding decision does not ask its decision\'s question: %s' % rk[:60])
    return [{'manifest': dict(man, superseded_by=nk, result='APPLIED'), 'decision': new},
            {'manifest': same, 'decision': None}]


def stored():
    return list(ST.iter_rows([VERSION])) if VERSION in ST.versions() else []


def main():
    try:
        k = E.Ctx()
        if '--check' in sys.argv:
            got = rows(k)
            bad = []
            if E.body([x['manifest'] for x in got]) != open(MANIFEST, 'rb').read():
                bad.append('the manifest')
            have = {M6.row_key(d): d for d in stored()}
            want = {x['manifest']['superseded_by']: x['decision'] for x in got if x['decision']}
            if set(have) != set(want):
                bad.append('v8 is not exactly the manifest\'s decision')
            bad += ['v8 decision %s' % key[:50] for key in sorted(want)
                    if key in have and not E.same_but_git(want[key], have[key])]
            print('M3.6H ' + ('is current' if not bad else 'differs: %s' % bad[:5]))
            sys.exit(1 if bad else 0)
        if '--apply' in sys.argv:
            if VERSION in ST.versions():
                raise Stop('v%d already exists' % VERSION)
            got = rows(k)
            n = ST.append([x['decision'] for x in got if x['decision']], VERSION)
            open(MANIFEST, 'wb').write(E.body([x['manifest'] for x in got]))
            c = collections.Counter(x['manifest'].get('outcome', x['manifest']['record']) for x in got)
            print('%d superseding decision(s) appended to v%d (reader %s, git %s%s); %s; manifest written'
                  % (n, VERSION, k.fp, k.git['commit'][:12], ' dirty' if k.git['dirty'] else '', dict(sorted(c.items()))))
            return
        print(__doc__)
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)


if __name__ == '__main__':
    main()
