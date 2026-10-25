# -*- coding: utf-8 -*-
"""Phase 3.4: what the harvested corpus says about the domain model.

    python -I tools/review-corpus.py [--workers N]

Reads the Phase 3.3 harvest - the committed discovery data and the local
full texts (sources/discovery/extracted/) - and writes
data/review/phase34-corpus-analysis.json: counts, spreads and a few short
quoted samples for every question the review asks. Read-only on the
harvest; deterministic (sorted inputs, first samples in hash order).

The patterns are detectors for the review, not a schema: each section says
what it counted, so a figure in the review can be traced to a pattern
here.
"""
import argparse
import collections
import concurrent.futures as cf
import io
import json
import os
import re
import statistics
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
DISC = ROOT + 'data/discovery/'
EXT = ROOT + 'sources/discovery/extracted/'
OUT = ROOT + 'data/review/phase34-corpus-analysis.json'
SAMPLES = 6
CTX = 110


def jl(p):
    return [json.loads(l) for l in io.open(p, encoding='utf-8') if l.strip()]


def fold(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def key(s):
    return ' '.join(re.sub(r'[^a-z0-9一-鿿]+', ' ', fold(s)).split())


# ---------------------------------------------------------------- patterns
# Hierarchy and range wording. Each is searched in the folded full text.
HIERARCHY = collections.OrderedDict([
    ('grand_vin', r'\bgrands? vins?\b'),
    ('first_wine', r'\b(premier vin|first wine|1er vin)\b'),
    ('second_wine', r"\b(seconde?s? vins?|deuxieme vin|2 ?(nd|eme|e|d) vin|second wines?|2nd wine|zweitwein)\b"),
    ('second_label', r'\b(second label|deuxieme etiquette|seconde? etiquette)\b'),
    ('third_wine', r'\b(troisieme vin|3 ?(eme|e|rd) vin|third (wine|label)s?|3rd wine)\b'),
    ('prestige', r'\b(cuvee (de )?prestige|prestige cuvee)\b'),
    ('superior', r'\b(cuvee superieure|superior cuvee|tete de cuvee)\b'),
    ('premium', r'\b(premium|haut de gamme|top of the range)\b'),
    ('plot_selection', r'\b(selection parcellaire|plot selection|parcel selection|single[- ]plot|'
                       r'mono-?parcellaire|single parcel|une seule parcelle|a single plot)\b'),
    ('special_cuvee', r'\b(cuvee speciale|special cuvee|cuvee confidentielle|cuvee limitee|'
                      r'limited edition|edition limitee)\b'),
    ('old_vines', r'\b(vieilles vignes|old vines)\b'),
    ('young_vines', r'\b(jeunes vignes|young(er)? vines)\b'),
    ('single_variety', r'\b(mono-?cepage|single[- ]variet(y|al)|pur merlot|pure merlot|'
                       r'100 ?% (merlot|cabernet sauvignon|cabernet franc|petit verdot|malbec|carmenere|'
                       r'sauvignon blanc|semillon))\b'),
    ('little_brother', r'\b(petit frere|little brother|petite soeur|little sister|cadet)\b'),
    ('no_hierarchy', r"(pas de second vin|no second wine|premier (vin )?et (un )?second vin.{0,40}(pas|ne)|"
                     r"(ne|not).{0,60}(premier et second|first and second (wine|label))|"
                     r"do not represent.{0,50}first and second|n'est pas un second vin|is not a second wine|"
                     r"sans hierarchie|without (a )?hierarchy|non hierarchi)"),
])
TYPE_WORDS = collections.OrderedDict([
    ('red', r'\b(vin rouge|red wine|rouge)\b'),
    ('dry_white', r'\b(blanc sec|vin blanc sec|dry white)\b'),
    ('sweet_white', r'\b(liquoreux|moelleux|sweet (white )?wine|botrytis|sauternes|barsac)\b'),
    ('rose', r'\b(rose|clairet)\b'),
    ('sparkling', r'\b(cremant|petillant|sparkling|bulles)\b'),
])
RELATION = collections.OrderedDict([
    ('from_estate_vines', r"(issue?s? (des|de) (jeunes )?(vignes|parcelles|plus jeunes)|from (the )?(young(er)? )?vines of|"
                          r"made from (some of )?the (young(er)? )?vines|planted on .{0,40}(estate|property))"),
    ('produced_at', r'(vinifie(e|s)? (au|a la|a|par)|produit (au|par|a)|elabore(e)? (au|par|a)|made at|produced (at|by)|vinified at|'
                    r'made by the (same )?team)'),
    ('brand_negoce', r'\b(marque|brand|negoce|negociant|distribue par|distributed by|exclusivite)\b'),
    ('owned_group', r'(propriete (de|du groupe|de la famille)|appartient a|owned by|belongs to|member of the|'
                    r'fait partie (du|des)|part of the)'),
    ('other_property', r'(autre propriete|other (property|estate)|our other estates?|nos autres proprietes|'
                       r'nos proprietes|our properties|our estates)'),
    ('historical', r'\b(anciennement|autrefois|formerly|previously|jadis|auparavant)\b'),
])
TEMPORAL = collections.OrderedDict([
    ('since_year', r'\b(depuis|since) (l.annee |le millesime |the )?(1[89]\d\d|20[0-3]\d)\b'),
    ('from_vintage', r'(a partir du millesime|des le millesime|from the|starting with the|beginning with the) (1[89]\d\d|20[0-3]\d)( vintage)?'),
    ('until', r"(jusqu.(en|au|a) (millesime )?(1[89]\d\d|20[0-3]\d)|until (1[89]\d\d|20[0-3]\d)|up to the (1[89]\d\d|20[0-3]\d))"),
    ('formerly', r'\b(anciennement|autrefois|formerly|previously|auparavant|jadis|once known as|ex-)\b'),
    ('renamed', r"(rebaptise|renomme|renamed|change (de nom|d.identite)|changed (its )?name|prend le nom|took the name|devient|became)"),
    ('introduced', r"(premier millesime|first vintage|introduced in|lance(e)? en|cree(e)? en (1[89]\d\d|20[0-3]\d)|ne(e)? en (1[89]\d\d|20[0-3]\d)|born in (1[89]\d\d|20[0-3]\d)|launched in)"),
    ('discontinued', r"(dernier millesime|last vintage|n.est plus produit|no longer (produced|made)|discontinued|abandonne)"),
    ('acquired', r'(acquis(e)? (en|par)|rachete|rachat|acquired (in|by)|purchased (in|by)|bought (in|by)|reprend|took over)'),
    ('merged', r'\b(fusionne|merged|absorbe|reunis?)\b'),
    ('now', r"\b(aujourd.hui|today|now|actuellement|currently|desormais|henceforth)\b"),
    ('classification_change', r'(promu|promoted|reclasse|declasse|entre(e)? (au|dans le) classement|joined the classification|'
                              r'accede au rang|elevated to)'),
    ('appellation_change', r'(appellation .{0,40}(creee|created|devenue|became|nouvelle|new))'),
])
GRAVES_COLOUR = r'(cru classe de graves .{0,60}(rouge|blanc|red|white)|classe(s)? en (rouge|blanc)|classified (for|in) (both )?(red|white)|' \
                r'(rouge|red) (et|and) (blanc|white).{0,40}cru classe)'
LEGAL_LABELS = ('siret', 'n siret', 'capital social', 'share capital', 'siege social', 'registered office', 'head office',
                'forme juridique', 'rcs', 'n tva', 'tva intracommunautaire', 'directeur de la publication',
                'responsable publication', 'hebergeur', 'raison sociale', 'company')
COMPANY_FORMS = r'\b(scea|sca|sas|sasu|sa|sarl|earl|gfa|sc|snc|gaec|sci|scev|ste|societe)\b'
LANG_TOKEN = re.compile(r'(?i)(?<![a-z])(fr|fra|french|francais|en|eng|english|uk|gb|us|cn|zh|chn|chinese|jp|ja|jpn|'
                        r'de|deu|ger|es|esp|it|ita|nl|ru|pt)(?![a-z])')


def compile_all(d):
    return [(k, re.compile(v)) for k, v in d.items()]


H = compile_all(HIERARCHY)
TY = compile_all(TYPE_WORDS)
RE_ = compile_all(RELATION)
TE = compile_all(TEMPORAL)
GC = re.compile(GRAVES_COLOUR)
CF_ = re.compile(COMPANY_FORMS)


def text_of(sha):
    p = EXT + sha + '.json'
    if not os.path.exists(p):
        return None, None
    d = json.load(io.open(p, encoding='utf-8'))
    if d.get('media') == 'html':
        t = '\n'.join(b['text'] for b in d.get('blocks', []))
    else:
        t = '\n'.join(d.get('pages') or [])
    return t, d


def scan(args):
    """Every pattern family over one artifact: counts and first contexts."""
    sha, = args
    raw, d = text_of(sha)
    if not raw:
        return sha, None
    f = fold(raw)
    f = ' '.join(f.split())
    out = {'len': len(f), 'meta_date': None, 'hits': {}}
    if d and d.get('media') == 'pdf':
        m = (d.get('meta') or {})
        out['meta_date'] = (m.get('creationDate') or m.get('modDate') or '')[2:10] or None
    for fam, pats in (('hier', H), ('type', TY), ('rel', RE_), ('temp', TE)):
        for k, rx in pats:
            ms = list(rx.finditer(f))
            if ms:
                ctxs = [f[max(0, m.start() - CTX):m.end() + CTX] for m in ms[:3]]
                out['hits']['%s:%s' % (fam, k)] = [len(ms), ctxs]
    ms = list(GC.finditer(f))
    if ms:
        out['hits']['class:graves_colour'] = [len(ms), [f[max(0, m.start() - CTX):m.end() + CTX] for m in ms[:3]]]
    # Co-occurrences that decide whether a phrase is a rank or a production mode.
    for a, b, name in (('second_wine', 'young_vines', 'second_with_young_vines'),
                       ('plot_selection', 'second_wine', 'plot_with_second'),
                       ('plot_selection', 'grand_vin', 'plot_with_grand'),
                       ('prestige', 'grand_vin', 'prestige_with_grand')):
        ra, rb = dict(H)[a], dict(H)[b]
        n = 0
        for m in ra.finditer(f):
            if rb.search(f[max(0, m.start() - 200):m.end() + 200]):
                n += 1
        if n:
            out['hits']['co:' + name] = [n, []]
    return sha, out


def wanted_text(sha, needles):
    raw, d = text_of(sha)
    if not raw:
        return None
    f = ' '.join(fold(raw).split())
    res = {}
    for n in needles:
        idx = [m.start() for m in re.finditer(re.escape(n), f)]
        if idx:
            res[n] = [len(idx), [f[max(0, i - 160):i + 200] for i in idx[:3]]]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    T = json.load(io.open(DISC + 'targets.json', encoding='utf-8'))
    dom_est = {d['domain']: d['estates'] for d in T['domains']}
    arts = {r['sha256']: r for r in jl(DISC + 'artifacts.jsonl')}
    vc = {r['artifact']: r for r in jl(DISC + 'vintage-candidates.jsonl')}
    shas = sorted(s for s, r in arts.items() if r['media'] in ('html', 'pdf', 'office', 'text'))
    res = {}
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        for sha, out in ex.map(scan, [(s,) for s in shas], chunksize=64):
            if out:
                res[sha] = out

    def agg(prefix):
        o = collections.OrderedDict()
        keys = sorted({k for r in res.values() for k in r['hits'] if k.startswith(prefix)})
        for k in keys:
            arts_k = sorted(s for s, r in res.items() if k in r['hits'])
            doms = collections.Counter(d for s in arts_k for d in arts[s]['domains'])
            ests = set(e for d in doms for e in dom_est.get(d, []))
            langs = collections.Counter(arts[s].get('lang_detected') or '?' for s in arts_k)
            media = collections.Counter(arts[s]['media'] for s in arts_k)
            samples = []
            seen = set()
            for s in arts_k:
                for c in res[s]['hits'][k][1]:
                    kk = c[60:160]
                    if kk not in seen and len(samples) < SAMPLES:
                        seen.add(kk)
                        samples.append({'artifact': s[:16], 'domain': arts[s]['domains'][0], 'context': c})
            o[k.split(':', 1)[1]] = {
                'mentions': sum(res[s]['hits'][k][0] for s in arts_k), 'artifacts': len(arts_k),
                'domains': len(doms), 'estates_by_crawl_context': len(ests),
                'langs': dict(langs.most_common()), 'media': dict(media.most_common()),
                'top_domains': [d for d, _ in doms.most_common(8)], 'samples': samples}
        return o

    analysis = collections.OrderedDict()
    analysis['meta'] = {'phase': '3.4', 'built_by': 'tools/review-corpus.py', 'input': 'b278121',
                        'artifacts_scanned': len(res), 'note': 'Contexts are folded (lower case, no accents).'}
    analysis['hierarchy'] = agg('hier:')
    analysis['type_wording'] = agg('type:')
    analysis['relationship_wording'] = agg('rel:')
    analysis['temporal_wording'] = agg('temp:')
    analysis['classification'] = agg('class:')
    analysis['cooccurrence'] = {k.split(':', 1)[1]: v['mentions'] for k, v in
                                (('co:' + n, agg('co:' + n).get(n, {'mentions': 0}))
                                 for n in ('second_with_young_vines', 'plot_with_second', 'plot_with_grand',
                                           'prestige_with_grand'))}

    # -------------------------------------------------- observations
    obs = []
    for f in sorted(os.listdir(DISC + 'observations')):
        obs += jl(DISC + 'observations/' + f)
    # Appellations per site: does one site state several appellations?
    apps = collections.defaultdict(collections.Counter)
    for o in obs:
        if re.match(r'^(appellation|aoc|aop|denomination)\b', key(o['label'])):
            v = key(o['value'])[:60]
            for d in arts.get(o['artifact'], {}).get('domains', []):
                apps[d][v] += 1
    multi = {d: c for d, c in apps.items() if len([v for v, n in c.items() if n >= 2]) >= 2}
    analysis['appellation_per_site'] = {
        'sites_stating_an_appellation': len(apps),
        'sites_with_two_or_more_recurring_values': len(multi),
        'examples': {d: dict(c.most_common(4)) for d, c in sorted(multi.items())[:12]}}

    # Document dating: what dates a statement could be anchored to.
    pdfs = [s for s, r in arts.items() if r['media'] == 'pdf']
    upl = sum(1 for s in pdfs if re.search(r'/(19|20)\d\d/\d\d/', arts[s]['first_url']))
    meta = sum(1 for s in pdfs if s in res and res[s]['meta_date'])
    lm = 0
    locs = {}
    for f in sorted(os.listdir(DISC + 'locations')):
        for r in jl(DISC + 'locations/' + f):
            if r.get('kind') == 'OK' and r.get('sha256'):
                locs.setdefault(r['sha256'], r)
                if r.get('last_modified'):
                    lm += 1
    vint = sum(1 for s in arts if (vc.get(s) or {}).get('url_years') or (vc.get(s) or {}).get('title_years'))
    analysis['document_dating'] = {
        'pdfs': len(pdfs), 'pdfs_with_metadata_date': meta, 'pdfs_with_upload_path_date': upl,
        'fetches_with_last_modified': lm,
        'artifacts_with_url_or_title_year': vint, 'artifacts': len(arts)}

    # Taxonomy, from the labels as found, with structure measures.
    TAX = collections.OrderedDict([
        ('IDENTITY_CONTACT', r'^(tel|telephone|phone|fax|e ?mail|mail|adresse|address|contact|site web|website|gps|'
                             r'location|situation|localisation|horaires?|电话)\b'),
        ('LEGAL_ENTITY', r'^(siret|n siret|capital social|share capital|siege social|registered office|head office|'
                         r'forme juridique|rcs|n tva|tva|directeur de la publication|responsable (de la )?publication|'
                         r'hebergeur|createur|webmaster|raison sociale|editeur|design|credits photos)\b'),
        ('PRIVACY_LEGAL_TEXT', r'^(article \d|droit d|informations personnelles|personal information|utilisateur|user|'
                               r'cookies?|sous (chrome|firefox|safari|internet explorer)|google analytics|textes)\b'),
        ('OWNERSHIP_PEOPLE', r'^(proprietaires?|owners?|famille|family|directeur|director|gerant|manager|oenologue|'
                             r'oenologist|consultant|winemaker|maitre de chai|cellar master|chef de culture|regisseur)\b'),
        ('CLASSIFICATION', r'^(classement|classification|cru bourgeois|grand cru|cru classe|cru artisan)\b'),
        ('APPELLATION', r'^(appellation|aoc|aop|denomination|产区)\b'),
        ('VINEYARD_AREA', r'^(superficie|surface|area|hectares?|vignoble|vineyard)\b'),
        ('SOIL_TERROIR', r'^(sols?|soils?|sous sol|subsoil|terroir|geologie|geology)\b'),
        ('PLANTING', r'^(encepagement|cepages?|grape variet|varietals?|densite|planting density|density|'
                     r'age (moyen )?(des vignes|du vignoble)|average age|vine age|porte greffe|rootstock|merlot|'
                     r'cabernet|petit verdot|sauvignon|semillon|malbec|muscadelle)'),
        ('VITICULTURE', r'^(taille|pruning|enherbement|travaux|viticulture|conduite|vendange en vert|effeuillage|'
                        r'labour|ploughing)\b'),
        ('HARVEST_VINTAGE', r'^(vendanges?|harvest|recolte|dates? de vendange|harvest dates?|millesime|vintage|'
                            r'climat|weather|meteo|rendement|yield|floraison|veraison)'),
        ('WINEMAKING', r'^(vinification|winemaking|fermentation|maceration|cuvaison|extraction|cuves?|vats?|'
                       r'levures?|yeast|temperature|tri|sorting|egrappage|destemming)'),
        ('ELEVAGE', r'^(elevage|ageing|aging|barriques?|barrels?|futs|oak|chene|duree|duration|amphor)'),
        ('BLEND', r'^(assemblage|blend|composition)\b'),
        ('BOTTLING_PRODUCTION', r'^(mise en bouteilles?|bottling|production|bouteilles|bottles|formats?|contenance|'
                                r'poids|weight)'),
        ('ANALYTICAL', r'^(alcool|alcohol|degre|tav|ph|acidite|acidity|sucres?|sugar|volatil|so2|ipt|tannins?|'
                       r'酒精|酸度|ph值|总多酚)'),
        ('TASTING', r'^(degustation|tasting|robe|couleur|colou?r|nez|nose|bouche|palate|finale|finish|aromes|'
                    r'aromas|commentaire|notes? de degustation)'),
        ('SERVICE_AGEING', r'^(service|serving|temperature de service|garde|ageing potential|apogee|drink|accords?|'
                           r'pairing|food|carafage|decant)'),
        ('PRESS_SCORES', r'^(note|notes|score|james suckling|jane anson|yves beck|jeb dunnuck|markus del monego|'
                         r'jean marc quarin|bernard burtschy|la revue du vin de france|wine advocate|robert parker|'
                         r'decanter|vinous|wine spectator|terre de vins|guide hachette|bettane|gault)'),
        ('COMMERCIAL', r'^(prix|price|tarif|disponib|availability|livraison|delivery|commande|order|'
                       r'secure delivery|livraison securisee)'),
        ('TOURISM', r'^(visite|visit|duree de la visite|langues|languages|ouvert|opening|reservation|booking|'
                    r'hebergement|accommodation|chambres?)'),
        ('SUSTAINABILITY', r'^(bio|biologique|organic|biodynam|hve|certification|certifications?|terra vitis|'
                           r'environnement|environment|labels?)\b'),
        ('HISTORY', r'^(histoire|history|historique|fondation|founded|origine)\b'),
    ])
    TAXC = [(k, re.compile(v)) for k, v in TAX.items()]
    docvint = {s for s in arts if (vc.get(s) or {}).get('url_years') or (vc.get(s) or {}).get('title_years')}
    tax = collections.OrderedDict((k, {'observations': 0, 'artifacts': set(), 'domains': set(), 'labels': collections.Counter(),
                                       'numeric': 0, 'pdf': 0, 'in_vintage_docs': 0, 'langs': collections.Counter(),
                                       'value_len': []}) for k in list(TAX) + ['UNCLASSIFIED'])
    for o in obs:
        k = key(o['label'])
        cat = next((c for c, rx in TAXC if rx.search(k)), 'UNCLASSIFIED')
        t = tax[cat]
        t['observations'] += 1
        t['artifacts'].add(o['artifact'])
        for d in arts.get(o['artifact'], {}).get('domains', []):
            t['domains'].add(d)
        t['labels'][k] += 1
        t['numeric'] += bool(o.get('normalized'))
        t['pdf'] += arts.get(o['artifact'], {}).get('media') == 'pdf'
        t['in_vintage_docs'] += o['artifact'] in docvint
        t['langs'][o.get('lang') or '?'] += 1
        t['value_len'].append(len(o['value']))
    analysis['taxonomy'] = collections.OrderedDict()
    for c, t in tax.items():
        n = max(t['observations'], 1)
        analysis['taxonomy'][c] = {
            'observations': t['observations'], 'artifacts': len(t['artifacts']), 'domains': len(t['domains']),
            'distinct_labels': len(t['labels']), 'top_labels': [l for l, _ in t['labels'].most_common(8)],
            'share_numeric': round(t['numeric'] / n, 3), 'share_in_pdfs': round(t['pdf'] / n, 3),
            'share_in_vintage_documents': round(t['in_vintage_docs'] / n, 3),
            'median_value_length': int(statistics.median(t['value_len'])) if t['value_len'] else 0,
            'langs': dict(t['langs'].most_common(5))}

    # Fiche families: technical-sheet PDFs grouped by their label sets.
    by_art = collections.defaultdict(set)
    for o in obs:
        if arts.get(o['artifact'], {}).get('media') == 'pdf':
            by_art[o['artifact']].add(key(o['label']))
    sheets = {s: ls for s, ls in by_art.items() if len(ls) >= 5}
    fam = []          # (domain, signature, [shas])
    for s in sorted(sheets):
        d = arts[s]['domains'][0]
        placed = False
        for F in fam:
            if F[0] == d:
                inter = len(F[1] & sheets[s])
                if inter / float(len(F[1] | sheets[s])) >= 0.5:
                    F[2].append(s)
                    placed = True
                    break
        if not placed:
            fam.append([d, set(sheets[s]), [s]])
    sizes = sorted((len(F[2]) for F in fam), reverse=True)
    per_dom = collections.Counter(F[0] for F in fam if len(F[2]) >= 3)
    multilang = sum(1 for F in fam if len({arts[s].get('lang_detected') for s in F[2]} - {None}) > 1)
    cross = collections.Counter()
    sig = collections.defaultdict(set)
    for F in fam:
        if len(F[2]) >= 3:
            sig[frozenset(sorted(F[1])[:12])].add(F[0])
    analysis['fiche_families'] = {
        'sheet_like_pdfs': len(sheets), 'families': len(fam), 'families_with_3_or_more': sum(1 for x in sizes if x >= 3),
        'largest_family_sizes': sizes[:15], 'domains_with_a_family_of_3_or_more': len(per_dom),
        'domains_with_several_families': sum(1 for n in per_dom.values() if n > 1),
        'families_spanning_languages': multilang,
        'label_sets_shared_by_several_domains': sum(1 for v in sig.values() if len(v) > 1)}

    # Language versions of one document: same folder and name but a language token.
    groups = collections.defaultdict(list)
    for s, r in arts.items():
        if r['media'] != 'pdf':
            continue
        u = r['first_url'].split('?')[0]
        folder, name = u.rsplit('/', 1)
        base = LANG_TOKEN.sub('#', re.sub(r'\.\w+$', '', name).replace('_', '-'))
        if base != re.sub(r'\.\w+$', '', name).replace('_', '-'):
            groups[(r['domains'][0], base)].append(s)
    pairs = {k: v for k, v in groups.items() if len(v) > 1}
    ANALYTIC = {'alc': re.compile(r'^(alcool|alcohol|degre|tav|酒精)'), 'ph': re.compile(r'^(ph|ph值)\b'),
                'yield': re.compile(r'^(rendement|yield)')}
    disagree = []
    obs_by = collections.defaultdict(list)
    for o in obs:
        obs_by[o['artifact']].append(o)
    for k, v in sorted(pairs.items()):
        vals = collections.defaultdict(set)
        for s in v:
            for o in obs_by.get(s, []):
                for name, rx in ANALYTIC.items():
                    if rx.search(key(o['label'])) and o.get('normalized'):
                        vals[name].add((s, round(o['normalized'][0]['number'], 2)))
        for name, sv in vals.items():
            nums = {n for _, n in sv}
            docs = {s for s, _ in sv}
            if len(docs) > 1 and len(nums) > 1:
                disagree.append({'domain': k[0], 'document': k[1][:80], 'field': name, 'values': sorted(nums)})
    analysis['language_versions'] = {
        'pdf_groups_differing_only_by_language_token': len(pairs),
        'pdfs_in_them': sum(len(v) for v in pairs.values()),
        'groups_with_analytical_disagreement': len(disagree), 'examples': disagree[:12]}

    # Legal entity statements.
    legal = collections.defaultdict(lambda: {'observations': 0, 'domains': set()})
    forms = collections.Counter()
    for o in obs:
        k = key(o['label'])
        for L in LEGAL_LABELS:
            if k == L or k.startswith(L + ' '):
                legal[L]['observations'] += 1
                for d in arts.get(o['artifact'], {}).get('domains', []):
                    legal[L]['domains'].add(d)
                for m in CF_.finditer(key(o['value'])):
                    forms[m.group(1)] += 1
    analysis['legal_entity'] = {
        'labels': {L: {'observations': v['observations'], 'domains': len(v['domains'])} for L, v in sorted(legal.items())},
        'company_forms_in_values': dict(forms.most_common(12)),
        'domains_with_any_legal_label': len(set().union(*[v['domains'] for v in legal.values()])) if legal else 0}

    # Shared sources: artifacts naming several estates, by kind of document.
    att = jl(DISC + 'attribution.jsonl')
    multi = [a for a in att if a['multi_estate']]
    analysis['shared_sources'] = {
        'multi_estate_artifacts': len(multi),
        'by_media': dict(collections.Counter(arts[a['artifact']]['media'] for a in multi)),
        'domains_serving_several_targets': sum(1 for d in T['domains'] if len(d['estates']) > 1),
        'artifacts_found_on_several_domains': sum(1 for r in arts.values() if len(r['domains']) > 1)}

    # The three proposals, the Averous case and the Graves whites, in full text.
    needles = ['echo de lynch', 'haut-bages averous', 'haut bages averous', 'terrasses de saint christophe',
               'murets de caillou', 'myosotis', 'lagrave-martillac', 'lacroix-martillac', 'les argileuses',
               'les rocheuses', 'bouscaut blanc', 'carbonnieux blanc', 'latour-martillac blanc',
               'malartic-lagraviere blanc', 'malartic lagraviere blanc', 'blanc de bouscaut',
               'chateau bouscaut blanc', 'chateau carbonnieux blanc']
    found = collections.defaultdict(lambda: {'artifacts': 0, 'mentions': 0, 'domains': collections.Counter(),
                                             'years': collections.Counter(), 'samples': []})
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        it = ex.map(_wanted, [(s, needles) for s in shas], chunksize=64)
        for s, r in zip(shas, it):
            if not r:
                continue
            for n, (cnt, ctxs) in r.items():
                F = found[n]
                F['artifacts'] += 1
                F['mentions'] += cnt
                for d in arts[s]['domains']:
                    F['domains'][d] += 1
                for y in (vc.get(s) or {}).get('url_years', []) + (vc.get(s) or {}).get('title_years', []):
                    F['years'][y] += 1
                if len(F['samples']) < SAMPLES:
                    F['samples'].append({'artifact': s[:16], 'url': arts[s]['first_url'][:140], 'context': ctxs[0]})
    analysis['named_cases'] = {n: {'artifacts': F['artifacts'], 'mentions': F['mentions'],
                                   'domains': dict(F['domains'].most_common(5)),
                                   'document_years': sorted(F['years']), 'samples': F['samples']}
                               for n, F in sorted(found.items())}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(analysis, ensure_ascii=False, indent=1) + '\n')
    print('scanned %d artifacts -> %s' % (len(res), OUT))


def _wanted(args):
    return wanted_text(*args)


if __name__ == '__main__':
    main()
