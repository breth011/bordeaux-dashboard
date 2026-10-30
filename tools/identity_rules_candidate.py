"""Candidate identity rules over M3.4A's decide (tools/m34a-mapping-audit.py): a proposal, not production.

M3.4A's decide is not changed and its file is fingerprinted. These rules rewrite, mask or annotate the text decide
reads, or veto its result, and decide itself runs unchanged on the result. They are the M3.12 rule-layer proposal,
moved here from the phase's scratchpad unchanged in substance, so that the integration dry-run
(tools/integration-dryrun.py) can exercise them; nothing in production calls this module.

  R1   name form: the estate's and its wines' names, written in the text with other separators (hyphen, space,
       apostrophe, line break) between the same words, are written as the model writes them. Words are never
       changed, only the separators; the rewrite keeps the text's length.
  R1b  short name: the estate's core name (its name without "chateau", articles and prepositions) standing
       beside the year names the grand vin - not when it is part of a longer name (a sibling's word or an
       article before it), and only for a wine whose name is the estate's.
  R2   late heading: a heading outside the opening - a whole line, or up to four short lines, holding the wine's
       name (with an optional classification) and the year - counts as the document's opening statement, when
       no heading of the same shape heads another year. "Millesime YYYY" alone is a heading only when R4 names
       the wine.
  R3   non-vintage years: years standing in a drinking window, a planting or certification date, an earlier
       season, a comparison or a dated event are not read as vintages. They are masked, never replaced.
  R4   file series: the site's own pages, each reviewed as the page of one wine (FILE_SERIES_PAGES), link a
       document; when every reviewed page linking it is one wine's, the document is that wine's
       (EXPLICIT_FILE_SERIES_MAPPING). A file linked from two wines' pages, or none, establishes nothing.
  G1   safety guard: an acceptance a rule created, resting on the grand vin's name, is withdrawn where the text
       anywhere speaks of another wine of the estate (a dry white, a cuvee, a second wine) - not where R4 says
       whose document it is.

REVIEW_HOLD lists the rescues the rule audit read and classified LIKELY_RESCUE_REQUIRES_REVIEW: the rules settle
them, the audit did not accept them, and no one has decided them. A caller must not treat them as settled.

    with applied(m34a_module) as log:      # decide answers with the rules; log[(sha12, wine, vintage)] is the trace
        ...
"""
import collections
import contextlib
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import migration_lib as L  # noqa: E402

VERSION = 'identity-rules-candidate/1'
ROOT = L.ROOT
YR = r'(?<!\d)(?:19[5-9]\d|20[0-2]\d)(?!\d)'
YRC = re.compile(YR)
SEP = r"[\s\-'’]+"
RULES = ('R1', 'R1b', 'R2', 'R3', 'R4')

# (sha256 prefix, wine, vintage): the rule audit's LIKELY_RESCUE_REQUIRES_REVIEW claims, with its reading
REVIEW_HOLD = {
    ('ff3f74b8517dd5cc', 'wn_00167', 2022): '"Chateau Paloumey 2022" is a line of its own, but at 57% of a two-column '
                                            'sheet: it may be a table label, not the title (R2)',
    ('1c74d87a4ddcd665', 'wn_00534', 1998): 'the text never names the wine: the identity is the listing\'s alone (R4), '
                                            'the year a bare "Millesime 1998" as the last line (R2)',
    ('a9dd99ecfc891e24', 'wn_00215', 2023): 'the identity is sound, but the document is a critics\' score sheet with no '
                                            'technical field (R1)',
    ('6ee0816c58139392', 'wn_00215', 2023): 'the identity is sound, but the document is a critics\' score sheet with no '
                                            'technical field (R1)',
    ('f59854e5d18e7e5a', 'wn_00386', 2003): 'the estate\'s 2003 press review: R3 masks review dates and drinking '
                                            'windows; a press compilation, not a sheet (R3)',
}


def held_for_review(sha, w, y):
    for (pre, hw, hy), why in REVIEW_HOLD.items():
        if sha and sha.startswith(pre) and hw == w and hy == y:
            return why
    return None


# ---- R4: the reviewed wine pages, (host, path prefix) -> wine id; a page of a wine the model does not list is
# UNLISTED:<name>. Download pages that list every wine are deliberately absent.
FILE_SERIES_PAGES = [
    ('desmirail.com', '/nos-vins/chateau-desmirail/', 'wn_00254'),
    ('desmirail.com', '/en/our-wines/chateau-desmirail/', 'wn_00254'),
    ('desmirail.com', '/nos-vins/initial-de-desmirail/', 'wn_00499'),
    ('desmirail.com', '/en/our-wines/initial-de-desmirail/', 'wn_00499'),
    ('desmirail.com', '/nos-vins/iris-pourpre-de-desmirail/', 'wn_00500'),
    ('desmirail.com', '/en/our-wines/iris-pourpre-de-desmirail/', 'wn_00500'),
    ('desmirail.com', '/nos-vins/la-perle-de-desmirail/', 'wn_00501'),
    ('desmirail.com', '/en/our-wines/la-perle-de-desmirail/', 'wn_00501'),
    ('desmirail.com', '/nos-vins/rose-de-desmirail/', 'UNLISTED:Rose de Desmirail'),
    ('desmirail.com', '/en/our-wines/rose-de-desmirail/', 'UNLISTED:Rose de Desmirail'),
] + [('chateau-issan.com', '/%s/vin_%s.html' % (lg, p), w) for lg in ('fr', 'en', 'ja', 'zh')
     for p, w in (('chateau_d_issan', 'wn_00283'), ('blason_d_issan', 'wn_00527'), ('moulin_d_issan', 'wn_00528'))] + [
    ('haut-brion.com', '/nos-vins/la-clarte-de-haut-brion/', 'wn_00525'),
    ('haut-brion.com', '/en/the-wines/la-clarte-de-haut-brion/', 'wn_00525'),
    ('haut-brion.com', '/zh/the-wines/la-clarte-de-haut-brion/', 'wn_00525'),
    ('mission-haut-brion.com', '/nos-vins/la-clarte-de-haut-brion/', 'wn_00535'),
    ('mission-haut-brion.com', '/en/the-wines/la-clarte-de-haut-brion/', 'wn_00535'),
    ('mission-haut-brion.com', '/zh/the-wines/la-clarte-de-haut-brion/', 'wn_00535'),
    ('mission-haut-brion.com', '/nos-vins/la-chapelle-de-la-mission-haut-brion', 'wn_00534'),
    ('mission-haut-brion.com', '/en/the-wines/la-chapelle-de-la-mission-haut-brion', 'wn_00534'),
    ('mission-haut-brion.com', '/zh/the-wines/la-chapelle-de-la-mission-haut-brion', 'wn_00534'),
]


def nurl(u):
    p = urlparse(u or '')
    return (p.netloc.lower().removeprefix('www.'), p.path)


def fkey(u):
    """A linked file as (host, file name): the sites link relatively (./docs/fr/...) under a base the extraction
    does not keep, so the resolved path is not the file's; the name on the host is."""
    h, path = nurl(u)
    return (h, os.path.basename(path).lower())


def page_wine(u):
    h, path = nurl(u)
    for host, pre, w in FILE_SERIES_PAGES:
        if h == host and path.startswith(pre):
            return w
    return None


class Series:
    """The reviewed listing: document URL -> the wines of the reviewed pages linking it, with the pages."""

    def __init__(self):
        self.linked = collections.defaultdict(lambda: collections.defaultdict(set))
        self.urls_of_sha = collections.defaultdict(set)
        ex = ROOT + 'sources/discovery/extracted/'
        for r in L.jsonl_lines(ROOT + 'data/discovery/artifacts.jsonl'):
            if r.get('first_url'):
                self.urls_of_sha[r['sha256']].add(r['first_url'])
            if r.get('media') != 'html' or not page_wine(r.get('first_url')):
                continue
            p = ex + r['sha256'] + '.json'
            if not os.path.exists(p):
                continue
            x = json.load(open(p, encoding='utf-8'))
            for l in x.get('links') or []:
                href = urljoin(r['first_url'], l.get('href') or '')
                if href.lower().split('?')[0].endswith('.pdf'):
                    self.linked[fkey(href)][page_wine(r['first_url'])].add(r['first_url'])
        locdir = ROOT + 'data/discovery/locations/'
        for f in sorted(os.listdir(locdir)):
            for line in open(locdir + f, encoding='utf-8'):
                x = json.loads(line)
                if x.get('sha256'):
                    for k in ('url', 'final_url'):
                        if x.get(k):
                            self.urls_of_sha[x['sha256']].add(x[k])
                pw = page_wine(x.get('referrer'))
                if pw and (x.get('url') or '').lower().split('?')[0].endswith('.pdf'):
                    self.linked[fkey(x['url'])][pw].add(x['referrer'])
        self.by_prefix = collections.defaultdict(set)
        for sha, us in self.urls_of_sha.items():
            self.by_prefix[sha[:12]] |= us

    def urls(self, a):
        """Every URL the document was held at: an artifact's placements, or a discovery sha's locations."""
        aid = a.get('id') or ''
        out = set()
        if aid.startswith('ar_'):
            out |= {p['locator']['value'] for p in A.placements_of(aid) if p['locator']['kind'] == 'URL'}
            if a.get('sha256'):
                out |= self.urls_of_sha.get(a['sha256'], set())
        elif aid.startswith('m3.8:'):
            out |= self.by_prefix.get(aid[5:], set())
        return sorted(out)

    def mapping(self, urls):
        """(status, wine or None, basis) for a document held at these URLs."""
        wines = collections.defaultdict(set)
        for u in urls:
            for w, pages in self.linked.get(fkey(u), {}).items():
                wines[w] |= pages
        if not wines:
            return ('NO_REVIEWED_LISTING', None, None)
        if len(wines) > 1:
            return ('AMBIGUOUS_LISTING', None, {w: sorted(p)[:3] for w, p in sorted(wines.items())})
        (w, pages), = wines.items()
        return ('EXPLICIT_FILE_SERIES_MAPPING', w, sorted(pages)[:3])


_SERIES = []


def series():
    if not _SERIES:
        _SERIES.append(Series())
    return _SERIES[0]


# ---- R1 -----------------------------------------------------------------------------------------------------

def name_rx(name):
    toks = [t for t in re.split(SEP, A.fold(name)) if t]
    # never inside a web or email address (www.chateau-latour.com, /chateau-corbin/, doisy-daene@)
    return re.compile(r'(?<![\w./@-])' + SEP.join(re.escape(t) for t in toks) + r'(?![\w]|[.@/-][a-z0-9])') if toks else None


def r1(text, names):
    out, trace = text, []
    # longest first; names of one length in their own order (the scratchpad left that tie to set order)
    for n in sorted({A.fold(x) for x in names if x}, key=lambda n: (-len(n), n)):
        rx = name_rx(n)
        if not rx:
            continue
        buf, last = [], 0
        for m in rx.finditer(out):
            s = m.group(0)
            if s == n:
                continue
            if len(n) > len(s):
                trace.append(('R1_SKIPPED_LONGER', s, n))
                continue
            buf.append(out[last:m.start()] + n + ' ' * (len(s) - len(n)))
            last = m.end()
            trace.append(('R1', s, n))
        out = ''.join(buf) + out[last:]
    return out, trace


# ---- R3 -----------------------------------------------------------------------------------------------------

MONTHS = (r'janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre'
          r'|january|february|march|april|may|june|july|august|september|october|november|december')
R3_PATTERNS = [
    # (name, pattern, which years in the match are masked: ALL, OTHER (not the claimed year), EARLIER, LATER_RANGE)
    ('DRINK', r'(?:a boire|boire|a deguster|drink(?:ing)?(?: window)?|a garder|garder|garde|apogee|consommer|best|peak)'
              r'\s+(?:a partir de|des|from|after|jusqu.?(?:a|au|en)|until|till|to|by|entre|between|now(?:\s+(?:to|until|through|-))?)'
              r'\s+(?:%s\s*(?:-|–|a|to|et|and|through)\s*)?%s' % (YR, YR), 'ALL'),
    ('WINDOW_RANGE', r'%s\s*[-–]\s*%s' % (YR, YR), 'LATER_RANGE'),
    ('PLANTING', r'(?:\bplant\w*|\breplant\w*|la plus (?:ancienne|jeune|vieille)|the (?:oldest|youngest))\b[^.\n]{0,30}?%s' % YR, 'ALL'),
    ('CERTIFICATION', r'\bcertifi\w*\b[^.\n]{0,40}?%s' % YR, 'ALL'),
    ('EARLIER_SEASON', r'\b(?:automne|hiver|autumn|winter|fall)\s+(?:de\s+|of\s+)?%s' % YR, 'EARLIER'),
    ('COMPARISON_LIST', r'\(\s*%s(?:\s*[/,;]\s*%s)+\s*\)' % (YR, YR), 'OTHER'),
    ('COMPARISON', r'(?:a l.?instar d[ue]s?|voire d[ue]s?|comme (?:le|en|les)|like (?:the|in)|as in|reminiscent of(?: the)?'
                   r'|apres le|after the|que le|than the)\s+%s' % YR, 'OTHER'),
    ('EVENT_DATE', r'(?:\b\d{1,2}(?:er)?\s+)?\b(?:%s)\s+%s' % (MONTHS, YR), 'OTHER'),
]
R3_RX = [(n, re.compile(p), how) for n, p, how in R3_PATTERNS]


def r3(text, y):
    chars, trace = list(text), []
    for name, rx, how in R3_RX:
        for m in rx.finditer(text):
            ys = [(int(v.group(0)), m.start() + v.start()) for v in YRC.finditer(m.group(0))]
            for v, at in ys:
                if how == 'OTHER' and v == y or how == 'EARLIER' and v >= y:
                    continue
                if how == 'LATER_RANGE' and not (len(ys) == 2 and ys[0][0] > y and ys[1][0] > ys[0][0]):
                    continue
                if chars[at:at + 4] == ['#'] * 4:
                    continue
                chars[at:at + 4] = '####'
                trace.append(('R3', name, v, text[max(0, m.start() - 10):m.end()].replace('\n', ' / ')))
    return ''.join(chars), trace


# ---- R2 -----------------------------------------------------------------------------------------------------

CLASS = r'(?:(?:1er |premier )?grand cru classe(?: [ab])?(?: en 1855)?|cru classe(?: en 1855)?|cru bourgeois(?: superieur| exceptionnel)?)'


def headings(text, wname, vintage_word_ok):
    """[(year, form, joined text, line index)] of the text's headings of the wine and of bare 'millesime YYYY'."""
    toks = [t for t in re.split(SEP, A.fold(wname)) if t]
    nm = SEP.join(re.escape(t) for t in toks)
    named = re.compile(r'(?:%s)(?:\s+%s)?\s+(%s)' % (nm, CLASS, YR))
    bare = re.compile(r'(?:millesime|vintage)\s+(%s)' % YR)
    lines = text.split('\n')
    out = []
    for i in range(len(lines)):
        for k in range(1, 5):
            win = [l.strip() for l in lines[i:i + k]]
            if len(win) < k or not all(win) or any(len(l) > 60 for l in win) or (k > 1 and any(len(l) > 30 for l in win)):
                break
            j = ' '.join(' '.join(win).split())
            m = named.fullmatch(j)
            if m:
                out.append((int(m.group(1)), 'NAMED' if k == 1 else 'NAMED_BLOCK', j, i))
            elif k == 1 and vintage_word_ok and bare.fullmatch(j):
                out.append((int(bare.fullmatch(j).group(1)), 'BARE', j, i))
    return out


def r2(text, wname, y, opening, bare_ok):
    if re.search(r'(?<!\d)%d(?!\d)' % y, text[:opening]):
        return text, [], None
    hs = headings(text, wname, bare_ok)
    mine = [h for h in hs if h[0] == y]
    others = sorted({h[0] for h in hs if h[0] != y})
    if not mine:
        return text, [], 'no heading of %s %d' % (wname, y)
    if others:
        return text, [], 'competing headings of %s' % others
    h = mine[0]
    return h[2] + '\n' + text, [('R2', h[1], h[2], 'line %d of %d' % (h[3], text.count('\n') + 1))], None


# ---- R1b ----------------------------------------------------------------------------------------------------

GENERIC = {'chateau', 'clos', 'domaine', 'cru', 'vignobles', 'le', 'la', 'les', 'de', 'du', 'des', 'd', 'l'}


def core_name(ename):
    toks = [t for t in re.split(SEP, A.fold(ename)) if t and t not in GENERIC]
    c = ' '.join(toks)
    return c if len(c) >= 4 else None


def r1b(text, ename, wname, y, sibling_words):
    core = core_name(ename)
    if not core:
        return text, [], 'no core name'
    c = SEP.join(re.escape(t) for t in core.split())
    pats = [re.compile(r'(?<![\w.@/\'’-])(%s)\s+%d(?!\d)' % (c, y)),
            re.compile(r'(?<!\d)%d\s+(%s)(?![\w\'’-]|[.@/][a-z0-9])' % (y, c))]
    for rx in pats:
        for m in rx.finditer(text):
            before = text[max(0, m.start(1) - 30):m.start(1)]
            if re.search(r"(?:\b[dl]['’]|\bde\s+|\bdu\s+)$", before) and not re.search(r"\bchateau\s+(?:[dl]['’]|de\s+|du\s+)$", before):
                continue
            if any(re.search(r'\b%s\b' % re.escape(s), before) for s in sibling_words):
                continue
            full = A.fold(wname)
            return (text[:m.start(1)] + full + text[m.end(1):],
                    [('R1b', m.group(0).replace('\n', ' / '), 'core "%s" beside %d' % (core, y))], None)
    return text, [], 'core "%s" not beside %d' % (core, y)


# ---- the layer ----------------------------------------------------------------------------------------------

G1_EXTRA = r'|grand vin sec|vin blanc sec|\bblanc sec\b|\bdry white\b|\bsec du chateau\b'
G1_SWEET = r'|\bbordeaux blanc\b|\bvin sec\b'      # a sweet wine's estate speaking of a dry white: maybe that wine


def evaluate(mod, orig, rules, text, how, smap, args):
    """decide's answer with the rules: {'result': decide's 4-tuple, 'trace': [...], 'notes': [...]}."""
    row, a, claims, e, w, y, nm, ew, wines, blocked, vdocs = args
    base = orig(*args)
    ename, wname = nm.get(e, ''), nm.get(w, '')
    siblings = [s for s in ew.get(e, []) if s != w]
    t, trace, notes = text, [], []

    def run(tx):
        old = mod.document_text
        mod.document_text = lambda aid: (tx, how)
        try:
            return orig(*args)
        finally:
            mod.document_text = old
    r4w = smap[1] if smap[0] == 'EXPLICIT_FILE_SERIES_MAPPING' else None
    if 'R3' in rules:
        t, tr = r3(t, y)
        trace += tr
    if 'R1' in rules:
        t, tr = r1(t, [ename] + [nm.get(s, '') for s in ew.get(e, [])])
        trace += tr
    if 'R2' in rules:
        t, tr, why = r2(t, wname, y, mod.OPENING, 'R4' in rules and r4w == w)
        trace += tr
        if why:
            notes.append('R2: ' + why)
    result = run(t) if t != text else base
    if result[0] == 'ESTATE_VINTAGE_ONLY' and 'R1b' in rules and not siblings:
        notes.append('R1b: the model lists one wine for the estate; one wine decides nothing (M3.9)')
    elif result[0] == 'ESTATE_VINTAGE_ONLY' and 'R1b' in rules and not mod.distinct_name(wname, ename):
        sw = [x for s in siblings for x in (mod.distinct_name(nm.get(s, ''), ename) or [])]
        t2, tr, why = r1b(t, ename, wname, y, sw)
        if tr:
            trace += tr
            result = run(t2)
        elif why:
            notes.append('R1b: ' + why)
    if 'R4' in rules and smap[0] == 'EXPLICIT_FILE_SERIES_MAPPING':
        # the wine is not named in the text: by the estate's name only, or not at all (a cuvee's own name)
        unnamed = result[0] == 'ESTATE_VINTAGE_ONLY' or (
            result[0] == 'WINE_AMBIGUOUS' and result[1].startswith('the document does not name the wine'))
        if r4w == w and unnamed:
            m = re.search(r'(?<!\d)%d(?!\d)' % y, t[:mod.OPENING])
            if m:
                t2 = t[:m.start()] + A.fold(wname) + ' ' + t[m.start():]
                trace.append(('R4', 'EXPLICIT_FILE_SERIES_MAPPING', w, smap[2]))
                result = run(t2)
        elif r4w != w and result[0] == 'SAFE_TO_MAP':
            trace.append(('R4_VETO', 'EXPLICIT_FILE_SERIES_MAPPING', r4w, smap[2]))
            result = ('WINE_AMBIGUOUS', 'the site\'s own listing files this document under %s, not %s' % (
                nm.get(r4w, r4w), wname), None, result[3])
    elif 'R4' in rules and smap[0] != 'NO_REVIEWED_LISTING':
        notes.append('R4: %s' % smap[0])
    # G1: an acceptance a rule created, resting on the grand vin's name, where the text anywhere speaks of
    # another wine of the estate (a dry white, a cuvee, a second wine) the claim might be - the unlisted
    # cuvee the guards cannot refuse. Not where the site's own listing (R4) says whose document it is.
    if (rules and result[0] == 'SAFE_TO_MAP' and base[0] != 'SAFE_TO_MAP' and (result[3] or {}).get('grand_vin')
            and not any(x[0] == 'R4' for x in trace)):
        sweet = ((wines.get(w) or {}).get('type') == 'WHITE_SWEET')
        m = re.compile(mod.OTHER_WINE.pattern + G1_EXTRA + (G1_SWEET if sweet else '')).search(t)
        if m:
            trace.append(('G1', m.group(0)))
            result = ('WINE_AMBIGUOUS', 'G1: the document also speaks of "%s": the grand vin is not established '
                      'by its name alone' % m.group(0), None, result[3])
    return {'base': base, 'result': result, 'trace': trace, 'notes': notes}


@contextlib.contextmanager
def applied(mod, rules=RULES):
    """Within the block, mod.decide (an M3.4A module instance) answers with the rules; outside it, unchanged.
    Yields the log: (sha256 prefix, wine, vintage) -> the call's base and rule result, trace and notes."""
    orig = mod.decide
    log = {}

    def decide(row, a, claims, e, w, y, nm, ew, wines, blocked, vdocs):
        args = (row, a, claims, e, w, y, nm, ew, wines, blocked, vdocs)
        if not a or not a.get('bytes_available') or not a.get('id'):
            return orig(*args)
        text, how = mod.document_text(a['id'])
        if not text:
            return orig(*args)
        s = series()
        smap = s.mapping(s.urls(a))
        res = evaluate(mod, orig, rules, text, how, smap, args)
        base, out = res['base'], res['result']
        aid = a['id']
        log[(aid[5:] if aid.startswith('m3.8:') else (a.get('sha256') or aid)[:12], w, y)] = {
            'base': list(base[:2]), 'result': list(out[:2]), 'trace': [list(t) for t in res['trace']],
            'notes': res['notes'], 'series': [smap[0], smap[1]]}
        if out[0] != base[0]:
            return out[:3] + (dict(out[3], candidate_rules=res['trace']),)
        return base
    mod.decide = decide
    try:
        yield log
    finally:
        mod.decide = orig
