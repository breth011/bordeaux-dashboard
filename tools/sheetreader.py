# -*- coding: utf-8 -*-
"""Reading a technical sheet: the rules, and why each one is here.

Imported by tools/read-sheets.py. Every rule in this file was added
because a wrong figure reached the dashboard without it, and the
comment on each says which.

The one principle underneath all of them: a document is read, never
counted. A filename, a folder, a URL and a file count have each been
wrong in a way that looked like success - 454 sheets for an estate that
published none, 6,227 PDFs where a media library showed 83, a blend
that was the estate's own figures with the varieties shuffled. The
number is never the evidence.
"""
import io, os, re, collections, warnings
warnings.filterwarnings('ignore')
import pymupdf

VARS = [('CS', r'cabernets?[\s\-]*sauvignons?'),
        ('CF', r'cabernets?[\s\-]*francs?'),
        ('PV', r'petits?[\s\-]*verdots?'),
        ('MA', r'malbecs?|c[oô]ts?\b'),
        ('CA', r'carm[eé]n[eè]res?'),
        ('SEM', r's[eé]millons?'),
        ('SB', r'sauvignons?[\s\-]*blancs?'),
        ('SG', r'sauvignons?[\s\-]*gris'),
        ('MU', r'muscadelles?'),
        # The Haut-Brion group writes "Merlot Noir: 54%". Without the
        # suffix, "Merlot" matched but the colon and figure did not
        # follow it, so the variety-first reading failed and the
        # share-first one paired each figure with the variety after it:
        # 54% to Cabernet Sauvignon, 45% to Cabernet Franc, reaching 99
        # and passing the tolerance with Merlot absent altogether.
        ('ME', r'merlots?(?:\s+noirs?)?')]
NAMES = '|'.join(p for _, p in VARS)
NUM = r'\d{1,3}(?:[.,]\d{1,2})?'

PCT_FIRST = re.compile(r'(?i)(' + NUM + r')\s*%\s*(?:de\s+|d’|d\'|et\s+)?('
                       + NAMES + r')')
VAR_FIRST = re.compile(r'(?i)(' + NAMES + r')\s*[:\-–]?\s*(' + NUM
                       + r')\s*%')

# The word the sheet uses for the wine, and the word it uses for the
# vineyard. Malartic-Lagraviere 2021 says "BLEND Cabernet-Sauvignon 67 %"
# at the top and "Grape varieties 56% Merlot" under the estate's
# description, and a reader that takes the first figures it finds takes
# the plantings.
# Varietals and Cepages belong here, not with the vineyard: the Domaines
# Barons de Rothschild sheets - Lafite, Duhart-Milon, L'Evangile,
# Rieussec - give the wine's blend as "TECHNICAL INFORMATION Varietals :
# Semillon 75%, Sauvignon 25%" and nothing else, so without them those
# sheets yielded no blend at all. Encepagement and Grape varieties stay
# with the vineyard below, which is where they belong.
WINE_LABEL = re.compile(r'(?i)\b(assemblage(?:\s+du\s+vin)?|blend|'
                        r'composition\s+du\s+vin|varietals?|'
                        r'c[eé]pages?)\b')
# Giscours writes its plantings as "SURFACE EN PRODUCTION 65 % Cabernet
# Sauvignon - 32 % Merlot - 3% Petit Verdot" and gives no assemblage
# figure at all, so without that label the plantings were read as the
# 2021 blend.
VINE_LABEL = re.compile(r'(?i)\b(enc[eé]pagement(?:\s+du\s+vignoble)?|'
                        r'grape\s+varieties|vineyard|plantation|'
                        r'surface\s+en\s+production|surface\s+du\s+vignoble|'
                        r'area\s+under\s+vines?|varieties\s+planted|'
                        r'the\s+domaine|le\s+domaine)\b')
STOP = re.compile(r'(?i)\b(rendement|yield|analyse|vinification|'
                  r'[eé]levage|ageing|aging|vendange|harvest|mise\s+en|'
                  r'bottling|production|d[eé]gustation|tasting|alcool|'
                  r'alcohol|ph\b|terroir|sol\b|the\s+domaine)\b')

LABEL = re.compile(r'(?i)mill[eé]sime\s*:?\s*(19[89]\d|20[0-4]\d)')
VINTAGE = re.compile(r'(?i)vintage\s*:?\s*(19[89]\d|20[0-4]\d)')
BEFORE = re.compile(r'(?i)(19[89]\d|20[0-4]\d)\s+vintage')
YEAR = re.compile(r'(?<!\d)(19[89]\d|20[0-4]\d)(?!\d)')

# A letterhead is not a statement about the wine. Every sheet in the
# Dubourdieu group's library carries "doisy-daene@wanadoo.fr" in its
# header, so a reader looking for an estate name anywhere in the
# document found the email address and filed Cantegril, Haura and
# Reynon as Doisy-Daene - 454 sheets of them.
CONTACT = re.compile(r'(?i)(t[eé]l\s*[:.]|fax|@|www\.|'
                     r'\d{2}\s\d{2}\s\d{2}\s\d{2})')

# How far into a document its title still counts as its title, measured
# in letters and digits with everything else stripped out. Malartic's
# own sheet names it at 7; the sibling property's names it at 244.
TITLE = 180

# Properties that share a folder with an estate in this dashboard
# because they share an owner, and are not that estate. Each one was
# found filed as its neighbour's grand vin.
#
# Diamandes de Uco is the Bonnie family's estate in the Valle de Uco,
# Mendoza; one of its sheets gave Malartic-Lagravière 2020 an Argentine
# Cabernet's alcohol, oak and press scores. Gazin-Rocquencourt is a
# Pessac-Léognan château of the same owners, and its sheet does name
# Malartic - 244 characters in, where it credits the owner - so being
# mentioned is not enough to be the wine.
# Vignobles K keeps all its properties in one library, and 104 of the
# 144 sheets filed under Tour Saint-Christophe are not Tour
# Saint-Christophe: Chateau La Patache and its Badine, Enclos
# Tourmaline, Enclos de Viaud, Chateau Le Rey in three cuvees, Chateau
# Haut-Brisson. Each names itself in its filename and none is in this
# dashboard.
SIBLINGS = {
    'diamandes': None,
    'perlita': None,
    'gazinrocquencourt': None,
    'rocquencourt': None,
    'lapatache': None,
    'badine': None,
    'enclostourmaline': None,
    'tourmaline': None,
    'enclosdeviaud': None,
    'viaud': None,
    'lerey': None,
    'hautbrisson': None,
    'labegorce': None,
}


# A press dossier is one document per property, not per vintage: the
# estate's history, its plantings, its standing practice and a page of
# clippings. Clos Floridene's gave twenty vintages the same "9 mois",
# which is its whites' ageing, and the red's standing assemblage, for a
# red that did not exist in the years it was filed under.
DOSSIER = re.compile(r'(?i)(dossier\s+de\s+presse|press\s+(kit|pack)|'
                     r'revue\s+de\s+presse|press\s+review)')


ESTATE_FILES = ('chateaux.js', 'crubourgeois.js', 'cruartisan.js',
                'graves.js', 'sauternes.js', 'saintemilion.js', 'pomerol.js',
                'rightbank.js', 'libournais.js', 'batch2.js', 'batch3.js')


# A single-quoted JavaScript string, escapes and all.
#
# Reading these files with [^']+ looked fine and was not. "Château
# Lalande d\'Auvion" ends the match at the escaped apostrophe, and the
# scan then resumes inside the string - so every estate after the first
# escaped apostrophe in the list was lost. That silently dropped 7 Cru
# Bourgeois estates, and because their records had nothing to attach to,
# a check I had just written reported them as estates the dashboard no
# longer lists. The data was right the whole time.
JSSTR = re.compile(r"'((?:[^'\\]|\\.)*)'")


def js_strings(text):
    """Every single-quoted string in some JavaScript, unescaped."""
    return [re.sub(r'\\(.)', r'\1', m.group(1)) for m in JSSTR.finditer(text)]


def js_strings_after(key, text):
    """The strings assigned to a given key, as in name:'Les Cyprès'."""
    rx = re.compile(re.escape(key) + JSSTR.pattern)
    return [re.sub(r'\\(.)', r'\1', m.group(1)) for m in rx.finditer(text)]


def slug(s):
    """The same slug app.js makes, so the ids match."""
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if not unicodedata.combining(c))
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s.lower()))


def estates(root):
    """Every estate, its name, and the names of its other wines.

    One loader, because three tools were each parsing these files their
    own way and one of them was quietly failing: a regex that tried to
    match a whole estate block returned nothing for most of them, so the
    estate name came back empty and every sheet looked unattributable.
    A check that cannot find its own reference data reports clean.

    So this reads it the dull way - find each id, then look forward a
    bounded distance for the fields - and is the only thing that does.
    """
    out = {}
    for f in ESTATE_FILES:
        p = os.path.join(root, 'data', f)
        if not os.path.exists(p):
            continue
        t = io.open(p, encoding='utf-8').read()
        for m in re.finditer(r"id:'([a-z0-9-]+)'", t):
            win = t[m.end():m.end() + 900]
            # Stop at the next estate, so no field is read off a neighbour.
            nxt = re.search(r"id:'[a-z0-9-]+'", win)
            if nxt:
                win = win[:nxt.start()]
            e = out.setdefault(m.group(1), {'name': None, 'second': None,
                                            'cuvees': [], 'cat': None})
            nm = js_strings_after('name:', win)
            sc = js_strings_after('second:', win)
            ct = js_strings_after('cat:', win)
            if nm and not e['name']:
                e['name'] = nm[0]
            if sc and not e['second']:
                e['second'] = sc[0]
            if ct and not e['cat']:
                e['cat'] = ct[0]
    # The sparse lists. app.js builds these estates' ids itself, from
    # `cls + '-' + slug(name)` - so most of the dashboard's estates are
    # named nowhere as `id:'...', name:'...'`, and a loader that only
    # looked for that pattern found 160 of them instead of 500. Those
    # ids have to be derived the same way here or every one of their
    # sheets looks unattributable.
    sparse = [('crubourgeois.js', 'BDX_CRU_BOURGEOIS', 'bourgeois'),
              ('cruartisan.js', 'BDX_CRU_ARTISAN', 'artisan'),
              ('saintemilion.js', 'BDX_STEM_GCC', 'stem'),
              ('pomerol.js', 'BDX_POMEROL_OTHER', 'pomerol')]
    for f, var, cls in sparse:
        p = os.path.join(root, 'data', f)
        if not os.path.exists(p):
            continue
        t = io.open(p, encoding='utf-8').read()
        m = re.search(re.escape(var) + r'\s*=\s*([\[{])', t)
        if not m:
            continue
        # The literal, to its matching bracket.
        open_c, close_c = m.group(1), (']' if m.group(1) == '[' else '}')
        depth, i = 0, m.end(1) - 1
        while i < len(t):
            if t[i] == open_c:
                depth += 1
            elif t[i] == close_c:
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = t[m.end(1):i]
        # A row is either a bare name or ['name','appellation']. Where
        # there are rows, the estate's name is the first string of each;
        # where the list is flat, every string is an estate.
        rows = re.findall(r'\[([^\[\]]*)\]', body)
        names = ([js_strings(r)[:1] for r in rows] if rows
                 else [[n] for n in js_strings(body)])
        for pair in names:
            for nm in pair:
                if not nm or len(nm) < 5 or nm[0].islower():
                    continue
                e = out.setdefault(cls + '-' + slug(nm),
                                   {'name': None, 'second': None,
                                    'cuvees': [], 'cat': None})
                if not e['name']:
                    e['name'] = nm

    p = os.path.join(root, 'data', 'cuvees.js')
    if os.path.exists(p):
        t = io.open(p, encoding='utf-8').read()
        for m in re.finditer(r"^'([a-z0-9-]+)':\[(.*)\],?$", t, re.M):
            e = out.setdefault(m.group(1), {'name': None, 'second': None,
                                            'cuvees': [], 'cat': None})
            # Built from JSSTR rather than written out again, so the
            # escape handling lives in one place and cannot drift.
            e['cuvees'] = js_strings_after('name:', m.group(2))
    for e in out.values():
        if not e['cat']:
            e['cat'] = 'red'
        # 34 estates record their second wine as an em-dash, meaning they
        # have none. Carried through as a name it becomes a mark with no
        # letters in it, which matches nothing and silently disables the
        # check - which is how three L'Arc Saint Pierre sheets were read
        # as Chateau Saint-Pierre's.
        if e['second'] and len(packed(e['second'])) < 3:
            e['second'] = None
        e['cuvees'] = [c for c in e['cuvees'] if len(packed(c)) >= 3]
        if e['second'] and e['second'] not in e['cuvees']:
            e['cuvees'].append(e['second'])
    return out


def code(label):
    low = label.lower().strip()
    for c, p in VARS:
        if re.match('(?i)' + p + '$', low):
            return c
    for c, p in VARS:
        if re.search('(?i)' + p, low):
            return c
    return None


# Extracted text, by path. Reading one sheet asks the same document
# five or six questions - is it a dossier, does it call itself a second
# wine, does it name another of the estate's wines, whose is it, what is
# its blend - and each one was opening the PDF again. Across the archive
# that is thirty thousand opens for five thousand sheets, and the full
# pass took longer than the ten minutes a command is allowed.
#
# The cache is per process and keyed on the path, so nothing survives a
# run. A sheet's text does not change while a run is reading it.
_TEXT = {}
_CACHE_LIMIT = 2000


def _cached(key, make):
    if key in _TEXT:
        return _TEXT[key]
    val = make()
    if len(_TEXT) >= _CACHE_LIMIT:
        _TEXT.clear()
    _TEXT[key] = val
    return val


def by_columns(path, pages=3):
    """The page's text, column by column, each read top to bottom.

    Grand-Puy-Ducasse publishes sixty-two vintages and every blend read
    off them came out as nonsense - "SB:13", Sauvignon Blanc in a
    Pauillac red - because the pages are set in two columns and a flat
    extraction interleaves them: "Sauvignon terroirssont entreprisde
    Pauillac". Sorting by position is not enough, because position is
    two-dimensional. The columns have to be found first.
    """
    return _cached(('cols', path, pages), lambda: _by_columns(path, pages))


def _by_columns(path, pages):
    out = []
    d = pymupdf.open(path)
    for i in range(min(pages, d.page_count)):
        page = d[i]
        width = page.rect.width or 600
        blocks = [b for b in page.get_text('blocks') if (b[4] or '').strip()]
        if not blocks:
            continue
        lefts = sorted(b[0] for b in blocks)
        cuts, prev = [], None
        for x in lefts:
            if prev is not None and x - prev > width * 0.18:
                cuts.append((prev + x) / 2)
            prev = x

        def col_of(b):
            return sum(1 for c in cuts if b[0] >= c)

        blocks.sort(key=lambda b: (col_of(b), round(b[1], 1), b[0]))
        out.append('\n'.join(b[4].strip() for b in blocks))
    d.close()
    return '\n'.join(out)


def flat(path, pages=0):
    return _cached(('flat', path, pages), lambda: _flat(path, pages))


def _flat(path, pages):
    d = pymupdf.open(path)
    n = d.page_count if not pages else min(pages, d.page_count)
    t = ' '.join(d[i].get_text() for i in range(n))
    d.close()
    return t


def unspace(text):
    """Put back a word that was set letter by letter.

    "A S S E M B L A G E" is nine single letters with single spaces
    between them. Four or more in a row is a spaced-out word and not
    four one-letter words, which French and English do not have.
    """
    return re.sub(r'(?:(?<=^)|(?<= ))(?:[A-Za-zÀ-ÿ] ){3,}'
                  r'[A-Za-zÀ-ÿ](?= |$)',
                  lambda m: m.group(0).replace(' ', ''), text)


def paired(win):
    """Shares in one column and varieties in the next.

    "85 % 15 % Merlot Cabernet franc" is a table read across: the first
    share belongs to the first variety. Only taken when the two counts
    match, there are at least two of each, and the shares make a
    hundred - otherwise it is a guess about a layout.
    """
    m = re.search(r'(?:\s*' + NUM + r'\s*%){2,}', win)
    if not m or m.start() > 40:
        return None
    nums = re.findall(NUM + r'\s*%', m.group(0))
    rest = win[m.end():]
    if re.search(r'\d', rest[:4]):
        return None
    names = []
    for x in re.finditer('(?i)' + NAMES, rest):
        if x.start() > 90:
            break
        names.append(code(x.group(0)))
    nums = [float(n.replace('%', '').replace(',', '.').strip()) for n in nums]
    if len(nums) < 2 or len(nums) != len(names) or None in names:
        return None
    if abs(sum(nums) - 100) > 1.5 or len(set(names)) != len(names):
        return None
    return dict(zip(names, nums))


# Words that distinguish nothing, because a sheet's prose is full of
# them. "Petit-Figeac" reduces to "petit", which matches Petit Verdot
# and flagged Figeac's own datasheet as its second wine's.
COMMON = set((
    'petit petite petits petites grand grande grands grandes haut haute '
    'hauts hautes clos vieux vieille vieilles cuvee reserve prestige '
    'chateau domaine blanc blanche rouge rose selection tradition '
    'merlot cabernet sauvignon semillon verdot franc malbec muscadelle '
    'carmenere cote cotes coteaux terrasses hauts bas fleur fleurs '
    'tour tours croix mont monts').split())


# "Second vin /Second wine : Les Chênes de Macquin" is a fact about the
# estate, printed among its bottling figures. So is Figeac's "Second
# wine: Petit-Figeac". Neither is the document claiming to be that wine,
# and both filed a grand vin's own sheet as its second wine's. A
# statement about another wine is not a claim to be it, so the label and
# the name it introduces come out before any name is looked for.
OTHER_LABEL = re.compile(
    r'(?i)(second\s*vin|second\s*wine|deuxi[eè]me\s*vin|'
    r'grand\s*vin|premier\s*vin|first\s*wine)'
    r'(\s*/\s*[a-zÀ-ÿ\s]{0,20})?\s*:\s*[^•\n\r]{0,60}')


def without_other_wine_labels(text):
    return OTHER_LABEL.sub(' ', text or '')


def norm(s):
    """Lower case, no accents, every separator a single space.

    Unlike packed(), this keeps the word boundaries - which matters,
    because packed() turned "marqué par des conditions" into
    "...marquepardesconditions..." and found "parde" in it, so a
    Haut-Bailly sheet was filed as La Parde de Haut-Bailly's on the
    strength of the French for "by the".
    """
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if not unicodedata.combining(c))
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip() + ' '


def says(text, name):
    """Does this text name that wine, as a name and not as a fragment?

    The words have to appear in order and whole. Spacing and
    punctuation between them is free, because a filename writes
    Haut-Carles, HAUT_CARLES and hautcarles alike.
    """
    words = [w for w in re.split(r'[^a-z0-9]+', norm(name)) if w]
    if not words:
        return False
    # Letters bound a name; digits do not. batailley2000-web_fr.pdf is
    # the estate's name with the year run onto it, and refusing that
    # left eighty-three correctly filed sheets looking unattributable.
    pat = (r'(?<![a-z])' + r'\s*'.join(re.escape(w) for w in words)
           + r'(?![a-z])')
    return bool(re.search(pat, norm(text)))


# A filename that says CHATEAU, CLOS or DOMAINE is naming its wine, and
# the words after it are that name:
# FICHE-PRODUIT-CHATEAU-HAUT-BRISSON-2018.pdf, which sat under Chateau
# Saint-Christophe in the Medoc and gave it a 90% Merlot right-bank
# blend. The name runs until a year, a language tag, or anything that is
# not a word.
HOUSE_IN_NAME = re.compile(
    r'(?i)(?<![a-z])(?:ch[aâ]teau|clos|domaine)[\s_\-]+'
    r'((?:(?!\d)(?:[a-zÀ-ÿ]{2,})[\s_\-]*){1,4})')
NOT_A_NAME = re.compile(r'(?i)^(fr|en|gb|eng|ang|de|es|it|zh|cn|ro|bl|'
                        r'rouge|blanc|rge|red|white|web|print|ft|td|cp|'
                        r'fiche|technique|produit|product|sheet|primeur|'
                        r'primeurs|millesime|vintage|final|version|vf|va)$')


def property_in_filename(filename):
    """The wine a filename names after the word Chateau, if any."""
    m = HOUSE_IN_NAME.search(filename or '')
    if not m:
        return None
    words = [w for w in re.split(r'[\s_\-]+', m.group(1)) if w]
    kept = []
    for w in words:
        if NOT_A_NAME.match(w):
            break
        kept.append(w)
    name = ' '.join(kept)
    return name if len(packed(name)) >= 5 else None


def says_in_name(filename, name):
    """The same test, loosened for a filename.

    A filename is a slug, not prose: lionsdebatailley2014-web_fr.pdf
    runs the words together, and requiring a boundary between them
    reported 424 correctly-filed second wines as misfiled. Prose is
    where the boundary matters - "marqué par des conditions" - and a
    filename does not contain prose, so there both forms count.
    """
    return (says(filename, name)
            or packed(name) in packed(filename or ''))


def mark_of(other, grand):
    mark = _mark_of(other, grand)
    # A mark has to be a word. "Cuvee 1762" reduced to 1762, which is
    # the founding year Marquis de Terme prints in its history, so the
    # estate's own 2011 sheet was filed as that cuvee's.
    if mark and not re.search(r'[a-z]{3}', mark):
        return None
    return mark


def _mark_of(other, grand):
    """What a wine's name has that the grand vin's name does not.

    Returned as words, not run together, so that says() can require
    them whole and in order: "haut carles" matches HAUT-CARLES,
    HAUT_CARLES and hautcarles, and "petit figeac" does not match
    "2% Petit Verdot".
    """
    g = packed(grand)
    # A parenthetical is a note to the reader, not part of the name:
    # "Haut-Carles (prestige cuvée)" is called Haut-Carles on its sheet.
    other = re.sub(r'\s*\([^)]*\)', '', other or '').strip()
    words = [w for w in re.split(r'[^A-Za-z0-9À-ÿ]+', other) if w]
    if not words:
        return None
    # One distinctive word is the best mark there is - but it has to be
    # a word. "Cuvee 1762" reduced to 1762, which is the founding year
    # Marquis de Terme prints in its history, so its own 2011 sheet was
    # filed as that cuvee's.
    for w in words:
        p = packed(w)
        if (len(p) >= 4 and p not in g and p not in COMMON
                and re.search(r'[a-z]{3}', p)):
            return p
    # Otherwise the whole name, less the words that distinguish nothing,
    # since those are the ones a filename drops. "D de Dauzac Blanc"
    # becomes "d de dauzac", which its sheet and its filename both
    # carry; "Petit-Figeac" keeps both words, because dropping "petit"
    # leaves only the estate's own name.
    kept = [w for w in words if packed(w) not in COMMON]
    if kept and packed(''.join(kept)) not in g:
        return ' '.join(kept).lower()
    if packed(''.join(words)) not in g:
        return ' '.join(words).lower()
    return None


def packed(s):
    import unicodedata
    s = ''.join(c for c in unicodedata.normalize('NFD', s or '')
                if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '', s.lower())


def blend_of(path, grand=None, others=(), both=False):
    """The blend, from the window the sheet labels as this wine's.

    A sheet often carries more than one blend. Haut-Bailly's 2021 sheet
    says "Assemblage Château Haut-Bailly 2021 : 65 % Cabernet Sauvignon
    22 % Merlot 10 % Petit Verdot 3 % Cabernet Franc" and then
    "Assemblage Haut-Bailly II 2021 : 70 % Merlot 25 % Cabernet
    Sauvignon", and Haut-Bailly II is the second wine. Taking the first
    labelled window found is not enough, because reading the page column
    by column can put the second wine's first.

    So where the estate's other wines are known, a window that names one
    of them is refused, and a window that names the grand vin is
    preferred over one that names nothing.
    """
    # Both readings of the page are considered, because each fails
    # differently. A flat extraction interleaves two columns into
    # nonsense; reading column by column can separate a label from the
    # figures that belong to it, which is what Haut-Bailly's 2021 sheet
    # does. A window that names its wine is believed from either.
    texts = []
    for fn in (lambda: flat(path), lambda: by_columns(path, 3)):
        try:
            t = re.sub(r'\s+', ' ', unspace(fn()))
        except Exception:
            continue
        if t and WINE_LABEL.search(t):
            texts.append(t)
    if not texts:
        return (None, None) if both else None
    marks = [m for m in (mark_of(o, grand or '') for o in (others or ())) if m]
    gmark = None
    if grand:
        bare = re.sub(r'(?i)^(château|chateau|clos|domaine)\s+', '',
                      grand)
        gmark = norm(bare).strip()

    # The flat reading first, and the column reading only if the flat
    # one finds nothing.
    #
    # I had this the other way round, with a score to break the tie, and
    # measured it: across 1,401 sheets the two readings disagree 16
    # times, and the record that was checked by hand agrees with the
    # flat reading 13 of those and the column reading twice. On
    # Grand-Puy-Ducasse, the estate by_columns was written for, they no
    # longer disagree at all.
    #
    # The reorder's failure is the more dangerous one, because it joins
    # a label to another label's figures and the result looks right:
    # Lacour-Jacquet's "Assemblage 55% Cabernet Sauvignon ...
    # Encepagement 50% Cabernet Sauvignon" becomes Assemblage 50%, and
    # Badette's bare "Assemblage" table heading acquires a 90/7/3 block
    # from a neighbouring column while the prose says 95/5.
    #
    # Columns still earn their place: on 66 of those sheets the flat
    # reading found nothing and the column reading found the blend.
    #
    # And where both readings resolve but disagree, neither is believed.
    # Ferriere's 2019 sheet is a table: read flat, "Assemblage" is
    # followed by "Elevage Second vin Claire VILLARS LURTON" and the
    # figures picked up belong to another section; read column by
    # column it says "Assemblage 70 % cabernet sauvignon, 25 % merlot,
    # 5 % petit verdot", which is right. Trotte Vieille and Pape Clement
    # are the other way round. There is no order that is right for both,
    # so the sheet is reported rather than guessed at - which is what
    # the report is for.
    found = []
    for text in texts:
        wins = []
        for m in WINE_LABEL.finditer(text):
            win = text[m.end():m.end() + 240]
            # Whose blend is this? Decided on the words right after the
            # label, before any figure is read - and kept as words, so
            # that a wine's name is matched as a name.
            lead_in = win[:70]
            # "Blend: 87% Merlot & 13% Cabernet Franc" is the data
            # block; "blend of 80% Merlot and 20% Cabernet Franc" is the
            # tasting note two inches below it, and La Conseillante's
            # 2020 sheet carries both. The data block is the wine's
            # figures, so a label followed by "of" or "de" goes second.
            prose = bool(re.match(r'(?i)\s*(of|de)\s', win))
            wins.append((lead_in, _from_window(win), prose))

        # Best first: the data block that names this wine, then any data
        # block, then the prose that names it, then any prose.
        ranked = []
        for lead_in, got, prose in wins:
            if not got or any(says(lead_in, k) for k in marks):
                continue
            named = bool(gmark and says(lead_in, gmark))
            ranked.append(((1 if prose else 0, 0 if named else 1), got))
        if not ranked:
            continue
        ranked.sort(key=lambda r: r[0])

        # If several data blocks give different blends and not one of
        # them names this wine, the document has not said which is
        # which and there is nothing to choose between them. Giscours'
        # Carnet Primeurs 2025 carries "ASSEMBLAGE - BLEND 60 % Merlot
        # 35 % Cabernet Sauvignon 5 % Cabernet Franc" and "ASSEMBLAGE -
        # BLEND 86 % Cabernet Sauvignon 7 % Merlot 7 % Petit Verdot" -
        # the second wine and the grand vin, in that order, under
        # identical headings. Refuse it. A coin toss recorded as a fact
        # is worse than a gap.
        blocks = [g for (pr, nmd), g in ranked if pr == 0]
        named_any = any(nmd == 0 for (pr, nmd), g in ranked)
        distinct = []
        for b in blocks:
            if not any(b == d for d in distinct):
                distinct.append(b)
        if len(distinct) > 1 and not named_any:
            return (None, None) if both else None
        found.append(ranked[0][1])

    if not found:
        return (None, None) if both else None
    if both:
        return (found[0], found[1] if len(found) > 1 else None)
    return found[0]


WHITE_CTX = re.compile(r'(?i)(s[eé]millon|muscadelle)')
RED_CTX = re.compile(r'(?i)(merlot|cabernet[\s\-]*franc|petit[\s\-]*verdot|'
                     r'malbec|carm[eé]n[eè]re)')
BARE_SAUV = re.compile(r'(?i)(?<!cabernet )(?<!cabernet-)'
                       r'(?<![a-zà-ÿ])sauvignons?'
                       r'(?![\s\-]*(?:blanc|gris))')
BARE_CAB = re.compile(r'(?i)(?<![a-zà-ÿ])cabernets?'
                      r'(?![\s\-]*(?:sauvignon|franc))')


def disambiguate(win):
    """Say which grape a bare name means, from the company it keeps.

    "Sauvignon 25%" is Sauvignon Blanc beside Semillon and Cabernet
    Sauvignon beside Merlot, and the sheets write it both ways. Guessing
    one of them would have been wrong half the time, so it is read from
    the other varieties in the same window; where the window has both a
    white and a red variety it is left alone, because then it genuinely
    is not clear.

    "Cabernet 31%" is always Cabernet Sauvignon - no Bordeaux sheet
    abbreviates Cabernet Franc to Cabernet.
    """
    white, red = bool(WHITE_CTX.search(win)), bool(RED_CTX.search(win))
    if white and not red:
        win = BARE_SAUV.sub('Sauvignon Blanc', win)
    elif red and not white:
        win = BARE_SAUV.sub('Cabernet Sauvignon', win)
    return BARE_CAB.sub('Cabernet Sauvignon', win)


def _from_window(win):
    """The figures in one labelled window."""
    win = disambiguate(win)
    s = STOP.search(win)
    if s and s.start() > 10:
        win = win[:s.start()]
    v = VINE_LABEL.search(win)
    if v and v.start() > 0:
        win = win[:v.start()]
    side = paired(win)
    if side:
        return side
    a, b = {}, {}
    for x in PCT_FIRST.finditer(win):
        c = code(x.group(2))
        if c and c not in a:
            a[c] = float(x.group(1).replace(',', '.'))
    for x in VAR_FIRST.finditer(win):
        c = code(x.group(1))
        if c and c not in b:
            b[c] = float(x.group(2).replace(',', '.'))
    ao = a and abs(sum(a.values()) - 100) <= 1.5
    bo = b and abs(sum(b.values()) - 100) <= 1.5
    if ao and not bo:
        return a
    if bo and not ao:
        return b
    if ao and bo:
        if a == b:
            return a
        # Both add up, so the one that adds up better is the one
        # whose varieties were paired with the right shares.
        # "Cabernet sauvignon 67 % Merlot 32 %" reaches 99 read
        # either way, and the reading nearer 100 is the right one.
        da, db = abs(sum(a.values()) - 100), abs(sum(b.values()) - 100)
        if abs(da - db) > 0.01:
            return a if da < db else b
    return None


def vintage_of(text):
    """The year the document states, before the year anyone guessed."""
    for rx, how in ((LABEL, 'the millésime label'),
                    (VINTAGE, 'the vintage label'),
                    (BEFORE, 'the year before the word vintage')):
        m = rx.search(text)
        if m:
            return int(m.group(1)), how
    years = YEAR.findall(text[:3000])
    if years:
        y, n = collections.Counter(years).most_common(1)[0]
        if n >= 2:
            return int(y), 'the commonest year on the page'
    return None, 'no vintage in the document'


def is_second_wine(path):
    """Does the document say it is the second wine?

    Belgrave 2023 came through at 65% Merlot against an estate that is
    55% Cabernet, and its document opens "SE C O N D VI N D U CH ÂT EA U
    BE LG RA V E" - chunked, not evenly letter-spaced, so no tidy
    unspacing finds it. Taking every space out of the opening and
    looking for the phrase run together does.

    Taking the spaces out destroys word boundaries, though, so the
    phrase has to be the document's own title and not a fact in a list.
    Figeac's datasheet says "41 hectares (101 acres) under vines. Second
    wine: Petit-Figeac" among its estate facts, two hundred characters
    in and followed by a colon that introduces a different wine - and
    that filed Figeac's own datasheet as its second wine's. So: near the
    very top, and not used as a label.
    """
    import unicodedata
    try:
        head = flat(path, 1)
    except Exception:
        return False
    s = re.sub(r'\s+', '', head)[:400].lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if not unicodedata.combining(c))
    for phrase in ('secondvin', 'deuxiemevin', 'secondwine'):
        i = s.find(phrase)
        if i < 0 or i > 120:
            continue
        after = s[i + len(phrase):i + len(phrase) + 1]
        if after == ':':
            continue        # a label naming another wine, not a title
        if after == 's':
            # "mapping of the first and second wines - 2025", which is
            # Pedesclaux's own sheet talking about both of them.
            continue
        if s[max(0, i - 3):i] in ('and', 'et'):
            continue
        return True
    return False


def names_another_wine(path, filename, grand, second):
    """Does this sheet name the second wine rather than the grand vin?

    Branaire-Ducru's library holds Duluc de Branaire-Ducru sheets, and
    Duluc never says "second vin" about itself - it just says Duluc. The
    estates data already records every second wine's name, so the test
    is whether the document, or its filename, names that wine ahead of
    the grand vin. 136 estates name their second wine; where one does
    not, this says nothing and the other tests still apply.

    The letterhead comes off first, for the same reason as always.
    """
    if not second:
        return None
    # The distinctive part of the other wine's name: what it has that
    # the grand vin's name does not. "Duluc de Branaire-Ducru" against
    # "Chateau Branaire-Ducru" leaves "duluc".
    mark = mark_of(second, grand)
    if not mark:
        return None

    # Named in the filename, the file says whose it is and that settles
    # it. Named only in the body, it settles nothing on its own: a sheet
    # that carries both wines names both. Haut-Bailly's 2022 sheet says
    # "Blend Chateau Haut-Bailly 2022 : 56% ..." and then "Blend
    # Haut-Bailly II 2022 : 65% Merlot ...", and it is the grand vin's
    # sheet as much as the second wine's. So the body only decides when
    # the grand vin is not in it at all - which is true of Duluc's own
    # sheet, where Branaire-Ducru appears solely in the address.
    if says_in_name(filename, mark):
        return second
    # Bordeaux names a good many wines with a single letter and the
    # estate's name: Y d'Yquem, G d'Estournel, R de Rieussec, D de
    # Dauzac. The letter carries all the meaning and no name-matching
    # will find it, because one letter matches everything. But the
    # filename writes it the same way every time - Y2022_Fiche-
    # Millesime_Chateau-dYquem.pdf - with the letter first and a year
    # or a separator after it.
    #
    # Yquem 2022 held Y's blend and Y's tasting note, read off
    # Y2022_Fiche-Millesime, and Y is the dry white.
    initial = re.match(r'(?i)^([a-z])\s+(?:d’|d\'|de\s+|du\s+)',
                       re.sub(r'\s*\([^)]*\)', '', second or '').strip())
    if initial and re.match(r'(?i)^%s[\d_\-]' % re.escape(initial.group(1)),
                            filename or ''):
        return second
    # Otherwise it comes down to the title: whichever wine the document
    # names first is the one it is for. "HAUT-CARLES 2017 LE VIGNOBLE"
    # opens Haut-Carles' sheet and "CHÂTEAU DE CARLES 2018" opens the
    # grand vin's, and both mention de Carles further down, where the
    # owner is named.
    head = without_other_wine_labels(body_without_letterhead(path, 1))
    title = head[:TITLE * 2]
    if not says(title, mark):
        return None
    gbare = re.sub(r'(?i)^(château|chateau|clos|domaine)\s+', '',
                   grand or '')
    if not (gbare and says(title, gbare)):
        return second

    # Both names are in the title, which happens whenever the other
    # wine's name contains the estate's - L'Abeille de Fieuzal, Le
    # Marquis de Calon-Segur, Pavillon Rouge du Chateau Margaux, Les
    # Pensees de Lafleur. Then the one named first is the one the
    # document is for: "L'Abeille rouge devoile une robe rouge rubis"
    # opens a sheet for the second wine even though Fieuzal follows two
    # words later.
    flat_title = norm(title)
    where = {}
    for nm, label in ((mark, 'other'), (gbare, 'grand')):
        words = [w for w in re.split(r'[^a-z0-9]+', norm(nm)) if w]
        if not words:
            continue
        m = re.search(r'(?<![a-z])' + r'\s*'.join(re.escape(w)
                                                  for w in words)
                      + r'(?![a-z])', flat_title)
        if m:
            where[label] = m.start()
    if ('other' in where and 'grand' in where
            and where['other'] < where['grand']):
        return second
    return None


WHITE_VARS = set(['SEM', 'SB', 'SG', 'MU'])
# How a sheet says in its own filename which wine it is for.
SAYS_WHITE = re.compile(r'(?i)(?<![a-z])(blanc|blanche|blc|bl|white|blanco)'
                        r'(?![a-z])')
SAYS_RED = re.compile(r'(?i)(?<![a-z])(rouge|rge|ro|red|tinto)(?![a-z])')
SAYS_DRY = re.compile(r'(?i)(?<![a-z])(sec|s[eè]che|dry|'
                      r'grand\s*vin\s*sec)(?![a-z])')
# A rose is made from red grapes, so no blend will ever betray it - only
# the filename will. Domaine de Chevalier 2019 held "ASSEMBLAGE : 70%
# Cabernet Sauvignon ; 30 % Merlot" off Chevalier-Rose-2019-FT-FR.pdf,
# and Desmirail two vintages off FT-ROSE-2021-FR.pdf and -2024-.
SAYS_ROSE = re.compile(r'(?i)(?<![a-z])(ros[eé]s?|rosado|clairet)'
                       r'(?![a-z])')


def wrong_colour(filename, blend, cat):
    """Is this a different-coloured wine from the one it is filed under?

    Nearly every classified red estate also makes a white, and the two
    sheets sit in the same folder with almost the same name:
    Olivier-2012-FT-FR and Olivier-Blc-2014-FT-FR,
    Cos-dEstournel-Blanc-2015-FT-FR, Haut-Brion-Blanc-2016-FT-GB,
    ft_pape-clement-blanc-2018. Read as the grand vin they put Sauvignon
    Blanc and Sémillon on a Pauillac or a Pessac red.

    Two independent signals, either of which is enough: the filename
    says which colour it is, or the blend is made of varieties the
    estate's wine is not made of. The second catches a white sheet whose
    filename does not say so, which is why it is not simply left to the
    gate at merge time.
    """
    share = (sum(v for k, v in (blend or {}).items() if k in WHITE_VARS)
             if blend else None)
    # Carbonnieux-Rge-Blc-2018-FT-FR.pdf is one sheet for the red and
    # the white, and the manifest already has a word for that - role
    # combined, "one sheet covering both the red and the white, so
    # either may cite it". Saying both colours is not saying the wrong
    # one.
    if (SAYS_WHITE.search(filename or '')
            and SAYS_RED.search(filename or '')):
        return None
    # No estate in this dashboard is judged on its rose.
    if SAYS_ROSE.search(filename or ''):
        return 'the filename says it is the rosé'
    if cat == 'red':
        if SAYS_WHITE.search(filename or ''):
            return 'the filename says it is the white'
        if share is not None and share > 50:
            return 'the blend is a white wine’s'
    elif cat == 'sweet':
        # A Sauternes is made of white grapes, so the share says nothing
        # about it - treating "sweet" as a red estate rejected every
        # Sauternes sheet in the archive as a white wine's. What does
        # distinguish these estates' two wines is dry against sweet:
        # the Grand Vin Sec de Doisy Daene, R de Rieussec, Y d'Yquem.
        if SAYS_DRY.search(filename or ''):
            return 'the filename says it is the dry white'
        if share is not None and share < 50:
            return 'the blend is a red wine’s'
    elif cat == 'white':
        if share is not None and share < 50:
            return 'the blend is a red wine’s'
    return None


def confirms_estate(path, filename, grand, cuvees=()):
    """Does this sheet name the estate it is filed under?

    A folder is not a claim about a document. Malartic-Lagravière's
    library holds Diamandes de Uco - the same family's Mendoza estate -
    and one of those sheets was filed as Malartic's grand vin, which
    gave it an Argentine Cabernet's alcohol, oak and press scores. The
    same folder holds Gazin-Rocquencourt, which is not in this
    dashboard at all.

    The test is that the estate is named somewhere - in the filename, or
    in the document with the letterhead off. Diamandes de Uco never
    mentions Malartic at all, which is the whole of its case.

    I tried a second clause first: reject a filename carrying any long
    word that belongs to no wine of this estate. It rejected fifty-nine
    sheets that were correctly filed, because filenames are full of
    appellations (Chateau_Suduiraut_..._Sauternes_2001), of words like
    compressed and commentaires, and of hex that reads as letters
    (66deb5cbdbede8689cb3c02d). Each exception needed another word in a
    list, which is the sign of a rule shaped wrong.

    What that clause was really for is two narrower things that have
    their own tests: a sheet for another of the estate's own wines, which
    is names_another_wine, and a sibling property sharing the folder,
    which is SIBLINGS below - a short list, because each entry is a
    claim about one estate and ought to be read as one.

    Three answers, not two, because "the document does not name the
    estate" and "the document names another estate" are different
    facts. Camensac's 2025 sheet and Desmirail's 2016 name their
    château only in the logo at the top, which is an image, so no
    extraction will ever find it. Those are not somebody else's sheets;
    they are sheets whose only evidence is the folder they came in, and
    the manifest already has a word for that.

      'named'   the filename or the document names this estate
      'folder'  nothing in it names any estate; the folder is all there is
      'other'   it names a sibling property, so it is not this wine's
    """
    for mark, owner in SIBLINGS.items():
        if says_in_name(filename, mark) and owner != grand:
            return 'other'
    if not grand:
        return 'folder'
    want = [grand] + list(cuvees or ())
    marks = []
    for nm in want:
        # The house word and the article come off, in that order. Yquem
        # files as Yquem-2015-FT-FR, and keeping the article made
        # "Château d'Yquem" reduce to dyquem, which matches nothing -
        # that one mistake discarded 29 Domaine de Chevalier sheets, 28
        # Camensac and 8 Ferrand, and failed to match 126 more.
        bare = re.sub(r'(?i)^(château|chateau|clos|domaine|vieux\s+'
                      r'château)\s+', '', nm or '')
        bare = re.sub(r"(?i)^(d'|de\s+|du\s+|des\s+|la\s+|le\s+|les\s+|l')",
                      '', bare)
        # As words, not run together, so says() can require them whole:
        # "mission haut brion" matches MissionHBR's "Mission Haut-Brion"
        # where the run-together form never would.
        for cand in (bare, nm):
            w = norm(cand).strip()
            if len(packed(w)) >= 5:
                marks.append(w)
        for w in re.split(r'[\s\-–]+', nm or ''):
            p = packed(w)
            if len(p) >= 5 and p not in COMMON:
                marks.append(p)
    if not marks:
        return 'folder'
    if any(says_in_name(filename, k) for k in marks):
        return 'named'
    body = body_without_letterhead(path, 1)
    if any(says(body, k) for k in marks):
        return 'named'
    return 'folder'


# A role whose note says why it was given. Those reasons were reached by
# reading the documents, and no rule here knows them, so no rule here
# may overturn them.
#
# The Dubourdieu dossiers are the case in point. They are press dossiers
# - history, plantings, standing practice, clippings - and is_dossier()
# cannot tell, because each one does carry a "Millésime : 2016" label at
# the top. What identified them was the shape of the whole set: one
# document per property, with the same text under every year. A
# re-judging pass that did not know that put 27 of them back as grand
# vins in one go.
REASONED = re.compile(r'(?i)(press dossier|press release|another property|'
                      r'the estate’s dry white|'
                      r'hectares of new planting|'
                      r'not in this dashboard|'
                      r'not a technical sheet|'
                      r'one sheet for the|covers both|'
                      r'calls itself the second wine)')


def role_is_reasoned(sheet):
    return bool(REASONED.search(sheet.get('note') or ''))


def is_dossier(path):
    """Is this a press dossier rather than a vintage's sheet?

    Two tells: it says so, or it carries no vintage label at all while
    running to several pages of history and clippings. Either way its
    figures are the property's standing ones and belong to no year.
    """
    try:
        d = pymupdf.open(path)
        n = d.page_count
        d.close()
        text = re.sub(r'\s+', ' ', flat(path))
    except Exception:
        return False
    if DOSSIER.search(text[:1500]):
        return True
    if n >= 3 and not LABEL.search(text) and not VINTAGE.search(text):
        clippings = len(re.findall(r'(?i)(note\s*:|score\s*:|/\s*20\b|'
                                   r'\b9[0-9]\s*-\s*9[0-9]\b)', text))
        return clippings >= 4
    return False


def body_without_letterhead(path, pages=2):
    """The document with its contact block removed.

    So that an estate's name is read from what the sheet says about the
    wine, and not from the email address in its header.
    """
    try:
        d = pymupdf.open(path)
        got = [d[i].get_text() for i in range(min(pages, d.page_count))]
        d.close()
    except Exception:
        return ''
    keep = []
    for page in got:
        for line in page.split('\n'):
            if not CONTACT.search(line):
                keep.append(line)
    return re.sub(r'\s+', ' ', ' '.join(keep))
