"""Phase 4 M13: derived indexes over the normalized model.

    python tools/build-indexes.py          (re)build data/model/derived/*.json
    python tools/build-indexes.py --check  exit 1 unless each index rebuilds byte for byte

Every index is computed from the model's tables and nothing else, and no
table refers to an index: deleting data/model/derived/ loses no fact. They
exist for the application's lookups (M12):

  estate-wines            estate -> the wines it produces (any relationship kind)
  wine-vintages           wine -> its vintage labels
  vintage-documents       vintage -> the artifacts attributed to it or cited as a
                          field's source for one of its values
  source-documents        source -> the artifacts placed at a URL on its host
  wine-current-rank       wine -> rank claims whose validity is still open
  estate-classifications  estate -> classification memberships of its wines
"""
import collections
import json
import os
import sys
from urllib.parse import urlparse

import migration_lib as L
import model_reader as R

DERIVED = 'derived/'


def build():
    M = R.Model()
    rows = M.rows
    rels = rows('state/estate-wine.jsonl')
    rel = {r['id']: r for r in rels}
    idx = {}
    ew = collections.defaultdict(set)
    for r in rels:
        ew[r['estate']].add(r['wine'])
    idx['estate-wines'] = ew
    wv = collections.defaultdict(set)
    for v in rows('identity/vintages.jsonl'):
        wv[v['wine']].add(v['label'])
    idx['wine-vintages'] = wv
    vd = collections.defaultdict(set)
    for a in rows('document/attributions.jsonl'):
        if a.get('vintage'):
            vd[a['vintage']].add(a['artifact'])
    prov = {p['id']: p for p in rows('cross/provenance.jsonl')}
    for o in rows('observation/observations.jsonl'):
        p = prov[o['provenance']]
        if o['subject'].startswith('vt:') and p.get('artifact') and p['kind'] == 'LEGACY_FIELD_SOURCE':
            vd[o['subject']].add(p['artifact'])
    idx['vintage-documents'] = vd
    host = {}
    for s in rows('identity/sources.jsonl'):
        if s['name'] and '.' in s['name'] and ' ' not in s['name']:
            host[s['name']] = s['id']
    sd = collections.defaultdict(set)
    for p in rows('document/placements.jsonl'):
        if p['locator']['kind'] == 'URL' and p.get('artifact'):
            h = urlparse(p['locator']['value']).netloc.lower().removeprefix('www.')
            if h in host:
                sd[host[h]].add(p['artifact'])
    idx['source-documents'] = sd
    cr = collections.defaultdict(list)
    for r in rows('state/rank-assertions.jsonl'):
        if r['validity']['valid_to']['kind'] == 'OPEN':
            cr[rel[r['relationship']]['wine']].append({k: r[k] for k in ('tier', 'scope', 'claimant')
                                                       if k in r} | ({'legacy_term': r['legacy_term']}
                                                                     if 'legacy_term' in r else {}))
    idx['wine-current-rank'] = cr
    ed = {e['id']: e for e in rows('state/classification-editions.jsonl')}
    producer = collections.defaultdict(set)
    for r in rels:
        producer[r['wine']].add(r['estate'])
    ec = collections.defaultdict(list)
    for m in rows('state/classification-memberships.jsonl'):
        for e in producer[m['wine']]:
            ec[e].append({'wine': m['wine'], 'edition': m['edition'], 'label': ed[m['edition']]['label'],
                          'rank': m.get('rank')})
    idx['estate-classifications'] = ec
    out = {}
    for name, d in idx.items():
        clean = {k: (sorted(v) if isinstance(v, set) else sorted(v, key=L.dumps)) for k, v in sorted(d.items())}
        out[name] = (json.dumps(clean, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
    return out


def main():
    files = build()
    if '--check' in sys.argv:
        bad = [n for n, b in files.items()
               if not os.path.exists(L.MODEL + DERIVED + n + '.json')
               or open(L.MODEL + DERIVED + n + '.json', 'rb').read() != b]
        L.out('indexes ' + ('rebuild byte for byte' if not bad else 'stale: ' + ', '.join(bad)))
        sys.exit(1 if bad else 0)
    os.makedirs(L.MODEL + DERIVED, exist_ok=True)
    for n, b in files.items():
        open(L.MODEL + DERIVED + n + '.json', 'wb').write(b)
        L.out('%-24s %8d bytes' % (n, len(b)))


if __name__ == '__main__':
    main()
