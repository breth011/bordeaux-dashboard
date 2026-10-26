"""Phase 4 M9: dual read. The old reader and the new one, side by side.

    python tools/dual-read.py          write data/model/checks/dual-read.json
    python tools/dual-read.py --check  exit 1 on any disagreement

Two comparisons:

1. The page's path. The model is projected (tools/model_reader.py) and
   written as data files into a temporary directory (never data/); the
   page's own estate expansion (tools/canonical-view.js, the replica of
   app.js that test-phase30 guards) runs over the legacy data/ and over
   the generated directory, and the two estate lists are compared.

2. Queries. For every key the legacy files hold, the old reader looks it
   up in the legacy global; the new reader resolves the legacy key through
   the identity map to a model subject (an Estate, a Vintage) and reads
   that subject's observations, canonical values, relationships and legacy
   references. They must agree.

Nothing outside data/model/checks/ is written; the temporary directory is
removed.
"""
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile

import migration_lib as L
import model_reader as R

OUT = L.MODEL + 'checks/dual-read.json'


def write_js(dirpath, proj):
    """The projection as page-loadable files; files outside the contract
    are copied as they are (the page keeps reading them, D7)."""
    for f in sorted(os.listdir(L.ROOT + 'data')):
        if f.endswith('.js') and f not in proj:
            shutil.copyfile(L.ROOT + 'data/' + f, os.path.join(dirpath, f))
    for f, globs in proj.items():
        if not f.endswith('.js'):
            continue
        # The estate files append to one shared list, as the legacy files do.
        body = ''
        for g, v in sorted(globs.items()):
            js = json.dumps(v, ensure_ascii=False, sort_keys=True)
            if g == 'BDX_CHATEAUX':
                body += 'window.%s = (window.%s || []).concat(%s);\n' % (g, g, js)
            else:
                body += 'window.%s = %s;\n' % (g, js)
        if f == 'classifications.js':
            continue
        open(os.path.join(dirpath, f), 'w', encoding='utf-8').write(body)


def canonical_view(datadir=None):
    args = [L.node(), L.ROOT + 'tools/canonical-view.js'] + ([datadir] if datadir else [])
    return json.loads(subprocess.check_output(args, cwd=L.ROOT).decode('utf-8'))


def page_path(proj):
    tmp = tempfile.mkdtemp(prefix='bdx-dual-read-')
    try:
        write_js(tmp, proj)
        old, new = canonical_view(), canonical_view(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    diffs = []
    if old['collections'] != new['collections']:
        diffs.append('collections differ')
    o = {e['id']: e for e in old['estates']}
    n = {e['id']: e for e in new['estates']}
    for k in sorted(set(o) | set(n)):
        a, b = o.get(k), n.get(k)
        if a is None or b is None:
            diffs.append('%s only in %s' % (k, 'old' if b is None else 'new'))
            continue
        a = dict(a, wines=sorted(a['wines'], key=json.dumps))
        b = dict(b, wines=sorted(b['wines'], key=json.dumps))
        for f in sorted(set(a) | set(b)):
            if a.get(f) != b.get(f):
                diffs.append('%s.%s: old %r / new %r' % (k, f, a.get(f), b.get(f)))
    return {'estates_old': len(o), 'estates_new': len(n),
            'order_differs': [e['id'] for e in old['estates']] != [e['id'] for e in new['estates']],
            'disagreements': diffs}


class NewReader:
    """Queries answered from the model's entities, legacy keys resolved
    through the identity map."""

    def __init__(self):
        M = R.Model()
        self.im = collections.defaultdict(dict)
        for r in M.rows('identity/identity-map.jsonl'):
            self.im[r['namespace']][r['legacy_key']] = r
        self.obs = collections.defaultdict(list)
        for o in M.rows('observation/observations.jsonl'):
            self.obs[o['subject']].append(o)
        self.canon = {(c['subject'], c['field']): c['value'] for c in M.rows('canonical/values.jsonl')}
        self.refs = {(r['origin'], r['record_key'], r.get('field')): r['basename']
                     for r in M.rows('document/legacy-references.jsonl')}
        self.names = collections.defaultdict(list)
        for n in M.rows('identity/names.jsonl'):
            self.names[n['subject']].append(n['name'])
        self.rels = collections.defaultdict(list)
        for r in M.rows('state/estate-wine.jsonl'):
            self.rels[r['estate']].append(r['wine'])
        # the manifest's sheets per estate: its own attributions, not M3.4B's audited links
        manifest = {p['id'] for p in M.rows('cross/provenance.jsonl') if p['kind'] == 'LEGACY_MANIFEST'}
        self.att = collections.Counter(a.get('estate') for a in M.rows('document/attributions.jsonl')
                                       if a['provenance'] in manifest)

    def _vintage(self, ns, key):
        r = self.im[ns].get(key)
        return r.get('stable_id') if r else None

    def _record(self, subject, file, skip=()):
        rec = {}
        for o in self.obs.get(subject, []):
            if o['extraction']['file'] != file or o['field'] in skip:
                continue
            rec[o['field']] = self.canon.get((subject, o['field']), o['value'])
            rec.update(o['extraction'].get('field_meta') or {})
            rec.update(o['extraction'].get('record_meta') or {})
        return rec or None

    def fiche(self, key):
        v = self._vintage('estate|vintage', key)
        return self._record(v, 'data/fiches.js') if v else None

    def cuvee(self, key):
        v = self._vintage('estate|slug|vintage', key)
        return self._record(v, 'data/cuvees.js') if v else None

    def rating(self, key):
        v = self._vintage('estate|vintage', key)
        r = self._record(v, 'data/ratings.js') if v else None
        return r['rating'] if r else None

    def field_source(self, origin, key, field):
        return self.refs.get((origin, key, field))

    def wine_names(self, lid):
        e = self.im['estate'][lid].get('stable_id')
        return sorted(n for w in self.rels.get(e, []) for n in self.names[w])

    def sheets(self, lid):
        return self.att.get(self.im['estate'][lid].get('stable_id'), 0)


def queries():
    new = NewReader()
    out = collections.Counter()
    bad = []

    def agree(q, k, a, b):
        out[q] += 1
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            bad.append('%s %r: old %s / new %s' % (q, k, json.dumps(a)[:80], json.dumps(b)[:80]))
    unresolved = {(n, k) for n, k in kept_keys()}
    for k, v in L.g('BDX_FICHES').items():
        if ('BDX_FICHES', k) not in unresolved and not is_empty(v):
            agree('fiche', k, v, new.fiche(k))
    for k, v in L.g('BDX_CUVEES').items():
        if ('BDX_CUVEES', k) not in unresolved:
            agree('cuvee', k, v, new.cuvee(k))
    for k, v in L.g('BDX_RATINGS').items():
        if ('BDX_RATINGS', k) not in unresolved:
            agree('rating', k, v, new.rating(k))
    for origin, name in (('field-src.js', 'BDX_FIELD_SRC'), ('cuvee-src.js', 'BDX_CUVEE_SRC')):
        for k, fields in L.g(name).items():
            for f, b in fields.items():
                agree('field source', (k, f), b, new.field_source(origin, k, f))
    names = collections.defaultdict(list)
    for e in L.canonical_view()['estates']:
        names[e['id']].append(e['name'])
        for w in e['wines']:
            names[e['id']].append(w['name'])
    sec = {r['id']: r.get('second') for _, r in L.estate_files()}
    # M3.6D's Cuvée Mongravey: a wine of the model that no legacy file lists, so the old view cannot hold it
    m36d_prov = {p['id'] for p in L.read_table('cross/provenance.jsonl') if p.get('actor') == 'tools/m36d-cuvee.py'}
    m36d_names = {n['name'] for n in L.read_table('identity/names.jsonl') if n['provenance'] in m36d_prov}
    for lid, ns in names.items():
        # the new reader's wines: the grand vin, the listed wines, the seconds it minted, M3.6D's wine;
        # the old view's: the estate name and its listed wines. Compare what both hold.
        got = new.wine_names(lid)
        want = sorted(set(ns))
        extra = sorted(set(got) - set(want))
        out['estate wines'] += 1
        if set(want) - set(got) - ({names[lid][0]} if not got else set()):
            bad.append('estate wines %r: old %s / new %s' % (lid, want, got))
        for x in extra:
            if x != sec.get(lid) and x not in m36d_names:
                bad.append('estate wines %r: new holds %r' % (lid, x))
    man = collections.Counter(r['estate'] for r in L.sources_rows()['sheets'] if r['estate'])
    for lid, c in man.items():
        agree('sheets per estate', lid, c, new.sheets(lid))
    return dict(out), bad


def kept_keys():
    for p in L.jsonl_lines(L.MODEL + 'cross/provenance.jsonl'):
        cs = p.get('code_state') or {}
        if cs.get('unresolved'):
            yield cs['global'], cs['key']


def is_empty(rec):
    return not [f for f in rec if f not in ('src', 'url', 'via', 'wy', 'ttl', 'ntl', 'dtl', 'ftl',
                                            'wtl', 'sugl', 'tau')]


def build():
    proj = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
    page = page_path(proj)
    q, bad = queries()
    return {'_': 'Phase 4 M9: the old reader and the new one, side by side (tools/dual-read.py).',
            'page_path': page, 'queries': q, 'query_disagreements': bad,
            'pass': not page['disagreements'] and not bad}


def main():
    r = build()
    if '--check' not in sys.argv:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(r, ensure_ascii=False, indent=1) + '\n')
    L.out('page path: %d / %d estates, %d disagreement(s)' % (
        r['page_path']['estates_old'], r['page_path']['estates_new'], len(r['page_path']['disagreements'])))
    for d in r['page_path']['disagreements'][:20]:
        L.out('  ' + d)
    L.out('queries: %s' % json.dumps(r['queries']))
    for d in r['query_disagreements'][:20]:
        L.out('  ' + d)
    L.out('DUAL READ ' + ('PASS' if r['pass'] else 'FAIL'))
    sys.exit(0 if r['pass'] else 1)


if __name__ == '__main__':
    main()
