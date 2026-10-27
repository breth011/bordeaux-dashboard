"""M3.7: source confirmation - which candidate sources can be treated as the producer's own, and for whom.

    python tools/m37-source-confirmation.py           write the audit and docs/PHASE-M3.7-SOURCE-CONFIRMATION.md
    python tools/m37-source-confirmation.py --check   recompute both and compare, byte for byte

An audit, not a model change: nothing under data/model, data/evidence or data/app is read for writing.

THE CANDIDATES are the repository's own: every estate-source relationship in the model
(state/source-estate.jsonl, 409, all kind OFFICIAL_SITE, all LEGACY_UNSOURCED from data/websites.js). The
REVIEW SET is the relationships of the 21 domains M3.3 planned to acquire from as first-party sources
(its plan rows outside category A whose party is FIRST_PARTY: discovered-not-acquired, dead links, blocked
by policy). Every other relationship is inventoried as NOT_REVIEWED with its legacy tag; reviewing them
would be the broad crawl this phase excludes.

THE EVIDENCE for each reviewed relationship is a set of ELEMENTS, each a URL and a pattern that must match
one block (or the title) of a page the repository holds: the M3.3 discovery crawl
(sources/discovery/extracted) or this phase's narrow inspection (sources/acquisition/m3.7, 32 requests:
home pages, the legal notices they link, two G&C Lurton pages and three standard legal-notice paths). A
pattern that matches nothing stops the run. The quote recorded is the block itself.

    site        the site presents itself as the estate (its home title names it)
    publisher   the legal notice names who publishes the site, and whether that is the estate's own
                company (ESTATE_COMPANY) or a group, family or other company (GROUP)
    link        the site's own text ties the publisher, its owners or its family to the estate
                (owns, created, inherited, acquired, makes the wine), or says the content is the estate's
    redirect    the estate's own legacy domain redirects to this source (crawl profile moved_to, or an
                M3.6G probe)
    presents    the site has pages for the estate (crawl profile: estates named in page titles), or a
                page quoted for it
    unclear     what the relationship's estate is, on this source, is itself in question

THE STATUS follows from the elements by one rule (status()), never typed in:

    unclear                                        SOURCE_IDENTITY_UNCLEAR
    publisher ESTATE_COMPANY and site              CONFIRMED_FIRST_PARTY
    publisher ESTATE_COMPANY, not site             CONFIRMED_ESTATE_CONTROLLED (the estate's company
                                                   publishes a group site)
    link and (publisher or redirect)               CONFIRMED_ESTATE_CONTROLLED
    presents and (publisher or site)               PROBABLE_FIRST_PARTY
    presents, shared host                          SHARED_HOST_UNCONFIRMED
    otherwise                                      SOURCE_IDENTITY_UNCLEAR
    outside the review set                         NOT_REVIEWED

A domain carrying the estate's name, a URL path, a filename, a search result or a page that only mentions
the estate is never an element. THIRD_PARTY and SOURCE_NOT_RELEVANT are in the vocabulary; no reviewed
relationship reached them. Existing relationships are never upgraded or changed: where M3.7's reading
differs from what the model records, a `conflict` row says so for review.
"""
import collections
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.7-source-confirmation.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.7-SOURCE-CONFIRMATION.md'
M33 = L.ROOT + 'data/audit/m3.3-source-acquisition-plan.jsonl'
M36G = L.ROOT + 'data/audit/m3.6g-cuvee-acquisition.jsonl'
ACQ = L.ROOT + 'sources/acquisition/m3.7/'
DISC = L.ROOT + 'sources/discovery/extracted/'
STATUSES = ('CONFIRMED_FIRST_PARTY', 'CONFIRMED_ESTATE_CONTROLLED', 'PROBABLE_FIRST_PARTY', 'THIRD_PARTY',
            'SHARED_HOST_UNCONFIRMED', 'SOURCE_IDENTITY_UNCLEAR', 'SOURCE_NOT_RELEVANT', 'NOT_REVIEWED')
CONFIDENCE = {'CONFIRMED_FIRST_PARTY': 'HIGH', 'CONFIRMED_ESTATE_CONTROLLED': 'HIGH', 'PROBABLE_FIRST_PARTY': 'MEDIUM',
              'SHARED_HOST_UNCONFIRMED': 'LOW', 'SOURCE_IDENTITY_UNCLEAR': 'LOW', 'THIRD_PARTY': 'LOW',
              'SOURCE_NOT_RELEVANT': 'LOW', 'NOT_REVIEWED': None}
EFFORT = {'XS': 0, 'S': 1, 'M': 2, 'L': 3, 'XL': 4, 'UNKNOWN': 5, None: 5}
INSPECTED = '2026-10-27'

DCD = ('https://www.haut-brion.com/mentions-legales/', r'sont produits par la société DOMAINE CLARENCE DILLON')
DCD_M = ('https://www.mission-haut-brion.com/mentions-legales/', r'sont produits par la société DOMAINE CLARENCE DILLON')
GCL = ('https://www.gc-lurton-estates.com/en/family.html', r'Gonzague inherits Chateau Durfort-Vivens')
DDD = ('https://www.denisdubourdieu.com/info/legal/', r'est la propriété de la société Denis Dubourdieu Domaines')
VCN = ('https://www.neipperg.com/fr/mentions-legales.html', r'qui est édité par Vignobles Comtes von Neipperg')
VCN_BUY = ('https://www.neipperg.com/', r'se porte acqu.reur du Ch.teau Canon La Gaffeli.re et de La Mondotte')
BRN = ('https://vignobles-bernaleau.com/mentions-legales/', r'est édité par la société Mongravey')
POI = ('https://chateau-poitevin.com/mentions-legales/', r'^Propriétaire : Guillaume Poitevin')

# (source name, estate): the elements, each (url, pattern) - plus the publisher's kind, and what stays open
REVIEW = {
    ('batailley.com', 'es_00035'): dict(
        site=('https://batailley.com/', r'^Château Batailley'),
        publisher=('https://batailley.com/mentions-legales/', r'^Siège social : Château Batailley', 'ESTATE_COMPANY'),
        open=['the legal notice gives the société civile by its seat (Château Batailley) and SIREN, not by name; '
              'its contact is domaines@borie-manoux.fr']),
    ('boyd-cantenac.com', 'es_00213'): dict(
        site=('https://boyd-cantenac.fr/', r'Château Boyd-Cantenac'),
        publisher=('https://boyd-cantenac.fr/en/legal-notice/', r'SCEA CH\. BOYD CANTENAC & POUGET', 'ESTATE_COMPANY'),
        open=['the publishing company is Boyd-Cantenac\'s and Pouget\'s; the model records no source for Pouget']),
    ('calon-segur.com', 'es_00220'): dict(
        site=('https://www.calon-segur.fr/fr/', r'Calon S.gur'),
        publisher=('https://www.calon-segur.fr/fr/mentions-legales/', r'est édité par la SCEA de Château Calon Ségur',
                   'ESTATE_COMPANY')),
    ('chateau-belair-monange.com', 'es_00038'): dict(
        site=('https://www.belairmonange.com/', r'Château Bélair-Monange'),
        publisher=('https://www.belairmonange.com/fr/mentions-legales', r'est titulaire du nom de domaine', 'ESTATE_COMPANY')),
    ('chateau-couhins-lurton.com', 'es_00241'): dict(
        site=('https://www.chateau-couhins-lurton.com/', r'Couhins-Lurton'),
        publisher=('https://www.chateau-couhins-lurton.com/mentions-legales/', r'^S\.A\.S\. LES VIGNOBLES ANDR', 'GROUP'),
        link=('https://www.chateau-couhins-lurton.com/le-chateau-son-histoire/', r'porte désormais le nom de Château Couhins-Lurton')),
    ('chateau-issan.com', 'es_00283'): dict(
        site=('https://www.chateau-issan.com/', r'Issan'),
        publisher=('https://www.chateau-issan.com/fr/mentions.html', r'^Société civile Château d.Issan', 'ESTATE_COMPANY')),
    ('chateau-poitevin.com', 'es_00177'): dict(
        site=('https://chateau-poitevin.com/', r'^Chateau Poitevin'),
        publisher=POI + ('ESTATE_COMPANY',)),
    ('chateau-poitevin.com', 'es_00161'): dict(
        publisher=POI + ('GROUP',),
        link=('https://chateau-poitevin.com/savoir-faire/', r'Nous vinifions et assemblons 5 cuvées'),
        open=['the site sells Moulin de Canhaut as one of its five cuvées; it has no site of its own here']),
    ('chateau-sigalas-rabaud.com', 'es_00386'): dict(
        site=('https://www.chateau-sigalas-rabaud.com/', r'Sigalas Rabaud'),
        publisher=('https://www.chateau-sigalas-rabaud.com/mentions-legales/', r'^Propriétaire : SAS Chateau Sigalas Rabaud',
                   'ESTATE_COMPANY')),
    ('chateaudemyrat.fr', 'es_00253'): dict(
        site=('https://chateaudemyrat.fr/index.php/fr', r'^Chateau de Myrat'),
        publisher=('https://chateaudemyrat.fr/index.php/fr/2-uncategorised/241-mentions-legales',
                   r"appartient l'exploitation agricole J\. de Pontac", 'GROUP'),
        link=('https://chateaudemyrat.fr/index.php/fr/2-uncategorised/241-mentions-legales',
              r'appartient exclusivement à Château de Myrat')),
    ('denisdubourdieu.com', 'es_00232'): dict(
        publisher=DDD + ('GROUP',),
        link=('https://www.denisdubourdieu.com/histoire/', r'la création du Clos Floridène'),
        open=['the link is historical ("la création du Clos Floridène dans les Graves en 1982"); the site sells and '
              'hosts visits at Clos Floridène today']),
    ('denisdubourdieu.com', 'es_00255'): dict(
        publisher=DDD + ('GROUP',),
        link=('https://www.denisdubourdieu.com/en/chateau-doisy-daene-en/', r'presided over the destiny of Doisy-Da.ne')),
    ('denisdubourdieu.com', 'es_00256'): dict(
        publisher=DDD + ('GROUP',),
        link=('https://www.denisdubourdieu.com/chateau-doisy-dubroca/',
              r'la famille Dubourdieu, renoue avec une petite production du Château Doisy-Dubroca')),
    ('durfort-vivens.fr', 'es_00263'): dict(link=GCL, redirect='gc-lurton-estates.com',
                                            open=['no legal notice names the publisher of gc-lurton-estates.com']),
    ('ferriere.com', 'es_00265'): dict(link=GCL, redirect='gc-lurton-estates.com',
                                       open=['no legal notice names the publisher of gc-lurton-estates.com']),
    ('hautbagesliberal.com', 'es_00277'): dict(link=GCL, redirect='gc-lurton-estates.com',
                                               open=['no legal notice names the publisher of gc-lurton-estates.com']),
    ('haut-brion.com', 'es_00281'): dict(
        site=('https://www.haut-brion.com/', r'Haut-Brion'),
        publisher=DCD + ('GROUP',),
        open=['the publisher is DOMAINE CLARENCE DILLON S.A.S.; no held or inspected page says it owns the estate']),
    ('latourmartillac.com', 'es_00311'): dict(
        site=('https://www.latourmartillac.com/', r'Latour Martillac'),
        open=['no legal notice: none is linked from the home page and /mentions-legales/ answers 404']),
    ('malartic-lagraviere.com', 'es_00324'): dict(
        site=('https://www.malartic-lagraviere.com/', r'Malartic Lagravi.re'),
        open=['/mentions-legales/ serves no readable publisher text (an age gate and a cookie notice)']),
    ('mission-haut-brion.com', 'es_00292'): dict(
        site=('https://www.mission-haut-brion.com/', r'Mission Haut-Brion'),
        publisher=DCD_M + ('GROUP',),
        open=['the publisher is DOMAINE CLARENCE DILLON S.A.S.; no held or inspected page says it owns the estate']),
    ('mission-haut-brion.com', 'es_00312'): dict(
        publisher=DCD_M + ('GROUP',),
        unclear=('https://www.mission-haut-brion.com/nos-vins/chateau-la-mission-haut-brion-blanc/'
                 'chateau-la-mission-haut-brion-blanc-2009/', r'Autrefois nommé Château Laville Haut-Brion'),
        open=['the site names Laville Haut-Brion as the former name of Château La Mission Haut-Brion blanc: an '
              'identity transition, not resolved here; it presents no estate of that name']),
    ('neipperg.com', 'es_00222'): dict(publisher=VCN + ('GROUP',), link=VCN_BUY),
    ('neipperg.com', 'es_00293'): dict(publisher=VCN + ('GROUP',), link=VCN_BUY),
    ('neipperg.com', 'es_00452'): dict(
        publisher=VCN + ('GROUP',),
        link=('https://www.neipperg.com/', r"puis du Clos de l.Oratoire")),
    ('neipperg.com', 'es_00244'): dict(
        publisher=VCN + ('GROUP',),
        presents=('https://www.neipperg.com/fr/visiter.html', r"^Lieu : Château d'Aiguilhe"),
        open=['the site hosts visits at Château d\'Aiguilhe and its documents; no page held says the group owns it']),
    ('trottevieille.com', 'es_00464'): dict(
        site=('https://www.trottevieille.com/', r'^Château TrotteVieille'),
        publisher=('https://www.trottevieille.com/mentions-legales/', r'^Siège social : Château TrotteVieille', 'ESTATE_COMPANY'),
        open=['the legal notice gives the société civile by its seat and SIREN, not by name; its contact is '
              'domaines@borie-manoux.fr']),
    ('vignobles-bernaleau.com', 'es_00158'): dict(
        publisher=BRN + ('ESTATE_COMPANY',), redirect='M3.6G probe: mongravey.fr',
        open=['the site is the group\'s (Vignobles Bernaleau), published by the estate\'s company, SARL Mongravey']),
    ('vignobles-bernaleau.com', 'es_00073'): dict(
        publisher=BRN + ('GROUP',),
        link=('https://vignobles-bernaleau.com/produit/chateau-braude-fellonneau-2019/',
              r'nos meilleures barriques neuves du Château de Braude'),
        open=['the site also sells "Château Braude Fellonneau", a selection of Château de Braude the model does '
              'not list; not created here']),
    ('vignoblesdeterroirs.com', 'es_00216'): dict(
        publisher=('https://www.vignoblesdeterroirs.com/mentions-legales/', r'^Propriétaire : VIGNOBLES DE TERROIRS SAS', 'GROUP'),
        presents=('https://www.vignoblesdeterroirs.com/chateau-broustet/', r'^Château Broustet - Vignobles de Terroirs'),
        open=['the group says it owns the châteaux of its range ("dont il est propriétaire"), 11 properties; no page '
              'held names Broustet as one of them in words']),
}

# where M3.7's reading differs from what the model records: recorded for review, the record left as it is
CONFLICTS = {
    ('mission-haut-brion.com', 'es_00312'): 'the model records this site as the OFFICIAL_SITE of Château Laville '
        'Haut-Brion (legacy tag "domg", which data/websites.js does not define); the site names Laville Haut-Brion '
        'only as the former name of La Mission Haut-Brion blanc',
    ('durfort-vivens.fr', 'es_00263'): 'the model records this host as an ESTATE_SITE of one estate; it redirects to '
        'gc-lurton-estates.com, which serves three estates',
    ('ferriere.com', 'es_00265'): 'the model records this host as an ESTATE_SITE of one estate; it redirects to '
        'gc-lurton-estates.com, which serves three estates',
    ('hautbagesliberal.com', 'es_00277'): 'the model records this host as an ESTATE_SITE of one estate; it redirects '
        'to gc-lurton-estates.com, which serves three estates',
    ('vignoblesdeterroirs.com', 'es_00216'): 'the model records this host as an ESTATE_SITE of one estate; it is the '
        'site of a group of 11 properties',
}


class Stop(Exception):
    pass


def status(e, shared):
    """The one rule from elements to a status (see the module docstring)."""
    if e.get('unclear'):
        return 'SOURCE_IDENTITY_UNCLEAR'
    pub = (e.get('publisher') or {}).get('kind')
    if pub == 'ESTATE_COMPANY':
        return 'CONFIRMED_FIRST_PARTY' if e.get('site') else 'CONFIRMED_ESTATE_CONTROLLED'
    if e.get('link') and (pub or e.get('redirect')):
        return 'CONFIRMED_ESTATE_CONTROLLED'
    if e.get('presents') and (pub or e.get('site')):
        return 'PROBABLE_FIRST_PARTY'
    if e.get('presents') and shared:
        return 'SHARED_HOST_UNCONFIRMED'
    return 'SOURCE_IDENTITY_UNCLEAR'


class Held:
    """The pages the repository holds, by URL: this phase's inspection first, then the discovery crawl."""

    def __init__(self):
        self.inv = json.load(open(ACQ + 'inventory.json', encoding='utf-8'))
        self.disc = collections.defaultdict(list)
        self.arts = collections.defaultdict(list)
        for l in open(L.ROOT + 'data/discovery/artifacts.jsonl', encoding='utf-8'):
            a = json.loads(l)
            self.disc[a['first_url']].append(a['sha256'])
            for d in a.get('domains') or []:
                self.arts[d].append(a)

    def pages(self, url):
        out = [('m3.7', r['sha256'], ACQ + 'extracted/%s.json' % r['sha256'])
               for r in self.inv if r['url'] == url and r.get('sha256')]
        out += [('discovery', s, DISC + '%s.json' % s) for s in sorted(self.disc.get(url, []))]
        return [(o, s, p) for o, s, p in out if os.path.exists(p)]

    def quote(self, url, rx):
        for origin, sha, path in self.pages(url):
            x = json.load(open(path, encoding='utf-8'))
            for t in [x.get('title') or ''] + [b.get('text') or '' for b in x.get('blocks') or []]:
                if re.search(rx, unicodedata.normalize('NFC', t.strip())):   # matched composed; quoted as held
                    return {'url': url, 'held': origin, 'sha256': sha, 'quote': t.strip()}
        raise Stop('no held page at %s says /%s/' % (url, rx))


def universe_estates():
    im = {r['legacy_key']: r['stable_id'] for r in L.read_table('identity/identity-map.jsonl')
          if r['namespace'] == 'estate' and r.get('stable_id')}
    t = json.load(open(L.ROOT + 'data/discovery/targets.json', encoding='utf-8'))['estates']
    out = {}
    for e in t:
        ids = sorted({im[k] for k in e['canonical_ids'] if k in im})
        if len(ids) == 1:
            out[e['universe_id']] = ids[0]
    return out


def review_set(plan):
    return sorted({d for r in plan if r['category'] != 'A' and r['party'] == 'FIRST_PARTY' for d in r['domains']})


def m33_for(plan, domain, estate):
    out = {'ranked': None, 'dead_links': 0, 'blocked_by_policy': 0}
    for r in plan:
        if domain not in r['domains'] or estate not in r['estates']:
            continue
        if r['source_family'] == 'DISCOVERED_NOT_ACQUIRED':
            out['ranked'] = {'rank': r['rank'], 'locators': r['locator_count'], 'vintages': r['potential_vintage_count'],
                             'items_by_confidence': r['items_by_confidence'], 'effort': r['acquisition_effort'],
                             'candidate': r['source_candidate_id']}
        elif r['source_family'] == 'DISCOVERED_DEAD_LINK':
            out['dead_links'] += r['locator_count']
        elif r['source_family'] == 'BLOCKED_BY_POLICY':
            out['blocked_by_policy'] += r['locator_count']
    return out


def build():
    plan = L.jsonl_lines(M33)
    doms = review_set(plan)
    if len(doms) != 21:
        raise Stop('M3.3 names %d first-party acquisition domains, expected 21' % len(doms))
    src = {s['id']: s for s in L.read_table('identity/sources.jsonl')}
    by_name = {s['name']: s for s in src.values()}
    rels = L.read_table('state/source-estate.jsonl')
    pv = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    names = {}
    for n in L.read_table('identity/names.jsonl'):
        if n.get('kind') == 'CURRENT' and str(n.get('subject', '')).startswith('es_'):
            names[n['subject']] = n['name']
    prof = json.load(open(L.ROOT + 'data/discovery/profiles.json', encoding='utf-8'))
    srcdocs = json.load(open(L.MODEL + 'derived/source-documents.json', encoding='utf-8'))
    links = collections.Counter()
    for l in L.read_table('observation/evidence-links.jsonl'):
        links[(l.get('artifact'), l.get('estate'))] += 1
    probes = [r for r in L.jsonl_lines(M36G) if r['record'] == 'probe']
    U = universe_estates()
    H = Held()
    if set(k[0] for k in REVIEW) != set(doms):
        raise Stop('the review table and M3.3\'s domains differ: %s' % sorted(set(doms) ^ set(k[0] for k in REVIEW)))
    reviewed = {(by_name[d]['id'], e) for d, e in REVIEW}
    have = {(r['source'], r['estate']) for r in rels}
    if not reviewed <= have:
        raise Stop('a reviewed relationship the model does not record: %s' % sorted(reviewed - have))
    for d in doms:
        if {e for s, e in have if s == by_name[d]['id']} != {e for dd, e in REVIEW if dd == d}:
            raise Stop('%s: the model records other estates than the review table' % d)

    rows = [{'record': 'scope', 'phase': 'M3.7', 'candidates': 'state/source-estate.jsonl (%d relationships, %d sources)'
             % (len(rels), len({r['source'] for r in rels})),
             'review_set': doms, 'review_set_rule': 'M3.3 plan rows outside category A whose party is FIRST_PARTY',
             'statuses': list(STATUSES), 'inspected': INSPECTED,
             'excluded': ['no model, evidence, gap-register or application change', 'no document acquisition or OCR',
                          'no identity transition, D5, rank or Mongravey Cuvée Margaux decision',
                          'no relationship added, changed or upgraded']}]
    srows = []
    for d in doms:
        s = by_name[d]
        p = prof.get(d) or {}
        val = lambda k: (p.get(k) or {}).get('value')
        named = {U.get(u, u): n for u, n in sorted((val('estates_named_in_titles') or {}).items())}
        robots = val('robots') or {}
        exts = (val('document_patterns') or {}).get('extensions') or {}
        held = H.arts.get(d, [])
        srows.append({'record': 'source', 'source': s['id'], 'name': d, 'kind_recorded': s['kind'],
                      'base_urls': s.get('base_urls') or [], 'moved_to': val('moved_to') or [],
                      'canonical_host': (val('moved_to') or [d])[0],
                      'languages': val('languages') or {}, 'document_types': exts,
                      'wordpress_media_listing': val('wordpress_media_listing'),
                      'robots': {'kind': robots.get('kind'), 'ai_refused': robots.get('ai_refused') or []},
                      'crawled': ((val('crawl') or {}).get('finished') or '')[:10],
                      'estates_named_in_titles': named, 'shared': len(named) > 1,
                      'held': {'pages': sum(1 for a in held if a['media'] == 'html'),
                               'pdfs': sum(1 for a in held if a['media'] == 'pdf')},
                      'model_documents': len(srcdocs.get(s['id']) or [])})
    shared = {r['source']: r['shared'] for r in srows}
    named_by = {r['source']: r['estates_named_in_titles'] for r in srows}
    rrows, conflicts, rank = [], [], []
    for r in sorted(rels, key=lambda r: (r['source'], r['estate'])):
        s = src[r['source']]
        p = pv[r['provenance']]
        base = {'record': 'relationship', 'id': 'm37:%s:%s' % (r['source'], r['estate']), 'source': r['source'],
                'source_name': s['name'], 'estate': r['estate'], 'estate_name': names.get(r['estate']),
                'recorded': {'relationship': r['id'], 'kind': r['kind'], 'provenance': p['kind'],
                             'legacy_tag': (p.get('code_state') or {}).get('tag'),
                             'legacy_url': (p.get('code_state') or {}).get('url')}}
        key = (s['name'], r['estate'])
        if key not in REVIEW:
            rrows.append(dict(base, status='NOT_REVIEWED', reason='not an M3.3 first-party acquisition candidate'))
            continue
        spec = REVIEW[key]
        e = {}
        for k in ('site', 'link', 'presents', 'unclear'):
            if spec.get(k):
                e[k] = H.quote(*spec[k])
        if spec.get('publisher'):
            url, rx, kind = spec['publisher']
            e['publisher'] = dict(H.quote(url, rx), kind=kind)
        if spec.get('redirect'):
            if spec['redirect'].startswith('M3.6G probe: '):
                host = spec['redirect'][len('M3.6G probe: '):]
                pr = [x for x in probes if x['source'] in (host, 'www.' + host) and x['answer'].startswith('301 -> https://'
                                                                                                              + s['name'])]
                if not pr:
                    raise Stop('no M3.6G probe shows %s redirecting to %s' % (host, s['name']))
                e['redirect'] = {'held': 'M3.6G probe', 'from': pr[0]['ask'], 'to': pr[0]['answer']}
            else:
                mv = (prof.get(s['name']) or {}).get('moved_to', {}).get('value') or []
                if spec['redirect'] not in mv:
                    raise Stop('%s does not redirect to %s in its crawl profile' % (s['name'], spec['redirect']))
                e['redirect'] = {'held': 'crawl profile moved_to', 'from': s['name'], 'to': spec['redirect']}
        n = named_by[r['source']].get(r['estate'])
        if not e.get('presents') and n:
            e['presents'] = {'held': 'crawl profile', 'pages_naming_the_estate_in_their_title': n}
        st = status(e, shared[r['source']])
        m33 = m33_for(plan, s['name'], r['estate'])
        acc = sum(1 for a in srcdocs.get(r['source']) or [] if links[(a, r['estate'])])
        rk = m33['ranked']
        # M3.3's blocked URLs are never among its discovered ones: a blocked count is a caveat, not a veto
        suitable = st in STATUSES[:3] and bool(rk)
        why = ('first-party URLs naming %d vintage(s) already discovered' % rk['vintages'] if suitable else
               'no discovered vintage URL in M3.3' if not rk else 'authority not established')
        if m33['blocked_by_policy']:
            why += '; %d other URL(s) blocked by policy in M3.3, respected' % m33['blocked_by_policy']
        row = dict(base, status=st, confidence=CONFIDENCE[st], elements=e, open=spec.get('open', []),
                   currency='CURRENT as published (crawl 2026-10-25, inspection %s)' % INSPECTED,
                   acquisition={'m33': m33, 'documents_with_accepted_evidence': acc,
                                'model_documents': len(srcdocs.get(r['source']) or [])},
                   vintage_documents={'suitable': suitable, 'why': why})
        rrows.append(row)
        if key in CONFLICTS:
            conflicts.append({'record': 'conflict', 'relationship': r['id'], 'audit': row['id'], 'recorded_kind': r['kind'],
                              'm37_status': st, 'difference': CONFLICTS[key], 'action': 'none: preserved for review'})
        if suitable:
            conf = rk['items_by_confidence']
            rank.append(((STATUSES.index(st) > 1), -conf.get('HIGH', 0), -rk['vintages'], -rk['locators'],
                         EFFORT.get(rk['effort'], 5), len(spec.get('open', [])), r['source'], r['estate'], row))
    if {r['status'] for r in rrows} - set(STATUSES):
        raise Stop('a status outside the vocabulary')
    rank.sort(key=lambda x: x[:-1])
    ranked = []
    for i, x in enumerate(rank, 1):
        row = x[-1]
        rk = row['acquisition']['m33']['ranked']
        ranked.append({'record': 'ranking', 'rank': i, 'relationship': row['id'], 'source_name': row['source_name'],
                       'estate': row['estate'], 'estate_name': row['estate_name'], 'status': row['status'],
                       'high_confidence_items': rk['items_by_confidence'].get('HIGH', 0), 'vintages': rk['vintages'],
                       'locators': rk['locators'], 'effort': rk['effort'], 'm33_rank': rk['rank'],
                       'held_pdfs': next(s['held']['pdfs'] for s in srows if s['source'] == row['source']),
                       'documents_with_accepted_evidence': row['acquisition']['documents_with_accepted_evidence'],
                       'open_questions': len(row['open'])})
    findings = shared_findings(srows, U, rels, names)
    c = collections.Counter(r['status'] for r in rrows)
    rv = [r for r in rrows if r['status'] != 'NOT_REVIEWED']
    summary = {'record': 'summary', 'relationships': len(rrows), 'reviewed_relationships': len(rv),
               'reviewed_sources': len(doms), 'reviewed_estates': len({r['estate'] for r in rv}),
               'by_status': {k: c.get(k, 0) for k in STATUSES}, 'conflicts': len(conflicts),
               'inspection_requests': len(H.inv), 'ranked': len(ranked), 'model_changes': 0}
    insp = [dict({'record': 'inspection', 'n': i}, **{k: v for k, v in q.items()}) for i, q in enumerate(H.inv, 1)]
    return rows + srows + insp + rrows + findings + conflicts + ranked + [summary]


def shared_findings(srows, U, rels, names):
    """A host serving several estates, or a redirect onto one: each estate it names, related or not."""
    rel = {(r['source'], r['estate']) for r in rels}
    by_host = collections.defaultdict(list)
    for s in srows:
        by_host[s['canonical_host']].append(s)
    out = []
    for host, ss in sorted(by_host.items()):
        named = {}
        for s in ss:
            named.update(s['estates_named_in_titles'])
        if len(named) < 2 and len(ss) < 2:
            continue
        out.append({'record': 'finding', 'kind': 'SHARED_HOST', 'host': host, 'sources': [s['source'] for s in ss],
                    'estates_named': {e: {'name': names.get(e), 'pages': n,
                                          'relationship_recorded': any((s['source'], e) in rel for s in ss)}
                                      for e, n in sorted(named.items())}})
    return out


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def cell(s, n=None):
    s = str(s if s is not None else '—').replace('|', '\\|').replace('\n', ' ')
    return s if not n or len(s) <= n else s[:n - 1] + '…'


def report(rows):
    """docs/PHASE-M3.7-SOURCE-CONFIRMATION.md, from the audit's records alone."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r['record']].append(r)
    [scope], [sm] = by['scope'], by['summary']
    rel = by['relationship']
    rv = [r for r in rel if r['status'] != 'NOT_REVIEWED']
    out = []
    w = out.append
    w('# Phase M3.7 — Source confirmation\n')
    w('Generated by `python tools/m37-source-confirmation.py` (`data/audit/m3.7-source-confirmation.jsonl`); never '
      'edited by hand. **Audit only: no model, evidence, gap-register or application data was created or changed.** '
      'No relationship was added, changed or upgraded; no document was acquired or OCR\'d.\n')
    w('## 1. Scope\n')
    w('- **The question:** for each candidate source, what evidence shows it speaks for the estate, and what that '
      'evidence permits us to claim.')
    w('- **The candidates:** %s. Every one is kind `OFFICIAL_SITE` and `LEGACY_UNSOURCED`: an address taken from '
      '`data/websites.js` with a tag saying how it was found (a register entry, OpenStreetMap, a guessed domain read '
      'by hand). None had been confirmed.' % scope['candidates'])
    w('- **The review set:** the %d domains M3.3 planned to acquire from as first-party sources (%s): %d '
      'relationships, %d estates. The six named for this phase (La Mission Haut-Brion, Latour-Martillac, Calon-Ségur, '
      'Durfort-Vivens, Myrat, Ferrière) are among them, and so is Vignobles Bernaleau from M3.6.'
      % (len(scope['review_set']), scope['review_set_rule'], len(rv), sm['reviewed_estates']))
    w('- **The rest** (%d relationships) are inventoried as `NOT_REVIEWED`, each with its legacy tag; reviewing them '
      'would be the broad crawl this phase excludes.' % sm['by_status']['NOT_REVIEWED'])
    w('- **What was read:** the pages the M3.3 discovery crawl already holds (crawl of 2026-10-25), and a narrow '
      'inspection on %s of %d requests (section 10).\n' % (scope['inspected'], sm['inspection_requests']))
    w('## 2. Candidate-source inventory\n')
    w('| Source | Recorded kind | Serves today from | Estates named in page titles | Languages | PDFs held | '
      'WP media list | robots.txt |')
    w('|---|---|---|---|---|---:|---|---|')
    names = {r['estate']: r['estate_name'] for r in rel}
    for s in by['source']:
        named = ', '.join('%s (%d)' % (names.get(e) or e, n) for e, n in s['estates_named_in_titles'].items())
        w('| `%s` (%s) | %s | %s | %s | %s | %d | %s | %s |' % (
            s['name'], s['source'], s['kind_recorded'],
            s['canonical_host'] + (' (redirect)' if s['moved_to'] else ''), cell(named),
            ', '.join(sorted(s['languages'])), s['held']['pdfs'], 'yes' if s['wordpress_media_listing'] else 'no',
            s['robots']['kind']))
    w('')
    nr = collections.Counter(r['recorded']['legacy_tag'] for r in rel if r['status'] == 'NOT_REVIEWED')
    w('Not reviewed, by the legacy tag that says how the address was found: %s.\n'
      % ', '.join('`%s` %d' % (k, n) for k, n in sorted(nr.items(), key=lambda x: (-x[1], x[0]))))
    w('## 3. Source-status results\n')
    w('The status follows from the evidence elements by one rule (`status()`); it is never typed in.\n')
    w('| Elements | Status |')
    w('|---|---|')
    for a, b in (('what the relationship\'s estate is, on this source, is in question', 'SOURCE_IDENTITY_UNCLEAR'),
                 ('the legal notice names the estate\'s own company, and the site presents itself as the estate',
                  'CONFIRMED_FIRST_PARTY'),
                 ('the estate\'s own company publishes a group site', 'CONFIRMED_ESTATE_CONTROLLED'),
                 ('the site\'s own text ties its publisher, owners or family to the estate, and the publisher is '
                  'named or the estate\'s own domain redirects there', 'CONFIRMED_ESTATE_CONTROLLED'),
                 ('the site presents the estate and names a publisher, or presents itself as the estate, but nothing '
                  'held ties the two', 'PROBABLE_FIRST_PARTY'),
                 ('a shared host presents the estate, nothing more', 'SHARED_HOST_UNCONFIRMED'),
                 ('outside the review set', 'NOT_REVIEWED')):
        w('| %s | `%s` |' % (a, b))
    w('\nA domain carrying the estate\'s name, a URL path, a filename, a search result or a page that only mentions '
      'the estate is never an element.\n')
    w('| Status | Relationships |')
    w('|---|---:|')
    for k in STATUSES:
        w('| `%s` | %d |' % (k, sm['by_status'][k]))
    w('\n`THIRD_PARTY` and `SOURCE_NOT_RELEVANT` were reached by no reviewed relationship: every reviewed source is '
      'run by the estate or a group that presents it, or is unresolved.\n')
    w('## 4. Estate/source relationships\n')
    w('| Estate | Source | Status | Confidence | Vintage documents | Open questions |')
    w('|---|---|---|---|---|---:|')
    for r in sorted(rv, key=lambda r: (STATUSES.index(r['status']), r['estate_name'] or '')):
        w('| %s (`%s`) | `%s` | `%s` | %s | %s | %d |' % (
            r['estate_name'], r['estate'], r['source_name'], r['status'], r['confidence'],
            ('yes: ' if r['vintage_documents']['suitable'] else 'no: ') + r['vintage_documents']['why'], len(r['open'])))
    w('\nEvery reviewed relationship is current as published: crawl of 2026-10-25, inspection of %s. Where a link '
      'statement is historical, the open questions say so.\n' % scope['inspected'])
    w('## 5. Evidence supporting each relationship\n')
    for r in sorted(rv, key=lambda r: (r['source_name'], r['estate'])):
        w('**%s ← `%s`: `%s`**\n' % (r['estate_name'], r['source_name'], r['status']))
        for k in ('site', 'publisher', 'link', 'redirect', 'presents', 'unclear'):
            e = r['elements'].get(k)
            if not e:
                continue
            if 'quote' in e:
                w('- %s%s: "%s" (%s, held: %s `%s`)' % (k, ' (%s)' % e['kind'] if e.get('kind') else '',
                                                        cell(e['quote'], 240), e['url'], e['held'], e['sha256'][:12]))
            elif k == 'redirect':
                w('- redirect: %s → %s (%s)' % (e['from'], e['to'], e['held']))
            else:
                w('- presents: %d page(s) naming the estate in their title (crawl profile)'
                  % e['pages_naming_the_estate_in_their_title'])
        m = r['acquisition']
        w('- held already: %d model document(s) from this source, %d with an accepted evidence link to this estate'
          % (m['model_documents'], m['documents_with_accepted_evidence']))
        w('')
    w('## 6. Third-party and shared-host findings\n')
    w('No reviewed source is a retailer, critic, distributor or importer. Shared hosts:\n')
    w('| Host | Model sources | Estates named in page titles (pages; relationship recorded?) |')
    w('|---|---|---|')
    for f in by['finding']:
        w('| `%s` | %s | %s |' % (f['host'], ', '.join('`%s`' % s for s in f['sources']), '; '.join(
            '%s (%d; %s)' % (v['name'], v['pages'], 'yes' if v['relationship_recorded'] else 'no')
            for v in f['estates_named'].values())))
    w('\n- **gc-lurton-estates.com:** the three estates\' own domains (`durfort-vivens.fr`, `ferriere.com`, '
      '`hautbagesliberal.com`) all redirect to one group site. The model keeps three sources; M3.7 creates no fourth.')
    w('- **Domaine Clarence Dillon:** one legal notice says the company produces `domaineclarencedillon.com`, '
      '`haut-brion.com` and `mission-haut-brion.com`.')
    w('- **Borie-Manoux:** the Batailley and TrotteVieille legal notices share the address 88 Quai de Bacalan and the '
      'contact domaines@borie-manoux.fr; each names its own société civile, seated at its château.')
    w('- An estate named on a shared host without a recorded relationship (Pouget, Guiraud, Carcanieux, Les Lattes) '
      'is reported, not added.\n')
    w('## 7. Unresolved source questions\n')
    for r in sorted(rv, key=lambda r: (r['source_name'], r['estate'])):
        for q in r['open']:
            w('- **%s ← `%s`:** %s' % (r['estate_name'], r['source_name'], q))
    w('\nWhere M3.7\'s reading differs from what the model records, the record is preserved and the difference '
      'is listed for review:\n')
    w('| Relationship | Recorded | M3.7 | Difference |')
    w('|---|---|---|---|')
    for c in by['conflict']:
        w('| `%s` | `%s` | `%s` | %s |' % (c['relationship'], c['recorded_kind'], c['m37_status'], c['difference']))
    w('')
    w('## 8. Recommended next acquisition targets\n')
    w('Ranked from evidence already established, nothing fetched for the ranking: confirmed before probable, then '
      'M3.3\'s high-confidence items (a discovered URL that names the exact vintage), vintages, discovered URLs, '
      'effort, and fewest open questions. Only relationships with discovered first-party vintage URLs qualify.\n')
    w('| # | Estate | Source | Status | High-confidence items | Vintages | URLs | Effort | PDFs held | '
      'Documents with accepted evidence | Open |')
    w('|---:|---|---|---|---:|---:|---:|---|---:|---:|---:|')
    for k in by['ranking']:
        w('| %d | %s | `%s` | `%s` | %d | %d | %d | %s | %d | %d | %d |' % (
            k['rank'], k['estate_name'], k['source_name'], k['status'], k['high_confidence_items'], k['vintages'],
            k['locators'], k['effort'], k['held_pdfs'], k['documents_with_accepted_evidence'], k['open_questions']))
    w('\nThe four probable sources rank last for their unresolved authority, not their yield: Latour-Martillac has '
      'the most high-confidence items of all. One legal notice (Latour-Martillac, Malartic) or one ownership '
      'statement (Domaine Clarence Dillon) would settle each.\n')
    w('## 9. Explicit exclusions\n')
    for x in scope['excluded']:
        w('- %s' % x)
    w('- no new source identity: a redirect target (e.g. `gc-lurton-estates.com`, `calon-segur.fr`) is recorded as '
      'where a model source serves today, not as a source')
    w('- no wine for "Château Braude Fellonneau", no relationship for Pouget, Guiraud, Carcanieux or Les Lattes\n')
    w('## 10. No model or application data was changed\n')
    w('The audit reads the model and writes only `data/audit/m3.7-source-confirmation.jsonl` and this document. '
      '`tools/test-m37.py` checks that `data/model`, `data/evidence` (v1-v8), `data/app`, the gap register and '
      'the app files are as M3.6H left them.\n')
    w('The narrow inspection (stored locally in `sources/acquisition/m3.7/`, not committed), through '
      '`tools/discover.py`\'s fetch, user agent, robots rules and 1.5 s delay:\n')
    w('| # | Request | Why | Status | Title |')
    w('|---:|---|---|---|---|')
    for q in by['inspection']:
        w('| %d | %s | %s | %s %s | %s |' % (q['n'], q['url'], q['why'], q.get('status'), q.get('kind'),
                                             cell(q.get('title'), 70)))
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    try:
        rows = build()
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)
    b, doc = body(rows), report(rows)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.7 outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d records); %s written' % (OUT[len(L.ROOT):], b.count(b'\n'), DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
