# -*- coding: utf-8 -*-
"""Phase 3.0: build the authoritative universe from the retrieved sources.

    python -I tools/build-universe.py            # writes data/scope/authoritative-universe.json
    python -I tools/build-universe.py --check    # rebuilds and compares, writes nothing

Every estate and wine in the universe comes from a document listed in
SOURCES, retrieved into sources/scope/<id>/ (gitignored, like the rest of
sources/). Each document's sha256 is pinned here: if a file is missing or
has changed, the build stops rather than producing a universe from
something nobody read.

Nothing is taken from the dashboard's own data, its sheets or its
evidence store. The comparison with those is tools/compare-universe.py.
"""
import hashlib
import html
import io
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
SCOPE = ROOT + 'sources/scope/'
OUT = ROOT + 'data/scope/authoritative-universe.json'
RETRIEVED = '2026-10-25'

# --------------------------------------------------------------------------
# The source registry. `role` says what the source may establish:
#   MEMBERSHIP   - which estates/wines a classification holds, and their rank
#   WINE_FACTS   - which wines an estate makes, in its own words
#   TEMPORAL     - when something changed
#   REFERENCE    - cited, not retrieved; establishes nothing here
# --------------------------------------------------------------------------
SOURCES = [
    dict(id='gcc-1855-listing', path='gcc-1855-listing/listing.pdf',
         sha256='05d4ddb569fb226f5eeaea4097f0bb96925e7e1b7fb3e57e6673f8d34f81e91c',
         name='Grands Crus Classés en 1855 — listing (Médoc; Sauternes & Barsac)',
         publisher='Conseil des Grands Crus Classés en 1855',
         url='https://gcc-1855.fr/ListingGCC1855-fr.pdf',
         type='OFFICIAL_BODY_LIST', primary=True, current=True,
         role=['MEMBERSHIP'],
         authority='membership and rank of the 1855 classification, both lists',
         geographic_scope='Médoc and Graves (red list); Sauternes and Barsac',
         temporal_scope='the classification as it stands today (includes the 1973 promotion)',
         limitations='The Council is the growers\' body, not the legal text; the 1855 '
                     'list has no statute. Gives a place name per cru that mixes '
                     'communes (Pauillac, Pessac) and appellations (Haut-Médoc). '
                     'Does not state colour.'),
    dict(id='gcc-1855-histoire', path='gcc-1855-histoire/p.html',
         sha256='7530dba2f915921b42c06c191b72d0a415131ccbd4440660d1eeb23c9a18171a',
         name='Histoire du classement', publisher='Conseil des Grands Crus Classés en 1855',
         url='https://gcc-1855.fr/histoire-du-classement/',
         type='OFFICIAL_BODY_PAGE', primary=True, current=True, role=['TEMPORAL'],
         authority='the amendments to the 1855 list',
         geographic_scope='as gcc-1855-listing', temporal_scope='1855 to today',
         limitations='Narrative page; dates only the two amendments it names.'),
    dict(id='inao-stem-2022', path='inao-stem-2022/doc.pdf',
         sha256='d4dee85e231661c208f9f2179f5c7aace34a0e125baf33289582a270ed7a58aa',
         name='Saint-Emilion grand cru : le classement pour la prochaine décennie',
         publisher='INAO', url='https://www.inao.gouv.fr/node/32334/printable/pdf',
         type='OFFICIAL_BODY_COMMUNIQUE', primary=True, current=True,
         role=['MEMBERSHIP', 'TEMPORAL'],
         authority='membership and rank of the 2022 Saint-Émilion Grand Cru classification',
         geographic_scope='AOC Saint-Émilion grand cru',
         temporal_scope='approved 8 September 2022 for the coming decade; '
                        'the 2012 list it replaces is described only in counts',
         limitations='The communiqué of the approval by the INAO national committee; '
                     'the homologation order itself (Légifrance) was not retrievable. '
                     'Names in capitals, no communes.'),
    dict(id='acb-cb-2025', path='acb-cb-2025/liste-2025.pdf',
         sha256='995e40f947b6439c6bc94f97210e9dfcfd1af5ce775d9575f4d4b29ce341a5ef',
         name='Les Crus Bourgeois du Médoc — #CLASSEMENT 2025',
         publisher='Alliance des Crus Bourgeois du Médoc',
         url='https://www.crus-bourgeois.com/wp-content/uploads/2025/02/'
             'Liste-Classement-2025-Crus-Bourgeois-du-Medoc-web.pdf',
         type='OFFICIAL_BODY_LIST', primary=True, current=True, role=['MEMBERSHIP'],
         authority='membership, tier and appellation of the 2025 Crus Bourgeois',
         geographic_scope='the Médoc appellations',
         temporal_scope='the 2025 classification (published February 2025)',
         limitations='A designed two-page leaflet: tiers are read from the page bands '
                     'they are printed in. Cites the homologation of the rules '
                     '(arrêté of 29 December 2017), not of the list. No vintage '
                     'range is stated.'),
    dict(id='odg-pl-ccg', path='odg-pl-ccg/ccg.html',
         sha256='09c65c29f86b83faab861e884324302c3b39a141dd986a27b6900b013af97baf',
         name='Les Crus Classés de Graves',
         publisher='Syndicat viticole de Pessac-Léognan (ODG)',
         url='https://www.pessac-leognan.com/les-crus-classes-de-graves/',
         type='OFFICIAL_BODY_PAGE', primary=True, current=True, role=['MEMBERSHIP'],
         authority='current membership of the Crus Classés de Graves, with commune',
         geographic_scope='Pessac-Léognan',
         temporal_scope='current (14 crus)',
         limitations='Does not say for which colour each cru is classified. The 1959 '
                     'order and the Union des Crus Classés de Graves site were not '
                     'retrievable (Légifrance bot challenge; the Union\'s robots.txt '
                     'disallows all agents).'),
    dict(id='wp-graves', path='wp-graves/Classement_des_vins_de_Graves.json',
         sha256='848763ab12d6613fdc7e498008893a0521ca9fd2bc0ab9ad2588a385748f7c60',
         name='Classement des vins de Graves (revision 240039963)',
         publisher='Wikipédia (fr)',
         url='https://fr.wikipedia.org/w/index.php?oldid=240039963',
         type='SECONDARY_ENCYCLOPEDIA', primary=False, current=True,
         role=['MEMBERSHIP', 'TEMPORAL'],
         authority='the colour(s) for which each Graves cru is classified; the 2006 and '
                   '2009 mergers',
         geographic_scope='Pessac-Léognan', temporal_scope='1953, 1959, today',
         limitations='Secondary. Used only for colour and the two mergers, which no '
                     'retrieved primary source states; every value taken from it is '
                     'marked secondary.'),
    dict(id='sca-proclamation-b', path='sca-proclamation-b/p.jpg',
         sha256='491ed177458ee558d3733eecf6d2c93c4c1b92263b025d68d4670bb6b0cf0bf3',
         name='Proclamation des résultats du classement viticole « Crus Artisans du Médoc »',
         publisher='Syndicat des Crus Artisans du Médoc',
         url='https://crus-artisans.com/wp-content/uploads/2023/05/'
             'PROCLAMATION-DES-RESULTATS-22-26-2__.jpg',
         type='OFFICIAL_BODY_PROCLAMATION', primary=True, current=True,
         role=['MEMBERSHIP', 'TEMPORAL'],
         authority='membership, appellation and commune of the 2022–2026 Crus Artisans',
         geographic_scope='the Médoc appellations',
         temporal_scope='vintages 2022 to 2026 (proclaimed 12 May 2023)',
         limitations='An image: transcribed by reading, below, and checked line by line '
                     'against sca-proclamation-a. The homologation order of 21 October '
                     '2022 (Légifrance) was not retrievable.'),
    dict(id='sca-proclamation-a', path='sca-proclamation-a/p.jpg',
         sha256='4863260c9548dd821eedeeccd50326282df316b0fcbdeb7f73f2ab02f328f2ee',
         name='Publication du classement viticole « Crus Artisans du Médoc »',
         publisher='Syndicat des Crus Artisans du Médoc, with Qualisud',
         url='https://crus-artisans.com/wp-content/uploads/2023/05/'
             'PROCLAMATION-DES-RESULTATS-22-26-22.jpg',
         type='OFFICIAL_BODY_PROCLAMATION', primary=True, current=True,
         role=['MEMBERSHIP', 'TEMPORAL'],
         authority='second rendering of the same list, used to check the transcription',
         geographic_scope='as sca-proclamation-b', temporal_scope='vintages 2022 to 2026',
         limitations='An image; no communes.'),
    dict(id='sca-classement-page', path='sca-classement-page/'
         'classement-viticole-crus-artisans-du-medoc.html',
         sha256='54e1714ad674f23ac5df087151c211b687d43f092ed47cc03255642e5b0d4a61',
         name='Classement viticole Crus Artisans du Médoc (site page and menu)',
         publisher='Syndicat des Crus Artisans du Médoc',
         url='https://crus-artisans.com/classement-viticole-crus-artisans-du-medoc/',
         type='OFFICIAL_BODY_PAGE', primary=False, current=True, role=['REFERENCE'],
         authority='none: the page carries the proclamation images; its menu is site '
                   'navigation, not the list',
         geographic_scope='as sca-proclamation-b', temporal_scope='2022–2026',
         limitations='The navigation menu names 34 properties, two of them not in the '
                     'proclamation; it is recorded so that difference can be explained.'),
    dict(id='wp-cru-artisan', path='wp-cru-artisan/Cru_artisan.json',
         sha256='8448e8345f89adc95e7788a1e6c6bb4863992dc6d163e5995e47648a74be1c25',
         name='Cru artisan (revision 225013269)', publisher='Wikipédia (fr)',
         url='https://fr.wikipedia.org/w/index.php?oldid=225013269',
         type='SECONDARY_ENCYCLOPEDIA', primary=False, current=False,
         role=['TEMPORAL'],
         authority='the history of the Crus Artisans lists (2006, 2012)',
         geographic_scope='the Médoc appellations', temporal_scope='1994–2012',
         limitations='Secondary and out of date: stops at the 2012 additions. Its 2006 '
                     'list prints 43 names under a stated 44.'),
    dict(id='estate-lynch-bages', path='estate-lynch-bages-deguster/p.html',
         sha256='62cc211b2234eed973c41de4154bc8b9886bac0bba8d383963a852d758dc3748', name='Déguster — Château Lynch-Bages',
         publisher='Château Lynch-Bages', url='https://www.lynchbages.com/deguster/',
         type='ESTATE_PUBLICATION', primary=True, current=True,
         role=['WINE_FACTS', 'TEMPORAL'],
         authority='the wines Lynch-Bages makes, in its own words',
         geographic_scope='one estate', temporal_scope='current page; history as stated',
         limitations='Estate\'s own marketing page.'),
    dict(id='estate-caillou', path='estate-caillou-vins/p.html', sha256='7eb4b2db10caecb64d0c9c3f692f0771fa5effbffa23cc4f27778c387e2ca937',
         name='Les vins du Château Caillou', publisher='Château Caillou',
         url='https://www.chateaucaillou.com/vins-de-bordeaux-blancs-secs-effervescents-'
             'liquoreux-chateau-caillou/',
         type='ESTATE_PUBLICATION', primary=True, current=True, role=['WINE_FACTS'],
         authority='the wines Caillou makes, in its own words',
         geographic_scope='one estate', temporal_scope='current page',
         limitations='Estate\'s own shop/marketing page; assigns no "second" roles.'),
    dict(id='estate-caillou-murets-blanc', path='estate-caillou-murets-blanc/p.html',
         sha256='3da68c1bd4fbb6ecf6f0144c0b7fbf61012a7db65ef68e4473c9cdf35462275f', name='Les Murets de Caillou – Blanc', publisher='Château Caillou',
         url='https://www.chateaucaillou.com/product/murets-bordeaux-blanc-sec/',
         type='ESTATE_PUBLICATION', primary=True, current=True, role=['WINE_FACTS'],
         authority='this wine\'s appellation and blend', geographic_scope='one estate',
         temporal_scope='current page', limitations='Shop page.'),
    dict(id='estate-caillou-murets-rouge', path='estate-caillou-murets-rouge/p.html',
         sha256='91b97fcc559a2d3712512320bb1e0efacdb1f503522bb0c8a5f008dbfb45e166', name='Les Murets de Caillou – Rouge', publisher='Château Caillou',
         url='https://www.chateaucaillou.com/product/'
             'les-murets-de-caillou-bordeaux-superieur-rouge/',
         type='ESTATE_PUBLICATION', primary=True, current=True, role=['WINE_FACTS'],
         authority='this wine\'s appellation and blend', geographic_scope='one estate',
         temporal_scope='current page', limitations='Shop page.'),
    dict(id='estate-vk-tsc-vins', path='estate-vk-tsc-vins/p.html', sha256='7e81b730bd19966cc061c2efd33883d9b0f81f06545c2326a7e6960eebc5a510',
         name='Vin — Château Tour Saint Christophe', publisher='Vignobles K (owner)',
         url='https://www.vignoblesk.com/fr/vin-chateau-tour-saint-christophe.aspx',
         type='ESTATE_PUBLICATION', primary=True, current=True, role=['WINE_FACTS'],
         authority='the wines published under Tour Saint Christophe by its owner',
         geographic_scope='one estate', temporal_scope='current page; sheets to 2023',
         limitations='Owner group\'s site, the same site the Phase 2 sheets were '
                     'crawled from (but this page, not those sheets). Assigns no '
                     '"second" role.'),
    dict(id='estate-vk-tsc-propriete', path='estate-vk-tsc-propriete/p.html',
         sha256='9e37ba3e036a486cac96d6480f747b31e986112c0f5132ecfa02091deaaae9cf', name='Château Tour Saint Christophe — la propriété',
         publisher='Vignobles K (owner)',
         url='https://www.vignoblesk.com/fr/nos-proprietes/chateau-tour-saint-christophe.aspx',
         type='ESTATE_PUBLICATION', primary=True, current=True,
         role=['WINE_FACTS', 'TEMPORAL'],
         authority='ownership and classification history, as the owner states them',
         geographic_scope='one estate', temporal_scope='2012 to today',
         limitations='Owner\'s own account.'),
    # Cited by the sources above; not retrieved, so they establish nothing.
    dict(id='ref-jorf-graves-1959', path=None, sha256=None,
         name='Graves classification, as rectified 16 February 1959 (JORF)',
         publisher='Ministère de l\'Agriculture', url=None,
         type='LEGAL_TEXT', primary=True, current=True, role=['REFERENCE'],
         authority='would establish Graves membership and colour',
         geographic_scope='Graves', temporal_scope='1953, 1959',
         limitations='NOT RETRIEVED: Légifrance serves a bot challenge.'),
    dict(id='ref-jorf-artisans-2022', path=None, sha256=None,
         name='Homologation of the Crus Artisans classification, order of 21 October 2022',
         publisher='Ministère de l\'Agriculture', url=None,
         type='LEGAL_TEXT', primary=True, current=True, role=['REFERENCE'],
         authority='would establish Crus Artisans membership',
         geographic_scope='Médoc', temporal_scope='2022–2026',
         limitations='NOT RETRIEVED: Légifrance serves a bot challenge. Date as cited by '
                     'the trade press, unverified.'),
    dict(id='ref-jorf-stem-2022', path=None, sha256=None,
         name='Homologation of the 2022 Saint-Émilion classification',
         publisher='Ministères de l\'Agriculture et de l\'Économie', url=None,
         type='LEGAL_TEXT', primary=True, current=True, role=['REFERENCE'],
         authority='would establish Saint-Émilion membership in law',
         geographic_scope='Saint-Émilion grand cru', temporal_scope='2022–',
         limitations='NOT RETRIEVED. The INAO communiqué says the list was sent for '
                     'homologation; the order itself was not read.'),
]
for s in SOURCES:
    s['retrieved'] = RETRIEVED if s['path'] else None
SRC = {s['id']: s for s in SOURCES}


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 16), b''):
            h.update(b)
    return h.hexdigest()


def need(sid):
    """The source's file, after checking it is the one that was read."""
    s = SRC[sid]
    p = SCOPE + s['path']
    if not os.path.exists(p):
        sys.exit('missing %s: %s' % (sid, p))
    got = sha256(p)
    if s['sha256'] and got != s['sha256']:
        sys.exit('%s has changed since it was read: %s' % (sid, got))
    s['sha256'] = got
    return p


def html_lines(p):
    t = io.open(p, encoding='utf-8', errors='replace').read()
    t = re.sub(r'(?is)<(script|style|noscript)\b.*?</\1>', ' ', t)
    t = re.sub(r'(?i)<br\s*/?>|</(p|div|li|h\d|tr|td|a|span)>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return [' '.join(l.split()) for l in t.splitlines() if l.strip()]


def fold(s):
    s = unicodedata.normalize('NFD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def key(name):
    """An identity key: no accents, case, punctuation or 'Château'."""
    k = fold(name).lower().replace('’', "'")
    k = re.sub(r"[^a-z0-9]+", ' ', k)
    k = re.sub(r'^chateau ', '', k.strip())
    return ' '.join(k.split())


def tidy(name):
    return ' '.join(name.replace('’', '’').split())


# --------------------------------------------------------------------------
# Parsers, one per source layout.
# --------------------------------------------------------------------------
TIER_1855 = {'Premiers Crus': 1, 'Seconds Crus': 2, 'Troisièmes Crus': 3,
             'Quatrièmes Crus': 4, 'Cinquièmes Crus': 5,
             'Premier Cru Supérieur': 0}


def parse_1855():
    """The Council's listing: each cru is a name then a place; a tier's
    heading comes after its last cru. Page 1 is the red list, page 2
    Sauternes & Barsac."""
    import pymupdf
    doc = pymupdf.open(need('gcc-1855-listing'))
    out = []
    for pno, system in ((0, '1855-medoc'), (1, '1855-sauternes')):
        lines = [l.strip() for l in doc[pno].get_text().splitlines() if l.strip()]
        pending, cur = [], None
        for l in lines:
            if l in TIER_1855:
                for p in pending:
                    p['rank'] = TIER_1855[l]
                    p['rank_term'] = l
                    out.append(p)
                pending = []
                continue
            if l.startswith(('Grands Crus Classés', 'du Médoc', 'de Sauternes', 'en 1855',
                             'Conseil des')):
                continue
            letters = re.sub(r"[^A-Za-zÀ-ÿ]", '', l)
            starts = l.startswith(('Château', 'Clos'))
            upper = letters and letters == letters.upper()
            if starts:
                cur = {'system': system, 'name': l, 'place': None}
                pending.append(cur)
            elif upper and cur and cur['place'] is None:
                cur['name'] += ' ' + l           # a name over two lines
            elif cur and cur['place'] is None:
                cur['place'] = l
        if pending:
            sys.exit('1855 page %d: crus after the last tier heading' % (pno + 1))
    for e in out:
        e['name'] = tidy(e['name'])
        e['source'] = 'gcc-1855-listing'
    return out


def parse_stem():
    """INAO: each name is followed by its number; the 14 premiers then the
    71 grands crus classés, each list alphabetical."""
    import pymupdf
    doc = pymupdf.open(need('inao-stem-2022'))
    lines = [l.strip() for p in doc for l in p.get_text().splitlines() if l.strip()]
    out, section = [], None
    for i, l in enumerate(lines):
        if l.startswith('Premiers grand crus classés'):
            section = 'PGCC'
        elif l.startswith('Grands crus classés (par ordre'):
            section = 'GCC'
        elif l.startswith('Cette liste'):
            break
        elif section and i + 1 < len(lines) and re.match(r'^\d+\.$', lines[i + 1]):
            a = '(distinction A)' in l
            name = tidy(l.replace('(distinction A)', ''))
            rank = (1 if a else 2) if section == 'PGCC' else 3
            term = ('Premier grand cru classé (distinction A)' if a else
                    'Premier grand cru classé') if section == 'PGCC' else \
                'Grand cru classé'
            out.append({'system': 'stem-2022', 'name': name, 'rank': rank,
                        'rank_term': term, 'place': None,
                        'source': 'inao-stem-2022'})
    return out


def parse_cb():
    """The Alliance's leaflet. Page 1: the Exceptionnels in the band under
    their heading, the Supérieurs in the band under theirs; page 2: the
    Crus Bourgeois. Columns run top to bottom, left to right, and an
    appellation heading carries over into the next column."""
    import pymupdf
    doc = pymupdf.open(need('acb-cb-2025'))
    out = []
    for pno in (0, 1):
        spans = []
        for b in doc[pno].get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                for s in ln['spans']:
                    if s['text'].strip():
                        spans.append((s['bbox'][0], s['bbox'][1], s['font'],
                                      s['text']))
        if pno == 0:
            heads = {t.strip(): y for x, y, f, t in spans if t.strip().startswith('CRU BOURGEOIS')}
            y_exc, y_sup = heads['CRU BOURGEOIS EXCEPTIONNEL'], heads['CRU BOURGEOIS SUPÉRIEUR']
            bands = [((y_exc, y_sup), 1, 'Cru Bourgeois Exceptionnel'),
                     ((y_sup, 420), 2, 'Cru Bourgeois Supérieur')]
        else:
            y_cb = [y for x, y, f, t in spans if t.strip() == 'CRU BOURGEOIS'][0]
            y_end = min(y for x, y, f, t in spans if t.startswith('DÉPASSER'))
            # The footer starts lower down; the last name sits above it.
            bands = [((y_cb, 450), 3, 'Cru Bourgeois')]
        for (y0, y1), rank, term in bands:
            body = [s for s in spans if y0 < s[1] < y1 and not s[3].startswith('CRU BOURGEOIS')]
            cols = sorted(set(round(s[0] / 20) for s in body))
            app, rows = None, []
            for c in cols:
                col = sorted((s for s in body if round(s[0] / 20) == c), key=lambda s: s[1])
                head = []
                for x, y, f, t in col:
                    if 'Bold' in f:
                        head.append(t.strip())
                        continue
                    if head:
                        app = ' '.join(' '.join(head).split())
                        head = []
                    if t.startswith('   ') and rows:
                        rows[-1][0] += ' ' + t.strip()     # a name over two lines
                    else:
                        rows.append([t.strip(), app])
            for name, app in rows:
                app = re.sub(r'^AOC\s*', '', app or '').replace(' -', '-').replace('- ', '-')
                out.append({'system': 'cb-2025', 'name': tidy(name), 'rank': rank,
                            'rank_term': term, 'place': None,
                            'appellation_listed': app.title().replace('-En-', '-en-'),
                            'source': 'acb-cb-2025'})
    return out


def parse_graves():
    """The ODG page: name, 'Cru Classé de Graves', commune."""
    lines = html_lines(need('odg-pl-ccg'))
    out = []
    for i, l in enumerate(lines):
        if l == 'Cru Classé de Graves' and i > 0 and i + 1 < len(lines):
            out.append({'system': 'graves', 'name': tidy(lines[i - 1]),
                        'rank': None, 'rank_term': 'Cru Classé de Graves',
                        'place': lines[i + 1], 'source': 'odg-pl-ccg'})
    seen, uniq = set(), []
    for e in out:                       # the page repeats its own list
        if e['name'] not in seen:
            seen.add(e['name'])
            uniq.append(e)
    return uniq


def graves_colours():
    """Wikipedia's table: which colour each cru is classified for."""
    t = json.load(io.open(need('wp-graves'), encoding='utf-8'))['parse']['wikitext']['*']
    out = {}
    for m in re.finditer(r'^\|\[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*\|\|\s*([^|]+?)\s*\|\|',
                         t, re.M):
        c = m.group(2).strip().lower()
        out[key(m.group(1))] = [x for x in ('rouge', 'blanc') if x in c]
    return out


# The Crus Artisans 2022–2026 proclamation is an image. Transcribed from
# rendering B (which gives communes), each line checked against rendering
# A; where the two spell a name differently, both spellings are kept.
CA_2022 = [
    # appellation, name as in B, commune in B, name as in A
    ('Médoc', 'Château BEJAC ROMELYS', 'Saint Yzans de Médoc', 'Château Bejac Romelys'),
    ('Médoc', 'Château GADET TERREFORT', 'Gaillan en Médoc', 'Château Gadet Terrefort'),
    ('Médoc', 'Château GARANCE HAUT GRENAT', 'Begadan', 'Château Garance Haut Grenat'),
    ('Médoc', 'Château HAUT BRISEY', 'Jau Dignac et Loirac', 'Château Haut Brisey'),
    ('Médoc', 'Château HAUT COULOUMEY', 'Lesparre', 'Château Haut Couloumey'),
    ('Médoc', 'Château HAUT GRAVAT', 'Jau Dignac et Loirac', 'Château Haut Gravat'),
    ('Médoc', 'Château LA BAIE DE LALO', 'Saint Germain d’Esteuil', 'Château La baie de Lalo'),
    ('Médoc', 'Château LA HOURCADE', 'Jau Dignac et Loirac', 'Château La Hourcade'),
    ('Médoc', 'Château LA TESSONIERE', 'Civrac en Médoc', 'Château La Tessonnière'),
    ('Médoc', 'Château LES GRAVES DE LOIRAC', 'Jau Dignac et Loirac', 'Château les Graves de Loirac'),
    ('Médoc', 'Château L’EVASION', 'Civrac', 'Château l’Evasion'),
    ('Médoc', 'Château SAINT GREGOIRE', 'Blaignan', 'Château Saint Gregoire'),
    ('Médoc', 'Château VIEUX GADET', 'Gaillan en Médoc', 'Château Vieux Gadet'),
    ('Haut-Médoc', 'Château DE COUDOT', 'Cussac Fort Médoc', 'Château de Coudot'),
    ('Haut-Médoc', 'Château DE LAUGA', 'Cussac Fort Médoc', 'Château de Lauga'),
    ('Haut-Médoc', 'Domaine DE LA GARENNE', 'Lamarque', 'Domaine de la Garenne'),
    ('Haut-Médoc', 'Château D’OSMOND', 'Cissac en Médoc', 'Château d’Osmond'),
    ('Haut-Médoc', 'Château DU HÂ', 'Saint Sauveur de Médoc', 'Château du Ha'),
    ('Haut-Médoc', 'Château GRAND BRUN', 'Cussac Fort Médoc', 'Château Grand Brun'),
    ('Haut-Médoc', 'Château MICALET', 'Cussac Fort Médoc', 'Château Micalet'),
    ('Haut-Médoc', 'Château MOUTTE BLANC', 'Macau', 'Château Moutte Blanc'),
    ('Haut-Médoc', 'Château PEY MALLET', 'Avensan', 'Château Pey Mallet'),
    ('Haut-Médoc', 'Château TOUR DU GOUA', 'Cussac Fort Médoc', 'Château Tour du Goua'),
    ('Haut-Médoc', 'Château VIEUX GABAREY', 'Lamarque', 'Château Vieux Gabarey'),
    ('Listrac-Médoc', 'Château DACHER DE DELMONTE', None, 'Château Dacher de Delmonte'),
    ('Margaux', 'Clos DE BIGOS', 'Soussans', 'Clos de Bigos'),
    ('Margaux', 'Château DES GRAVIERS', 'Arsac', 'Château des Graviers'),
    ('Margaux', 'Château LES BARRAILLOTS', 'Margaux', 'Château les Barraillots'),
    ('Margaux', 'Château MOUTTE BLANC', 'Macau', 'Château Moutte Blanc'),
    ('Saint-Estèphe', 'Château GRAVES DE PEZ', None, 'Château Graves de Pez'),
    ('Saint-Estèphe', 'Château LINOT', None, 'Château Linot'),
    ('Saint-Estèphe', 'Château MARCELINE', None, 'Château Marceline'),
    ('Saint-Julien', 'Château LA FLEUR LAUGA', None, 'Château la Fleur Lauga'),
]


def parse_ca():
    need('sca-proclamation-a')
    need('sca-proclamation-b')
    return [{'system': 'ca-2022', 'name': a, 'name_b': b, 'rank': None,
             'rank_term': 'Cru Artisan', 'place': commune,
             'appellation_listed': app, 'source': 'sca-proclamation-b'}
            for app, b, commune, a in CA_2022]


# --------------------------------------------------------------------------
# Systems, temporal cases, and the wines the estates' own pages establish.
# --------------------------------------------------------------------------
SYSTEMS = [
    dict(id='1855-medoc', name='Classification of 1855 — red wines (Médoc and Graves)',
         body='Conseil des Grands Crus Classés en 1855', sources=['gcc-1855-listing'],
         unit='cru (the estate\'s grand vin)', ranked=True,
         ranks={0: None, 1: 'Premiers Crus', 2: 'Seconds Crus', 3: 'Troisièmes Crus',
                4: 'Quatrièmes Crus', 5: 'Cinquièmes Crus'},
         validity='1855, amended 16 September 1855 (Cantemerle) and June 1973 (Mouton '
                  'Rothschild); no fixed term', status='CURRENT', primary=True),
    dict(id='1855-sauternes', name='Classification of 1855 — Sauternes and Barsac',
         body='Conseil des Grands Crus Classés en 1855', sources=['gcc-1855-listing'],
         unit='cru (the estate\'s grand vin)', ranked=True,
         ranks={0: 'Premier Cru Supérieur', 1: 'Premiers Crus', 2: 'Seconds Crus'},
         validity='1855; no fixed term', status='CURRENT', primary=True),
    dict(id='graves', name='Crus Classés de Graves',
         body='INAO jury (1953), ministerial order rectified 16 February 1959',
         sources=['odg-pl-ccg', 'wp-graves'], unit='cru, per colour (red, white)',
         ranked=False, ranks=None,
         validity='1953, rectified 1959; no fixed term', status='CURRENT',
         primary=True, note='Membership from the ODG (primary, official body); colour '
                            'from Wikipédia (secondary). The legal text was not read.'),
    dict(id='stem-2022', name='Classement des vins de Saint-Émilion grand cru, 2022',
         body='INAO commission de classement; approved by the INAO national committee',
         sources=['inao-stem-2022'], unit='cru', ranked=True,
         ranks={1: 'Premier grand cru classé (distinction A)',
                2: 'Premier grand cru classé', 3: 'Grand cru classé'},
         validity='approved 8 September 2022, revisable every ten years',
         status='CURRENT', primary=True),
    dict(id='cb-2025', name='Classement des Crus Bourgeois du Médoc, 2025',
         body='Alliance des Crus Bourgeois du Médoc', sources=['acb-cb-2025'],
         unit='cru', ranked=True,
         ranks={1: 'Cru Bourgeois Exceptionnel', 2: 'Cru Bourgeois Supérieur',
                3: 'Cru Bourgeois'},
         validity='2025 classification; vintage range not stated by the retrieved list',
         status='CURRENT', primary=True),
    dict(id='ca-2022', name='Classement des Crus Artisans du Médoc, 2022–2026',
         body='Syndicat des Crus Artisans du Médoc (control body Qualisud)',
         sources=['sca-proclamation-b', 'sca-proclamation-a'],
         unit='cru, per appellation (one estate may be listed under two)',
         ranked=False, ranks=None, validity='vintages 2022 to 2026 inclusive',
         status='CURRENT', primary=True),
]

# Estates the sources themselves say are one property across two systems.
CROSS_SYSTEM = [
    dict(names=('1855-medoc:haut brion', 'graves:haut brion'), source='odg-pl-ccg',
         basis='the ODG page lists Château Haut-Brion among the Crus Classés de Graves '
               'and calls it "1er Grand Cru du Classement de 1855"'),
]

TEMPORAL = [
    dict(id='T1', subject='Château Mouton Rothschild', kind='RANK_CHANGE',
         change='promoted to Premier Cru', date='1973-06', source='gcc-1855-histoire',
         quote='la promotion du Mouton Rothschild en juin 1973'),
    dict(id='T2', subject='Château Cantemerle', kind='MEMBERSHIP_ADDED',
         change='included among the Cinquièmes Crus', date='1855-09-16',
         source='gcc-1855-histoire',
         quote='l’inclusion du Cantemerle parmi les cinquièmes crus le 16 septembre 1855'),
    dict(id='T3', subject='Château La Tour Haut-Brion (Graves, red)', kind='MERGED',
         change='vineyard merged into Château La Mission Haut-Brion', date='2006',
         source='wp-graves', secondary=True,
         quote='le vignoble du château la Tour Haut-Brion, classé en rouge, est fusionné '
               'en 2006 avec celui du château La Mission Haut-Brion'),
    dict(id='T4', subject='Château Laville Haut-Brion (Graves, white)', kind='MERGED',
         change='vineyard merged into Château La Mission Haut-Brion', date='2009',
         source='wp-graves', secondary=True,
         quote='comme l’est également en 2009 celui du château Laville Haut-Brion, classé '
               'en blanc'),
    dict(id='T5', subject='Saint-Émilion classification', kind='LIST_REPLACED',
         change='the 2012 list (18 premiers grands crus classés, 64 grands crus classés) '
                'replaced by the 2022 list (14 and 71)', date='2022-09-08',
         source='inao-stem-2022',
         quote='Le dernier classement datant de 2012 consacrait 18 « premiers grands crus '
               'classés » et 64 « grands crus classés »'),
    dict(id='T6', subject='Château Tour Saint Christophe', kind='MEMBERSHIP_ADDED',
         change='promoted Grand Cru Classé in the 2022 classification', date='2022-09',
         source='estate-vk-tsc-propriete',
         quote='En septembre 2022 ... le Château Tour Saint Christophe est promu Grand Cru '
               'Classé'),
    dict(id='T7', subject='Crus Artisans du Médoc', kind='LIST_REPLACED',
         change='2006 list (44 stated), additive list of 2012 (to 50), replaced by the '
                '2022–2026 list (33 entries)', date='2023-05-12',
         source='sca-proclamation-b', also=['wp-cru-artisan'],
         quote='sont classées pour les millésimes 2022 à 2026 les exploitations suivantes'),
    dict(id='T8', subject='Echo de Lynch-Bages', kind='WINE_RENAMED',
         change='the second wine was Château Haut-Bages Averous for over 30 years; from '
                'the 2008 vintage it is Echo de Lynch-Bages', date='2008 vintage',
         source='estate-lynch-bages',
         quote='Château Haut-Bages Averous ... désigne pendant plus de 30 ans le second vin '
               'du Château Lynch-Bages. À partir du millésime 2008, il change d’identité '
               'pour devenir « Echo de Lynch-Bages »'),
    dict(id='T9', subject='Château Haut-Brion', kind='APPELLATION_CONTEXT',
         change='classified in 1855 and 1959 as Graves; the Pessac-Léognan appellation '
                'was created only in 1987', date='1987', source='wp-graves',
         secondary=True,
         quote='À cette époque l\'appellation n\'existait pas encore, elle ne fut créée '
               'qu\'en 1987'),
]

# Wines beyond the classified one, only where an estate page was read.
# `source_term` is the estate's own wording; `role` is set only where the
# source itself uses a role word, otherwise it is null.
ESTATE_WINES = [
    # Lynch-Bages
    dict(estate='1855-medoc:lynch bages', name='Château Lynch-Bages',
         source_term='Lynch-Bages … grand Pauillac', role='grand_vin', colour='red',
         appellation='Pauillac', valid='', source='estate-lynch-bages',
         evidence='"Le goût des grands Pauillac"; "Echo de Lynch-Bages partage le '
                  'caractère et l’élégance du grand vin"'),
    dict(estate='1855-medoc:lynch bages', name='Echo de Lynch-Bages',
         source_term='second vin', role='second', colour='red', appellation='Pauillac',
         valid='from the 2008 vintage', source='estate-lynch-bages',
         evidence='"un potentiel de garde exceptionnel pour ce second vin"; renamed from '
                  'Château Haut-Bages Averous from the 2008 vintage'),
    dict(estate='1855-medoc:lynch bages', name='Château Haut-Bages Averous',
         source_term='second vin', role='second', colour='red', appellation='Pauillac',
         valid='"pendant plus de 30 ans", up to the 2007 vintage', historical=True,
         source='estate-lynch-bages',
         evidence='"désigne pendant plus de 30 ans le second vin du Château Lynch-Bages"'),
    dict(estate='1855-medoc:lynch bages', name='Blanc de Lynch-Bages',
         source_term='vin blanc', role=None, colour='white', appellation=None,
         valid='from 1990', source='estate-lynch-bages',
         evidence='"Né en 1990, le Blanc de Lynch-Bages est historiquement l’un des '
                  'premiers vins blancs produits par un Cru Classé"'),
    # Caillou
    dict(estate='1855-sauternes:caillou', name='Château Caillou',
         source_term='Grand Vin, classé en 1855 en Sauternes & Barsac', role='grand_vin',
         colour='sweet white', appellation='Barsac', valid='', source='estate-caillou',
         evidence='"Notre Grand Vin, classé en 1855 en Sauternes & Barsac, 100% Sémillon"'),
    dict(estate='1855-sauternes:caillou', name='Myosotis du Château Caillou',
         source_term='grand vin blanc sec', role=None, colour='dry white',
         appellation='Bordeaux', valid='', source='estate-caillou',
         evidence='listed under BORDEAUX BLANC: "Notre grand vin blanc sec 100% '
                  'Sauvignon"; the source calls it the grand vin of its dry whites, '
                  'not of the estate'),
    dict(estate='1855-sauternes:caillou', name='Les Murets de Caillou (blanc)',
         source_term='Bordeaux Blanc Sec', role=None, colour='dry white',
         appellation='Bordeaux', valid='', source='estate-caillou-murets-blanc',
         evidence='"Les Murets du Château Caillou associe … Sémillon (80 %) … '
                  'Sauvignon (20 %)"; "Bordeaux Blanc Sec"'),
    dict(estate='1855-sauternes:caillou', name='Les Murets de Caillou (rouge)',
         source_term='Bordeaux Supérieur Rouge', role=None, colour='red',
         appellation='Bordeaux Supérieur', valid='', source='estate-caillou-murets-rouge',
         evidence='"Les Murets du Château Caillou, en Bordeaux Supérieur Rouge et 100% '
                  'Merlot"'),
    dict(estate='1855-sauternes:caillou', name='Les Tourelles de Caillou',
         source_term='Sauternes', role=None, colour='sweet white', appellation='Sauternes',
         valid='', source='estate-caillou', evidence='listed under SAUTERNES'),
    dict(estate='1855-sauternes:caillou', name='Les Érables de Caillou',
         source_term='Sauternes', role=None, colour='sweet white', appellation='Sauternes',
         valid='', source='estate-caillou', evidence='listed under SAUTERNES'),
    dict(estate='1855-sauternes:caillou', name='Les Bulles de Caillou',
         source_term='crémant', role=None, colour='sparkling',
         appellation='Crémant de Bordeaux', valid='', source='estate-caillou',
         evidence='"Notre crémant 100 % Sémillon"'),
    # Tour Saint Christophe
    dict(estate='stem-2022:tour saint christophe', name='Château Tour Saint Christophe',
         source_term='Château Tour Saint Christophe', role='grand_vin', colour='red',
         appellation='Saint-Émilion grand cru', valid='', source='estate-vk-tsc-vins',
         evidence='the classified wine (promoted Grand Cru Classé 2022)'),
    dict(estate='stem-2022:tour saint christophe', name='Les Terrasses de Saint Christophe',
         source_term='Les Terrasses de Saint Christophe', role=None, colour='red',
         appellation='Saint Emilion Grand Cru', valid='technical sheets listed for '
         '2016–2023', source='estate-vk-tsc-vins',
         evidence='listed on the owner\'s Tour Saint Christophe wine page with '
                  '"Appellation Saint Emilion Grand Cru" and "90% Merlot - 10 % Cabernet '
                  'Franc"; its note cites "la minéralité si spécifique au terroir de Tour '
                  'Saint Christophe". The page uses no role word.'),
    dict(estate='stem-2022:tour saint christophe', name='Château Tour Saint Christophe '
         '\'Angela\'', source_term='Bordeaux Blanc', role=None, colour='white',
         appellation='Bordeaux', valid='2023 sheet listed', source='estate-vk-tsc-vins',
         evidence='"Appellation Bordeaux Blanc"; "Sauvignon Blanc - Sémillon - Sauvignon '
                  'Gris"'),
]
ESTATE_PAGES = {'1855-medoc:lynch bages': ['estate-lynch-bages'],
                '1855-sauternes:caillou': ['estate-caillou', 'estate-caillou-murets-blanc',
                                           'estate-caillou-murets-rouge'],
                'stem-2022:tour saint christophe': ['estate-vk-tsc-vins',
                                                    'estate-vk-tsc-propriete']}
OWNERS = {'stem-2022:tour saint christophe': dict(
    owner='Peter Kwok and his daughter Karen (Vignobles K)', since='2012',
    source='estate-vk-tsc-propriete',
    quote='Le Château Tour Saint Christophe a été acquis par Peter Kwok et sa fille Karen '
          'en 2012.')}
EXPECTED = {'1855-medoc': 61, '1855-sauternes': 27, 'stem-2022': 85, 'cb-2025': 170,
            'graves': 14, 'ca-2022': 33}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', fold(s).lower()).strip('-')


def build():
    for s in SOURCES:
        if s['path']:
            need(s['id'])
    rows = parse_1855() + parse_stem() + parse_cb() + parse_graves() + parse_ca()
    counts = {}
    for r in rows:
        counts[r['system']] = counts.get(r['system'], 0) + 1
    if counts != EXPECTED:
        sys.exit('parsed counts %r differ from the sources\' own totals %r'
                 % (counts, EXPECTED))
    colours = graves_colours()

    # Estates: one per (system, key), joined across systems only where a
    # source says so. Within one system, a repeated key is one estate
    # listed twice (Moutte Blanc, under two appellations).
    joined = {}
    for c in CROSS_SYSTEM:
        for n in c['names']:
            joined[n] = c
    estates, by_ref = {}, {}
    for r in rows:
        ref = '%s:%s' % (r['system'], key(r['name']))
        c = joined.get(ref)
        anchor = c['names'][0] if c else ref
        if anchor not in estates:
            estates[anchor] = {'id': 'u-' + slug(key(r['name'])), 'names': [],
                               'memberships': [], 'communes': [], 'owner': None,
                               'historical_names': [], 'identity_status': 'RESOLVED',
                               'identity_basis': [], 'sources': []}
        e = estates[anchor]
        by_ref[ref] = e
        for n in (r['name'], r.get('name_b')):
            if n and n not in [x['name'] for x in e['names']]:
                e['names'].append({'name': n, 'source': r['source']})
        m = {'system': r['system'], 'rank': r['rank'], 'rank_term': r['rank_term'],
             'appellation_listed': r.get('appellation_listed'),
             'place_listed': r['place'], 'source': r['source']}
        if r['system'] == 'graves':
            m['colours'] = colours.get(key(r['name']))
            m['colours_source'] = 'wp-graves'
        e['memberships'].append(m)
        if r['place'] and r['place'] not in e['communes'] and r['system'] in ('graves', 'ca-2022'):
            e['communes'].append(r['place'])
        if r['source'] not in e['sources']:
            e['sources'].append(r['source'])
        if c and c['basis'] not in e['identity_basis']:
            e['identity_basis'].append(c['basis'])
            if c['source'] not in e['sources']:
                e['sources'].append(c['source'])
    for e in estates.values():
        same = [m for m in e['memberships'] if m['system'] == 'ca-2022']
        if len(same) > 1:
            e['identity_basis'].append(
                'listed twice in one proclamation, under %s, with the same name and the '
                'same commune: one estate, two classified wines'
                % ' and '.join(m['appellation_listed'] for m in same))
    for ref, o in OWNERS.items():
        by_ref[ref]['owner'] = o
    ids = [e['id'] for e in estates.values()]
    dup = sorted(set(i for i in ids if ids.count(i) > 1))
    for e in estates.values():
        if e['id'] in dup:
            # The same name in two systems, with nothing saying they are
            # one estate: kept apart, and marked.
            e['identity_status'] = 'UNRESOLVED_IDENTITY'
            e['identity_basis'].append('the same name appears in another system and no '
                                       'retrieved source joins or separates them')
            e['id'] += '--' + e['memberships'][0]['system']

    # Wines: every classification membership is a classified wine; Graves
    # memberships are per colour. Then the estates' own pages.
    wines = []
    for e in estates.values():
        for m in e['memberships']:
            cols = m.get('colours') if m['system'] == 'graves' else [None]
            for col in cols or [None]:
                wid = '%s:%s%s' % (e['id'], m['system'],
                                   (':' + col) if col else '')
                if m['system'] == 'ca-2022' and len([x for x in e['memberships']
                                                    if x['system'] == 'ca-2022']) > 1:
                    wid += ':' + slug(m['appellation_listed'])
                wines.append({
                    'id': wid, 'estate': e['id'], 'name': e['names'][0]['name'],
                    'kind': 'CLASSIFIED_WINE', 'role': 'grand_vin',
                    'role_basis': 'the classification\'s unit is the cru: the wine sold '
                                  'under the estate\'s name',
                    'source_term': m['rank_term'],
                    'colour': {'rouge': 'red', 'blanc': 'white'}.get(col) if col else None,
                    'colour_source': m.get('colours_source') if col else None,
                    'appellation_listed': m.get('appellation_listed'),
                    'classification': {'system': m['system'], 'rank': m['rank']},
                    'valid': None, 'sources': [m['source']] + ([m['colours_source']]
                                                               if col else []),
                    'status': 'ESTABLISHED'})
    # The same wine in two systems (Haut-Brion red) is one wine.
    merged = {}
    for w in wines:
        k = (w['estate'], w['colour'] or 'red' if w['estate'] == 'u-haut-brion' else w['id'])
        if k in merged:
            merged[k]['also_classified'] = w['classification']
            merged[k]['sources'] += [s for s in w['sources'] if s not in merged[k]['sources']]
        else:
            merged[k] = w
    wines = list(merged.values())
    for w in ESTATE_WINES:
        e = by_ref[w['estate']]
        wid = '%s:estate:%s' % (e['id'], slug(w['name']))
        if w['role'] == 'grand_vin':
            # The classified wine already stands for it; record the estate's
            # own words on it rather than a second record.
            cw = [x for x in wines if x['estate'] == e['id'] and x['kind'] == 'CLASSIFIED_WINE']
            for x in cw:
                x.setdefault('estate_source', []).append(
                    {'source': w['source'], 'evidence': w['evidence']})
                if w['source'] not in x['sources']:
                    x['sources'].append(w['source'])
            continue
        wines.append({'id': wid, 'estate': e['id'], 'name': w['name'],
                      'kind': 'ESTATE_WINE', 'role': w['role'],
                      'role_basis': ('the source\'s own word: "%s"' % w['source_term'])
                      if w['role'] else 'the source uses no role word',
                      'source_term': w['source_term'], 'colour': w['colour'],
                      'colour_source': w['source'],
                      'appellation_listed': w['appellation'],
                      'classification': None, 'valid': w['valid'] or None,
                      'historical': bool(w.get('historical')),
                      'evidence': w['evidence'], 'sources': [w['source']],
                      'status': 'ESTABLISHED' if w['role'] or w['role'] is None else None})
    for e in estates.values():
        pages = ESTATE_PAGES.get(next((r for r, x in by_ref.items() if x is e), ''), [])
        e['wine_universe'] = ('ESTATE_SOURCE_READ' if pages else 'CLASSIFIED_WINE_ONLY')
        e['wine_sources'] = pages

    out = {
        'phase': '3.0',
        'built_by': 'tools/build-universe.py',
        'retrieved': RETRIEVED,
        'note': 'The authoritative universe: what the retrieved sources establish, '
                'and nothing else. An estate is here because a classification '
                'body lists it; a wine is here because a classification classifies '
                'it or the estate itself publishes it. Fields a source does not give '
                'are null, not guessed.',
        'sources': SOURCES,
        'systems': SYSTEMS,
        'counts': {'rows_by_system': counts, 'estates': len(estates),
                   'wines': len(wines),
                   'classified_wines': sum(1 for w in wines if w['kind'] == 'CLASSIFIED_WINE'),
                   'estate_wines': sum(1 for w in wines if w['kind'] == 'ESTATE_WINE')},
        'estates': sorted(estates.values(), key=lambda e: e['id']),
        'wines': sorted(wines, key=lambda w: w['id']),
        'temporal': TEMPORAL,
    }
    return out


def main():
    out = build()
    text = json.dumps(out, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    if '--check' in sys.argv:
        old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
        print('universe is current' if old == text else 'universe DIFFERS from a rebuild')
        sys.exit(0 if old == text else 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(text)
    print('%(estates)d estates, %(wines)d wines (%(classified_wines)d classified, '
          '%(estate_wines)d from estate pages)' % out['counts'])
    print(out['counts']['rows_by_system'])


if __name__ == '__main__':
    main()
