# -*- coding: utf-8 -*-
"""An evidence census: what the manifest claims, what the document says.

    python tools/census.py                  the whole archive
    python tools/census.py --estate lafite  one estate
    python tools/census.py --orphans        only artifacts nothing cites
    python tools/census.py --write          write data/artifact-census.json

WRITES NOTHING into the dataset. `--write` writes one new file,
data/artifact-census.json, which is an analysis and not a source of
truth. sources.json, fiches.js, cuvees.js, field-src.js and
cuvee-src.js are never touched.

                        THREE IDENTITIES, KEPT APART

The whole value of this pass is that it refuses to collapse three
different things:

  MANIFEST IDENTITY   what data/sources.json currently says. A fact
                      about the manifest, not about the document.

  OBSERVED IDENTITY   what the document itself appears to say, from
                      its filename, its URL, and its text - each
                      recorded as separate evidence so a disagreement
                      between them survives.

  CONCLUSION          only drawn after comparing the two, and never
                      written back.

The Echo de Lynch-Bages case is why. Fifty sheets whose filename says
`Echo-de-Lynch-Bages-2008-EN.pdf` sit in the manifest under
`wine: "Blanc de Lynch-Bages"`. Collapse the layers and you have to
pick one and lose the other. Keep them apart and the record reads:

    manifest_wine = Blanc de Lynch-Bages
    observed_wine = Echo de Lynch-Bages   (filename, text)
    conclusion    = MANIFEST_METADATA_WRONG

which is a finding, and changes nothing until someone decides it
should.

                              HOW IT READS

Documents are read once per sha1, so the 839 identical-byte groups
cost one read each rather than one per copy. Only the head of each
document is flattened - identity sits at the top of a fiche, and
reading 13,032 documents in full to find a name in the first line is
a poor trade.

An estate is looked for by a reverse index from distinctive word to
estate id, built once over all 468 estates, rather than by testing
468 names against every document.
"""
import argparse
import collections
import datetime
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

ANALYZER_VERSION = 1
HEAD = 9000          # characters of flattened text used for identity

YEAR_IN = re.compile(r'(?<!\d)((?:1[89]|20)\d\d)(?!\d)')
# A year a document states about ITSELF, which is stronger evidence
# than a year that merely appears in it.
YEAR_DECLARED = re.compile(
    r'(?i)\b(?:mill[eé]sime|vintage|a[nñ]ada|annata|'
    r'harvest|r[eé]colte)\b[^0-9]{0,24}((?:19|20)\d\d)')

# Document kinds. Ordered: the first rule that fires wins, so the
# narrow and confident ones come first.
#
# Deliberately NOT filename-only. Each rule names which signals it
# used, and `where` says whether the filename alone was enough.
KINDS = (
    ('PRESS_DOSSIER', re.compile(
        r'(?i)dossier\s+de\s+presse|press\s*kit|press\s+pack|'
        r'revue\s+de\s+presse|press\s+review')),
    ('PRICE_LIST', re.compile(
        r'(?i)\b(?:tarif|price\s*list|prix\s+de\s+vente|ex[\s-]?cellar'
        r'|allocation)\b')),
    ('EVENT_DOCUMENT', re.compile(
        r'(?i)\b(?:invitation|programme|rendez-vous|portes\s+ouvertes|'
        r'd[eé]gustation\s+publique|salon|masterclass|'
        r'save\s+the\s+date|evenement|[eé]v[eé]nement)\b')),
    ('CATALOG', re.compile(
        r'(?i)\b(?:catalogue|catalog|brochure|portfolio)\b')),
    ('NEWS_ARTICLE', re.compile(
        r'(?i)\b(?:article|communiqu[eé]|interview|press\s+release|'
        r'journal|magazine)\b')),
    ('TECHNICAL_SHEET', re.compile(
        r'(?i)\b(?:fiche\s+technique|technical\s+(?:sheet|data)|'
        r'fiche\s+produit|datasheet|caract[eé]ristiques?\s+'
        r'techniques?)\b')),
    ('PRODUCER_PROFILE', re.compile(
        r'(?i)\b(?:notre\s+histoire|our\s+history|the\s+estate|'
        r'le\s+domaine|the\s+property|la\s+propri[eé]t[eé])\b')),
)

# What a document must show to be wine evidence at all: a figure or a
# passage that belongs to one wine of one year. Measured rather than
# assumed - a document with none of this is not a data document
# whatever its filename says.
IS_DATA = (
    ('blend', re.compile(
        r'(?i)\d{1,3}\s*%[^%]{0,40}(?:cabernet|merlot|petit\s+verdot|'
        r'malbec|s[eé]millon|sauvignon|muscadelle)')),
    ('alcohol', re.compile(
        r'(?i)(?:\b1[0-6][.,]\d\s*(?:%|degr|°)|alcohol|alcool|'
        r'titre\s+alcoom)')),
    ('yield', re.compile(r'(?i)\bhl\s*/\s*ha|rendement')),
    ('ageing', re.compile(
        r'(?i)\b\d{1,2}\s*(?:mois|months)\b|[eé]levage|ageing')),
    ('tasting', re.compile(
        r'(?i)\b(?:tanins?|tannins?|palate|bouche|robe|nez|nose|'
        r'finale|finish|ar[oô]mes?|aromas?)\b')),
    ('season', re.compile(
        r'(?i)\b(?:d[eé]bourrement|budbreak|floraison|flowering|'
        r'v[eé]raison|vendange|harvest)\b')),
)


def flat_head(path):
    try:
        t = sr.flat(path)
    except Exception as e:
        return None, 'unreadable: %s' % type(e).__name__
    return ' '.join((t or '')[:HEAD * 3].split())[:HEAD], None


def words(s):
    return [w for w in re.split(r'[^a-z0-9]+', sr.norm(s or '')) if w]


def build_estate_index(E):
    """Distinctive word -> estate ids, so one scan finds any estate.

    Testing 468 names against 13,032 documents is 6 million calls to
    says(); a reverse index is one pass over the document's own words.
    """
    idx = collections.defaultdict(set)
    common = set(('chateau', 'clos', 'domaine', 'la', 'le', 'les', 'de',
                  'du', 'des', 'haut', 'grand', 'petit', 'vieux', 'saint',
                  'ste', 'st', 'cru', 'bourgeois', 'the', 'and', 'et'))
    for eid, e in E.items():
        for w in words(e.get('name')):
            if len(w) >= 4 and w not in common:
                idx[w].add(eid)
    return idx


def observed_estate(text, filename, url, idx, E, manifest_eid):
    """Which estates this document names, with where each was seen."""
    hits = collections.Counter()
    where = collections.defaultdict(set)
    for src, label in ((filename, 'filename'), (url, 'url'),
                       (text, 'text')):
        for w in set(words(src)):
            for eid in idx.get(w, ()):
                hits[eid] += 1
                where[eid].add(label)
    # A word is weak evidence; the full name is strong. Confirm with
    # says(), which requires the words whole and in order.
    strong = []
    for eid in list(hits):
        nm = (E.get(eid) or {}).get('name') or ''
        for src, label in ((filename, 'filename'), (url, 'url'),
                           (text, 'text')):
            if src and sr.says(src, nm):
                strong.append((eid, label))
                break
    return strong, where


def observed_wine(text, filename, url, e, manifest_eid):
    """Which of the estate's own wines this document names."""
    wines = []
    if e.get('name'):
        wines.append(('grand', e['name']))
    if e.get('second'):
        wines.append(('second', e['second']))
    for c in (e.get('cuvees') or ()):
        wines.append(('other', c))
    found = []
    # Longest first: "Blanc de Lynch-Bages" contains "Lynch-Bages", so
    # the specific name must win over the estate's own.
    for role, nm in sorted(wines, key=lambda w: -len(w[1])):
        for src, label in ((filename, 'filename'), (url, 'url'),
                           (text, 'text')):
            if src and sr.says(src, nm):
                if any(nm.lower() in prev.lower() for _r, prev, _l in found):
                    break
                found.append((role, nm, label))
                break
    return found


def classify(text, filename, url):
    """What kind of document this is, and what it was decided on."""
    joined = ' '.join(x for x in (filename, url) if x)
    for kind, rx in KINDS:
        m = rx.search(text or '')
        if m:
            return kind, 'text: "%s"' % m.group(0)[:40], 'text'
        m = rx.search(joined)
        if m:
            return kind, 'name: "%s"' % m.group(0)[:40], 'name'
    return 'UNKNOWN', '', ''


def data_signals(text):
    return [name for name, rx in IS_DATA if rx.search(text or '')]


def git_commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def load_cited():
    """filename -> the record keys whose fields came from it."""
    cited = collections.defaultdict(set)
    for name, nkey in (('fiches.js', 2), ('cuvees.js', 3)):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        pat = re.compile(r"^'([a-z0-9-]+)\|" +
                         (r"([a-z0-9-]+)\|" if nkey == 3 else '') +
                         r"(\d{4})':\{(.*)\},$")
        for line in io.open(p, encoding='utf-8'):
            m = pat.match(line.rstrip())
            if not m:
                continue
            key = '|'.join(m.group(i + 1) for i in range(nkey))
            s = re.search(r"src:'([^']*)'", m.group(nkey + 1))
            if s:
                cited[s.group(1)].add(key)
    for name in ('field-src.js', 'cuvee-src.js'):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding='utf-8'):
            m = re.match(r"^'([^']+)':\{(.*)\},$", line.rstrip())
            if not m:
                continue
            for f, v in re.findall(r"([a-z]+):'([^']*)'", m.group(2)):
                cited[v].add(m.group(1))
    return cited


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--orphans', action='store_true')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    idx = build_estate_index(E)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = man.get('sheets', [])
    cited = load_cited()

    disk = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            disk.setdefault(f, os.path.join(root, f))

    if a.estate:
        sheets = [s for s in sheets if s.get('estate') == a.estate]
    if a.orphans:
        sheets = [s for s in sheets if s.get('file') not in cited]
    if a.limit:
        sheets = sheets[:a.limit]

    by_hash = collections.defaultdict(list)
    for s in sheets:
        if s.get('sha1'):
            by_hash[s['sha1']].append(s.get('file'))

    read_cache = {}
    out = []
    n = 0
    for s in sheets:
        fn = s.get('file')
        if not fn:
            continue
        n += 1
        if n % 500 == 0:
            sys.stderr.write('  %d of %d\n' % (n, len(sheets)))
            sys.stderr.flush()
        meid = s.get('estate')
        e = E.get(meid) or {}
        path = disk.get(fn)
        h = s.get('sha1')
        if h and h in read_cache:
            text, err = read_cache[h]
        elif path:
            text, err = flat_head(path)
            if h:
                read_cache[h] = (text, err)
        else:
            text, err = None, 'not on disk'

        url = s.get('url') or ''
        ev = []

        # ---- observed vintage
        fy = set(int(y) for y in YEAR_IN.findall(fn))
        uy = set(int(y) for y in YEAR_IN.findall(url))
        dy = set(int(y) for y in YEAR_DECLARED.findall(text or ''))
        ty = set(int(y) for y in YEAR_IN.findall((text or '')[:1200]))
        if fy:
            ev.append('filename spells %s' % ','.join(map(str, sorted(fy))))
        if dy:
            ev.append('document declares vintage %s'
                      % ','.join(map(str, sorted(dy))))
        obs_year, yconf = None, 'UNKNOWN'
        if len(dy) == 1:
            obs_year, yconf = list(dy)[0], 'HIGH'
        elif dy:
            obs_year, yconf = min(dy), 'MEDIUM'
        elif len(fy) == 1:
            obs_year, yconf = list(fy)[0], 'MEDIUM'
        elif fy & uy:
            obs_year, yconf = min(fy & uy), 'MEDIUM'
        elif fy:
            obs_year, yconf = min(fy), 'LOW'

        # ---- observed estate
        strong, where = observed_estate(text or '', fn, url, idx, E, meid)
        obs_estates = sorted(set(eid for eid, _l in strong))
        if obs_estates:
            ev.append('names estate(s) %s' % ','.join(obs_estates))

        # ---- observed wine
        wines = observed_wine(text or '', fn, url, e, meid) if e else []
        if wines:
            ev.append('names wine(s) ' +
                      '; '.join('%s (%s)' % (nm, lb)
                                for _r, nm, lb in wines))

        kind, kev, kwhere = classify(text or '', fn, url)
        sigs = data_signals(text or '')
        if sigs:
            ev.append('data signals: ' + ','.join(sigs))
        if err:
            ev.append(err)

        # Kind, refined by whether it carries wine data at all.
        if kind == 'UNKNOWN':
            if err:
                kind = 'UNREADABLE'
            elif not text:
                kind = 'IMAGE_ONLY'
            elif len(sigs) >= 2:
                kind = 'DATA_SHEET'
            elif 'tasting' in sigs:
                kind = 'TASTING_NOTE'
            elif sigs:
                kind = 'WINE_PROFILE'
            else:
                kind = 'WEBSITE_COPY' if sr.is_page(fn) else 'UNKNOWN'
        # A technical sheet with no wine figure in it is not one.
        if kind == 'TECHNICAL_SHEET' and not sigs:
            kind, kev = 'MARKETING_DOCUMENT', kev + ' (but no wine data)'

        mwine = s.get('wine') or ''
        obs_names = [nm for _r, nm, _l in wines]
        # ---- the conclusion, drawn last and written nowhere
        status, reasons = 'UNRESOLVED', []
        recs = sorted(cited.get(fn) or ())
        if err or not path:
            status = 'UNRESOLVED'
            reasons.append(err or 'not on disk')
        elif len(sigs) == 0 and kind in (
                'PRESS_DOSSIER', 'EVENT_DOCUMENT', 'NEWS_ARTICLE',
                'CATALOG', 'PRICE_LIST', 'PRODUCER_PROFILE',
                'MARKETING_DOCUMENT'):
            status = 'LEGITIMATE_NON_RECORD'
            reasons.append('%s with no wine figure or passage in it'
                           % kind.lower().replace('_', ' '))
        elif mwine and obs_names and mwine not in obs_names:
            status = 'MANIFEST_METADATA_WRONG'
            reasons.append('manifest says %r; the document names %s'
                           % (mwine, ', '.join(obs_names)))
        elif len(obs_estates) > 1:
            status = 'DOCUMENT_IDENTITY_CONFLICT'
            reasons.append('names %d estates: %s'
                           % (len(obs_estates), ','.join(obs_estates)))
        elif obs_estates and meid and meid not in obs_estates:
            status = 'DOCUMENT_IDENTITY_CONFLICT'
            reasons.append('manifest estate %s; document names %s'
                           % (meid, ','.join(obs_estates)))
        elif len(obs_names) > 1:
            status = 'POSSIBLE_MULTI_WINE_DOCUMENT'
            reasons.append('names %d of the estate\'s wines'
                           % len(obs_names))
        elif h and len(by_hash.get(h) or []) > 1:
            status = 'POSSIBLE_DUPLICATE'
            reasons.append('%d artifacts share these bytes'
                           % len(by_hash[h]))
        elif recs:
            status = 'MATCH'
            reasons.append('cited by ' + ', '.join(recs[:3]))
        elif sigs:
            status = 'POSSIBLE_MISSING_RECORD'
            reasons.append('carries %s and no record cites it'
                           % ','.join(sigs))
        else:
            status = 'NOT_A_DATA_DOCUMENT'
            reasons.append('no wine figure or passage found')

        row = {
            'artifact_id': h or fn,
            'path': (s.get('folder') or '') + '/' + fn,
            'url': url or None,
            'sha1': h,
            'bytes': s.get('bytes'),
            'manifest': {'estate': meid, 'wine': mwine or None,
                         'vintage': s.get('year'), 'role': s.get('role')},
            'observed': {
                'estate': obs_estates or ['UNKNOWN'],
                'wine': obs_names or ['UNKNOWN'],
                'vintage': obs_year if obs_year else 'UNKNOWN',
                'document_type': kind,
                'data_signals': sigs,
            },
            'identity': {
                'estate_confidence': ('HIGH' if len(obs_estates) == 1
                                      else 'LOW' if obs_estates
                                      else 'UNKNOWN'),
                'wine_confidence': ('HIGH' if len(obs_names) == 1
                                    else 'LOW' if obs_names else 'UNKNOWN'),
                'vintage_confidence': yconf,
                'evidence': ev,
            },
            'classification': {'kind': kind, 'decided_on': kwhere or 'none',
                               'evidence': kev},
            'reconciliation': {'status': status,
                               'candidate_records': recs[:6],
                               'reasons': reasons},
            'duplicate': {'group_id': h if h and
                          len(by_hash.get(h) or []) > 1 else None,
                          'members': len(by_hash.get(h) or [])},
            'analysis': {'analyzer_version': ANALYZER_VERSION,
                         'analyzed_at': datetime.date.today().isoformat()},
        }
        out.append(row)

    # ----------------------------------------------------------- report
    print('%d artifact(s) analysed, analyzer version %d'
          % (len(out), ANALYZER_VERSION))
    print('%d distinct byte-sets read' % len(read_cache))
    print()
    print('DOCUMENT KIND')
    print('-' * 46)
    for k, c in collections.Counter(
            r['observed']['document_type'] for r in out).most_common():
        print('   %-26s %5d' % (k, c))
    print()
    print('RECONCILIATION STATUS')
    print('-' * 46)
    for k, c in collections.Counter(
            r['reconciliation']['status'] for r in out).most_common():
        print('   %-30s %5d' % (k, c))
    print()
    print('CARRIES WINE DATA')
    print('-' * 46)
    withdata = sum(1 for r in out if r['observed']['data_signals'])
    print('   %-30s %5d' % ('at least one data signal', withdata))
    print('   %-30s %5d' % ('none', len(out) - withdata))

    if a.write:
        p = ROOT + 'data/artifact-census.json'
        io.open(p, 'w', encoding='utf-8', newline='').write(
            json.dumps({
                'note': ['An analysis, not a source of truth. Manifest '
                         'identity, observed identity and the '
                         'conclusion are kept apart on purpose; '
                         'nothing here has been written back into '
                         'sources.json or the records.'],
                'analyzer_version': ANALYZER_VERSION,
                'analyzed_at': datetime.datetime.now().isoformat(
                    timespec='seconds'),
                'commit': git_commit(),
                'manifest_sheets': len(man.get('sheets', [])),
                'artifacts': out,
            }, indent=1, ensure_ascii=False) + '\n')
        print('\nwritten to data/artifact-census.json (%d artifacts)'
              % len(out))
    else:
        print('\nnothing written; pass --write for '
              'data/artifact-census.json')


if __name__ == '__main__':
    main()
