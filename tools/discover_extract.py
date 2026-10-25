# -*- coding: utf-8 -*-
"""Phase 3.3: what the harvested bytes say, kept as it is said.

    python -I tools/discover_extract.py [--workers N]

Reads every artifact the crawl stored (data/discovery/locations/*.jsonl ->
sources/discovery/blobs/) and writes:

  sources/discovery/extracted/<sha256>.json   the readable representation:
      title, headings, text blocks, tables, links, images (src, alt,
      caption), metadata, JSON-LD, page texts for PDFs. Local only: it is
      the estates' text.
  data/discovery/artifacts.jsonl              one row per artifact
  data/discovery/observations/<aa>.jsonl      label/value statements
  data/discovery/years.jsonl                  year mentions, by kind of context
  data/discovery/roles.jsonl                  role wording, quoted
  data/discovery/wines.jsonl                  wine-name candidates
  data/discovery/attribution.jsonl            attribution candidates

Nothing here imposes a schema. A label is the source's label, verbatim; a
value is the source's value, verbatim (capped in length, the full text
staying in the local extracted file); a normalisation is recorded only
alongside the raw value, and only where it is lossless. `category` is a
keyword guess for the discovery report, marked INFERRED.

The output is a pure function of the stored bytes and the location logs:
no clock, no network, sorted. Running it twice gives the same files.
"""
import argparse
import collections
import concurrent.futures as cf
import hashlib
import html
import io
import json
import os
import re
import sys
import unicodedata
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
EXTRACTOR = 'discover-extract/1.0'
STORE = ROOT + 'sources/discovery/'
OUT = ROOT + 'data/discovery/'
VALUE_CAP = 200

# ---------------------------------------------------------------- lexicons
# Detectors, not a schema: they decide which short lines look like labels
# and give the report a first, INFERRED, grouping. The observation keeps
# the source's own label.
CATEGORY_WORDS = collections.OrderedDict([
    ('APPELLATION', r'appellation|aoc|aop|a\.o\.c|denomination'),
    ('CLASSIFICATION', r'classement|classification|class[eé]|cru bourgeois|grand cru|growth|cru artisan'),
    ('VINEYARD', r'superficie|surface|hectare|vignoble|vineyard|parcel|terroir|sol|sols|soil|sous-sol|'
                 r'subsoil|g[eé]olog|exposition|exposure|altitude|elevation|densit|density|plantation|'
                 r'planting|[aâ]ge (moyen )?des vignes|vine age|age of (the )?vines|porte-greffe|rootstock|'
                 r'taille|pruning|enherbement|c[eé]page|grape variet|encépagement|encepagement|varietals?'),
    ('VINTAGE', r'mill[eé]sime|vintage|climat|weather|m[eé]t[eé]o|saison|season|vendange|harvest|'
                r'r[eé]colte|floraison|flowering|v[eé]raison|rendement|yield|production'),
    ('WINEMAKING', r'vinification|winemaking|fermentation|mac[eé]ration|cuvaison|extraction|cuves?|'
                   r'vats?|tanks?|levures?|yeast|temp[eé]rature|[eé]levage|ageing|aging|barriques?|barrels?|'
                   r'f[uû]ts?|oak|ch[eê]ne|b[eé]ton|concrete|amphor|mise en bouteille|bottling|assemblage|'
                   r'blend|collage|fining|filtration|soutirage|racking'),
    ('ANALYTICAL', r'alcool|alcohol|degr[eé]|tav|ph\b|acidit|acidity|sucres?|sugar|volatil|so2|'
                   r'sulfit|sulphit|iph|ipt|tannin'),
    ('TASTING', r'd[eé]gustation|tasting|robe|couleur|colou?r|nez|nose|bouche|palate|finale|finish|'
                r'ar[oô]mes?|aromas?|notes? de|commentaire'),
    ('SERVICE', r'service|serving|temp[eé]rature de service|carafe|decant|garde|ageing potential|'
                r'apog[eé]e|drink|accords?|pairing|food'),
    ('PRODUCTION', r'production|bouteilles|bottles|formats?|magnum|caisses?|cases|quantit'),
    ('COMMERCIAL', r'prix|price|tarif|disponib|availability|commande|order|distribut|n[eé]goce|'
                   r'place de bordeaux|primeur'),
    ('SUSTAINABILITY', r'bio\b|biolog|organic|biodynam|hve|haute valeur|certifi|terra vitis|'
                       r'environnement|environment|biodiversit|[eé]nergie|energy|eau\b|water|'
                       r'emballage|packaging|ecocert|demeter|agriculture raisonn'),
    ('OWNERSHIP', r'propri[eé]taire|owner|propri[eé]t[eé] de|famille|family|g[eé]rant|director|'
                  r'directeur|acquis|acquired|rachat|group'),
    ('PEOPLE', r'[oœ]nologue|oenologist|winemaker|ma[iî]tre de chai|cellar master|consultant|'
               r'chef de culture|vineyard manager|r[eé]gisseur'),
    ('HISTORY', r'histoire|history|historique|fond[eé]|founded|cr[eé][eé] en|since|depuis|origine'),
    ('IDENTITY', r'nom|name|ch[aâ]teau|propri[eé]t[eé]|estate|domaine|adresse|address|commune|'
                 r'contact|t[eé]l|phone|e-?mail|site'),
    ('PRESS', r'presse|press|notes?|scores?|parker|suckling|decanter|vinous|robinson|wine spectator|'
              r'wine advocate|bettane|gault|guide hachette|m[eé]daille|medal'),
])
CAT_RE = [(c, re.compile(r'(?i)\b(?:%s)' % p)) for c, p in CATEGORY_WORDS.items()]
# The label-line detector uses only the technical vocabularies: identity,
# press, history, ownership and commercial words start too many lines that
# are names, menus and addresses rather than labels.
LABELISH = re.compile(r'(?i)^(?:%s)\b' % '|'.join(
    CATEGORY_WORDS[c] for c in ('APPELLATION', 'CLASSIFICATION', 'VINEYARD', 'VINTAGE',
                                'WINEMAKING', 'ANALYTICAL', 'PRODUCTION', 'SERVICE')))
ROLE_WORDS = re.compile(
    r"(?i)\b(second(?:e)?s? vins?|second wines?|second labels?|second grand vin|deuxi[eè]me vin|"
    r"troisi[eè]me vin|third wines?|grand vin(?: blanc(?: sec)?| rouge| liquoreux)?|premier vin|"
    r"first wine|vin blanc sec|blanc sec|dry white(?: wine)?|vin liquoreux|liquoreux|sweet (?:white )?wine|"
    r"cuv[eé]e sp[eé]ciale|cuv[eé]e prestige|special cuv[eé]e|petit fr[eè]re|little brother|"
    r"zweitwein|second vin blanc sec|cl[eé] de vo[uû]te)\b")
# Not inside a longer number or a decimal; a year after '-', '_' or '/'
# is the common filename and URL case (fiche-2019.pdf, /2019/).
YEAR = re.compile(r'(?<![\d.,])(1[89]\d\d|20[0-3]\d)(?![\d%])')
YEAR_KIND = [
    ('HARVEST_OR_VINTAGE', re.compile(r"(?i)(mill[eé]sime|vintage|vendange|harvest|r[eé]colte|"
                                      r"jahrgang|cosecha|annata)")),
    ('OWNERSHIP', re.compile(r'(?i)(acqui|achet|rachet|rachat|bought|purchas|owner|propri[eé]taire|'
                             r'famille|family|h[eé]rit|inherit|depuis|since)')),
    ('CLASSIFICATION', re.compile(r'(?i)(class[eé]|classement|classification|grand cru|growth|cru bourgeois)')),
    ('FOUNDING_OR_HISTORY', re.compile(r'(?i)(fond[eé]|founded|cr[eé]|construit|built|si[eè]cle|century|'
                                       r'histoire|history|origine|origin)')),
]
NUM = re.compile(r'(\d+(?:[.,]\d+)?)\s*(%\s*vol|% ?vol\.?|%|hl\s*/\s*ha|hl/ha|hectolitres?|ha\b|hectares?|'
                 r'mois|months?|ans|years?|°\s*c|°c|g\s*/\s*l|g/l|m[eè]tres?|m\b|bouteilles|bottles|'
                 r'pieds\s*/\s*ha|vines?/ha|plants?/ha|jours|days)', re.I)

LANG_WORDS = {
    'fr': ' le la les des du de et est un une pour avec dans sur sont vin vins château notre nos ',
    'en': ' the and of to in is with for our are wine wines this from that ',
    'de': ' der die das und ist mit für wein den des ein eine von ',
    'nl': ' de het een en van is met voor wijn zijn op ',
    'es': ' el la los las y de es con para vino del una ',
    'it': ' il la le e di che con per vino del una sono ',
    'pt': ' o a os as e de do da com para vinho uma ',
}
LANG_SETS = {k: set(v.split()) for k, v in LANG_WORDS.items()}


def detect_lang(text):
    if not text or len(text) < 40:
        return None
    sample = text[:6000]
    cjk = sum(1 for c in sample if '一' <= c <= '鿿')
    kana = sum(1 for c in sample if '぀' <= c <= 'ヿ')
    cyr = sum(1 for c in sample if 'Ѐ' <= c <= 'ӿ')
    if kana > 20:
        return 'ja'
    if cjk > 40:
        return 'zh'
    if cyr > 40:
        return 'ru'
    words = re.findall(r"[a-zà-ÿ]+", sample.lower())
    if len(words) < 8:
        return None
    sc = {k: sum(1 for w in words if w in s) for k, s in LANG_SETS.items()}
    best = max(sc, key=lambda k: sc[k])
    second = sorted(sc.values())[-2]
    if sc[best] < 4 or sc[best] < 1.3 * second:
        return None
    return best


def fold(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(c for c in s if not unicodedata.combining(c))


def key(s):
    k = fold(s).lower().replace('’', "'")
    k = re.sub(r'[^a-z0-9]+', ' ', k)
    return ' '.join(k.split())


def clean(s):
    return ' '.join((s or '').replace(' ', ' ').split())


def categories(label):
    return [c for c, rx in CAT_RE if rx.search(label)]


def normalise(value):
    """Numbers with units, only as found; the raw value stays beside."""
    out = []
    for m in NUM.finditer(value):
        try:
            n = float(m.group(1).replace(',', '.'))
        except ValueError:
            continue
        out.append({'number': n, 'unit': re.sub(r'\s+', '', m.group(2).lower())})
    return out[:6]


# ---------------------------------------------------------------- HTML
def parse_html(data):
    from html.parser import HTMLParser
    BLOCK = {'p', 'div', 'li', 'td', 'th', 'dt', 'dd', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br',
             'tr', 'section', 'article', 'header', 'footer', 'table', 'ul', 'ol', 'figcaption',
             'blockquote', 'pre', 'address', 'main', 'aside', 'nav', 'form', 'label', 'option'}
    rep = {'title': '', 'lang_declared': None, 'meta': {}, 'canonical': None, 'headings': [],
           'blocks': [], 'tables': [], 'links': [], 'images': [], 'jsonld': [], 'dl': []}
    state = {'skip': 0, 'buf': [], 'heading': None, 'path': [], 'table': None, 'row': None,
             'cell': None, 'a': None, 'title': False, 'script': None, 'dt': None,
             'in': collections.Counter(), 'fig': None}

    def flush(tag=None):
        t = clean(''.join(state['buf']))
        state['buf'] = []
        if t:
            rep['blocks'].append({'text': t, 'path': ' > '.join(state['path'][-3:]),
                                  'tag': tag or ''})

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            state['in'][tag] += 1
            if tag in ('script', 'style', 'noscript', 'template', 'svg'):
                if tag == 'script' and (a.get('type') or '').lower() == 'application/ld+json':
                    state['script'] = []
                state['skip'] += 1
                return
            if tag == 'html' and a.get('lang'):
                rep['lang_declared'] = a['lang']
            if tag == 'title':
                state['title'] = True
            if tag == 'meta':
                k = a.get('property') or a.get('name') or a.get('itemprop')
                if k and a.get('content') and len(rep['meta']) < 80:
                    rep['meta'].setdefault(k.lower(), clean(a['content'])[:500])
            if tag == 'link' and (a.get('rel') or '').lower() == 'canonical' and a.get('href'):
                rep['canonical'] = a['href']
            if tag in BLOCK:
                flush(tag)
            if re.match(r'h[1-6]$', tag):
                state['heading'] = [int(tag[1]), []]
            if tag == 'table':
                state['table'] = []
            if tag == 'tr' and state['table'] is not None:
                state['row'] = []
            if tag in ('td', 'th') and state['row'] is not None:
                state['cell'] = []
            if tag == 'dt':
                state['dt'] = []
            if tag == 'a' and a.get('href'):
                state['a'] = [a['href'], []]
            if tag == 'img':
                src = a.get('src') or a.get('data-src') or a.get('data-lazy-src')
                if src:
                    rep['images'].append({'src': src, 'alt': clean(a.get('alt'))[:200],
                                          'title': clean(a.get('title'))[:200], 'caption': None})
            if tag == 'figure':
                state['fig'] = len(rep['images'])

        def handle_endtag(self, tag):
            if tag in ('script', 'style', 'noscript', 'template', 'svg'):
                if state['script'] is not None and tag == 'script':
                    rep['jsonld'].append(''.join(state['script'])[:20000])
                    state['script'] = None
                state['skip'] = max(0, state['skip'] - 1)
                return
            if tag == 'title':
                state['title'] = False
            if re.match(r'h[1-6]$', tag) and state['heading']:
                lvl, parts = state['heading']
                t = clean(''.join(parts))
                if t:
                    rep['headings'].append({'level': lvl, 'text': t[:300]})
                    state['path'] = state['path'][:lvl - 1] + [t[:80]]
                state['heading'] = None
            if tag in ('td', 'th') and state['cell'] is not None and state['row'] is not None:
                state['row'].append(clean(''.join(state['cell']))[:500])
                state['cell'] = None
            if tag == 'tr' and state['row'] is not None and state['table'] is not None:
                if any(state['row']):
                    state['table'].append(state['row'])
                state['row'] = None
            if tag == 'table' and state['table'] is not None:
                if state['table']:
                    rep['tables'].append({'rows': state['table'][:200],
                                          'path': ' > '.join(state['path'][-3:])})
                state['table'] = None
            if tag == 'dt' and state['dt'] is not None:
                state['dt_text'] = clean(''.join(state['dt']))
                state['dt'] = None
            if tag == 'a' and state['a']:
                rep['links'].append({'href': state['a'][0],
                                     'text': clean(''.join(state['a'][1]))[:200]})
                state['a'] = None
            if tag == 'figure':
                state['fig'] = None
            if tag in BLOCK:
                flush(tag)

        def handle_data(self, d):
            if state['skip']:
                if state['script'] is not None:
                    state['script'].append(d)
                return
            if state['title']:
                rep['title'] += d
                return
            state['buf'].append(d)
            if state['heading']:
                state['heading'][1].append(d)
            if state['cell'] is not None:
                state['cell'].append(d)
            if state['dt'] is not None:
                state['dt'].append(d)
            if state['a']:
                state['a'][1].append(d)
            if state['in']['figcaption'] and state['fig'] is not None and state['fig'] < len(rep['images']):
                img = rep['images'][-1]
                img['caption'] = clean((img['caption'] or '') + ' ' + d)[:300]

    p = P(convert_charrefs=True)
    text = decode(data)
    try:
        p.feed(text)
        p.close()
    except Exception as e:
        rep['parse_error'] = str(e)[:200]
    flush()
    rep['title'] = clean(rep['title'])[:500]
    # dt/dd pairs, read back from the block sequence (dt then dd blocks)
    for i, b in enumerate(rep['blocks'][:-1]):
        if b['tag'] == 'dt' and rep['blocks'][i + 1]['tag'] == 'dd':
            rep['dl'].append([b['text'][:120], rep['blocks'][i + 1]['text']])
    rep['blocks'] = rep['blocks'][:3000]
    rep['links'] = rep['links'][:3000]
    rep['images'] = rep['images'][:500]
    return rep


def decode(data):
    m = re.search(rb'charset=["\']?([A-Za-z0-9_-]+)', data[:4096])
    for enc in ([m.group(1).decode('ascii', 'ignore')] if m else []) + ['utf-8', 'cp1252']:
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode('utf-8', 'replace')


# ---------------------------------------------------------------- PDF etc.
def parse_pdf(data):
    import pymupdf
    rep = {'pages': [], 'page_count': None, 'meta': {}, 'ocr': 'NOT_ATTEMPTED'}
    doc = pymupdf.open(stream=data, filetype='pdf')
    rep['page_count'] = len(doc)
    rep['meta'] = {k: clean(str(v))[:300] for k, v in (doc.metadata or {}).items() if v}
    for i, page in enumerate(doc):
        if i >= 60:
            rep['truncated_pages'] = True
            break
        rep['pages'].append(page.get_text())
    chars = sum(len(t.strip()) for t in rep['pages'])
    if rep['page_count'] and chars < 40 * min(rep['page_count'], 60):
        # Text-sparse: an image PDF. OCR needs an engine this machine does
        # not have (no tesseract); recorded, the original kept.
        rep['ocr'] = 'NEEDED_NO_ENGINE'
    return rep


def parse_office(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    parts = [n for n in z.namelist() if re.match(r'(word/document|xl/sharedStrings|ppt/slides/slide\d+|'
                                                  r'content)\.xml$', n)]
    texts = []
    for n in sorted(parts)[:50]:
        x = z.read(n).decode('utf-8', 'replace')
        x = re.sub(r'</(w:p|a:p|si|text:p)>', '\n', x)
        texts.append(html.unescape(re.sub(r'<[^>]+>', '', x)))
    return {'pages': texts, 'page_count': len(texts)}


# ---------------------------------------------------------------- statements
LV = re.compile(r'^\s*([^\n:：]{2,48}?)\s*[:：]\s*(\S.{0,400})$')


def label_ok(label):
    l = clean(label)
    if not l or len(l) > 48 or len(l.split()) > 6:
        return False
    if re.search(r'(https?|www\.|@|\{|\}|=)', l) or not re.search(r'[A-Za-zÀ-ɏ一-鿿]', l):
        return False
    if re.match(r'^\d', l):
        return False
    return True


def statements(lines, locus_prefix):
    """Label/value statements from a sequence of text lines."""
    out = []
    for i, line in enumerate(lines):
        line = clean(line)
        if not line:
            continue
        m = LV.match(line)
        if m and label_ok(m.group(1)):
            out.append((m.group(1).strip(), m.group(2).strip(), '%s:l%d' % (locus_prefix, i),
                        'LABEL_COLON', 'MEDIUM'))
            continue
        # A short label line the lexicon recognises, then its value line.
        if (i + 1 < len(lines) and len(line) <= 40 and len(line.split()) <= 4
                and not re.search(r'[.;!?]$', line)
                and LABELISH.match(fold(line).lower()) and label_ok(line)):
            nxt = clean(lines[i + 1])
            # A value looks like one: a figure, several words, or a
            # compound term - not a lone menu word ("Visit", "Homepage").
            looks = nxt and (re.search(r'\d', nxt) or len(nxt.split()) >= 2 or '-' in nxt)
            if looks and not LABELISH.match(fold(nxt).lower()) and len(nxt) <= 400:
                out.append((line, nxt, '%s:l%d' % (locus_prefix, i), 'LABEL_LINE_THEN_VALUE', 'LOW'))
    return out


def years_in(text, where, kind_default):
    out = []
    for m in YEAR.finditer(text):
        lo = max(0, m.start() - 70)
        ctx = text[lo:m.end() + 70]
        kind = kind_default
        if kind_default == 'PROSE':
            # The kind whose keyword sits nearest the year, within 60
            # characters: "acquis en 1998 ... Le millésime 2019" gives 1998
            # to ownership and 2019 to the vintage, not both to the first.
            pos = m.start() - lo
            best = None
            for k, rx in YEAR_KIND:
                for km in rx.finditer(ctx):
                    d = min(abs(km.start() - pos), abs(km.end() - pos))
                    if d <= 60 and (best is None or d < best[0]):
                        best = (d, k)
            kind = best[1] if best else 'DATE_IN_PROSE'
        out.append({'year': int(m.group(1)), 'where': where, 'kind': kind,
                    'context': clean(ctx)[:160]})
    return out


NAME = re.compile(r"\b((?:Ch[aâ]teau|Chateau|Clos|Domaine|Cuv[eé]e|Pavillon|R[eé]serve|Le|La|Les|L['’]|"
                  r"Esprit|Echo|Pagus|Blanc|Ros[eé]|Petit|Petite)\s*(?:[A-ZÉÈÀÂÔ][\w'’-]+|d['’][A-ZÉ][\w'’-]+)"
                  r"(?:\s+(?:de|du|des|d['’]|la|le|les|et|&|Blanc|Rouge|Ros[eé])?\s*[A-ZÉÈÀÂÔ][\w'’-]+){0,5})")


def wine_names(text):
    return [clean(m.group(1)) for m in NAME.finditer(text) if 2 <= len(m.group(1).split()) <= 8]


# ---------------------------------------------------------------- per artifact
def extract_one(args):
    sha, ctypes, urls, store = args
    p = '%sblobs/%s/%s' % (store, sha[:2], sha)
    if os.path.exists(p):
        data = open(p, 'rb').read()
    else:                       # text-like blobs are stored gzipped
        import gzip
        data = gzip.decompress(open(p + '.gz', 'rb').read())
    head = data[:8]
    ctype = sorted(ctypes)[0] if ctypes else ''
    url0 = sorted(urls)[0]
    path0 = url0.split('?')[0].lower()
    rep = {'sha256': sha, 'extractor': EXTRACTOR}
    media = 'other'
    try:
        if head.startswith(b'%PDF'):
            media = 'pdf'
            rep.update(parse_pdf(data))
        elif head.startswith(b'PK') and path0.endswith(('.docx', '.xlsx', '.pptx', '.odt', '.ods')):
            media = 'office'
            rep.update(parse_office(data))
        elif head[:4] in (b'\x89PNG', b'GIF8') or head[:3] == b'\xff\xd8\xff' or head[:4] == b'RIFF':
            media = 'image'
        elif 'json' in ctype or path0.endswith('.json') or '/wp-json/' in url0:
            media = 'json'
            try:
                j = json.loads(decode(data))
                rep['json_shape'] = type(j).__name__
                rep['json_len'] = len(j) if hasattr(j, '__len__') else None
            except Exception as e:
                rep['parse_error'] = str(e)[:200]
        elif 'xml' in ctype or path0.endswith('.xml') or data.lstrip()[:5] == b'<?xml':
            t = decode(data)
            media = 'sitemap' if ('<urlset' in t or '<sitemapindex' in t) else (
                'feed' if ('<rss' in t or '<feed' in t) else 'xml')
            rep['xml_root'] = (re.search(r'<([A-Za-z:_-]+)[\s>]', t[t.find('<', 5):] or '') or
                               re.search(r'x', 'x')).group(1)[:40]
        elif ctype.startswith(('text/html', 'application/xhtml')) or b'<html' in data[:2048].lower():
            media = 'html'
            rep.update(parse_html(data))
        elif ctype.startswith('text/') or path0.endswith(('.txt', '.csv')):
            media = 'text'
            rep['pages'] = [decode(data)]
            rep['page_count'] = 1
        rep['status'] = 'EXTRACTED' if media not in ('image', 'other') else (
            'STORED_NOT_EXTRACTED' if media == 'image' else 'UNSUPPORTED')
    except Exception as e:
        rep['status'] = 'EXTRACTION_FAILED'
        rep['error'] = ('%s: %s' % (type(e).__name__, e))[:300]
    rep['media'] = media

    # Text views for statements, years, roles, names, language.
    lines_by_locus = []
    if media == 'html':
        lines_by_locus.append(('block', [b['text'] for b in rep.get('blocks', [])]))
    elif rep.get('pages'):
        for i, t in enumerate(rep['pages']):
            lines_by_locus.append(('p%d' % (i + 1), t.splitlines()))
    full = '\n'.join('\n'.join(ls) for _, ls in lines_by_locus)
    rep['lang_detected'] = detect_lang(full)
    obs = []
    for loc, ls in lines_by_locus:
        for lab, val, locus, method, conf in statements(ls, loc):
            obs.append((lab, val, locus, method, conf))
    for ti, t in enumerate(rep.get('tables', [])):
        for ri, row in enumerate(t['rows']):
            cells = [c for c in row if c]
            if len(cells) == 2 and label_ok(cells[0]):
                obs.append((cells[0], cells[1], 'table%d:r%d' % (ti, ri), 'TABLE_TWO_CELL', 'MEDIUM'))
    for di, (dt, dd) in enumerate(rep.get('dl', [])):
        if label_ok(dt):
            obs.append((dt, dd, 'dl%d' % di, 'DEFINITION_LIST', 'MEDIUM'))
    lang = rep['lang_detected'] or (rep.get('lang_declared') or '')[:2].lower() or None
    observations = []
    seen = set()
    for lab, val, locus, method, conf in obs:
        k = (lab, val, locus)
        if k in seen:
            continue
        seen.add(k)
        oid = hashlib.sha1(('%s|%s|%s|%s' % (sha, locus, lab, EXTRACTOR)).encode('utf-8')).hexdigest()[:16]
        observations.append({
            'id': oid, 'artifact': sha, 'locus': locus, 'label': clean(lab)[:80],
            'value': clean(val)[:VALUE_CAP], 'value_truncated': len(clean(val)) > VALUE_CAP,
            'normalized': normalise(val) or None, 'lang': lang, 'method': method,
            'confidence': conf, 'category': categories(lab) or None,
            'category_basis': 'INFERRED_KEYWORD', 'extractor': EXTRACTOR})

    years = []
    for u in sorted(urls):
        years += years_in(urllib_unquote(u), 'url', 'URL_OR_FILENAME')
    if rep.get('title'):
        years += years_in(rep['title'], 'title', 'TITLE')
    for h in rep.get('headings', [])[:80]:
        years += years_in(h['text'], 'heading', 'HEADING')
    if media == 'pdf' and rep.get('meta', {}).get('title'):
        years += years_in(rep['meta']['title'], 'pdf_title', 'TITLE')
    years += years_in(full[:60000], 'text', 'PROSE')
    yrs = []
    yseen = set()
    for y in years:
        k = (y['year'], y['where'], y['kind'], y['context'])
        if k not in yseen:
            yseen.add(k)
            yrs.append(dict(y, artifact=sha))

    roles = []
    rseen = set()
    for m in ROLE_WORDS.finditer(full[:200000]):
        ctx = clean(full[max(0, m.start() - 160):m.end() + 160])
        k = (m.group(1).lower(), ctx[:120])
        if k in rseen or len(roles) >= 60:
            continue
        rseen.add(k)
        roles.append({'artifact': sha, 'wording': m.group(1), 'context': ctx[:320],
                      'names_in_context': sorted(set(wine_names(ctx)))[:8], 'lang': lang})

    names = collections.Counter()
    sources = []
    if rep.get('title'):
        sources.append(('title', rep['title']))
    for h in rep.get('headings', [])[:120]:
        sources.append(('heading', h['text']))
    for l in rep.get('links', [])[:1500]:
        if l['text']:
            sources.append(('anchor', l['text']))
    if media in ('pdf', 'office', 'text'):
        first = '\n'.join(rep.get('pages', [''])[:1])[:1500]
        sources.append(('first_page', first))
        if rep.get('meta', {}).get('title'):
            sources.append(('pdf_title', rep['meta']['title']))
    for u in sorted(urls):
        fn = urllib_unquote(u.split('?')[0].rstrip('/').rsplit('/', 1)[-1])
        sources.append(('filename', re.sub(r'[-_]+', ' ', re.sub(r'\.\w{2,4}$', '', fn))))
    for where, txt in sources:
        for n in wine_names(txt):
            names[(n, where)] += 1
    # Names beside role wording: where an unknown wine is most often named.
    for r in roles:
        for n in r['names_in_context']:
            names[(n, 'role_context')] += 1

    rep['observation_count'] = len(observations)
    return {'sha': sha, 'bytes': len(data), 'rep': rep, 'observations': observations,
            'years': yrs, 'roles': roles,
            'names': [[n, w, c] for (n, w), c in sorted(names.items())], 'full_len': len(full),
            'title': (rep.get('title') or rep.get('meta', {}).get('title') or '')[:200],
            'headings': [h['text'] for h in rep.get('headings', [])[:40]],
            'head_text': full[:4000]}


def urllib_unquote(s):
    import urllib.parse
    try:
        return urllib.parse.unquote(s)
    except Exception:
        return s


# ---------------------------------------------------------------- driver
def estate_names():
    """Every name an estate is known by, for attribution candidates."""
    names = {}
    T = json.load(io.open(OUT + 'targets.json', encoding='utf-8'))
    for e in T['estates']:
        for n in [e['name']] + [x for x in e['canonical_names'] if x]:
            k = key(n)
            k2 = re.sub(r'^(chateau|clos|domaine) ', '', k)
            if len(k2) >= 5 and len(k2.split()) >= 1:
                names.setdefault(k, set()).add(e['universe_id'])
    return names, T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--only', action='append', help='limit to these domains (testing)')
    ap.add_argument('--store')
    ap.add_argument('--out')
    a = ap.parse_args()
    global STORE, OUT
    if a.store:
        STORE = a.store.rstrip('/') + '/'
    if a.out:
        OUT = a.out.rstrip('/') + '/'
    locs = collections.defaultdict(lambda: [set(), set(), set()])
    ldir = OUT + 'locations/'
    for fn in sorted(os.listdir(ldir)):
        dom = fn[:-6]
        if a.only and dom not in a.only:
            continue
        for l in io.open(ldir + fn, encoding='utf-8'):
            r = json.loads(l)
            if r.get('sha256') and r.get('kind') in ('OK', 'NOT_MODIFIED'):
                L = locs[r['sha256']]
                if r.get('content_type'):
                    L[0].add(r['content_type'])
                L[1].add(r.get('final_url') or r['url'])
                L[2].add(dom)
    os.makedirs(STORE + 'extracted', exist_ok=True)
    os.makedirs(OUT + 'observations', exist_ok=True)
    names, T = estate_names()
    dom_estates = {d['domain']: d['estates'] for d in T['domains']}
    name_rx = re.compile(r'\b(' + '|'.join(sorted((re.escape(k) for k in names), key=len, reverse=True))
                         + r')\b') if names else None
    known = set()
    cv = io.open(ROOT + 'data/cuvees.js', encoding='utf-8').read()
    for n in re.findall(r"name:'((?:[^'\\]|\\.)*)'", cv):
        known.add(key(n.replace("\\'", "'")))
    for e in T['estates']:
        for n in [e['name']] + [x for x in e['canonical_names'] if x]:
            known.add(key(n))
    for f in ('chateaux.js', 'sauternes.js', 'saintemilion.js', 'pomerol.js', 'graves.js',
              'libournais.js', 'batch2.js', 'batch3.js', 'batch4.js'):
        for n in re.findall(r"second:'((?:[^'\\]|\\.)*)'", io.open(ROOT + 'data/' + f,
                                                                    encoding='utf-8').read()):
            known.add(key(n.replace("\\'", "'")))

    jobs = [(sha, sorted(v[0]), sorted(v[1]), STORE) for sha, v in sorted(locs.items())]
    arts, obs_shards, years, roles, wines, attrib = [], collections.defaultdict(list), [], [], \
        collections.defaultdict(lambda: {'count': 0, 'where': collections.Counter(),
                                         'artifacts': set(), 'domains': set()}), []
    with cf.ProcessPoolExecutor(max_workers=a.workers) as ex:
        for res in ex.map(extract_one, jobs, chunksize=8):
            sha = res['sha']
            rep = res.pop('rep')
            io.open('%sextracted/%s.json' % (STORE, sha), 'w', encoding='utf-8').write(
                json.dumps(rep, ensure_ascii=False, sort_keys=True))
            L = locs[sha]
            arts.append({'sha256': sha, 'media': rep['media'], 'status': rep['status'],
                         'error': rep.get('error'), 'content_types': sorted(L[0]),
                         'locations': len(L[1]), 'domains': sorted(L[2]),
                         'first_url': sorted(L[1])[0], 'bytes': res['bytes'],
                         'page_count': rep.get('page_count'), 'ocr': rep.get('ocr'),
                         'lang_detected': rep.get('lang_detected'),
                         'lang_declared': rep.get('lang_declared'),
                         'title': res['title'][:160] or None,
                         'observations': len(res['observations']), 'text_chars': res['full_len'],
                         'images_seen': len(rep.get('images', [])),
                         'jsonld': len(rep.get('jsonld', [])), 'tables': len(rep.get('tables', [])),
                         'extractor': EXTRACTOR})
            obs_shards[sha[:2]] += res['observations']
            years += res['years']
            roles += res['roles']
            for n, where, c in res['names']:
                k = key(n)
                w = wines[k]
                w['count'] += c
                w['where'][where] += c
                w['artifacts'].add(sha)
                w['domains'] |= L[2]
                w.setdefault('forms', collections.Counter())[n] += c
            # Attribution candidates: crawl context (weak), names (graded).
            cands = collections.OrderedDict()
            for d in sorted(L[2]):
                for u in dom_estates.get(d, []):
                    cands.setdefault(u, {'estate': u, 'evidence': []})['evidence'].append(
                        {'kind': 'CRAWL_CONTEXT', 'detail': d, 'weight': 'WEAK'})
            if name_rx:
                for where, txt, wgt in (('title', res['title'], 'STRONG'),
                                        ('filename', ' '.join(urllib_unquote(u.split('?')[0].rsplit('/', 1)[-1])
                                                              for u in sorted(L[1])), 'STRONG'),
                                        ('heading', ' | '.join(res['headings']), 'MEDIUM'),
                                        ('text', res['head_text'], 'WEAK')):
                    for m in set(name_rx.findall(key(re.sub(r'[-_]+', ' ', txt or '')))):
                        for u in sorted(names[m]):
                            cands.setdefault(u, {'estate': u, 'evidence': []})['evidence'].append(
                                {'kind': 'NAMED_IN_' + where.upper(), 'detail': m, 'weight': wgt})
            named = {c['estate'] for c in cands.values()
                     if any(e['kind'] in ('NAMED_IN_TITLE', 'NAMED_IN_FILENAME', 'NAMED_IN_HEADING')
                            for e in c['evidence'])}
            attrib.append({'artifact': sha, 'candidates': list(cands.values()),
                           'multi_estate': len(named) > 1, 'status': 'CANDIDATES_ONLY'})
    arts.sort(key=lambda r: r['sha256'])
    # Write the committed layers, sorted, so a rerun is byte-identical.
    for f in os.listdir(OUT + 'observations'):
        os.remove(OUT + 'observations/' + f)
    for shard, rows in sorted(obs_shards.items()):
        rows.sort(key=lambda r: (r['artifact'], r['locus'], r['label']))
        with io.open('%sobservations/%s.jsonl' % (OUT, shard), 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')

    def dump(name, rows, sortkey):
        rows.sort(key=sortkey)
        with io.open(OUT + name, 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')

    dump('artifacts.jsonl', arts, lambda r: r['sha256'])
    # Every year mention with its context stays local (it is the estates'
    # prose, 100 MB of it); committed is, per artifact, the years its URL,
    # title and headings carry - the document-vintage candidates - and how
    # many prose mentions of each kind it holds, without their text.
    os.makedirs(STORE + 'derived', exist_ok=True)
    years.sort(key=lambda r: (r['artifact'], r['where'], r['year'], r['context']))
    with io.open(STORE + 'derived/years.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for r in years:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
    vc = collections.OrderedDict()
    for r in years:
        v = vc.setdefault(r['artifact'], {'artifact': r['artifact'], 'url': set(), 'title': set(),
                                          'heading': set(), 'prose_by_kind': collections.Counter()})
        if r['kind'] in ('URL_OR_FILENAME',):
            v['url'].add(r['year'])
        elif r['kind'] == 'TITLE':
            v['title'].add(r['year'])
        elif r['kind'] == 'HEADING':
            v['heading'].add(r['year'])
        else:
            v['prose_by_kind'][r['kind']] += 1
    vrows = [{'artifact': v['artifact'], 'url_years': sorted(v['url']), 'title_years': sorted(v['title']),
              'heading_years': sorted(v['heading']), 'prose_by_kind': dict(sorted(v['prose_by_kind'].items()))}
             for v in vc.values()]
    dump('vintage-candidates.jsonl', vrows, lambda r: r['artifact'])
    if os.path.exists(OUT + 'years.jsonl'):
        os.remove(OUT + 'years.jsonl')
    dump('roles.jsonl', roles, lambda r: (r['artifact'], r['wording'].lower(), r['context']))
    dump('attribution.jsonl', attrib, lambda r: r['artifact'])
    wrows = []
    for k, w in wines.items():
        if w['count'] < 1 or not k:
            continue
        wrows.append({'key': k, 'forms': [n for n, _ in w['forms'].most_common(4)],
                      'count': w['count'], 'where': dict(sorted(w['where'].items())),
                      'artifacts': len(w['artifacts']), 'domains': sorted(w['domains'])[:12],
                      'known_in_canonical': k in known,
                      'status': 'KNOWN_NAME' if k in known else 'UNRESOLVED'})
    dump('wines.jsonl', wrows, lambda r: r['key'])
    print('%d artifacts, %d observations, %d year mentions, %d role statements, %d name candidates'
          % (len(arts), sum(len(v) for v in obs_shards.values()), len(years), len(roles), len(wrows)))


if __name__ == '__main__':
    main()
