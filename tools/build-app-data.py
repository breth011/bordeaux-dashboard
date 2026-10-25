"""Phase 5: the application's data files, generated from the normalized model.

    python tools/build-app-data.py          write data/app/*.js
    python tools/build-app-data.py --check  exit 1 unless data/app/ is exactly what the model gives

normalized model -> generated application data -> application. The model is
projected by tools/model_reader.py (the projection M8 compared with today's
files and M9 read side by side with them) and written as page-loadable
files, one per data file the page used to load, with the same globals: the
23 files of the M12 boundary (CONTRACT). The page assets outside the
contract (map geometry, notes, regional vintages, classification prose)
stay in data/ and are not generated.

Records are written in the model's order (by id): the model holds no
display order, and the reordering this causes in the producers list is
accepted, with presentation order on the backlog (docs/PHASE-5-APPLICATION-
SOURCE-SWITCH.md). Nothing here migrates, reconciles or reads the evidence,
the discovery corpus or the raw store; the application never runs it.
"""
import json
import os
import sys

import migration_lib as L
import model_reader as R

OUT = L.ROOT + 'data/app/'
# The page's data files the model projects (tools/app-boundary.py CONTRACT).
CONTRACT = ['batch2.js', 'batch3.js', 'batch4.js', 'cellar.js', 'chateaux.js', 'coords.js', 'cruartisan.js',
            'crubourgeois.js', 'cuvee-url.js', 'cuvees.js', 'fiches-nl.js', 'fiches-url.js', 'fiches.js',
            'graves.js', 'libournais.js', 'overrides.js', 'plantings.js', 'pomerol.js', 'ratings.js',
            'saintemilion.js', 'sauternes.js', 'terroir.js', 'websites.js']
HEADER = ('/* Generated from the normalized model (data/model/) by tools/build-app-data.py.\n'
          '   Do not edit: python tools/build-app-data.py rebuilds it; --check compares. */\n')


FIGURE_SOURCES = 'figure-sources.js'


def figure_sources(model=None):
    """Each vintage figure's own source, from the model (Phase 6.1).

    {record key: {field: source}} for the fiche and cuvee records, where the
    record key is the legacy 'estate|year' or 'estate|slug|year' the page
    looks records up by, and source is one of
      {"n": file, "u": url}   the field's own document, with an address
      {"n": file}             the field's own document, no address recorded
      {"a": file, "c": n}     the field names a file that n documents could be
    A field whose provenance is only its record's, or none, has no entry: it
    is shown without a source rather than given the record's sheet (I13).
    Where one document is at several addresses, the record's own address is
    used if it is one of them, otherwise the first in sorted order; all of
    them hold the same bytes."""
    M = model or R.Model()
    prov = {p['id']: p for p in M.rows('cross/provenance.jsonl')}
    urls = {}
    for p in M.rows('document/placements.jsonl'):
        if p['locator']['kind'] == 'URL' and p.get('artifact'):
            urls.setdefault(p['artifact'], []).append(p['locator']['value'])
    refs = {(r['origin'], r['record_key'], r.get('field'), r['basename']): r
            for r in M.rows('document/legacy-references.jsonl')}
    record_url = {}
    obs = M.rows('observation/observations.jsonl')
    for o in obs:
        if o['field'] == 'document_url':
            record_url[o['extraction']['record']] = o['value']
    out = {}
    for o in obs:
        ex = o['extraction']
        if ex['file'] not in ('data/fiches.js', 'data/cuvees.js'):
            continue
        p = prov[o['provenance']]
        lr = p.get('legacy_reference')
        if p['kind'] == 'LEGACY_FIELD_SOURCE':
            src = {'n': lr['basename']}
            us = sorted(urls.get(p['artifact'], []))
            if us:
                own = record_url.get(ex['record'])
                src['u'] = own if own in us else us[0]
        elif p['kind'] == 'LEGACY_AMBIGUOUS_SOURCE':
            r = refs[(lr['origin'], lr['record_key'], lr.get('field'), lr['basename'])]
            src = {'a': lr['basename'], 'c': len(r['candidates'])}
        else:
            continue
        out.setdefault(ex['record'], {})[o['field']] = src
    return out


SECOND_STATUS = 'second-status.js'


def second_status(model=None):
    """Each estate's second-wine statement, in the state the model records it
    (Phase 6.3). The estate files' `second` string is in the identity map
    (namespace second-by-name, Phase 4 M4); the state comes from that entry,
    the estate's RankAbsence and the findings M4 wrote. Nothing is resolved here.

    {legacy estate id: {"s": state, ...}} where state is
      "resolved"       ACTIVE: the string names one wine of the estate
      "none"           RETIRED with a RankAbsence: the dataset records no second wine
      "conflict"       RETIRED, and a CONFLICT finding: the estate's listed wines name a
                       second all the same ("w": those wines)
      "unestablished"  AMBIGUOUS: the name is recorded, which wine it is is not
                       established ("n": the recorded name, "w": the candidate wines)
      "note"           AMBIGUOUS, and an AMBIGUOUS_SEMANTICS finding that the string
                       is not a plain name ("n": the text, verbatim)"""
    M = model or R.Model()
    im = [r for r in M.rows('identity/identity-map.jsonl')]
    est = {r['legacy_key']: r['stable_id'] for r in im if r['namespace'] == 'estate' and r.get('stable_id')}
    names = {}
    for n in M.rows('identity/names.jsonl'):
        names.setdefault(n['subject'], n['name'])
    absent = {r['estate'] for r in M.rows('state/rank-absences.jsonl') if r['tier'] == 'SECOND'}
    prov = {p['id']: p for p in M.rows('cross/provenance.jsonl')}
    rels = {r['id']: r for r in M.rows('state/estate-wine.jsonl')}
    listed_second = {}
    for r in M.rows('state/rank-assertions.jsonl'):
        if r['tier'] == 'SECOND' and prov[r['provenance']]['actor'] == 'data/cuvees.js':
            rel = rels[r['relationship']]
            listed_second.setdefault(rel['estate'], []).append(names[rel['wine']])
    findings = {}
    for f in M.rows('cross/findings.jsonl'):
        findings.setdefault(f['target'], []).append(f)
    out = {}
    for r in im:
        if r['namespace'] != 'second-by-name':
            continue
        lid, text = r['legacy_key'].split('|', 1)
        eid = est[lid]
        fs = findings.get(eid, [])
        if r['status'] == 'ACTIVE':
            out[lid] = {'s': 'resolved'}
        elif r['status'] == 'RETIRED':
            assert eid in absent, lid
            if any(f['kind'] == 'CONFLICT' and 'no second wine' in f['detail'] for f in fs):
                out[lid] = {'s': 'conflict', 'w': sorted(listed_second.get(eid, []))}
            else:
                out[lid] = {'s': 'none'}
        elif any(f['kind'] == 'AMBIGUOUS_SEMANTICS' and 'second is not a plain name' in f['detail']
                 and repr(text) in f['detail'] for f in fs):
            out[lid] = {'s': 'note', 'n': text}
        else:
            out[lid] = {'s': 'unestablished', 'n': text,
                        'w': sorted(names[c] for c in r.get('candidates', []))}
    return out


def render():
    """{filename: bytes} for every contract file, and the figure sources."""
    proj = R.project(classifications={c['id']: c for c in L.g('BDX_CLASSIFICATIONS')})
    out = {}
    for f in CONTRACT:
        body = HEADER
        for g, v in sorted(proj[f].items()):
            js = json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
            if g == 'BDX_CHATEAUX':
                # The estate files append to one list, as today's files do.
                body += 'window.%s = (window.%s || []).concat(%s);\n' % (g, g, js)
            else:
                body += 'window.%s = %s;\n' % (g, js)
        out[f] = body.encode('utf-8')
    # Each distinct source once ("docs"), each figure an index into it ("rec"):
    # a file name repeated on every figure made the file 0.9 MB.
    fs = figure_sources()
    docs = sorted({json.dumps(v, sort_keys=True) for r in fs.values() for v in r.values()})
    index = {d: i for i, d in enumerate(docs)}
    packed = {'docs': [json.loads(d) for d in docs],
              'rec': {k: {f: index[json.dumps(v, sort_keys=True)] for f, v in r.items()} for k, r in fs.items()}}
    js = json.dumps(packed, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    out[FIGURE_SOURCES] = (HEADER + 'window.BDX_FIGURE_SRC = %s;\n' % js).encode('utf-8')
    js = json.dumps(second_status(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    out[SECOND_STATUS] = (HEADER + 'window.BDX_SECOND_STATUS = %s;\n' % js).encode('utf-8')
    return out


def main():
    files = render()
    if '--check' in sys.argv:
        bad = [f for f, b in files.items()
               if not os.path.exists(OUT + f) or open(OUT + f, 'rb').read() != b]
        extra = sorted(set(os.listdir(OUT)) - set(files)) if os.path.isdir(OUT) else []
        L.out('data/app ' + ('is the model, byte for byte' if not bad and not extra else
                             'differs: %s' % (bad + extra)))
        sys.exit(1 if bad or extra else 0)
    os.makedirs(OUT, exist_ok=True)
    for f, b in files.items():
        with open(OUT + f + '.tmp', 'wb') as h:
            h.write(b)
        os.replace(OUT + f + '.tmp', OUT + f)
    L.out('%d files, %d bytes' % (len(files), sum(len(b) for b in files.values())))


if __name__ == '__main__':
    main()
