"""M3.6A-R1: what a fetched web page itself establishes - the web-page evidence rules (pure functions).

A web page is not a sheet. M3.6A found that the rules written for sheets, applied to a page's
flattened text, accept pages for what their furniture says: the site's name in the browser tab
("Le millésime 2019 | Château Bélair-Monange"), a related product ("Château Poitevin Blanc 2021"
on the page for Insula 2018), a sidebar of recent articles, an archive or listing page, a New Year
greeting, a range page. These rules read the page as a structure instead - the discovery
extraction (sources/discovery/extracted/<sha256>.json: its headings and its blocks, each block with
its tag and the headings above it) - and are additive to the M3.5 rubric, never a replacement:

  W1 identity    the page's own visible main heading (its first H1) is its identity. Never the
                 browser <title>, the URL, a file or folder name, the site's or domain's name.
  W2 separator   a heading split by a separator (|, –, —, a spaced hyphen) whose trailing part is a
                 site or estate name: that part is the site's name, not the wine's.
  W3 asset       a heading that names an image or other asset of a wine ("visuel bouteille ...",
                 "bottle - ...") names the wine only as fully as the words after the asset word do.
  W4 regions     identity and scope are read only in the page's content: the blocks after the main
                 heading, outside navigation, header, footer and list items, and outside any
                 sub-section that is an item card or an item list (its heading names a wine or a
                 year other than the page's own, or it holds two or more such headings) or a
                 recommendation, social, newsletter or sharing region. What such a region names is
                 recorded as an excluded match; it establishes nothing.
  W5 page type   decided before any mapping: WINE_DOCUMENT, ESTATE_PAGE, NEWS_ARTICLE, ARCHIVE_PAGE,
                 LISTING_PAGE, RANGE_PAGE, GREETING_EVENT_PAGE, OTHER_WEB_PAGE. Only a WINE_DOCUMENT -
                 a main heading that is a model wine's exact name, with or without its year and its
                 colour - can establish a wine.
  W6 the rubric  on a WINE_DOCUMENT, M3.5's rules hold unchanged over the content region: exact
                 name (T2), the vintage from the heading or a labelled field, never a date (T4),
                 no other wine of the estate (T5), no other vintages heading the page, the colour
                 (T6), open identity decisions (T7).

judge_page() returns the disposition with the structured facts behind it: page type, identity
source, identity region, vintage source, excluded-region matches and the ambiguity reason.
"""
import json
import os
import re

import m35_rubric as RB

PAGE_TYPES = ['WINE_DOCUMENT', 'ESTATE_PAGE', 'NEWS_ARTICLE', 'ARCHIVE_PAGE', 'LISTING_PAGE', 'RANGE_PAGE',
              'GREETING_EVENT_PAGE', 'OTHER_WEB_PAGE']
SEPARATOR = re.compile(r'\s+[|–—]\s+|\s+-\s+|\s*\|\s*')
YEAR = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')
COLOURS = {'blanc': 'WHITE', 'white': 'WHITE', 'rouge': 'RED', 'red': 'RED', 'rose': 'ROSE'}
ASSET = re.compile(r'^(?:visuel(?:\s+de)?(?:\s+la)?\s+bouteille|visuel|bouteille|bottle|packshot|etiquette|label|photo|image)\b\s*')
# a region's heading that says what kind of region it is - recommendation, navigation, social,
# sharing, newsletter, comments: secondary to the structural test (item cards, item lists)
OFF_CONTENT = re.compile(
    r'\b(?:you may also|vous aimerez|vous pourriez|related|similaires?|apparentes?|recommand|a decouvrir|decouvrir|'
    r'discover|nos autres|our other|other vintages|autres millesimes|autres vins|voir aussi|see also|recent|recents?|'
    r'articles?\s+recents?|derniers? articles?|latest|categories|tags?\b|archives?|partager|share|suivez|follow|'
    r'newsletter|commentaires?|comments?|laisse[rz]? (?:ton|votre) commentaire|panier|cart)\b')
GREETING = re.compile(
    r'\b(?:happy new year|bonne annee|meilleurs? v(?:oe|œ)ux|season.s greetings|joyeux noel|merry christmas|'
    r'joyeuses fetes|happy holidays|guinguette|portes? ouvertes?|open days?|salon|festival|concert|soiree|'
    r'invitation|evenements?|events?|journees? du patrimoine)\b')
DATED = re.compile(r'\b\d{1,2}(?:er)?\s+(?:%s)\b|\b\d{1,2}\s*h\s*\d{0,2}\b' % RB.MONTHS)
ARCHIVE = re.compile(r'^(?:(?:les|la|le|l|nos|our|the) )?(?:archives?|actualites|news|blog|presse|press|press room|espace presse|categorie|category|'
                     r'tag|articles?|journal)\b')
LISTING = re.compile(r'^(?:(?:les|la|le|l|the) )?(?:nos vins|our wines|les vins|the wines|boutique|shop|e-?shop|store|produits|products|'
                     r'acheter|buy|nos cuvees|our cuvees|gamme|range)\b')
ESTATE_WIDE = re.compile(r'\b(?:le millesime|the \d{4} vintage|millesime \d{4}|vintage \d{4}|vendanges?|harvest|'
                         r'recolte|rapport|report|bilan|meteo|weather|growing season)\b')
PRESS = re.compile(r'\b\d{2,3}\s*(?:\+|pts?\b|points\b|/\s*100\b|/\s*20\b)|\b\d{2,3}\s*[-–]\s*\d{2,3}\b|\btop \d+\b'
                   r'|\bpresse?\b|\bpress\b|\bguide\b')
ARTICLE_TYPES = {'Article', 'NewsArticle', 'BlogPosting', 'Event', 'WebPage'}
SKIP_TAGS = {'nav', 'header', 'footer', 'li', 'option', 'label', 'form', 'button', 'select'}
SHEET = re.compile(r'\b(?:cepages?|assemblage|blend|grape varieties|alcool|alcohol|degustation|tasting note|vinification|elevage)\b')
# a labelled field, not a sentence: "Millésime : 2019", or a block that is only the label and the year
# ("le millésime 2014 ..." in prose is no field - found in review: Sigalas-Rabaud)
LABELLED_VINTAGE = re.compile(r'(?:^|\n)\s*(?:millesime|vintage|annee|year)\s*(?::\s*((?:19|20)\d\d)\b|\s((?:19|20)\d\d)\s*(?:$|\n))')


def load(sha, root):
    p = os.path.join(root, 'sources', 'discovery', 'extracted', sha + '.json')
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding='utf-8'))
    return d if d.get('status') == 'EXTRACTED' and d.get('media') == 'html' else None


def _n(s):
    return RB.norm_name(s)


def site_names(ext, estate_names):
    """Names the site goes by: every model estate's name, and what the page's own metadata calls the site."""
    out = {_n(n) for n in estate_names if n}
    meta = ext.get('meta') or {}
    items = meta.items() if isinstance(meta, dict) else (meta if isinstance(meta, list) else [])
    for k, v in items:
        if str(k).lower() in ('og:site_name', 'application-name', 'apple-mobile-web-app-title') and v:
            out.add(_n(str(v)))
    return {s for s in out if s}


def identity(ext, sites):
    """W1-W3: the page's main heading, read: {heading, source, name, year, colour, asset, site_suffix}."""
    h1 = [h.get('text') or '' for h in ext.get('headings') or [] if h.get('level') == 1 and (h.get('text') or '').strip()]
    if not h1:
        return {'heading': None, 'source': 'none', 'name': None, 'year': None, 'colour': None, 'asset': False,
                'site_suffix': None}
    # split before folding: folding drops the dashes that separate a heading from the site's name
    parts = [RB.fold(p).strip() for p in SEPARATOR.split(h1[0].strip()) if RB.fold(p).strip()]
    suffix = None
    while len(parts) > 1 and _n(parts[-1]) in sites:          # W2: the trailing site or estate name
        suffix = parts.pop()
    asset = False
    if parts and ASSET.match(parts[0]):                        # W3: an asset of the wine
        asset = True
        rest = ASSET.sub('', parts[0]).strip()
        parts = ([rest] if rest else []) + parts[1:]
    text = ' '.join(parts)
    years = YEAR.findall(text)
    name = _n(YEAR.sub(' ', text))
    colour = None
    words = name.split()
    if words and words[-1] in COLOURS:
        colour = COLOURS[words[-1]]
        name = ' '.join(words[:-1])
    return {'heading': h1[0].strip(), 'source': 'h1', 'name': name, 'year': int(years[0]) if len(years) == 1 else None,
            'years': [int(y) for y in years], 'colour': colour, 'asset': asset, 'site_suffix': suffix}


def _names_wine(text, by_name):
    """A heading that names a model wine, or reads like a wine's name (a strong wine word, then a name)."""
    n = _n(YEAR.sub(' ', text))
    return n in by_name or bool(re.match(r'(?:chateau|clos|domaine|cuvee?)\s+\S', n) and len(n.split()) <= 8)


def _item_like(text, by_name):
    """An entry of a list of wines: it names a wine, or carries a year, or a chateau within it."""
    return _names_wine(text, by_name) or bool(YEAR.search(text)) or ' chateau ' in ' %s ' % _n(text)


def full_heading(b):
    """A heading block's whole text. The extractor can keep only the part of a heading after an inline
    element ("les vins de Paloumey" of "Découvrir les vins de Paloumey"); the heading path, whose last
    segment is the heading itself, keeps all of it."""
    text = (b.get('text') or '').strip()
    last = ((b.get('path') or '').split(' > ') or [''])[-1].strip()
    return last if text and last and text in last else text


def regions(ext, ident, by_name):
    """W4: (content blocks, excluded matches). Blocks are walked in order; before the main heading is
    navigation; a sub-section is excluded with every block under it until a heading of its level or above."""
    blocks = ext.get('blocks') or []
    content, excluded = [], []
    started = False
    off = None                                                 # (level, why) of the excluded section in force
    own_year = ident.get('year')
    own_name = ident.get('name')
    heads = [b for b in blocks if re.fullmatch(r'h[1-6]', b.get('tag') or '')]
    for b in blocks:
        tag = b.get('tag') or ''
        text = full_heading(b) if re.fullmatch(r'h[1-6]', tag) else (b.get('text') or '')
        f = RB.fold(text).strip()
        if not started:
            if tag == 'h1' and ident.get('heading') and text.strip() and (
                    text.strip() == ident['heading'] or text.strip() in ident['heading']):
                started = True
                content.append(b)
            else:
                excluded.append((b, 'before the main heading: navigation, header or sidebar'))
            continue
        if re.fullmatch(r'h[2-6]', tag):
            lvl = int(tag[1])
            if off and lvl <= off[0]:
                off = None
            if off is None:
                why = None
                ys = {int(y) for y in YEAR.findall(f)}
                if OFF_CONTENT.search(f):
                    why = 'a recommendation, navigation or sharing region ("%s")' % text.strip()[:60]
                elif _names_wine(f, by_name) and (_n(YEAR.sub(' ', f)) != own_name or (ys and own_year and ys != {own_year})):
                    why = 'an item card naming another wine or vintage ("%s")' % text.strip()[:60]
                elif ys and own_year and ys - {own_year} and _names_wine(f, by_name):
                    why = 'an item card naming another vintage ("%s")' % text.strip()[:60]
                else:
                    # an item list: two or more sub-headings below it naming wines or years
                    sub = []
                    for h in heads[heads.index(b) + 1:] if b in heads else []:
                        hl = int(h['tag'][1])
                        if hl <= lvl:
                            break
                        hf = RB.fold(full_heading(h))
                        if _item_like(hf, by_name):
                            sub.append(h)
                    if len(sub) >= 2:
                        why = 'an item list (%d entries under "%s")' % (len(sub), text.strip()[:40])
                if why:
                    off = (lvl, why)
            if off:
                excluded.append((b, off[1]))
                continue
            content.append(b)
            continue
        if off:
            excluded.append((b, off[1]))
        elif tag in SKIP_TAGS:
            excluded.append((b, 'a list item, navigation, header, footer or form control'))
        else:
            content.append(b)
    return content, excluded


def page_type(ext, ident, content, by_name, sites, excluded=()):
    """W5: what kind of page this is, from its main heading and its content."""
    name = ident.get('name') or ''
    heading = RB.fold(ident.get('heading') or '')
    if not ident.get('heading'):
        return 'OTHER_WEB_PAGE', 'the page has no main heading'
    if name in by_name:
        return 'WINE_DOCUMENT', 'the main heading is a wine\'s exact name'
    if GREETING.search(heading) or DATED.search(heading):
        return 'GREETING_EVENT_PAGE', 'the main heading is a greeting or an event'
    # the page's entries: its own sub-headings, and the item cards and item lists set aside as regions
    items = [b for b in content[1:] if re.fullmatch(r'h[2-6]', b.get('tag') or '')]
    items += [b for b, why in excluded if why.startswith('an item') and re.fullmatch(r'h[2-6]', b.get('tag') or '')]
    wine_items = {_n(YEAR.sub(' ', RB.fold(full_heading(b)))) for b in items if _item_like(RB.fold(full_heading(b)), by_name)}
    if ARCHIVE.match(_n(heading)):
        return 'ARCHIVE_PAGE', 'the main heading names an archive, a news or press index'
    if LISTING.match(_n(heading)) and len(wine_items) < 2:
        return 'LISTING_PAGE', 'the main heading names a shop or wine listing'
    if len(wine_items) >= 2 or (LISTING.match(_n(heading)) and wine_items):
        return 'RANGE_PAGE', 'the page lists %d wines' % len(wine_items)
    if name in sites or ESTATE_WIDE.search(heading):
        return 'ESTATE_PAGE', 'the main heading names the estate, or a vintage or harvest generally'
    types = set()
    for j in ext.get('jsonld') or []:
        t = j.get('@type') if isinstance(j, dict) else None
        types |= set(t if isinstance(t, list) else [t]) if t else set()
    prose = [b for b in content if b.get('tag') == 'p' and len(b.get('text') or '') >= 120]
    if PRESS.search(heading) or types & (ARTICLE_TYPES - {'WebPage'}):
        return 'NEWS_ARTICLE', 'an article: a press or score heading, or an article\'s metadata'
    # a wine's own page for a wine the model does not list: a short name and one year as the heading, and
    # the content of a wine's sheet (its grapes, blend, alcohol, tasting)
    sheet = SHEET.search(RB.fold(' '.join(b.get('text') or '' for b in content[1:])))
    if ident.get('year') and len(ident.get('years') or []) == 1 and 1 <= len(name.split()) <= 5 and sheet:
        return 'WINE_DOCUMENT', 'the main heading is a wine and a year, the content a wine\'s sheet (a wine the model does not list)'
    if prose:
        return 'NEWS_ARTICLE', 'an article: prose under a heading that names no wine'
    return 'OTHER_WEB_PAGE', 'the main heading names no wine'


def judge_page(ext, claim, wines, estate_wines, blocked, estate_names):
    """The review of one claim {estate, wine, vintage} on one fetched web page. Returns
    {disposition, basis, page_type, identity_source, identity, identity_region, vintage_source,
     excluded_region_match, ambiguity_reason}. Dispositions are M3.6A's."""
    by_name = {}
    for wid, (n, _) in wines.items():
        by_name.setdefault(_n(n), set()).add(wid)
    sites = site_names(ext, estate_names)
    ident = identity(ext, sites)
    content, excluded = regions(ext, ident, by_name)
    ptype, why_type = page_type(ext, ident, content, by_name, sites, excluded)
    e, w, y = claim['estate'], claim['wine'], claim['vintage']
    wname, wtype = wines.get(w, ('', None))
    ex = sorted({'%s: %s' % (why, (b.get('text') or '').strip()[:60]) for b, why in excluded
                 if YEAR.search(b.get('text') or '') and (str(y) in (b.get('text') or '') or
                                                       _n(wname) in _n(b.get('text') or ''))})
    out = {'page_type': ptype, 'page_type_basis': why_type, 'identity_source': ident['source'],
           'identity': {k: ident[k] for k in ('heading', 'name', 'year', 'colour', 'asset', 'site_suffix')},
           'identity_region': 'main heading (H1)' if ident['heading'] else None, 'vintage_source': None,
           'excluded_region_match': ex[:6], 'ambiguity_reason': None}

    def done(disp, basis, reason=None):
        out.update(disposition=disp, basis=basis, ambiguity_reason=reason)
        return out

    if w in blocked:
        return done('IDENTITY_BLOCKED', 'open identity decision %s governs %s' % (blocked[w], wname), 'open decision')
    if ptype in ('ARCHIVE_PAGE', 'LISTING_PAGE', 'GREETING_EVENT_PAGE'):
        return done('NOT_RELEVANT', 'a %s (%s): it establishes no wine' % (ptype.lower().replace('_', ' '), why_type), ptype)
    if ptype == 'RANGE_PAGE':
        return done('MULTI_WINE_AMBIGUOUS', 'a range page (%s): no one wine is the page\'s' % why_type, 'range page')
    if ptype == 'ESTATE_PAGE':
        return done('ESTATE_ONLY', 'an estate-wide page ("%s"): the wine is not established' % ident['heading'][:70],
                    'estate identity is not wine identity')
    if ptype == 'NEWS_ARTICLE':
        return done('EVIDENCE_INSUFFICIENT', 'a news article ("%s") whose main heading is not a wine\'s exact name'
                    % ident['heading'][:70], 'incidental mention')
    if ptype == 'OTHER_WEB_PAGE':
        return done('EVIDENCE_INSUFFICIENT', 'the page establishes no wine (%s)' % why_type, why_type)
    # a WINE_DOCUMENT: W6, the M3.5 rubric over the content region
    if w not in by_name.get(ident['name'], set()):
        other = sorted(by_name.get(ident['name'], set()))
        return done('NOT_RELEVANT', 'the page is %s, not %s' % (wines[other[0]][0] if other else ident['name'], wname),
                    'another wine')
    if ident['year']:
        out['vintage_source'] = 'main heading'
        if ident['year'] != y:
            return done('NOT_RELEVANT', 'the page is %s %d, not %d' % (wname, ident['year'], y), 'another vintage')
    else:
        body = '\n'.join(RB.fold(b.get('text') or '') for b in content[1:])
        lab = {int(a or b) for a, b in LABELLED_VINTAGE.findall(body)}
        if lab == {y}:
            out['vintage_source'] = 'labelled field in the content'
        elif len(ident.get('years') or []) > 1:
            return done('VINTAGE_AMBIGUOUS', 'the main heading states several years', 'several years in the heading')
        else:
            return done('VINTAGE_AMBIGUOUS', 'neither the main heading nor a labelled field states %d' % y, 'no vintage')
    body = '\n'.join(b.get('text') or '' for b in content[1:])
    fb = RB.fold(body)
    others = sorted(s for s in estate_wines.get(e, []) if s != w and _n(wines[s][0]) and
                    re.search(r'(?<![a-z])%s(?![a-z])' % re.escape(_n(wines[s][0])), _n(body)))
    if others:
        return done('MULTI_WINE_AMBIGUOUS', 'the content also names %s' % ', '.join(wines[s][0] for s in others), 'another wine of the estate')
    vheads = sorted({int(v) for b in content[1:] if re.fullmatch(r'h[2-6]', b.get('tag') or '')
                     for v in YEAR.findall(full_heading(b))} - {y})
    if len(vheads) >= 2:
        return done('VINTAGE_AMBIGUOUS', 'the content heads other vintages (%s)' % ', '.join(map(str, vheads[:5])), 'several vintages')
    m = RB.OTHER_WINE.search(fb[:600])
    if m:
        return done('ROLE_AMBIGUOUS', 'the content speaks of another wine ("%s")' % m.group(0), 'role')
    # T6: a colour the heading names is a colour variant - it must be the wine's, which the model must hold;
    # a blend's colour may only not contradict it (as for a sheet)
    c = ident['colour']
    if c and wtype in (None, 'UNKNOWN'):
        return done('COLOUR_AMBIGUOUS', 'the main heading names the %s, and the model does not hold %s\'s colour'
                    % (c.lower(), wname), 'colour not held')
    c = c or RB.blend_colour(body)
    if c and wtype not in (None, 'UNKNOWN') and (wtype == 'RED') != (c == 'RED'):
        return done('COLOUR_AMBIGUOUS', 'a %s wine, and the page is the %s' % (wtype.lower(), c.lower()), 'colour')
    return done('SAFE_TO_MAP', 'the main heading "%s" is %s %d%s; no other wine of the estate in the content'
                % (ident['heading'][:70], wname, y, ' (%s)' % c.lower() if c else ''))
