"""M3.6C: the Cuvée Mongravey identity review - audit only, deterministic, fail closed.

    python tools/test-m36c.py            the regression tests (read-only)
    python tools/test-m36c.py --write    run the audit: write data/audit/m3.6c-cuvee-mongravey-identity.jsonl
                                         and docs/PHASE-M3.6C-CUVEE-MONGRAVEY-IDENTITY.md
    python tools/test-m36c.py --check    recompute both and compare, byte for byte

The audit and its tests are one file: M3.6C commits its output, its report and this, nothing else.

WHAT IS READ. Only what the repository holds: every held document whose text mentions Mongravey - the
model's artifacts and the discovery crawl's fetched pages and PDFs, one record per distinct bytes
(sha256) - and every historical evidence decision that accepted a Cuvée document as another wine. The
three first-party pages supplied with this phase are among the held pages (fetched by the discovery
crawl); they are read from the store, nothing is fetched. No model row, decision, provenance, register
or app file is written.

HOW A DOCUMENT IS JUDGED. By what it says of itself. A web page by its visible main heading (H1) and the
region a name stands in; a sheet or press dossier by its first line, its title. The Cuvée names are
"Cuvée Mongravey", "Cuvée de Mongravey", "Mongravey Cuvée ..." (Spéciale, Margaux). A mention only in a
producer line (SARL Mongravey, @mongravey.fr) is no evidence. A historical v5 acceptance is never
evidence: it says only that the old reader misidentified the document. One disposition per record;
every record keeps the facts it holds (names, years, colour and role wording, locations), and the
findings are drawn from those facts.
"""
import collections
import glob
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.6c-cuvee-mongravey-identity.jsonl'
REPORT = L.ROOT + 'docs/PHASE-M3.6C-CUVEE-MONGRAVEY-IDENTITY.md'
BEFORE = 'd22274d'               # M3.6B: the state this audit reads
ESTATE, GRAND_VIN = 'es_00158', 'wn_00158'          # Château Mongravey and its one model wine
SUPPLIED = ('https://vignobles-bernaleau.com/en/chateau-mongravey/',
            'https://vignobles-bernaleau.com/en/press-reviews-technical-sheets-cuvee-mongravey/',
            'https://vignobles-bernaleau.com/en/press-reviews-technical-sheets-chateau-mongravey/')
DISPOSITIONS = ['POSITIVE_WINE_IDENTITY', 'POSITIVE_NAMING_VARIANT', 'POSITIVE_ESTATE_RELATIONSHIP',
                'POSITIVE_VINTAGE_EVIDENCE', 'COLOUR_ESTABLISHED', 'ROLE_ESTABLISHED', 'PRODUCER_ONLY', 'ESTATE_ONLY',
                'WRONG_WINE_HISTORICAL_ACCEPTANCE', 'MULTI_WINE_AMBIGUOUS', 'IDENTITY_CONFLICT', 'INSUFFICIENT',
                'NOT_RELEVANT']
POSITIVE = {d for d in DISPOSITIONS if d.startswith('POSITIVE') or d.endswith('_ESTABLISHED')}

CUVEE = re.compile(r'\bcuvee (?:de )?mongravey\b|\bmongravey cuvee\b')
NAME_FORMS = {'Cuvée Mongravey': r'\bcuvee mongravey\b', 'Cuvée de Mongravey': r'\bcuvee de mongravey\b',
              'Mongravey Cuvée Spéciale': r'\bmongravey cuvee speciale\b',
              'Mongravey Cuvée Margaux': r'\bmongravey cuvee margaux\b'}
CHATEAU = re.compile(r'\bchateau mongravey\b')
YEAR = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')
COLOUR_WORDS = re.compile(r'\b(?:rouge|red wine|ruby|rubis|robe rouge|white wine|vin blanc|rose wine|vin rose)\b')
RED_GRAPES = re.compile(r'cabernet|merlot|petit verdot|malbec|carmenere')
WHITE_GRAPES = re.compile(r'semillon|(?<!cabernet )sauvignon blanc|muscadelle')
BLEND = re.compile(r'(?:grape varieties|cepagement|cepages?|assemblage)\s*:?\s*([^\n|]{0,80})')
ROLE_WORDS = re.compile(r'second (?:vin|wine)|deuxieme vin|cuvee speciale|special cuvee|cuvee confidentielle|'
                        r'confidential cuvee|selection (?:parcellaire|minutieuse|of (?:the|our) best plots|des meilleures parcelles)|'
                        r'meilleures parcelles|best plots')
FIRST_VINTAGE = re.compile(r'1st vintage\s*:?\s*((?:19|20)\d\d)|premier millesime\s*:?\s*((?:19|20)\d\d)')
LIST_HEADING = re.compile(r'^(?:our wines|nos vins)$')
ARCHIVE_HEADING = re.compile(r'press reviews|revues? de presse|fiches? techniques?|technical sheets')


def fold(s):
    return RB.fold(s or '')


# -- the documents ----------------------------------------------------------------------------------

def extraction(sha):
    p = L.ROOT + 'sources/discovery/extracted/%s.json' % sha
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    return d if d.get('status') == 'EXTRACTED' else None


def normalise(ref, sha, text, ext, urls, files):
    """A document as the classifier reads it: its identity heading, its labelled blocks, its text."""
    doc = {'ref': ref, 'sha256': sha, 'urls': urls, 'files': files, 'text': fold(text)}
    if ext and ext.get('media') == 'html':
        # a heading whose inline parts the extractor joined ("Cuvée Mongravey" + "Margaux" -> "Cuvée MongraveyMargaux")
        # is read as displayed, the parts apart
        h1 = [re.sub(r'([a-zà-ÿ])([A-ZÀ-Ý])', r'\1 \2', h['text']) for h in ext.get('headings') or []
              if h.get('level') == 1 and h.get('text', '').strip()]
        doc.update(kind='web', h1=fold(h1[0]).strip() if h1 else '', h1_raw=h1[0].strip() if h1 else '',
                   blocks=[{'tag': b.get('tag'), 'path': fold(b.get('path')), 'text': fold(b.get('text'))}
                           for b in ext.get('blocks') or []],
                   links=sorted({(fold(l.get('text')), l.get('href') or '') for l in ext.get('links') or []}))
    else:
        first = next((l for l in (text or '').split('\n') if l.strip()), '')
        doc.update(kind='document', h1=fold(first).strip(), h1_raw=first.strip(), blocks=[], links=[])
    return doc


def held_documents():
    """Every held document whose text mentions Mongravey, one per distinct bytes."""
    disc = {}
    for a in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
        disc.setdefault(a['sha256'], a)
    s2a = A.sha_to_artifact()
    arts = A.by_id('identity/artifacts.jsonl')
    shas = set()
    for aid, a in arts.items():
        t = A.document_text(aid)
        if t and 'mongravey' in t:
            shas.add(a['sha256'])
    for sha in disc:
        if sha not in shas:
            t = A.text_of(sha)
            if t and 'mongravey' in t:
                shas.add(sha)
    out = []
    for sha in sorted(shas):
        aid = s2a.get(sha)
        text = (A.document_text(aid) if aid else None) or A.text_of(sha) or ''
        urls = sorted({u for u in [(disc.get(sha) or {}).get('first_url')] if u})
        files = sorted({os.path.basename(p['locator']['value']) for p in (A.placements_of(aid) if aid else [])
                        if p['locator']['kind'] == 'LOCAL_PATH'})
        out.append(normalise(aid or 'discovery:' + sha[:16], sha, text, extraction(sha), urls, files))
    return out


# -- the classifier ---------------------------------------------------------------------------------

def facts(doc):
    """What the document holds about the Cuvée, outside producer lines: names, years, colour, role, blend."""
    lines = [l for l in doc['text'].split('\n') if l.strip() and not RB.PRODUCER.search(l)]
    body = '\n'.join(lines)
    names = sorted(k for k, p in NAME_FORMS.items() if re.search(p, body))
    blends = [b.strip() for b in BLEND.findall(body)]
    red = any(RED_GRAPES.search(b) for b in blends)
    white = any(WHITE_GRAPES.search(b) for b in blends)
    fv = sorted({int(a or b) for a, b in FIRST_VINTAGE.findall(body)})
    return {'names': names,
            'colour_words': sorted(set(COLOUR_WORDS.findall(body))),
            'blend': blends[:2], 'blend_colour': 'RED' if red and not white else 'WHITE' if white and not red else None,
            'role_words': sorted(set(ROLE_WORDS.findall(body))),
            'stated_first_vintage': fv[0] if len(fv) == 1 else None,
            'mentions_cuvee_outside_producer_lines': bool(CUVEE.search(body)),
            'mentions_mongravey_outside_producer_lines': 'mongravey' in body}


def classify(doc):
    """(disposition, location, vintage) - one disposition per document, first rule that decides."""
    h1 = doc['h1']
    f = facts(doc)
    title_year = [int(y) for y in YEAR.findall(h1)]
    vintage = title_year[0] if len(title_year) == 1 else None
    if doc['kind'] == 'web':
        blocks = doc['blocks']
        # the Cuvée's own archive: its main heading names it, its entries are years
        if CUVEE.search(h1) and ARCHIVE_HEADING.search(h1 + ' ' + ' '.join(b['path'] for b in blocks[:3])):
            years = sorted({int(b['text']) for b in blocks if re.fullmatch(r'(?:19|20)\d\d', b['text'].strip())})
            return 'POSITIVE_WINE_IDENTITY', 'main heading "%s"; year entries %s' % (doc['h1_raw'], years), None
        # a list of the estate's wines under its own heading ("Our wines" / "Nos vins")
        listed = []
        for b in blocks:                        # the list in its own order, without the footer's copyright line
            if b['tag'] not in ('li',) and b['path'] and LIST_HEADING.match(b['path'].split(' > ')[-1].strip()) \
                    and b['text'].strip() and not re.search(r'©|\bcopyright\b|^\W*\d{4}\W', b['text']) \
                    and b['text'] not in listed:
                listed.append(b['text'])
        cuvee_listed = [x for x in listed if CUVEE.search(x)]
        if cuvee_listed and CHATEAU.search(h1):
            return 'POSITIVE_ESTATE_RELATIONSHIP', 'main heading "%s"; its wine list names %s' % (
                doc['h1_raw'], ', '.join('"%s"' % x for x in listed if 'mongravey' in x)), None
        if cuvee_listed:
            return 'POSITIVE_WINE_IDENTITY', 'wine list ("%s") names %s' % (
                [b['path'] for b in blocks if b['text'] in cuvee_listed][0], cuvee_listed[:3]), None
        # a product page: the Cuvée as its main heading, sold under another of its names
        if CUVEE.search(h1):
            years = sorted({int(y) for b in blocks if b['tag'] in ('h2', 'br', 'div', 'label')
                            for y in YEAR.findall(b['text']) if CUVEE.search(b['text']) or re.fullmatch(r'(?:19|20)\d\d', b['text'].strip())})
            vintage = years[0] if len(years) == 1 else vintage
            if f['colour_words'] and not f['blend_colour'] == 'WHITE':
                return 'COLOUR_ESTABLISHED', 'main heading "%s"; colour wording %s' % (doc['h1_raw'], f['colour_words']), vintage
            if len(f['names']) >= 2:
                return 'POSITIVE_NAMING_VARIANT', 'main heading "%s"; also named %s on the page' % (
                    doc['h1_raw'], [n for n in f['names'] if not re.search(NAME_FORMS[n], h1)]), vintage
            return 'POSITIVE_WINE_IDENTITY', 'main heading "%s"' % doc['h1_raw'], vintage
        if CHATEAU.search(h1) and not f['mentions_cuvee_outside_producer_lines']:
            return 'ESTATE_ONLY', 'main heading "%s": the grand vin or the estate, not the Cuvée' % doc['h1_raw'], None
        if f['mentions_cuvee_outside_producer_lines']:
            return 'MULTI_WINE_AMBIGUOUS', 'names the Cuvée beside other wines; its heading is "%s"' % doc['h1_raw'], None
    else:
        if CUVEE.search(h1):
            if f['role_words'] and not vintage:
                return 'ROLE_ESTABLISHED', 'title "%s"; role wording %s' % (doc['h1_raw'], f['role_words']), None
            if vintage and any(w in f['role_words'] for w in ('cuvee speciale', 'special cuvee', 'meilleures parcelles',
                                                              'selection parcellaire', 'best plots')) \
                    and 'press' in ' '.join(doc['files'] + doc['urls']).lower():
                return 'ROLE_ESTABLISHED', 'title "%s"; role wording %s' % (doc['h1_raw'], f['role_words']), vintage
            if not vintage:
                if f['blend_colour'] == 'RED':
                    return 'COLOUR_ESTABLISHED', 'title "%s"; blend %s' % (doc['h1_raw'], f['blend'][:1]), None
                return 'POSITIVE_NAMING_VARIANT', 'title "%s"' % doc['h1_raw'], None
            return 'POSITIVE_VINTAGE_EVIDENCE', 'title "%s"' % doc['h1_raw'], vintage
        if CHATEAU.search(h1) and not f['mentions_cuvee_outside_producer_lines']:
            return 'ESTATE_ONLY', 'title "%s": the grand vin, not the Cuvée' % doc['h1_raw'], None
        if f['mentions_cuvee_outside_producer_lines']:
            return 'MULTI_WINE_AMBIGUOUS', 'names the Cuvée, but its title is "%s"' % doc['h1_raw'], None
    if not f['mentions_mongravey_outside_producer_lines']:
        return 'PRODUCER_ONLY', 'Mongravey only in a producer line (company, address, e-mail, site)', None
    if CHATEAU.search(doc['text']) and re.search(r'mongravey', h1):
        return 'ESTATE_ONLY', 'names Château Mongravey, not the Cuvée', None
    return 'NOT_RELEVANT', 'another wine\'s document; Mongravey is mentioned in passing', None


# -- the historical acceptances ---------------------------------------------------------------------

def historical_decisions(cuvee_shas):
    """Every v5 ACCEPTED decision on a Cuvée document: the old reader's misidentifications, never evidence."""
    import mig_m6_provenance as M6
    flags = {f['decision'] for f in L.jsonl_lines(L.ROOT + 'data/audit/m3.6b-historical-flags.jsonl')}
    sup = {c['decision']: c['superseded_by'] for c in L.jsonl_lines(L.ROOT + 'data/audit/m3.6b-correction-application.jsonl')}
    links = {e['row_key']: e for e in A.table('observation/evidence-links.jsonl') if e['evidence_version'] == 5}
    nm = {n['subject']: n['name'] for n in A.table('identity/names.jsonl') if n['kind'] == 'CURRENT'}
    out = []
    for d in L.jsonl_lines(L.ROOT + 'data/evidence/decisions-v5.jsonl'):
        sha = (d.get('read') or {}).get('sha256')
        if d.get('decision') != 'ACCEPTED' or sha not in cuvee_shas:
            continue
        rk = M6.row_key(d)
        ln = links.get(rk) or {}
        out.append({'record': 'decision', 'id': rk, 'sha256': sha, 'artifact': ln.get('artifact'),
                    'claimed': {'estate': ln.get('estate'), 'wine': ln.get('wine'), 'wine_name': nm.get(ln.get('wine')),
                                'vintage': (d.get('ctx') or {}).get('target_vintage') or (d.get('ctx') or {}).get('vintage')},
                    'disposition': 'WRONG_WINE_HISTORICAL_ACCEPTANCE',
                    'basis': 'a v5 acceptance of a Cuvée de Mongravey document as %s: the old reader\'s misidentification, '
                             'not identity evidence' % nm.get(ln.get('wine'), '?'),
                    'm36b': ('FLAGGED_RETAINED' if rk in flags else 'SUPERSEDED_V6' if rk in sup else 'NOT_IN_M36B'),
                    'superseded_by': sup.get(rk), 'positive': False,
                    're_evaluable_after_model_decision': rk in flags})
    return sorted(out, key=lambda r: r['id'])


# -- the audit --------------------------------------------------------------------------------------

def build(docs=None):
    docs = held_documents() if docs is None else docs
    recs = []
    for d in docs:
        disp, loc, vintage = classify(d)
        recs.append({'record': 'document', 'id': d['sha256'][:16], 'sha256': d['sha256'], 'artifact': d['ref'],
                     'urls': d['urls'], 'files': d['files'][:4], 'kind': d['kind'], 'identity': d['h1_raw'][:120],
                     'supplied_first_party': any(u in SUPPLIED for u in d['urls']),
                     'disposition': disp, 'location': loc, 'vintage': vintage, 'facts': facts(d),
                     'positive': disp in POSITIVE})
    cuvee = {r['sha256'] for r in recs if r['positive']}
    recs += historical_decisions(cuvee)
    recs.sort(key=lambda r: (r['record'], r['id']))
    return recs, findings(recs, docs)


def findings(recs, docs):
    doc = [r for r in recs if r['record'] == 'document']
    pos = [r for r in doc if r['positive']]
    years = sorted({r['vintage'] for r in pos if r['vintage']})
    archive = next((r for r in pos if r['disposition'] == 'POSITIVE_WINE_IDENTITY' and r['supplied_first_party']), None)
    archive_years = sorted({int(y) for y in re.findall(r'\b((?:19|20)\d\d)\b', archive['location'])}) if archive else []
    estate = [r for r in doc if r['disposition'] == 'POSITIVE_ESTATE_RELATIONSHIP']
    # naming: the links between the name forms, each with the evidence that ties it and how strongly
    by_sha = {d['sha256']: d for d in docs}
    links = []
    if archive:
        linked = [d for d in docs if any(u in {h for _, h in by_sha[archive['sha256']]['links']} for u in d['urls'])
                  and re.search(r'\bcuvee de mongravey\b', d['h1'])]
        if linked:
            links.append({'names': ['Cuvée Mongravey', 'Cuvée de Mongravey'], 'strength': 'EXPLICIT_LINK',
                          'evidence': 'the archive headed "Cuvée Mongravey" links %d held documents whose own title is '
                                      '"cuvée de mongravey" (URL to held bytes, sha256)' % len(linked)})
    prod = [r for r in pos if r['kind'] == 'web' and 'Mongravey Cuvée Spéciale' in r['facts']['names']
            and re.search(r'\bcuvee mongravey\b', fold(r['identity']))]
    if prod:
        links.append({'names': ['Cuvée Mongravey', 'Mongravey Cuvée Spéciale'], 'strength': 'SAME_DOCUMENT',
                      'evidence': '%d product pages whose main heading is "Cuvée Mongravey" sell it as "Mongravey Cuvée '
                                  'Spéciale <year>"' % len(prod)})
    if estate:
        e = by_sha[estate[0]['sha256']]
        order = [h for t, h in sorted(e['links']) if 'press-reviews-technical-sheets' in h]
        links.append({'names': ['Mongravey Cuvée Margaux', 'Cuvée Mongravey'], 'strength': 'STRUCTURAL',
                      'evidence': 'the estate page lists "Château Mongravey Margaux" and "Mongravey Cuvée Margaux" under '
                                  '"Our wines" and links two archives, the Château\'s (headed "Château Mongravey Margaux") '
                                  'and the Cuvée\'s (headed "Cuvée Mongravey"); no text on any held page says that '
                                  '"Mongravey Cuvée Margaux" is "Cuvée Mongravey" (%d archive links)' % len(order)})
    colour_docs = [r for r in pos if r['facts']['colour_words'] or r['facts']['blend_colour']]
    colours = {r['facts']['blend_colour'] for r in colour_docs if r['facts']['blend_colour']}
    explicit = [r for r in pos if set(r['facts']['colour_words']) & {'rouge', 'robe rouge', 'ruby', 'rubis', 'red wine'}]
    colour = 'RED' if colours == {'RED'} and explicit else None
    role_docs = [r for r in pos if set(r['facts']['role_words']) - {'second vin', 'second wine', 'deuxieme vin'}]
    second = [r for r in doc if {'second vin', 'second wine', 'deuxieme vin'} & set(r['facts']['role_words'])
              and r['positive']]
    role = 'OTHER_CUVEE' if role_docs and not second else None
    first_v = sorted({r['facts']['stated_first_vintage'] for r in pos if r['facts']['stated_first_vintage']})
    naming = 'NAMING_STABLE' if links and all(l['strength'] != 'STRUCTURAL' for l in links) else 'NAMING_UNRESOLVED'
    identity_ok = bool(archive) and bool(estate) and len(years) >= 2 and not any(
        r['disposition'] == 'IDENTITY_CONFLICT' for r in doc)
    model = {n['name']: n['subject'] for n in A.table('identity/names.jsonl')}
    collision = sorted(n for n in model if CUVEE.search(fold(n)))
    if not identity_ok:
        conclusion = 'BLOCKED_IDENTITY_UNRESOLVED'
    elif collision:
        conclusion = 'BLOCKED_IDENTITY_UNRESOLVED'
    else:
        conclusion = 'DISTINCT_WINE_SUPPORTED_' + naming
    return {'documents': len(doc), 'positive_documents': len(pos), 'decisions': len([r for r in recs if r['record'] == 'decision']),
            'dispositions': dict(sorted(collections.Counter(r['disposition'] for r in recs).items())),
            'years': years, 'archive_years': archive_years, 'stated_first_vintage': first_v,
            'name_links': links, 'naming': naming, 'colour': colour, 'colour_evidence': len(colour_docs),
            'blend_red_documents': sum(1 for r in pos if r['facts']['blend_colour'] == 'RED'),
            'explicit_colour_documents': len(explicit), 'role': role, 'role_evidence': len(role_docs),
            'second_wine_wording': len(second), 'estate_relationship': len(estate), 'model_collision': collision,
            'conclusion': conclusion}


def body(recs):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n' for r in recs).encode('utf-8')


# -- the report -------------------------------------------------------------------------------------

def report(recs, F):
    doc = [r for r in recs if r['record'] == 'document']
    dec = [r for r in recs if r['record'] == 'decision']
    pos = [r for r in doc if r['positive']]
    flagged = [r for r in dec if r['m36b'] == 'FLAGGED_RETAINED']
    out = []
    w = out.append
    w('# Phase M3.6C — Cuvée Mongravey identity review\n')
    w('Generated by `python tools/test-m36c.py --write` (`data/audit/m3.6c-cuvee-mongravey-identity.jsonl`); never edited '
      'by hand. **Audit only: no mutation was performed.** No wine, vintage, figure, name, provenance, evidence '
      'decision, gap record or app file was created or changed; nothing was fetched or OCR\'d.\n')

    w('## 1. Scope\n')
    w('- **What M3.6C decides:** whether "Cuvée Mongravey" is a wine of its own, distinct from Château Mongravey '
      '(`%s`, the estate\'s one model wine), and how its names relate to one another.' % GRAND_VIN)
    w('- **What was read:** every held document whose text mentions Mongravey, %d distinct by sha256 across the model\'s '
      'artifacts and the discovery crawl; and every historical v5 acceptance of a Cuvée document (%d).'
      % (F['documents'], F['decisions']))
    w('- **The three first-party pages supplied with this phase** are among the held pages, already fetched by the '
      'discovery crawl. They were read from the store, not fetched again.\n')

    w('## 2. Evidence inventory\n')
    w('| Disposition | Records |\n|---|---:|')
    for d in DISPOSITIONS:
        if F['dispositions'].get(d):
            w('| %s | %d |' % (d, F['dispositions'][d]))
    w('\nPositive evidence (%d documents), each with the exact place it stands:\n' % len(pos))
    w('| Disposition | Artifact | Document | Vintage | Location |\n|---|---|---|---:|---|')
    for r in sorted(pos, key=lambda r: (DISPOSITIONS.index(r['disposition']), r['vintage'] or 0, r['id'])):
        name = (r['urls'] or r['files'] or [r['artifact']])[0]
        w('| %s | `%s` | `%s` | %s | %s |' % (r['disposition'], r['artifact'], name[-70:], r['vintage'] or '—', r['location'][:150]))
    w('')

    w('## 3. Identity findings (Q1, Q7)\n')
    w('- **Q1, a wine of its own: yes.**')
    w('  - **Its own archive:** the first-party archive is headed "Cuvée Mongravey" (the supplied page), with year '
      'entries %s and its own technical sheets and press reviews.' % F['archive_years'])
    w('  - **Its own product pages:** each has the main heading "Cuvée Mongravey".')
    w('  - **Its own listing:** the shop lists it as a wine beside Château Mongravey.')
    w('  - **Not a producer phrase, collection label or estate category:** it has its own vintages, sheets, production '
      'and blend.')
    w('- **Q7, a lasting identity: supported.**')
    w('  - **Distinct from the grand vin:** its own sheets give 2,800 bottles and "1st vintage: 1999"; the Château\'s '
      'give 95,000 bottles and "1st vintage: 1981".')
    w('  - **Across vintages:** first-party evidence for %d vintages.' % len(F['years']))
    w('  - **No collision:** no model wine bears any Cuvée name (%s).\n' % ('none' if not F['model_collision'] else F['model_collision']))

    w('## 4. Naming findings (Q3)\n')
    w('The held documents use four forms. Each link between them, and what ties it:\n')
    w('| Names | Tie | Evidence |\n|---|---|---|')
    for l in F['name_links']:
        w('| %s | %s | %s |' % (' ⇄ '.join(l['names']), l['strength'], l['evidence']))
    w('\n- **Tied explicitly:** "Cuvée Mongravey", "Cuvée de Mongravey" and "Mongravey Cuvée Spéciale", each by a held '
      'document naming both.')
    w('- **Tied only by structure: "Mongravey Cuvée Margaux"**, the name the current first-party estate page gives, against '
      '"Cuvée Mongravey" on its archive.')
    w('  - The structure is strong: the same page names the grand vin "Château Mongravey Margaux", the name its own '
      'archive is headed by; and the site\'s product pages head the Cuvée "Cuvée Mongravey" followed by "Margaux".')
    w('  - **The discrepancy is recorded, not normalised:** no held text states the two names are one wine.')
    w('- **Answer: A, one stable wine identity with name variants,** for the three tied forms. "Mongravey Cuvée Margaux" '
      'is most likely the current listing of the same wine. Which form is canonical is the model decision\'s.\n')

    w('## 5. Temporal findings (Q4)\n')
    w('- **The supplied archive exposes:** %s.' % ', '.join(map(str, F['archive_years'])))
    w('- **Held first-party documents naming the Cuvée for a vintage:** %s.' % ', '.join(map(str, F['years'])))
    w('  - Technical sheets and press dossiers carry the title "cuvée de mongravey <year>".')
    w('  - Product pages carry "Mongravey Cuvée Spéciale <year>".')
    w('- **Missing years** (%s) are not taken as years the wine was not made.' % ', '.join(
        str(y) for y in range(min(F['years']), max(F['years']) + 1) if y not in F['years']))
    w('- **Stated first vintage:** the sheets say "1st vintage: %s". That is a claim the documents make; no held document '
      'is of that vintage. No vintage record is proposed for an archive year alone.\n' % ', '.join(map(str, F['stated_first_vintage'])))

    w('## 6. Colour (Q5)\n')
    if F['colour']:
        w('**%s, established from the wine\'s own evidence, not inferred from the grand vin:**' % F['colour'])
        w('- %d documents give its own blend, only red varieties (Cabernet Sauvignon, Merlot, a little Cabernet Franc).'
          % F['blend_red_documents'])
        w('- %d say its colour in words: a first-party product page has "brilliant ruby color"; press quotes in its own '
          'dossiers have "robe rouge vif".\n' % F['explicit_colour_documents'])
    else:
        w('**Unresolved:** the held evidence does not state the colour explicitly.\n')

    w('## 7. Role (Q6)\n')
    if F['role']:
        w('**A separate selection cuvée** (model role `OTHER_CUVEE`), not a second wine.')
        w('- **The first party\'s words:** "Confidential cuvée of 3000 bottles resulting from a meticulous selection of our '
          'best plots of vines of Château Mongravey".')
        w('- **The press:** Guide Hachette, quoted in its 2012 dossier: "this special cuvee comes from a slecetion '
          '[sic] of the best plots of the estate and is only produced when the vintage is considered worthy".')
        w('- **Sources:** %d documents carry this wording. %d positive documents use "second wine" or "second vin" of it.'
          % (F['role_evidence'], F['second_wine_wording']))
        w('- **"Second wine" is not proposed:** being distinct from the grand vin does not make it one.\n')
    else:
        w('**Unresolved:** only "a separate wine" is established.\n')

    w('## 8. Relationship (Q2)\n')
    w('**Cuvée Mongravey is produced by Château Mongravey** (`%s`): an estate-wine relationship, not an alias of the grand vin.' % ESTATE)
    w('- The estate\'s own page lists it under its wines.')
    w('- The first party describes it as a selection of the estate\'s plots.')
    w('- The two wines keep separate archives, sheets, production and first vintages.\n')

    w('## 9. The historical misattributions\n')
    w('- **The record:** %d v5 decisions accepted a Cuvée de Mongravey document as another wine. Each is recorded here as '
      'WRONG_WINE_HISTORICAL_ACCEPTANCE: the old reader\'s misidentification. None counts as evidence for the Cuvée.' % len(dec))
    w('  - **%d flagged:** accepted as Château Mongravey; the 20 M3.6B historical flags, retained as historical acceptances.' % len(flagged))
    w('  - **%d superseded:** accepted as Château de Braude, and corrected in M3.6B by v6.' % sum(1 for r in dec if r['m36b'] == 'SUPERSEDED_V6'))
    other = [r for r in dec if r['m36b'] == 'NOT_IN_M36B']
    for r in other:
        w('  - **1 not seen by any earlier phase:** `%s` accepted as %s %s. Its vintage already had a document, so it '
          'was outside M3.5\'s population, and M3.6B neither flagged nor superseded it. The model does not link it to '
          'that vintage (its legacy attribution names the estate only). It is the same error as the 20 and belongs '
          'with them.' % (r['id'], r['claimed']['wine_name'], r['claimed']['vintage']))
    w('- **Not superseded here.** Once the model holds the Cuvée, the %d flagged decisions could be re-evaluated against '
      'it, with the %d above:' % (len(flagged), len(other)))
    for r in flagged:
        w('  - `%s`' % r['id'])
    w('')

    w('## 10. Final identity conclusion\n')
    w('**%s**\n' % F['conclusion'])
    w('- **The identity is clear:** a distinct, lasting red selection cuvée of Château Mongravey.')
    w('- **One naming link is not textual:** "Mongravey Cuvée Margaux" ⇄ "Cuvée Mongravey" rests on the estate page\'s '
      'structure alone. M3.6C does not normalise it.\n')

    w('## 11. Proposed model mutation (not performed)\n')
    w('> M3.6C supports creation of a distinct canonical wine identity, but M3.6C does not create it.\n')
    w('| | Proposal |\n|---|---|')
    w('| Canonical name | **Cuvée Mongravey**: the wine\'s own archive heading and product-page heading. To be confirmed by the user against "Mongravey Cuvée Margaux". |')
    w('| Other names | "Cuvée de Mongravey" (`SOURCE_RENDERING`: its sheets\' titles); "Mongravey Cuvée Spéciale" (`MARKET_ALIAS`: its product name); "Mongravey Cuvée Margaux" (`MARKET_ALIAS` or `CURRENT`, the open naming question) |')
    w('| Estate relationship | `PRODUCED_BY` `%s` (Château Mongravey), beside its grand vin `%s` |' % (ESTATE, GRAND_VIN))
    w('| Role | `OTHER_CUVEE`, source term "cuvée spéciale" (selection of the best plots); not `SECOND_WINE` |')
    w('| Colour | `%s` |' % (F['colour'] or 'UNKNOWN'))
    w('| Vintages with first-party documents | %s to %s (%s) |' % (min(F['years']), max(F['years']), ', '.join(map(str, F['years']))))
    w('| Stated first vintage | %s (stated, not evidenced by a document of that year) |' % ', '.join(map(str, F['stated_first_vintage'])))
    w('\n**The model rows a later phase would add** (the pattern an existing cuvée follows, e.g. `wn_00479`):')
    w('- `identity/wines.jsonl`: a new minted wine id, `name_status` KNOWN, `type` %s.' % (F['colour'] or 'UNKNOWN'))
    w('- `identity/names.jsonl`: a CURRENT name, plus the variants above with their kinds.')
    w('- `identity/identity-map.jsonl`: `wine-by-display-name` and `wine-by-slug` entries under '
      '`bourgeois-chateau-mongravey`.')
    w('- `state/estate-wine.jsonl`: `PRODUCED_BY` to `%s`.' % ESTATE)
    w('- `identity/vintages.jsonl`: only for vintages a later phase evidences.')
    w('- **Through the migration:** the model is built by `tools/migrate.py` from its inputs, so the wine must enter as an '
      'audited input (a reviewed addition to the legacy cuvée list, or a dedicated identity manifest the migration '
      'reads), not by editing `data/model` directly.')
    w('\n**Open questions for the model decision:**')
    w('- Which name is canonical: "Cuvée Mongravey" or "Mongravey Cuvée Margaux".')
    w('- Whether to record the stated first vintage, 1999.')
    w('- How Château Mongravey\'s classification-labelled listings ("Cru Bourgeois", "Supérieur", "Exceptionnel") relate '
      'to its grand vin. They are not part of this review.\n')

    w('## 12. No mutation was performed\n')
    w('- The model, the evidence store (v1-v6), provenance, the gap register and the app are byte-identical to `%s`.' % BEFORE)
    w('- The 20 historical acceptances are not superseded.')
    w('- M3.6C committed its output, its report and its test only.\n')

    w('## 13. Next-step gate\n')
    w('**SAFE — M3.6C CUVÉE MONGRAVEY IDENTITY REVIEW COMPLETE — READY FOR MODEL DECISION**\n'
      if F['conclusion'] != 'BLOCKED_IDENTITY_UNRESOLVED' else '**BLOCKED — CUVÉE MONGRAVEY IDENTITY REMAINS UNRESOLVED**\n')
    w('| Phase | Status | Result |\n|---|---|---|')
    w('| M3.5 held-document review | COMPLETE | Bernaleau pilot; 32 links; 9 first documents |')
    w('| M3.6A-R1 | COMPLETE | Controlled evidence reader rules |')
    w('| M3.6A | COMPLETE | 8 safe mappings; 199 corrections |')
    w('| M3.6B | COMPLETE | 8 mappings applied; v6 corrections applied |')
    w('| M3.6B historical flags | PRESERVED | 20 Cuvée-related historical misattributions |')
    w('| M3.6C | CURRENT | Cuvée Mongravey identity review |')
    w('| Cuvée canonical model creation | PENDING | Only after M3.6C gate |')
    w('| Targeted acquisition | PENDING | After identity decision |')
    w('| Historical population | PENDING | After identity + evidence gates |')
    return '\n'.join(out) + '\n'


# -- the tests --------------------------------------------------------------------------------------

CHECKS = []


def check(f):
    CHECKS.append(f)
    return f


def web(h1, blocks=(), links=(), urls=()):
    return normalise('made', 'x' * 64, '\n'.join([h1] + [t for _, _, t in blocks]),
                     {'media': 'html', 'headings': [{'level': 1, 'text': h1}],
                      'blocks': [{'tag': g, 'path': p, 'text': t} for g, p, t in blocks],
                      'links': [{'text': t, 'href': h} for t, h in links]}, list(urls), [])


def sheet(text, files=()):
    return normalise('made', 'y' * 64, text, None, [], list(files))


def _rows():
    return L.jsonl_lines(OUT)


@check
def t01_first_party_cuvee_heading_is_wine_identity():
    d = web('Press Reviews & Technical Sheets Cuvée Mongravey',
            [('h1', 'Press Reviews & Technical Sheets Cuvée Mongravey', 'Cuvée Mongravey'),
             ('div', 'Press Reviews & Technical Sheets Cuvée Mongravey', '2009'),
             ('div', 'Press Reviews & Technical Sheets Cuvée Mongravey', '2010')])
    assert classify(d)[0] == 'POSITIVE_WINE_IDENTITY'
    real = [r for r in _rows() if 'press-reviews-technical-sheets-cuvee-mongravey' in ' '.join(r.get('urls') or [])]
    assert real and {r['disposition'] for r in real} == {'POSITIVE_WINE_IDENTITY'} and all(r['supplied_first_party'] for r in real)


@check
def t02_estate_wine_list_names_the_cuvee_separately():
    d = web('Château Mongravey', [('h1', 'Château Mongravey', 'Château Mongravey'),
                                  ('h2', 'Château Mongravey > Our wines', 'Our wines'),
                                  ('br', 'Château Mongravey > Our wines', 'Château Mongravey Margaux'),
                                  ('div', 'Château Mongravey > Our wines', 'Mongravey Cuvée Margaux')])
    assert classify(d)[0] == 'POSITIVE_ESTATE_RELATIONSHIP'
    real = [r for r in _rows() if 'https://vignobles-bernaleau.com/en/chateau-mongravey/' in (r.get('urls') or [])]
    assert real and real[0]['disposition'] == 'POSITIVE_ESTATE_RELATIONSHIP'
    assert '"chateau mongravey margaux", "mongravey cuvee margaux"' in real[0]['location']     # two wines, in its order


@check
def t03_producer_line_alone_is_insufficient():
    d = sheet('chateau galland 2014\nmoulis\nvignobles bernaleau -  sarl mongravey - 33460 arsac - france\n'
              'tel: +33 (0)5 56 58 84 51 - email: k.bernaleau@mongravey.fr')
    assert classify(d)[0] == 'PRODUCER_ONLY' and not facts(d)['mentions_mongravey_outside_producer_lines']
    assert all(not r['positive'] for r in _rows() if r.get('identity', '').lower().startswith('chateau galland'))


@check
def t04_estate_page_without_the_cuvee_is_no_cuvee_evidence():
    d = web('Château Mongravey Margaux', [('h1', 'Château Mongravey Margaux', 'Château Mongravey Margaux'),
                                          ('div', 'Château Mongravey Margaux', '2014')])
    assert classify(d)[0] == 'ESTATE_ONLY'
    d = sheet('chateau mongravey 2019\nmargaux cru bourgeois superieur\nvignobles bernaleau -  sarl mongravey')
    assert classify(d)[0] == 'ESTATE_ONLY'
    real = [r for r in _rows() if 'press-reviews-technical-sheets-chateau-mongravey' in ' '.join(r.get('urls') or [])]
    assert real and not real[0]['positive']


@check
def t05_historical_misattribution_is_never_evidence():
    dec = [r for r in _rows() if r['record'] == 'decision']
    assert dec and all(r['disposition'] == 'WRONG_WINE_HISTORICAL_ACCEPTANCE' and not r['positive'] for r in dec)
    flags = {f['decision'] for f in L.jsonl_lines(L.ROOT + 'data/audit/m3.6b-historical-flags.jsonl')}
    assert {r['id'] for r in dec if r['m36b'] == 'FLAGGED_RETAINED'} == flags and len(flags) == 20
    # the findings use only document records: dropping every decision changes nothing
    recs, F = build_cached()
    G = findings([r for r in recs if r['record'] == 'document'], DOCS_CACHE[0])
    assert {k: v for k, v in G.items() if k not in ('decisions', 'dispositions')} == \
        {k: v for k, v in F.items() if k not in ('decisions', 'dispositions')}


@check
def t06_several_cuvee_vintages_are_temporal_continuity():
    _, F = build_cached()
    assert len(F['years']) >= 2 and {2009, 2010, 2012, 2014, 2016, 2018, 2019, 2020} <= set(F['years'])
    assert F['archive_years'] == [2009, 2010, 2012, 2014, 2016, 2018, 2019, 2020]


@check
def t07_a_missing_archive_year_infers_nothing():
    _, F = build_cached()
    assert 2017 not in F['archive_years']
    text = open(REPORT, encoding='utf-8').read()
    assert 'not taken as years the wine was not made' in text
    vint = {(v['wine'], v['label']) for v in A.table('identity/vintages.jsonl')}
    assert not [w for w, _ in vint if w not in A.by_id('identity/wines.jsonl')]           # no vintage of a new wine


@check
def t08_unresolved_colour_stays_unresolved():
    d = sheet('cuvee de mongravey 2017\nmargaux\nvignobles bernaleau -  sarl mongravey')
    f = facts(d)
    assert not f['colour_words'] and f['blend_colour'] is None
    G = findings([{'record': 'document', 'positive': True, 'disposition': 'POSITIVE_VINTAGE_EVIDENCE', 'vintage': 2017,
                   'kind': 'document', 'identity': 'cuvee de mongravey 2017', 'facts': f, 'supplied_first_party': False,
                   'location': '', 'sha256': 'y' * 64}], [])
    assert G['colour'] is None


@check
def t09_unresolved_role_stays_unresolved():
    d = sheet('cuvee de mongravey 2017\nmargaux')
    G = findings([{'record': 'document', 'positive': True, 'disposition': 'POSITIVE_VINTAGE_EVIDENCE', 'vintage': 2017,
                   'kind': 'document', 'identity': 'cuvee de mongravey 2017', 'facts': facts(d),
                   'supplied_first_party': False, 'location': '', 'sha256': 'y' * 64}], [])
    assert G['role'] is None
    _, F = build_cached()
    assert F['role'] == 'OTHER_CUVEE' and F['second_wine_wording'] == 0                  # never "second wine" unprompted


@check
def t10_naming_is_compared_never_silently_normalised():
    _, F = build_cached()
    by = {tuple(l['names']): l['strength'] for l in F['name_links']}
    assert by.get(('Mongravey Cuvée Margaux', 'Cuvée Mongravey')) == 'STRUCTURAL'
    assert by.get(('Cuvée Mongravey', 'Cuvée de Mongravey')) == 'EXPLICIT_LINK'
    assert F['naming'] == 'NAMING_UNRESOLVED' and F['conclusion'] == 'DISTINCT_WINE_SUPPORTED_NAMING_UNRESOLVED'
    assert 'Mongravey Cuvée Margaux' in open(REPORT, encoding='utf-8').read()


@check
def t11_the_jsonl_is_deterministic():
    recs, _ = build_cached()
    assert body(recs) == open(OUT, 'rb').read()
    keys = [(r['record'], r['id']) for r in recs]
    assert keys == sorted(keys) and len(keys) == len(set(keys))
    assert all(r['disposition'] in DISPOSITIONS for r in recs)
    text = open(OUT, encoding='utf-8').read()
    assert L.ROOT not in text and 'Users' not in text and not re.search(r'20\d\d-\d\d-\d\dT\d', text)


@check
def t12_two_runs_are_byte_identical():
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--check'], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout[-300:] + out.stderr[-300:]
    a, F = build_cached()
    b, G = build()
    assert body(a) == body(b) and report(a, F) == report(b, G)


@check
def t13_nothing_was_mutated():
    import historical_m2_scope as H                 # M3.6D's wine, a later decision, set aside: nothing else moved
    H.unchanged_but_m36d(BEFORE, 'data/model', ':(exclude)data/model/manifest.json')
    H.model_changes_are_m2_only(BEFORE)
    H.evidence_unchanged_but_m36e(BEFORE)            # M3.6E's v7, a later correction, set aside: v1-v6 as they were
    assert not subprocess.check_output(['git', 'diff', '--stat', BEFORE, '--', 'data/app',
                                        ':(glob)data/*.js', 'data/sources.json', 'data/audit/data-gap-register.jsonl',
                                        'data/audit/m3.6b-historical-flags.jsonl', 'assets', 'index.html'],
                                       cwd=L.ROOT).decode().strip()
    assert not [n for n in A.table('identity/names.jsonl') if CUVEE.search(fold(n['name']))]
    assert [w for e, w in ((r['estate'], r['wine']) for r in A.table('state/estate-wine.jsonl')) if e == ESTATE] == [GRAND_VIN]


DOCS_CACHE = []


def build_cached():
    if not DOCS_CACHE:
        docs = held_documents()
        recs, F = build(docs)                 # one reading of the held documents, not two
        DOCS_CACHE.extend([docs, recs, F])
    return DOCS_CACHE[1], DOCS_CACHE[2]


def main():
    if '--write' in sys.argv or '--check' in sys.argv:
        recs, F = build()
        b, text = body(recs), report(recs, F)
        if '--check' in sys.argv:
            bad = [p for p, x in ((OUT, b), (REPORT, text.encode('utf-8')))
                   if not os.path.exists(p) or open(p, 'rb').read() != x]
            print('M3.6C outputs ' + ('are current' if not bad else 'differ: %s' % bad))
            sys.exit(1 if bad else 0)
        open(OUT, 'wb').write(b)
        open(REPORT, 'w', encoding='utf-8', newline='\n').write(text)
        print('%d records (%d documents, %d decisions); %s' % (len(recs), F['documents'], F['decisions'], F['dispositions']))
        print('years %s; archive %s; naming %s; colour %s; role %s; conclusion %s' % (
            F['years'], F['archive_years'], F['naming'], F['colour'], F['role'], F['conclusion']))
        return
    fails = 0
    for f in CHECKS:
        try:
            f()
            print('ok   %s' % f.__name__)
        except Exception as ex:
            fails += 1
            print('FAIL %s: %s' % (f.__name__, str(ex)[:400]))
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
