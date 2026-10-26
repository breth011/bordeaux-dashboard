"""M3.5: the held-document review rubric - what a document itself establishes (pure functions).

Applied to a document's folded text and an accepted claim (estate, wine, vintage) on it:

  T1 title      the document's first non-empty line, when it is a bare name phrase (a wine word -
                chateau, clos, domaine, cuvee ... - then words, then at most a year), is its title.
                The title names the document's wine and, with a year, its vintage.
  T2 exact      the title's name must equal a model wine's name, normalised (accents, case,
                hyphens, "ch." for "chateau"). A shared word is no match: "Château Braude
                Fellonneau" is not "Château de Braude", "Cuvée de Mongravey" not "Château Mongravey".
  T3 producer   lines naming the producer or how to reach it (company forms, address, postcode,
                telephone, e-mail, web site) are not identity: a group's footer names its company,
                not the wine (SARL Mongravey on every Bernaleau sheet).
  T4 vintage    the title's year is the vintage. A year in a dated line ("dec 2022", "guide hubert
                des vins 2017", "le 16 mai 2019") is a date, never the vintage; a file name, URL,
                retrieval or metadata year is never read.
  T5 scope      outside the producer lines, no other wine of the claimed estates may be named; a
                document naming two claimed wines each beside the one vintage is a shared sheet
                (both supported); "l'autre vin", a second wine or a named cuvee in the opening
                makes the wine ambiguous.
  T6 colour     a stated blend must be of the wine's colour.
  T7 open       a wine an open identity decision governs is never attributed.

A document with no title (T1) is judged by M3.4A's rules unchanged (tools/m34a-mapping-audit.py).
"""
import re
import unicodedata

WINE_WORD = r'(?:chateau|ch\.|clos|domaine|cuvee|le|la|les|l\'|vieux|petit|grand|pavillon|carruades|reserve|alter|dame|pagodes|fiefs)'
# a title must open with one of these, unless it is a model wine's whole name ("Les Forts de Latour"):
# a heading such as "Le climat" is no title (found in review: Laville Haut-Brion's sheet)
STRONG = ('chateau', 'clos', 'domaine', 'cuvee')
TITLE = re.compile(r'^\s*(%s\b[a-z\' .&-]{1,70}?)(?:\s+((?:19|20)\d\d))?\s*$' % WINE_WORD)
PRODUCER = re.compile(r'\b(?:sarl|sas|scea|earl|gfa|sca|gaec|eurl|snc)\b|@|\btel\b|t[eé]l[eé]phone|\bfax\b|\bsite\s*:|www\.|https?://'
                      r'|\b33\d{3}\s+[a-z]|\b(?:\+33|0)\s*\(?\d\)?[\s.]*\d{2}[\s.]*\d{2}[\s.]*\d{2}')
MONTHS = (r'janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre'
          r'|jan|feb|fev|mar|apr|avr|jun|jul|juil|aug|sep|sept|oct|nov|dec'
          r'|january|february|march|april|may|june|july|august|september|october|november|december')
DATED_YEAR = re.compile(r'\b(?:%s)\.?\s+((?:19|20)\d\d)\b|\b(?:guide|revue|magazine|concours|edition)\b[^\n]{0,40}?\b((?:19|20)\d\d)\b' % MONTHS)
OTHER_WINE = re.compile(r'second vin|second wine|deuxi[eè]me vin|second label|third wine|troisi[eè]me vin'
                        r'|l.autre vin\b|the other wine\b')
RED_GRAPE = re.compile(r'cabernet|merlot|petit verdot|malbec|carmen[eè]re')
WHITE_GRAPE = re.compile(r's[eé]millon|(?<!cabernet )(?<!cabernet-)sauvignon|muscadelle')
BLEND = re.compile(r'(?:assemblage|blending|blend|c[eé]pages?)\s*:?\s*((?:[^.;:\n]{0,25}?\d{1,3}\s*%[^.;:\d\n]{0,25}){1,5})')
VINTAGE_HEAD = re.compile(r'\b(?:mill[eé]sime|vintage)\s*:?\s*((?:19|20)\d\d)\b')


def fold(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return s


def norm_name(s):
    """A wine name for comparison: folded, 'ch.' for 'chateau', hyphens and punctuation as spaces."""
    s = fold(s)
    s = re.sub(r'\bch\.\s*', 'chateau ', s)
    s = re.sub(r'[^a-z0-9\']+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def title(text):
    """T1: (name, year or None) of the document's title line, or None when its first line is no title."""
    for line in (text or '').split('\n'):
        if line.strip():
            m = TITLE.match(fold(line).strip())
            if not m or PRODUCER.search(line):
                return None
            name = norm_name(m.group(1))
            if len(name.split()) < 2 or len(name.split()) > 8:
                return None
            return name, int(m.group(2)) if m.group(2) else None
    return None


def body(text):
    """T3: the text without its producer lines."""
    return '\n'.join(l for l in (text or '').split('\n') if not PRODUCER.search(fold(l)))


def dated_years(text):
    """T4: the years that stand in a dated line - press or event dates, never a vintage."""
    out = set()
    for m in DATED_YEAR.finditer(fold(text or '')):
        out.add(int(m.group(1) or m.group(2)))
    return out


def blend_colour(text):
    blends = BLEND.findall(fold(text or ''))
    red = any(RED_GRAPE.search(b) for b in blends)
    white = any(WHITE_GRAPE.search(b) for b in blends)
    return 'RED' if red and not white else 'WHITE' if white and not red else None


def judge(text, claim, wines, estate_wines, blocked):
    """The review of one accepted claim on one document, by the title rule.

    claim          {estate, wine, vintage} - the accepted decision's model target
    wines          {wine id: (name, type)} of the model
    estate_wines   {estate id: [wine ids]}
    blocked        {wine id: open decision}

    Returns None when the document has no title (T1): judge it by M3.4A's rules. Otherwise
    {'disposition', 'basis', 'title', 'supports': [wine ids the document establishes for that vintage]}.
    """
    t = title(text)
    if t is None:
        return None
    tname, tyear = t
    by_name = {}
    for wid, (name, _) in wines.items():
        by_name.setdefault(norm_name(name), set()).add(wid)
    if tname.split()[0] not in STRONG and tname not in by_name:
        return None                                   # a heading, not a title
    e, w, y = claim['estate'], claim['wine'], claim['vintage']
    wname, wtype = wines.get(w, ('', None))
    tw = by_name.get(tname, set())
    out = {'title': [tname, tyear], 'supports': sorted(tw) if tyear else []}
    if w in blocked:
        return dict(out, disposition='WINE_AMBIGUOUS', basis='open identity decision %s governs %s: not attributed' % (blocked[w], wname))
    if not tw:
        if norm_name(wname) and norm_name(wname) in tname:
            return dict(out, disposition='WINE_AMBIGUOUS', basis='the title "%s" contains %s but is not its name' % (tname, wname))
        return dict(out, disposition='WRONG_EXISTING_ATTRIBUTION',
                    basis='the title is "%s", a wine the model does not list; not %s' % (tname, wname))
    if w not in tw:
        other = sorted(tw)[0]
        return dict(out, disposition='WRONG_EXISTING_ATTRIBUTION',
                    basis='the title is "%s" (%s), not %s' % (tname, other, wname))
    if tyear is None:
        return dict(out, disposition='VINTAGE_AMBIGUOUS', basis='the title names %s with no vintage' % wname)
    if tyear != y:
        why = ' (%d is a dated line in it)' % y if y in dated_years(text) else ''
        return dict(out, disposition='WRONG_EXISTING_ATTRIBUTION',
                    basis='the title is %s %d, not %d%s' % (wname, tyear, y, why))
    b = body(text)
    fb = fold(b)
    headed = sorted({int(v) for v in VINTAGE_HEAD.findall(fb)} - {y} - dated_years(text))
    if len(headed) >= 3:
        return dict(out, disposition='VINTAGE_AMBIGUOUS', basis='the document heads %d other vintages' % len(headed))
    # T5: the claimed estate's other wines, named outside the producer lines
    siblings = [s for s in estate_wines.get(e, []) if s != w]
    named = sorted(wines[s][0] for s in siblings
                   if norm_name(wines[s][0]) and re.search(r'(?<![a-z])%s(?![a-z])' % re.escape(norm_name(wines[s][0])), norm_name(b)))
    if named:
        return dict(out, disposition='MULTI_WINE_AMBIGUOUS', basis='the document also names %s' % ', '.join(named))
    head = fb[:600]
    m = OTHER_WINE.search(head)
    if m:
        return dict(out, disposition='WINE_AMBIGUOUS', basis='the opening speaks of another wine ("%s")' % m.group(0))
    c = blend_colour(b)
    if c and wtype and ((wtype == 'RED' and c == 'WHITE') or (wtype.startswith('WHITE') and c == 'RED')):
        return dict(out, disposition='COLOUR_AMBIGUOUS', basis='a %s wine, and the stated blend is %s' % (wtype.lower(), c.lower()))
    return dict(out, disposition='SAFE_TO_ATTRIBUTE', basis='the title is %s %d; no other wine of the estate is named '
                'outside the producer lines' % (wname, y))


def shared(text, claims, wines):
    """T5: a shared sheet - the document's body names each claimed wine by its full name beside the one
    vintage, and every claim is for that vintage. Returns the wine ids it supports, or []."""
    years = {c['vintage'] for c in claims}
    if len(years) != 1:
        return []
    y = years.pop()
    b = norm_name(body(text))
    ok = []
    for c in claims:
        n = norm_name(wines.get(c['wine'], ('', None))[0])
        if n and re.search(r'(?<![a-z])%s(?![a-z]).{0,40}\b%d\b' % (re.escape(n), y), b):
            ok.append(c['wine'])
    return sorted(set(ok)) if len(set(ok)) == len({c['wine'] for c in claims}) >= 2 else []
