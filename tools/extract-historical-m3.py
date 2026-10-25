"""Historical model M3: the candidate audit - every historical statement earlier research
exposed, and whether existing reviewed evidence lets the model record it.

    python tools/extract-historical-m3.py             write data/audit/historical-m3-candidates.jsonl
    python tools/extract-historical-m3.py --check     recompute and compare, byte for byte
    python tools/extract-historical-m3.py --dry-run   the counts and the rows the model would gain;
                                                      writes nothing

Not an extraction pass. The candidates are of two kinds:

  RESEARCH  the historical statements earlier phases found and quoted (Phase 3.4 fixtures
            P4, P6, P7, P8, P11; Phase 3.4 review section 7; Phase 6.2; the historical design
            section 13), plus the same statements wherever the evidence store accepted a sheet of
            that estate carrying them (a fixed phrase per fact, searched in that estate's
            accepted sheets only). Each is written out below as a reading: subject, property,
            what the source states, on which axis, and what it depends on.
  MODEL     rows the model already holds that carry history-like content: the 18 legacy
            NOT_PRODUCED vintage statements, the legacy owner and history texts that state a
            year with a since/bought wording, and the 34 dataset "no second wine" absences.

For each, the facts the gate needs are checked mechanically against the store: the artifact is
held, the passage is found at its locus in the held text, the evidence store's latest decisions
about that document for that estate, the identity map's status for the subject, the
provenance kind. tools/historical_m3.py decides. No clock, no network.
"""
import collections
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import historical_m3 as H  # noqa: E402
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

OUT = L.ROOT + 'data/audit/historical-m3-candidates.jsonl'
EXTRACTED = L.ROOT + 'sources/discovery/extracted/'
LATEST_EVIDENCE = L.ROOT + 'data/evidence/decisions-v5.jsonl'


def b(kind, value=None, axis=None, precision=None):
    return S.bound(kind, value, axis, precision, 'the source quote' if value is not None else None)


V = lambda y: b('EXACT', y, 'VINTAGE', 'VINTAGE')
Y = lambda y: b('EXACT', y, 'CALENDAR', 'YEAR')

# The research candidates: each a reading of a quoted passage, kept as written by earlier phases.
RESEARCH = [
    dict(key='echo-rename-en', research='3.4 fixture P7; design 13.A; D2', estate='lynch-bages',
         subject='wn_00547', subject_key='lynch-bages|Echo de Lynch-Bages', property='transition.RENAMED',
         statement='the second wine Haut-Bages Averous took the name Echo de Lynch-Bages in 2008',
         value={'from_name': 'Château Haut-Bages Averous', 'to_name': 'Echo de Lynch-Bages'},
         artifact='ar_022743', locus='b:452', contains='in 2008, a new identity was given to the second wine', lang='en',
         claimed={'claimed_window': {'earliest': b('EXACT', '2008', 'CALENDAR', 'YEAR'), 'latest': b('EXACT', '2008', 'CALENDAR', 'YEAR')}},
         statement_mode='EXPLICIT', temporal='STATED',
         temporal_note='"In 2008": a year with no axis named; the French version says "from the 2008 vintage"',
         depends_on=['D2']),
    dict(key='echo-rename-fr', research='3.4 review 7; design 13.A; D2', estate='lynch-bages',
         subject='wn_00547', subject_key='lynch-bages|Echo de Lynch-Bages', property='transition.RENAMED',
         statement='from the 2008 vintage Haut-Bages Averous "changes identity" to become Echo de Lynch-Bages',
         value={'from_name': 'Château Haut-Bages Averous', 'to_name': 'Echo de Lynch-Bages'},
         artifact='ar_022291', locus='b:438', contains='a partir du millesime 2008, il change d', lang='fr',
         claimed={'claimed_window': {'earliest': V(2008), 'latest': V(2008)}},
         statement_mode='EXPLICIT', temporal='STATED', depends_on=['D2']),
    dict(key='echo-rename-mobi', research='a page the user named in M3 (2026-10-25); read, not held', estate='lynch-bages',
         subject='wn_00547', subject_key='lynch-bages|Echo de Lynch-Bages', property='transition.RENAMED',
         statement='"As of the 2008 vintage, Château Haut-Bages Averous changed its name ... it became Echo de Lynch-Bages"',
         value={'from_name': 'Château Haut-Bages Averous', 'to_name': 'Echo de Lynch-Bages'},
         artifact=None, locus=None, contains=None, lang='en', url='https://www.lynchbages.mobi/en/echo-de-lynch-bages',
         claimed={'claimed_window': {'earliest': V(2008), 'latest': V(2008)}},
         statement_mode='EXPLICIT', temporal='STATED',
         temporal_note='"As of the 2008 vintage": the vintage axis, as the French page; publisher not confirmed '
                       '(lynchbages.mobi, links jmcazes.com, not lynchbages.com)',
         depends_on=['D2']),
    dict(key='averous-second-en', research='3.4 fixture P7', estate='lynch-bages',
         subject=None, subject_key='lynch-bages|Haut-Bages Averous', property='rank.SECOND',
         statement='Haut-Bages Averous was the second wine of Lynch-Bages "for over 30 years" before 2008',
         value='SECOND', artifact='ar_022743', locus='b:452', contains="for over 30 years, it was lynch-bages", lang='en',
         claimed={'claimed_validity': {'valid_from': b('UNKNOWN'), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='NONE',
         temporal_note='"for over 30 years": no bound is stated (design 4: UNKNOWN, the wording kept)',
         depends_on=['D2']),
    dict(key='averous-second-fr', research='3.4 review 7', estate='lynch-bages',
         subject=None, subject_key='lynch-bages|Haut-Bages Averous', property='rank.SECOND',
         statement='Haut-Bages Averous "désigne pendant plus de 30 ans" the second wine of Lynch-Bages',
         value='SECOND', artifact='ar_022291', locus='b:438', contains='designe pendant plus de 30 ans le second vin', lang='fr',
         claimed={'claimed_validity': {'valid_from': b('UNKNOWN'), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='NONE', depends_on=['D2']),
    dict(key='laparde-rename-2018', research='3.4 fixture P11; 6.2 section 5; design 13.B', estate='haut-bailly',
         subject=None, subject_key='haut-bailly|La Parde de Haut-Bailly', property='transition.RENAMED',
         statement='La Parde de Haut-Bailly "se voit renommer" Haut-Bailly II',
         value={'from_name': 'La Parde de Haut-Bailly', 'to_name': 'Haut-Bailly II'},
         artifact='ar_002853', locus='p:1', contains='se voit renommer', lang='fr',
         claimed={'claimed_window': {'earliest': V(2018), 'latest': V(2018)}},
         statement_mode='EXPLICIT', temporal='FRAMING',
         temporal_note='the "2018" is the heading of the 2018 sheet the passage opens: the date is the document\'s framing',
         depends_on=['IDENTITY:haut-bailly|La Parde de Haut-Bailly (6.2: "needs a decision", as D2)']),
    dict(key='laparde-born-1967', research='3.4 fixture P11; 6.2 section 5', estate='haut-bailly',
         subject=None, subject_key='haut-bailly|La Parde de Haut-Bailly', property='relationship.valid_from',
         statement='La Parde de Haut-Bailly was "né en 1967"', value='1967',
         artifact='ar_002853', locus='p:1', contains='ne en 1967', lang='fr',
         claimed={'claimed_validity': {'valid_from': Y('1967'), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='STATED',
         depends_on=['IDENTITY:haut-bailly|La Parde de Haut-Bailly (6.2: "needs a decision", as D2)']),
    dict(key='corbin-2022-no-second', research='3.4 fixture P6; design 13.D', estate='stem-chateau-corbin',
         subject='es_00398', property='rank_absence.SECOND',
         statement='no second wine of Corbin was produced in 2022', value='SECOND',
         artifact='ar_009394', locus='p:5', contains='no second wine was produced this year', lang='en',
         claimed={'claimed_validity': {'valid_from': V(2022), 'valid_to': V(2022)}},
         statement_mode='EXPLICIT', temporal='FRAMING',
         temporal_note='"this year": the year is the vintage the critic is reviewing, not written in the sentence'),
    dict(key='corbin-no-second-2025-en', research='Phase M3 lookup in accepted Corbin sheets', estate='stem-chateau-corbin',
         subject='es_00398', property='rank_absence.SECOND', statement='"No second wine" (production facts of the 2025 sheet)',
         value='SECOND', artifact='ar_002680', locus='p:1', contains='no second wine', lang='en', claimed={},
         statement_mode='EXPLICIT', temporal='NONE', excluded_as='CURRENT_STATEMENT',
         temporal_note='present tense, undated: a current fact as of the sheet; history only from the document date (H3)'),
    dict(key='corbin-no-second-2025-fr', research='Phase M3 lookup in accepted Corbin sheets', estate='stem-chateau-corbin',
         subject='es_00398', property='rank_absence.SECOND', statement='"Pas de second vin" (production facts of the 2025 sheet)',
         value='SECOND', artifact='ar_010117', locus='p:1', contains='pas de second vin', lang='fr', claimed={},
         statement_mode='EXPLICIT', temporal='NONE', excluded_as='CURRENT_STATEMENT'),
    dict(key='pontoise-bouillaud-1881-1959', research='3.4 corpus review (temporal wording)', estate='bourgeois-chateau-pontoise-cabarrus',
         subject='es_00181', property='owner', statement='the Bouillaud family owned the estate from 1881 to 1959',
         value='Famille Bouillaud', artifact='ar_012197', locus='b:58', contains='famille bouillaud proprietaire de 1881 a 1959', lang='fr',
         claimed={'claimed_validity': {'valid_from': Y('1881'), 'valid_to': Y('1959')}},
         statement_mode='EXPLICIT', temporal='STATED',
         temporal_note='a caption to an old label on the estate\'s journal page; the estate is the site\'s, not named in the caption'),
    dict(key='pontoise-cb-levels-2018', research='3.4 review 7 (classification by vintage); design 13.F', estate='bourgeois-chateau-pontoise-cabarrus',
         subject=None, subject_key='Crus Bourgeois classification 2020', property='classification_edition.valid_from',
         statement='the 2020 Crus Bourgeois classification reinstates three levels from the 2018 vintage', value='2018',
         artifact='ar_012197', locus='b:56', contains='a partir du millesime 2018', lang='fr',
         claimed={'claimed_validity': {'valid_from': V(2018), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='STATED'),
    dict(key='coutet-opalie-created-2010', research='3.4 review 7 (corpus wording)', estate='coutet',
         subject='wn_00490', property='relationship.valid_from', statement='the 2010 vintage marks the creation of Cuvée Opalie',
         value='2010', artifact='ar_012265', locus='b:42', contains='le millesime 2010 marque la creation de la cuvee opalie', lang='fr',
         claimed={'claimed_validity': {'valid_from': V(2010), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='STATED'),
    dict(key='coutet-opalie-label-2024', research='3.4 review 7', estate='coutet', subject='wn_00490', property='label',
         statement='from the 2024 vintage Opalie wears the same label as Coutet', value='label',
         artifact='ar_012265', locus='b:42', contains='a partir du millesime 2024, la cuvee opalie s', lang='fr',
         claimed={'claimed_validity': {'valid_from': V(2024), 'valid_to': b('UNKNOWN')}},
         statement_mode='EXPLICIT', temporal='STATED', excluded_as='NOT_IDENTITY',
         temporal_note='a label change of one wine is not identity history (3.4 section 7)'),
    dict(key='terrasses-second-2016-2019', research='3.4 fixture P4; 2.11', estate='stem-chateau-tour-saint-christophe',
         subject=None, subject_key='Les Terrasses de Saint Christophe', property='rank.SECOND',
         statement='Les Terrasses de Saint Christophe was the second label in 2016-2019', value='SECOND',
         artifact='ar_007920', locus='p:1', contains='is the second label of chateau tour saint christophe', lang='en',
         claimed={'claimed_validity': {'valid_from': b('NO_LATER_THAN', 2016, 'VINTAGE', 'VINTAGE'), 'valid_to': b('UNKNOWN')}},
         statement_mode='IMPLIED', temporal='FRAMING',
         temporal_note='"is the second label" is undated; 2016-2019 are the vintages of the sheets on file'),
    dict(key='batailley-no-second-before-2014', research='6.2 section 4; design 13.C', estate='batailley',
         subject='es_00035', property='rank_absence.SECOND', statement='Batailley had no second wine before 2014',
         value='SECOND', artifact=None, locus=None, contains=None, claimed={}, statement_mode='IMPLIED', temporal='NONE',
         excluded_as='ABSENCE', temporal_note='read off the Lions de Batailley vintages on file (from 2014): absence of records'),
    dict(key='desmirail-two-names', research='3.4 fixture P8', estate='desmirail', subject=None,
         subject_key='desmirail|Initial de Desmirail', property='name.ALIAS',
         statement='Initial de Desmirail is also sold as Origine de Desmirail', value='Origine de Desmirail',
         artifact='ar_012103', locus=None, contains='aussi distribue sous le nom de', lang='fr', claimed={},
         statement_mode='EXPLICIT', temporal='NONE', excluded_as='NOT_HISTORICAL',
         temporal_note='two current names; nothing is dated'),
]

SINCE = re.compile(r'since|depuis|bought|acqui|purchas|rachet', re.I)
A_YEAR = re.compile(r'(?<!\d)1[5-9]\d\d|20[0-2]\d(?!\d)')


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')


def segments(sha):
    import importlib.util
    spec = importlib.util.spec_from_file_location('xdd', L.ROOT + 'tools/extract-document-dates.py')
    X = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(X)
    p = EXTRACTED + sha + '.json'
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    return X.segments_of(d) if d.get('status') == 'EXTRACTED' else None


def passage(sha, locus, contains):
    """(found, locus, quote <= 200 chars) - the passage at its locus, or anywhere if no locus."""
    segs = segments(sha) if sha else None
    if not segs or not contains:
        return False, locus, None
    for loc, t in segs:
        if locus and loc != locus:
            continue
        i = fold(t).find(contains)
        if i >= 0:
            q = re.sub(r'\s+', ' ', t[max(0, i - 40):i + len(contains) + 100]).strip()
            return True, loc, q[:200]
    return False, locus, None


def main():
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    dates = {r['artifact']: r['value']['value'] for r in L.read_table('document/artifact-dates.jsonl')}
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    idmap = collections.defaultdict(set)
    for r in L.read_table('identity/identity-map.jsonl'):
        idmap[r['legacy_key']].add(r['status'])
    named = {n['subject'] for n in L.read_table('identity/names.jsonl')}
    wanted = {arts[c['artifact']]['sha256'] for c in RESEARCH if c.get('artifact')}
    verdict = collections.defaultdict(list)                      # sha256 -> [(estate, decision, code, wine, vintage)]
    for line in open(LATEST_EVIDENCE, encoding='utf-8'):
        if '"sha256"' not in line:
            continue
        r = json.loads(line)
        sha = (r.get('read') or {}).get('sha256')
        if sha in wanted:
            ctx = r['ctx']
            verdict[sha].append((ctx.get('estate') or ctx.get('folder'), r['decision'], r['code'],
                                 ctx.get('target_wine'), ctx.get('vintage')))
    rows = []
    for c in RESEARCH:
        a = arts.get(c['artifact']) if c.get('artifact') else None
        sha = a['sha256'] if a else None
        found, locus, quote = passage(sha, c.get('locus'), c.get('contains'))
        mine = [v for v in verdict.get(sha, []) if v[0] == c['estate']]
        evidence = ('ACCEPTED' if any(v[1] == 'ACCEPTED' for v in mine) else 'REFUSED' if mine
                    else 'NO_ARTIFACT' if not a else 'NOT_REVIEWED')
        if c.get('subject_key') and 'AMBIGUOUS' in idmap.get(c['subject_key'], set()):
            subject_status = 'AMBIGUOUS'
        elif not c.get('subject') or c['subject'] not in named:
            subject_status = 'NOT_IN_MODEL'
        else:
            subject_status = 'RESOLVED'
        facts = dict(c, artifact_present=bool(a), passage_found=found, evidence=evidence,
                     provenance_kind='DOCUMENT' if a else None, subject_status=subject_status)
        verdict_row = H.gate(facts)
        row = {'key': c['key'], 'kind': 'RESEARCH', 'research': c['research'], 'subject': c.get('subject'),
               'subject_key': c.get('subject_key'), 'subject_status': subject_status, 'property': c['property'],
               'statement': c['statement'], 'value': c.get('value'), 'artifact': c.get('artifact'), 'sha256': sha,
               'locus': locus, 'quote': quote, 'passage_found': found, 'lang': c.get('lang'), 'url': c.get('url'),
               'document_date': dates.get(c.get('artifact')),
               'evidence': {'verdict': evidence, 'decisions': sorted({(v[1], v[2], v[3], v[4]) for v in mine},
                                                                     key=repr)[:6]},
               'claimed': c.get('claimed') or {}, 'statement_mode': c['statement_mode'], 'temporal': c['temporal'],
               'temporal_note': c.get('temporal_note'), 'depends_on': c.get('depends_on') or [],
               'gates': H.gates(facts)}
        row.update(verdict_row)
        rows.append(row)
    # the model's own history-like rows
    for v in L.read_table('state/vintage-statements.jsonl'):
        p = prov[v['provenance']]
        wine, year = v['vintage'].split(':')[1], int(v['vintage'].split(':')[2])
        facts = {'artifact_present': False, 'passage_found': False, 'provenance_kind': p['kind'], 'evidence': 'NO_ARTIFACT',
                 'statement_mode': 'UNKNOWN', 'temporal': 'STATED', 'subject_status': 'RESOLVED'}
        row = {'key': 'legacy-not-made:%s' % v['vintage'], 'kind': 'MODEL', 'research': 'data/vintages.js BDX_NOT_PRODUCED (Phase 4)',
               'subject': wine, 'subject_status': 'RESOLVED', 'property': 'produced', 'value': False,
               'statement': 'not produced in %d (legacy, %s)' % (year, p['kind']), 'record': v['id'],
               'claimed': {'claimed_validity': {'valid_from': V(year), 'valid_to': V(year)}},
               'statement_mode': 'UNKNOWN', 'temporal': 'STATED', 'evidence': {'verdict': 'NO_ARTIFACT'},
               'provenance_kind': p['kind'], 'gates': H.gates(facts)}
        row.update(H.gate(facts))
        rows.append(row)
    for o in L.read_table('observation/observations.jsonl'):
        if o['field'] not in ('owner', 'history') or not isinstance(o.get('value'), str):
            continue
        if not (A_YEAR.search(o['value']) and (o['field'] == 'owner' or SINCE.search(o['value']))):
            continue
        p = prov[o['provenance']]
        facts = {'artifact_present': bool(o.get('artifact')), 'passage_found': False, 'provenance_kind': p['kind'],
                 'evidence': 'NO_ARTIFACT', 'statement_mode': 'UNKNOWN', 'temporal': 'STATED', 'subject_status': 'RESOLVED'}
        row = {'key': 'legacy-%s:%s' % (o['field'], o['id']), 'kind': 'MODEL', 'research': 'data/chateaux.js %s (legacy)' % o['field'],
               'subject': o['subject'], 'subject_status': 'RESOLVED', 'property': o['field'], 'observation': o['id'],
               'statement': o['value'][:120], 'statement_mode': 'UNKNOWN', 'temporal': 'STATED',
               'evidence': {'verdict': 'NO_ARTIFACT'}, 'provenance_kind': p['kind'], 'gates': H.gates(facts)}
        row.update(H.gate(facts))
        rows.append(row)
    for r in L.read_table('state/rank-absences.jsonl'):
        p = prov[r['provenance']]
        facts = {'artifact_present': False, 'passage_found': False, 'provenance_kind': p['kind'], 'evidence': 'NO_ARTIFACT',
                 'statement_mode': 'UNKNOWN', 'temporal': 'NONE', 'subject_status': 'RESOLVED', 'excluded_as': 'CURRENT_STATEMENT'}
        row = {'key': 'dataset-no-%s:%s' % (r['tier'].lower(), r['estate']), 'kind': 'MODEL',
               'research': 'data/chateaux.js second: "-" (6.2 section 6)', 'subject': r['estate'], 'subject_status': 'RESOLVED',
               'property': 'rank_absence.%s' % r['tier'], 'record': r['id'],
               'statement': 'no %s wine (%s claim, undated)' % (r['tier'].lower(), r['claimant']),
               'statement_mode': 'UNKNOWN', 'temporal': 'NONE', 'evidence': {'verdict': 'NO_ARTIFACT'},
               'provenance_kind': p['kind'], 'gates': H.gates(facts)}
        row.update(H.gate(facts))
        rows.append(row)
    for r in rows:
        r['id'] = 'hc_' + L.stable_hash('HistoricalCandidate', r['key'])
        r['extractor'] = H.VERSION
    rows.sort(key=lambda r: (r['kind'] != 'RESEARCH', r['key']))
    body = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in rows).encode('utf-8')
    if '--check' in sys.argv:
        same = os.path.exists(OUT) and open(OUT, 'rb').read() == body
        print('data/audit/historical-m3-candidates.jsonl ' + ('is current' if same else 'differs from a fresh run'))
        sys.exit(0 if same else 1)
    counts = collections.Counter(r['category'] for r in rows)
    print('%d candidates: %s' % (len(rows), json.dumps(dict(counts.most_common()))))
    accepted = [r for r in rows if r['category'] == H.ACCEPTED]
    print('historical facts the model would gain: %d' % len(accepted))
    if '--dry-run' in sys.argv:
        for r in rows:
            if r['kind'] == 'RESEARCH':
                print('  %-30s %-27s %-14s %s' % (r['key'], r['category'], r['evidence']['verdict'], ','.join(r['failed'])))
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(OUT + '.tmp', OUT)
    print('wrote', os.path.relpath(OUT, L.ROOT))


if __name__ == '__main__':
    main()
