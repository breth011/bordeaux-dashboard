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
        elif p['kind'] == 'DOCUMENT' and str((p.get('code_state') or {}).get('stream', '')).startswith('M3.2'):
            # M3.2: the figure's own sheet, recovered from the held document; an address only where
            # those exact bytes have one, otherwise an on-file source
            src = {'n': p['code_state']['basename']}
            us = sorted(urls.get(p['artifact'], []))
            if us:
                own = record_url.get(ex['record'])
                src['u'] = own if own in us else us[0]
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


SOURCE_FACTS = 'source-facts.js'
# The model's document types that say more than the file's name does. UNKNOWN
# and OTHER say nothing a reader can use, so they are not passed on.
TELLING_TYPES = ('WEB_PAGE', 'MULTI_WINE_SHEET', 'GROUP_REPORT')


def source_facts(model=None):
    """What the model records about the document behind a figure source, beyond
    its name and address (Phase 6.5): only what figure-sources.js cannot say.

    {record key: {field: facts}} for the LEGACY_FIELD_SOURCE figures of
    figure_sources(), with facts holding
      "t": type   the model's assessment of the artifact (document/assessments),
                  where it is one of TELLING_TYPES
      "o": n      how many other estates have a figure whose source is the same
                  artifact - the same model identity, not the same address or name
    A figure with neither has no entry. Ambiguous sources have none: which
    artifact they are is what is not known."""
    M = model or R.Model()
    prov = {p['id']: p for p in M.rows('cross/provenance.jsonl')}
    kind = {a['artifact']: a['document_type'] for a in M.rows('document/assessments.jsonl')}
    cited = []
    for o in M.rows('observation/observations.jsonl'):
        ex = o['extraction']
        if ex['file'] not in ('data/fiches.js', 'data/cuvees.js'):
            continue
        p = prov[o['provenance']]
        if p['kind'] == 'LEGACY_FIELD_SOURCE':
            cited.append((ex['record'], o['field'], p['artifact']))
    estates = {}
    for rec, _, a in cited:
        estates.setdefault(a, set()).add(rec.split('|', 1)[0])
    out = {}
    for rec, field, a in cited:
        facts = {}
        if kind.get(a) in TELLING_TYPES:
            facts['t'] = kind[a]
        others = len(estates[a] - {rec.split('|', 1)[0]})
        if others:
            facts['o'] = others
        if facts:
            out.setdefault(rec, {})[field] = facts
    return out


def pack(table):
    """Each distinct value once ("docs"), each record's field an index into it ("rec")."""
    docs = sorted({json.dumps(v, sort_keys=True) for r in table.values() for v in r.values()})
    index = {d: i for i, d in enumerate(docs)}
    return {'docs': [json.loads(d) for d in docs],
            'rec': {k: {f: index[json.dumps(v, sort_keys=True)] for f, v in r.items()} for k, r in table.items()}}


WINE_ESTABLISHED = 'wine-established.js'


def wine_established(model=None):
    """What the model establishes about each wine the page can show, now (Phase 6.7).

    {"estate|slug": facts}, slug "grand" for an estate's grand vin (identity map
    `grand-vin`) and the cuvee slug otherwise (`wine-by-slug`). Every fact is a
    model record as it stands; nothing is dated that the model does not date:
      "n"   the CURRENT NameRecord's name (absent if the wine has none)
      "nf"  that record's valid_from, where it is anything but UNKNOWN
      "fn"  FORMER names, where any are recorded (none are, at Phase 6.7)
      "r"   the distinct RankAssertion tiers, and "rc" their claimants
      "c"   classification memberships: [rank, scheme, edition year, edition status]
      "a"   appellation memberships' names
      "s"   sheets on file: [count, first year, last year]
      "y"   the years of those sheets (Phase 6.9: the page says how many lie
            outside the years it lists). A sheet on file is a fiche or cuvee
            record: one the wine's observations were extracted from, or one
            that names its document with no figure taken from it (a record-level
            legacy reference, e.g. Malescot 1995). Phase 6.7 counted only the
            first kind, three records short of the records the page shows.
      "x"   years with a NOT_PRODUCED VintageStatement
    A wine without a fact simply lacks the key: an absent record is not a value."""
    M = model or R.Model()
    # M3.6D's Cuvée Mongravey is in no legacy file, so the page cannot show it (tools/model_reader.py)
    m36d = {p['id'] for p in M.rows('cross/provenance.jsonl') if p.get('actor') == 'tools/m36d-cuvee.py'}
    im = {}
    for r in M.rows('identity/identity-map.jsonl'):
        if r['namespace'] == 'grand-vin' and r.get('stable_id'):
            im[r['stable_id']] = r['legacy_key'] + '|grand'
        elif r['namespace'] == 'wine-by-slug' and r.get('stable_id') and r['provenance'] not in m36d:
            im[r['stable_id']] = r['legacy_key']
    out = {key: {} for key in im.values()}
    for n in M.rows('identity/names.jsonl'):
        key = im.get(n['subject'])
        if key is None:
            continue
        if n['kind'] == 'CURRENT':
            out[key]['n'] = n['name']
            if n['validity']['valid_from'].get('kind') != 'UNKNOWN':
                out[key]['nf'] = n['validity']['valid_from']
        elif n['kind'] == 'FORMER':
            out[key].setdefault('fn', []).append(n['name'])
    rel = {r['id']: r for r in M.rows('state/estate-wine.jsonl')}
    for a in M.rows('state/rank-assertions.jsonl'):
        key = im.get(rel[a['relationship']]['wine'])
        if key is not None:
            out[key].setdefault('r', set()).add(a['tier'])
            out[key].setdefault('rc', set()).add(a['claimant'])
    schemes = {r['id']: r['name'] for r in M.rows('state/classification-schemes.jsonl')}
    editions = {r['id']: r for r in M.rows('state/classification-editions.jsonl')}
    for m in M.rows('state/classification-memberships.jsonl'):
        key = im.get(m['wine'])
        if key is None:
            continue
        e = editions[m['edition']]
        year = e['validity']['valid_from'].get('value') if e['validity']['valid_from'].get('kind') == 'EXACT' else None
        out[key].setdefault('c', []).append([m['rank'], schemes[e['scheme']], year, e['status']])
    apps = {r['id']: r['name'] for r in M.rows('state/appellations.jsonl')}
    for m in M.rows('state/appellation-memberships.jsonl'):
        key = im.get(m['wine'])
        if key is not None:
            out[key].setdefault('a', []).append(apps[m['appellation']])
    records = set()
    for o in M.rows('observation/observations.jsonl'):
        ex = o['extraction']
        if ex['file'] in ('data/fiches.js', 'data/cuvees.js'):
            records.add(ex['record'])
    for r in M.rows('document/legacy-references.jsonl'):
        if r['origin'] in ('fiches.js', 'cuvees.js') and r.get('field') is None:
            records.add(r['record_key'])
    years = {}
    for rec in records:
        parts = rec.split('|')
        key = parts[0] + '|grand' if len(parts) == 2 else parts[0] + '|' + parts[1]
        if key in out:
            years.setdefault(key, set()).add(int(parts[-1]))
    for key, ys in years.items():
        out[key]['s'] = [len(ys), min(ys), max(ys)]
        out[key]['y'] = sorted(ys)
    for v in M.rows('state/vintage-statements.jsonl'):
        if v['kind'] != 'NOT_PRODUCED':
            continue
        _, wine, year = v['vintage'].split(':')
        key = im.get(wine)
        if key is not None:
            out[key].setdefault('x', []).append(int(year))
    for f in out.values():
        for k in ('r', 'rc'):
            if k in f:
                f[k] = sorted(f[k])
        for k in ('c', 'a', 'x', 'fn'):
            if k in f:
                f[k] = sorted(f[k])
    return out


def render():
    """{filename: bytes} for every contract file, the figure sources, the second-wine
    states, the source facts and what is established about each wine."""
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
    js = json.dumps(pack(source_facts()), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    out[SOURCE_FACTS] = (HEADER + 'window.BDX_SOURCE_FACTS = %s;\n' % js).encode('utf-8')
    js = json.dumps(wine_established(), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    out[WINE_ESTABLISHED] = (HEADER + 'window.BDX_WINE_ESTABLISHED = %s;\n' % js).encode('utf-8')
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
