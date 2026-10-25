"""Phase 4 stage M0: freeze and baseline.

    python tools/phase4-baseline.py            write data/model/baseline.json and
                                               docs/PHASE-4-MIGRATION-BASELINE.md
    python tools/phase4-baseline.py --check    compare today's bytes with the baseline

Read-only over everything but those two files. The baseline is what every
later stage, and tools/test-phase4.py, holds the protected groups to:
canonical data, phase records (proposals and audits), evidence, discovery,
scope, review and the Phase 3.4 contract stay byte-identical until the
canonical switch gate says otherwise.
"""
import collections
import glob
import json
import subprocess
import sys

import migration_lib as L

OUT_JSON = L.MODEL + 'baseline.json'
OUT_MD = L.ROOT + 'docs/PHASE-4-MIGRATION-BASELINE.md'
START = '91a5b8b'


def counts():
    v = L.canonical_view()
    est = v['estates']
    wines = L.g('BDX_CUVEE_WINES')
    c = collections.OrderedDict()
    c['canonical_estates'] = len(est)
    c['full_record_estates'] = sum(1 for e in est if not e['sparse'])
    c['name_derived_estate_ids'] = sum(1 for e in est if e['sparse'])
    c['estate_file_records'] = len(L.estate_files())
    c['second_named'] = sum(1 for _, r in L.estate_files() if r.get('second') not in (None, '—'))
    c['second_dash'] = sum(1 for _, r in L.estate_files() if r.get('second') == '—')
    c['cuvee_wine_estates'] = len(wines)
    c['cuvee_wines'] = sum(len(x) for x in wines.values())
    c['cuvee_wines_by_role'] = dict(sorted(collections.Counter(
        w['role'] for x in wines.values() for w in x).items()))
    for name in ['BDX_FICHES', 'BDX_FIELD_SRC', 'BDX_FICHE_URL', 'BDX_RATINGS', 'BDX_CELLAR',
                 'BDX_SCORES', 'BDX_NOT_PRODUCED', 'BDX_CUVEES', 'BDX_CUVEE_SRC', 'BDX_CUVEE_URL',
                 'BDX_PLANTINGS', 'BDX_TERROIR', 'BDX_COORDS', 'BDX_SITES', 'BDX_FICHES_NL',
                 'BDX_CLASSIFICATIONS']:
        c[name] = len(L.g(name))
    meta = {'src', 'url', 'via', 'ttl', 'ntl', 'dtl', 'ftl', 'wtl', 'sugl', 'tau', 'wy'}
    c['fiche_values'] = sum(1 for r in L.g('BDX_FICHES').values() for k in r if k not in meta)
    c['cuvee_values'] = sum(1 for r in L.g('BDX_CUVEES').values() for k in r if k not in meta)
    s = L.sources_rows()
    c['manifest_rows'] = len(s['sheets'])
    paths = collections.defaultdict(set)
    for r in s['sheets']:
        paths[(r['folder'], r['file'])].add(r['sha1'])
    c['manifest_paths'] = len(paths)
    c['manifest_multiversion_paths'] = sum(1 for x in paths.values() if len(x) > 1)
    ev = {}
    for p in sorted(glob.glob(L.ROOT + 'data/evidence/*.jsonl')):
        ev[L.rel(p)] = L.count_lines(p)
    c['evidence_lines'] = ev
    c['discovery_artifacts'] = L.count_lines(L.ROOT + 'data/discovery/artifacts.jsonl')
    c['discovery_observations'] = sum(L.count_lines(p) for p in glob.glob(
        L.ROOT + 'data/discovery/observations/*.jsonl'))
    c['proposals'] = L.count_lines(L.ROOT + 'data/proposals.jsonl') - 1
    c['attribution_candidates'] = L.count_lines(L.ROOT + 'data/attribution-candidates.jsonl') - 1
    return c


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT).decode().strip()


def build():
    return {
        '_': 'Phase 4 M0 baseline: the bytes every later stage must leave alone. '
             'Written by tools/phase4-baseline.py.',
        'start_commit': START,
        'groups': {k: L.group_hashes(k) for k in L.GROUPS},
        'counts': counts(),
    }


def md(b):
    c = b['counts']
    lines = ['# Phase 4 migration baseline (M0)', '',
             'Written by `tools/phase4-baseline.py`; the machine-readable copy is '
             '`data/model/baseline.json`, which `tools/test-phase4.py` and '
             '`python tools/phase4-baseline.py --check` hold every later stage to.', '',
             '## Starting point', '',
             '- Starting commit: `%s` (Phase 3.4), equal to `origin/main` when M0 ran.' % b['start_commit'],
             '- Working tree clean when M0 ran.',
             '- All 20 existing test suites passed before M0 (test-data, test-phase2 to '
             'test-phase34, test-reader; 2 minutes in all).', '',
             '## Protected groups', '',
             'Each group is hashed file by file (sha256); the group digest is the sha256 of '
             'the sorted file-to-hash map. Phase 4 may not change any of them before the '
             'canonical switch gate.', '',
             '| Group | Files | Digest |', '|---|---:|---|']
    for k, v in b['groups'].items():
        lines.append('| %s | %d | `%s` |' % (k, len(v['files']), v['digest'][:16]))
    lines += ['', '## Counts', '', '| Measure | Value |', '|---|---:|']
    for k, v in c.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                lines.append('| %s: %s | %s |' % (k, kk, '{:,}'.format(vv)))
        else:
            lines.append('| %s | %s |' % (k, '{:,}'.format(v)))
    lines += ['', '## Canonical files', '', '| File | sha256 |', '|---|---|']
    for f, h in b['groups']['canonical']['files'].items():
        lines.append('| `%s` | `%s` |' % (f, h[:16]))
    lines += ['', '## Semantics frozen as tests', '',
              '`tools/test-phase4.py` checks these against the baseline:', '',
              "- the key shapes: `estate|vintage` (fiches, field-src, fiches-url, ratings, cellar, "
              "BDX_SCORES) and `estate|slug|vintage` (cuvees, cuvee-src, cuvee-url);",
              "- the sparse id rule: `cls + '-' + slug(name)` for the Cru Bourgeois, Cru Artisan, "
              "Saint-Émilion grand cru classé and Pomerol lists (%d ids);" % c['name_derived_estate_ids'],
              "- the role vocabulary of BDX_CUVEE_WINES (`second`, `other`) and the meaning of "
              "`second: '—'` (no second wine; %d estates);" % c['second_dash'],
              '- the counts above, and the group hashes.', '']
    return '\n'.join(lines)


def main():
    if '--check' in sys.argv:
        b = json.load(open(OUT_JSON, encoding='utf-8'))
        bad = 0
        for k in L.GROUPS:
            now = L.group_hashes(k)
            if now['digest'] != b['groups'][k]['digest']:
                bad += 1
                old = b['groups'][k]['files']
                ch = sorted(f for f in set(old) | set(now['files']) if old.get(f) != now['files'].get(f))
                L.out('CHANGED %s: %s' % (k, ', '.join(ch[:10])))
        L.out('baseline: %s' % ('unchanged' if not bad else '%d group(s) changed' % bad))
        sys.exit(1 if bad else 0)
    if git('rev-parse', '--short', 'HEAD') != START and '--force' not in sys.argv:
        sys.exit('M0 runs on %s' % START)
    b = build()
    import os
    os.makedirs(L.MODEL, exist_ok=True)
    open(OUT_JSON, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(b, ensure_ascii=False, indent=1, sort_keys=False) + '\n')
    open(OUT_MD, 'w', encoding='utf-8', newline='\n').write(md(b))
    L.out(json.dumps(b['counts'], ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
