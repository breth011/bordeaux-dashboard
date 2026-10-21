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
import io, os, re, collections, difflib, warnings
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


# ===========================================================================
#   WHAT A FICHE STATES, FIELD BY FIELD
#
#   read-sheets.py proposed a blend and nothing else, so every other
#   figure in fiches.js was typed in by hand: barrel months on 48% of
#   records, yield 35%, new oak 27%, alcohol 25%, pH 11%, harvest dates
#   7%. Sampling 158 sheets of vintages that already had a record showed
#   what that costs - 59 of them state a tasting note the record lacks,
#   48 a season, 46 harvest dates, 45 an alcohol - about 3,500 field
#   values across the 1,806 vintages that have both a sheet and a
#   record.
#
#   These are the rules for reading them. They live here and not in the
#   tool for the same reason every other reading rule does: there is one
#   library, and a pattern that is wrong is wrong everywhere at once.
# ===========================================================================

# --------------------------------------------------------------- gates
#
# A range a Bordeaux fiche can actually state. Outside it the figure was
# misread - a pH of 13.5 is an alcohol, an alcohol of 45 is a yield, a
# yield of 7200 is a planting density - and is dropped.
GATES = {
    'alc': (10.0, 17.0),
    'ph': (2.8, 4.2),
    'yld': (5.0, 70.0),
    'months': (6.0, 36.0),
    'oak': (0.0, 100.0),
}

MONTH = {'janvier': 1, 'january': 1, 'février': 2, 'fevrier': 2,
         'february': 2, 'mars': 3, 'march': 3, 'avril': 4, 'april': 4,
         'mai': 5, 'may': 5, 'juin': 6, 'june': 6, 'juillet': 7,
         'july': 7, 'août': 8, 'aout': 8, 'august': 8,
         'septembre': 9, 'september': 9, 'octobre': 10, 'october': 10,
         'novembre': 11, 'november': 11, 'décembre': 12,
         'decembre': 12, 'december': 12}
MON = '|'.join(sorted(MONTH, key=len, reverse=True))

# --------------------------------------------------------- the patterns
#
# Each is anchored on a label the sheet prints. Nothing is read from
# position alone, for the same reason blend_of refuses an unlabelled
# window: a fiche is a form, and a number with no label beside it
# belongs to whatever happens to be next to it on the page.

# "Alcool : 13,5 % vol." / "Alcohol 14% vol" / "Degre alcoolique 13,5"
# "potentiel" is excluded on purpose. Siaurac prints "DEGRE D'ALCOOL
# POTENTIEL : 14,5%", which is the sugar in the grapes at harvest
# expressed as the alcohol it could become - not the alcohol in the
# bottle. Thirteen readings came from that line and they are a different
# measurement, so they are refused rather than filed as alc.
RX_ALC = re.compile(
    r'(?i)(?:alcool|alcohol(?:\s+content|\s+by\s+volume)?|'
    r'degr[eé]\s*(?:alcoolique)?|teneur\s+en\s+alcool|titre\s+alcoom)'
    r'(?![^0-9%]{0,24}potentiel)'
    r'(?:(?!potentiel|potential)[^0-9%]){0,24}(\d{1,2}[,.]?\d?)\s*%?\s*'
    r'(?:vol|%)')
# a bare "13,5 % vol." with no label, which many sheets print
RX_ALC2 = re.compile(r'(?<![\d,.])(\d{2}[,.]\d)\s*%\s*vol')

RX_PH = re.compile(r'(?i)\bph\b[^0-9]{0,12}(\d[,.]\d{1,2})')

RX_YLD = re.compile(
    r'(?i)(?:rendement|yield)s?[^0-9]{0,24}(\d{1,2}(?:[,.]\d)?)\s*'
    r'(?:hl\s*/\s*ha|hl/ha|hectolitres)')
RX_YLD2 = re.compile(
    r'(?i)(\d{1,2}(?:[,.]\d)?)\s*(?:hl\s*/\s*ha|hl/ha)')

# "18 mois en barriques" / "ageing 16 months" / "Elevage : 12 mois"
RX_MONTHS = re.compile(
    r'(?i)(?:[eé]levage|ageing|aging|matur(?:ation|ing)|barrel\s+ag)'
    r'[^0-9]{0,40}(\d{1,2})(?:\s*(?:-|to|à|a)\s*(\d{1,2}))?\s*'
    r'(?:mois|months)')
RX_MONTHS2 = re.compile(
    r'(?i)(\d{1,2})(?:\s*(?:-|to|à)\s*(\d{1,2}))?\s*(?:mois|months)\s+'
    r'(?:en\s+)?(?:barriques?|f[uû]ts?|barrels?|oak)')

# "65 % de barriques neuves" / "new barrels 69%" / "60% new oak"
RX_OAK = re.compile(
    r'(?i)(\d{1,3})\s*%\s*(?:de\s+|of\s+)?(?:barriques?\s+|f[uû]ts?\s+|'
    r'barrels?\s+|oak\s+)?(?:neuves?|neufs?|new)')
RX_OAK2 = re.compile(
    r'(?i)(?:barriques?\s+neuves?|f[uû]ts?\s+neufs?|new\s+(?:oak|barrels?|'
    r'wood))[^0-9%]{0,16}(\d{1,3})\s*%')

# "Vendanges : du 18 septembre au 2 octobre" / "Harvest 25th September
# to 8th October" / "Vendanges le 17 septembre"
RX_HARV = re.compile(
    r'(?i)(?:vendanges?|r[eé]colte|harvest(?:ing|ed)?(?:\s+dates?)?|'
    r'picking)[^0-9]{0,30}'
    r'(?:du\s+|from\s+|le\s+)?(\d{1,2})(?:st|nd|rd|th|er)?\s*'
    r'(?:(' + MON + r')\s*)?'
    r'(?:\s*(?:au|to|-|jusqu’au|jusqu\'au)\s*'
    r'(\d{1,2})(?:st|nd|rd|th|er)?\s*(' + MON + r')?)?')

RX_TEMP = re.compile(
    r'(?i)(?:temp[eé]rature\s+(?:de\s+)?service|servir\s+(?:entre\s+)?'
    r'[aà]?|serve\s+(?:it\s+)?at|service\s+temperature)'
    r'[^0-9]{0,16}(\d{1,2})(?:\s*(?:-|to|à|et)\s*(\d{1,2}))?\s*'
    r'(?:°|degr|c\b)')

# ---------------------------------------------------- the stop-list
#
# Where the prose must not run on to. Each of these was trimmed out of a
# description by hand this week, which is the only reason the list is
# this specific.
PROSE_STOP = re.compile(
    r'(?i)('
    r'jean-ren[eé]\s+matignon|pierre\s+mont[eé]gut|directeur\s+technique|'
    r'technical\s+(?:manager|director)\s*[-–]|'
    r'date\s+de\s+mise\s+en\s+bouteille|mise\s+en\s+bouteille\s*:|'
    r'bottling\s+date|analyse\s|analyses\s*:|'
    r'harvest\s+time|dates?\s+de\s+vendanges?|'
    # Coutet prints its whole technical block under the season heading,
    # with no colons anywhere: "VENDANGES ... DATES DE VENDANGES 14
    # septembre au 3 octobre 2011 NOMBRE DE PASSAGES 4 tries ...
    # ASSEMBLAGE 75 % Semillon ... FERMENTATION en barriques ELEVAGE 18
    # mois ... MISE EN BOUTEILLES Juin 2013 COMMENTAIRES DE
    # DEGUSTATION". Requiring the colon let all of it into the note.
    r'nombre\s+de\s+(?:passages|jours)|'
    # La Tour Blanche appends its drinking advice to the tasting note:
    # "Mars 2010 Periode de degustation recommandee : Des aujourd'hui.
    # Apogee vers 2020. Decantation : de quelques minutes a plusieurs
    # heures selon l'age du vin." Those belong in window and decant,
    # which this file has fields for, and the reader does not read them
    # yet - so for now the prose stops there rather than swallowing them.
    r'p[eé]riode\s+de\s+d[eé]gustation|d[eé]cantation\s*:|'
    r'apog[eé]e\s+vers|drinking\s+window|'
    r'mise\s+en\s+bouteilles?|fermentation\s+en\s+barriques?|'
    r'commentaires?\s+de\s+d[eé]gustation|'
    r'[eé]levage\s+\d+\s+mois|assemblage\s+\d{1,3}\s*%|'
    r'surface\s+area|viticulture\s+by\s+plot|'
    r'enc[eé]pagement|grape\s+varieties|'
    r'\d{13}|'                              # an EAN barcode
    r'www\.|@|t[eé]l\.|\+\s*33|'            # contact details
    r'\d{5}\s+[A-Z][a-z]|'                  # a postcode and town
    r'scea\b|earl\b|sas\b|gfa\b|'           # the company
    r'accords?\s+mets|food\s+pairing|'      # belongs in food
    r'\d+\s*€|\d+\s*euros?|'           # a price list
    r'suivez-nous|follow\s+us|instagram|'
    # A critic's name starts a press citation, and press scores have
    # their own field. Beychevelle's 2010 note ran on into "La Revue
    # des Vins de France" and would have carried the review with it.
    r'la\s+revue\s+d(?:u|es)\s+vins?|wine\s+advocate|robert\s+parker|'
    r'james\s+suckling|jancis\s+robinson|neal\s+martin|vinous|'
    r'decanter|falstaff|wine\s+spectator|yves\s+beck|'
    r'bettane|antonio\s+galloni|\d{2,3}\s*/\s*100|'
    # More of the same, each from a description that ran on into it:
    # Lafite's 1968 and 1978 and L'Evangile's 1996 tasting notes all
    # continued into "TECHNICAL INFORMATION Varietals : Cabernet
    # sauvignon 59%..."; Beychevelle's 2006 into "Gault&Millau";
    # Ferriere's 2015 opened on "RVF - 16 / 17 -"; Siaurac's 2017 ran
    # into "Le Vignoble TERROIR".
    r'technical\s+information|informations?\s+techniques?|'
    r'varietals?\s*:|le\s+vignoble\b|the\s+vineyard\b|'
    r'gault\s*&?\s*millau|\brvf\b|guide\s+hachette|'
    r'\d{1,2}\s*/\s*20\b|'                  # a French twenty-point score
    r'pluviom[eé]trie|ensoleillement|amplitude\s+thermique|'
    # A score followed by a critic's initial, which is how Siaurac's
    # 2019 tasting note ended: "92-93 A. GALLONI 91 J.". The surnames
    # alone matter too, since the sheets abbreviate the first name.
    r'\d{2}\s*[-–]\s*\d{2}\s+[A-Z]\.|'
    r'\b(?:GALLONI|SUCKLING|PARKER|ROBINSON|BECK|DUBOURDIEU|BETTANE)\b'
    r')')

# A tasting note talks about tasting. Beychevelle's 2007 sheet puts
# "Prolonge d'un vaste parc qu'anime une piece d'eau, ce magnifique
# chateau est un paradis pour le promeneur" under DEGUSTATIONS, which is
# a description of the park. It has a heading, it is prose, and it is not
# about the wine - so the window must also say one of the things a
# tasting note says.
TASTES_OF = re.compile(
    r'(?i)(?<![a-zà-ÿ])'
    r'(nez|bouche|robe|palais|tanins?|tannins?|ar[oô]mes?|'
    r'attaque|finale|fruit|fruits?\s+(?:rouges?|noirs?)|'
    r'nose|palate|tannins?|aromas?|finish|attack|texture|'
    r'bouquet|colour|color|velout|soyeu|dense|frais|fra[iî]che)'
    r'(?![a-zà-ÿ])')

LABEL_TASTE = re.compile(
    r'(?i)(commentaire\s+de\s+d[eé]gustation|notes?\s+de\s+d[eé]gustation|'
    r'tasting\s+(?:notes?|comments?)|d[eé]gustations?|'
    r'fiche\s+de\s+d[eé]gustation)')
# The plural mattered. Beychevelle prints "DEGUSTATIONS 2004" and a
# pattern ending at "DEGUSTATION" left the S behind, so every tasting
# note it proposed began "S 2004 Sous sa robe grenat...".
LEADING_YEAR = re.compile(r'^(?:19|20)\d{2}\s*[-:–]?\s*')

# Is this prose, or is it a table that happens to sit under a heading?
#
# "filters keep passing fax numbers and phenology tables as tasting
# notes" is a lesson this project has already paid for, and here it is
# again: under MILLESIME 2018 Beychevelle prints "LES CONDITIONS
# CLIMATIQUES STADES CEPAGES Merlot Cab. Sauvignon Debourrement 30/03
# 5/04 Floraison...", which is a phenology table. It has a heading, it
# is long enough, and it is not a description of anything.
#
# A sentence has small words in it - de, la, and, the, is - and few
# digits. A table has dates, slashes and capitals and almost no
# connectives. Those two facts separate them.
_SMALL = re.compile(r'(?i)(?<![a-zà-ÿ])'
                    r'(?:de|du|des|la|le|les|un|une|et|est|sont|dans|'
                    r'avec|sur|pour|plus|tr[eè]s|the|a|an|of|and|is|'
                    r'are|in|with|on|for|its|this|that)'
                    r'(?![a-zà-ÿ])')


def looks_like_prose(s):
    if len(s) < 80:
        return False
    digits = sum(c.isdigit() for c in s)
    if digits > len(s) * 0.12:
        return False
    if len(re.findall(r'\d{1,2}\s*/\s*\d{1,2}', s)) >= 2:
        return False          # a column of dates
    # A run of capitals is a row of table headings, not a sentence.
    # Trotte-Vieille's 2021 tasting note opened on "PLUVIOMETRIE
    # MENSUELLE ENSOLEILLEMENT MENSUEL AMPLITUDE THERMIQUE JOURNALIERE
    # MOYENNE" and passed on the strength of the "avec des" behind it.
    letters = [c for c in s if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) > len(letters) * 0.35:
        return False
    small = len(_SMALL.findall(s))
    if small < max(4, len(s) // 90):
        return False
    # And the small words must be near the front. A sentence has one in
    # its first line; a list of adjectives has none until the prose
    # starts. Giscours prints "IM PER TUR BAB LE Audacieux Bold Precis
    # Precise Veloute Velvety Profond Deep Frais Fresh GISCOURS 2025 39"
    # and then its tasting note, and counting across the whole window
    # let the note's own connectives vouch for the word-cloud above it.
    return len(s) < 90 or len(_SMALL.findall(s[:90])) >= 2


# Leading rubbish a window opens on: a bullet glyph that extracted as a
# letter (Beauregard's 2018 note is peppered with "v La pluviometrie"),
# and a harvest fragment left over from the line above (Berliquet's 2022
# note began "Merlot : du 29 aout au 5 septembre Le premier nez est
# floral").
_M = r'(?:septembre|octobre|ao[uû]t|novembre|september|october|august)'
LEAD_JUNK = re.compile(
    r'^(?:[•▪●·v]\s+|'
    r'(?:merlots?|cabernets?(?:\s+\w+)?|petits?\s+verdots?|malbec|'
    r's[eé]millons?|sauvignons?)\s*:\s*(?:du\s+)?\d{1,2}[^.]{0,40}?'
    r'' + _M + r'\s*|'
    # "au 5 septembre" - the tail of a harvest range whose head was
    # stripped on the pass before. Berliquet's 2022 season note opened
    # on "au 5 septembre Le premier nez est floral".
    r'(?:au|to)\s+\d{1,2}\s*' + _M + r'\s*)+', re.I)

# A bullet glyph that extracted as a letter. Beauregard's 2018 note is
# peppered with "v La pluviometrie", and "v" standing alone is not a
# word in French or English, so it is safe to drop wherever it sits.
BULLET = re.compile(r'(?<=[\s.])[v•▪●·](?=\s)')

# A season note talks about the weather. Berliquet prints its tasting
# note under "Millesime 2022", so a window that reads as tasting and
# says nothing about a season is not one.
SEASON_OF = re.compile(
    r'(?i)(?<![a-zà-ÿ])'
    r'(hiver|printemps|[eé]t[eé]|automne|pluie|pluviom|gel\b|g[eé]l[eé]e|'
    r'temp[eé]rature|floraison|v[eé]raison|d[eé]bourrement|vendange|'
    r'r[eé]colte|s[eé]cheresse|canicule|mildiou|'
    r'winter|spring|summer|autumn|rainfall|rain|frost|flowering|'
    r'harvest|drought|heatwave|mildew|growing)'
    r'(?![a-zà-ÿ])')
# "le millesime" was in this list and had to come out. It is not a
# heading, it is ordinary French - "un fruite plus mur que le millesime
# precedent" - and matching it took the window from the middle of a
# sentence, so Beychevelle 2003's season note began "precedent. La
# floraison s'est deroulee". Worse, Beychevelle 2012's matched "Le
# millesime 2012 du Chateau Beychevelle est elegant et fruite, avec des
# tanins fins soyeux", which is a tasting note and not a season at all.
# Same mistake as putting "fine" in the French word list: a word that is
# also prose cannot mark a section.
LABEL_NOTE = re.compile(
    r'(?i)(climatologie|conditions?\s+climatiques|'
    r'the\s+\d{4}\s+vintage|mill[eé]sime\s+\d{4}|'
    r'cycle\s+v[eé]g[eé]tatif|growing\s+season|'
    r'notes?\s+sur\s+le\s+mill[eé]sime|'
    r'l[’\']ann[eé]e\s+viticole|the\s+(?:growing\s+)?year)')

# A label only counts where it stands as a heading, which on a fiche
# means one of three things: printed in capitals, followed by a colon,
# or starting a sentence. Without this the window opens wherever the
# words happen to appear, and a description that begins in the middle of
# somebody else's sentence is worse than no description.
def _is_heading(text, m):
    got = m.group(0)
    if got.isupper() and len(got) > 3:
        return True
    after = text[m.end():m.end() + 3]
    if after.lstrip().startswith(':'):
        return True
    before = text[max(0, m.start() - 2):m.start()]
    return m.start() == 0 or before.strip() in ('.', '!', '?', '')


def num(s):
    return float(s.replace(',', '.'))


def gated(field, v):
    lo, hi = GATES[field]
    return v if lo <= v <= hi else None


def first(text, *rxs):
    for rx in rxs:
        m = rx.search(text)
        if m:
            return m
    return None


def read_numbers(text):
    """Every gated figure the sheet states, with the words it said it in."""
    out, how = {}, {}

    m = first(text, RX_ALC, RX_ALC2)
    if m:
        v = gated('alc', num(m.group(1)))
        if v is not None:
            out['alc'], how['alc'] = v, m.group(0)[:60]

    m = RX_PH.search(text)
    if m:
        v = gated('ph', num(m.group(1)))
        if v is not None:
            out['ph'], how['ph'] = v, m.group(0)[:60]

    m = first(text, RX_YLD, RX_YLD2)
    if m:
        v = gated('yld', num(m.group(1)))
        if v is not None:
            out['yld'], how['yld'] = v, m.group(0)[:60]

    m = first(text, RX_MONTHS, RX_MONTHS2)
    if m:
        a = gated('months', num(m.group(1)))
        b = gated('months', num(m.group(2))) if m.group(2) else None
        if a is not None:
            out['months'] = ('%g-%g' % (a, b)) if b else '%g' % a
            how['months'] = m.group(0)[:60]

    m = first(text, RX_OAK, RX_OAK2)
    if m:
        v = gated('oak', num(m.group(1)))
        if v is not None:
            out['oak'], how['oak'] = v, m.group(0)[:60]

    m = RX_TEMP.search(text)
    if m:
        a, b = num(m.group(1)), num(m.group(2)) if m.group(2) else None
        if 12 <= a <= 22 and (b is None or 12 <= b <= 22):
            out['temp'] = [a, b] if b else [a]
            how['temp'] = m.group(0)[:60]

    m = RX_HARV.search(text)
    if m:
        d1, mo1, d2, mo2 = m.group(1), m.group(2), m.group(3), m.group(4)
        mo1 = MONTH.get((mo1 or '').lower())
        mo2 = MONTH.get((mo2 or '').lower()) or mo1
        # A harvest happens between August and November. Anything else
        # is a bottling date, a frost in April or a page number.
        if mo1 and 8 <= mo1 <= 11 and 1 <= int(d1) <= 31:
            a = '%02d-%02d' % (mo1, int(d1))
            b = ''
            if d2 and mo2 and 8 <= mo2 <= 11 and 1 <= int(d2) <= 31:
                b = '%02d-%02d' % (mo2, int(d2))
            out['pick'] = {'ALL': '%s|%s' % (a, b)}
            how['pick'] = m.group(0)[:60]
    return out, how


def read_prose(text):
    """The labelled tasting and season windows, cut at the stop-list."""
    out, how = {}, {}
    for field, lab in (('taste', LABEL_TASTE), ('note', LABEL_NOTE)):
        m = None
        for cand in lab.finditer(text):
            if _is_heading(text, cand):
                m = cand
                break
        if not m:
            continue
        win = text[m.end():m.end() + 1400].lstrip(' :–-—')
        s = PROSE_STOP.search(win)
        if s:
            win = win[:s.start()]
        win = BULLET.sub('', ' '.join(win.split()))
        win = LEADING_YEAR.sub('', ' '.join(win.split()))
        win = LEADING_YEAR.sub('', LEAD_JUNK.sub('', win).lstrip(' :-'))
        # Page numbers, table rulings and stray punctuation, which only
        # become the first thing in the window once the trimming above
        # has taken the label and the harvest dates off the front:
        # Haut-Bailly's 2019 note opened on "< < 12 Le débourrement" and
        # its 2022 on "11 12 Les mois de septembre".
        win = re.sub(r'^[\s<>|/•·\-–—!?,;:"\'’‘\u201c\u201d\d]{1,14}',
                     '', win)
        # A bilingual heading: Langoa-Barton and Leoville-Barton print
        # "DEGUSTATION / TASTING", so matching the French left "/
        # TASTING Robe dense de couleur pourpre" behind.
        # \d* because Giscours runs the heading into a page number:
        # "TASTING5 2 20 74 IM PER TUR BAB LE Audacieux Bold Precis".
        win = re.sub(r'^(?:TASTING|DEGUSTATION|D\u00c9GUSTATION|'
                     r'VINTAGE|MILL\u00c9SIME)\d*\b[\s:/–—-]*', '', win)
        # A date stamp: Villemaurine's note opens "AU 05/06/2014 Chateau
        # Villemaurine 2009, presente une robe".
        win = re.sub(r'^(?:AU|AS\s+OF|AT)\s+\d{1,2}[/.]\d{1,2}[/.]\d{2,4}'
                     r'[\s:,-]*', '', win, flags=re.I)
        # Once more, because taking the heading off can expose the page
        # numbers that were sitting behind it: "TASTING5 2 20 74 IM PER"
        # becomes "2 20 74 IM PER" and the first pass has already run.
        win = re.sub(r'^[\s<>|/•·\-–—!?,;:"\'’‘“”\d]{1,14}',
                     '', win)
        # And never end inside a word: the stop-list can cut anywhere.
        if win and not win[-1].isspace() and ' ' in win:
            if not re.search(r'[.!?"\u201d]$', win):
                win = win[:win.rfind(' ')]
        # And it must begin a sentence of its own - which is checked
        # here, after every trimming step, and not before them. Checking
        # first passed 23 windows that only became junk once the label
        # and the dates came off: "a été une année plus sèche" is the
        # tail of MILLÉSIME 2010's own sentence, and Palmer's 2010 note
        # began "will go down in history…".
        # Slide forward until the opening itself reads like prose,
        # rather than testing once and giving up. Giscours prints a
        # bilingual word-cloud above its tasting note - "IM PER TUR BAB
        # LE Audacieux Bold Precis Precise Veloute Velvety Profond Deep
        # Frais Fresh GISCOURS 2025 39" - which is neither lower-case
        # nor capitalised enough to fail the other tests, and the note
        # itself begins at "A la degustation" a hundred characters
        # later. Four tries, because a window that is still not prose
        # by the fourth sentence is not hiding one.
        for _ in range(4):
            if win[:1].islower():
                nxt = re.search(r'[.!?]\s+(?=[A-ZÀ-Ý])', win)
                if not nxt:
                    win = ''
                    break
                win = win[nxt.end():]
                continue
            if looks_like_prose(win[:190]) or len(win) < 190:
                break
            nxt = re.search(r'[.!?]\s+(?=[A-ZÀ-Ý])', win)
            if not nxt:
                break
            win = win[nxt.end():]
        if not win:
            continue
        # And end on a sentence, after all that trimming. The threshold
        # is 80 and not 120 because Beauregard's 2018 season note is 118
        # characters long and so was never cut at all - it ended on a
        # dangling "La", the start of a sentence the window did not
        # reach.
        cut2 = max(win.rfind('. '), win.rfind('! '), win.rfind('? '))
        if cut2 >= 80:
            win = win[:cut2 + 1]
        # The opening has to stand on its own, not be rescued by prose
        # further down. A window is up to 1,400 characters, so a
        # phenology table or a cloud of brand words - "Elegance
        # Fraicheur Finesse Soyeux Fruite Exigence Passion Engagement
        # Generosite Precision" - passed the test on the strength of the
        # paragraphs behind it, and Beychevelle's 2007 tasting note
        # opened on a description of the park.
        if not (looks_like_prose(win) and looks_like_prose(win[:190])):
            continue
        if field == 'taste' and not TASTES_OF.search(win[:260]):
            continue
        if field == 'note' and not SEASON_OF.search(win[:300]):
            continue
        out[field], how[field] = win, m.group(0)[:40]
    return out, how


# The three short advisory fields, each behind its own label. They were
# being thrown away: the stop-list was taught to halt the tasting note
# at "Periode de degustation recommandee" and "Decantation", which kept
# the advice out of the description and did not put it anywhere. Sampled
# over 150 sheets, about 104 of the 1,962 vintages state a drinking
# window, 156 a decanting instruction and 13 a food pairing, against
# coverage of 18, 11 and 8.
ADVICE = (
    # "garde" and "apogee" alone came out: both are ordinary French and
    # matched inside prose, which is how Kirwan's drinking window became
    # "downy mildew at bay Though catastrophe had been avoided".
    ('window', re.compile(
        r'(?i)(?:p[eé]riode\s+de\s+d[eé]gustation(?:\s+recommand[eé]e)?|'
        r'potentiel\s+de\s+garde|apog[eé]e\s+vers|drinking\s+window|'
        r'[aà]\s+boire\s+(?:entre|de|avant|d[eè]s)|'
        r'cellar(?:ing)?\s+potential)\s*:?\s*')),
    ('decant', re.compile(
        r'(?i)(?:d[eé]cantation|carafage|decanting)\s*:?\s*')),
    # The label has to swallow its own tail or the window opens on it:
    # "Food pairings:" left "es:", and "Accords mets/vin :" left
    # "/vin : gibier, plats en sauce".
    ('food', re.compile(
        r'(?i)(?:accords?\s+(?:mets|gourmands?)(?:\s*[-/&]\s*|\s+)?'
        r'(?:vins?|et\s+vins?)?|food\s*(?:and\s*wine\s*)?'
        r'(?:pairings?|match(?:es)?|matching)|'
        r'[aà]\s+servir\s+avec|suggestions?\s+d[\'e]\s*accompagnement|'
        r'to\s+be\s+served\s+with)\s*[:–—-]*\s*')),
)
# Where a piece of advice ends: at the next label of any kind.
#
# The first version stopped only at the next advisory label, so the
# advice ran on into whatever the sheet printed next - a press review
# ("2022 - 2038 April 2017 The Wine Doctor 91 A really enticing nose
# here"), the estate block ("10 a 15 ans SECOND VIN : Les Angelots de
# Villemaurine PROPRIETAIRE : Justin Onclin"), or the tasting note
# itself ("2023 et 2042. Le 2020 Badette presente une robe grenat").
ADVICE_STOP = re.compile(
    r'(?i)(p[eé]riode\s+de\s+d[eé]gustation|d[eé]cantation|carafage|'
    r'accords?\s+mets|temp[eé]rature|best\s+between|'
    r'conditions?\s+climatiques?|somme\s+des\s+|'
    r'commentaires?\s+de\s+d[eé]gustation|assemblage|enc[eé]pagement|'
    r'[eé]levage|mise\s+en\s+bouteille|analyse|www\.|@|t[eé]l\.|'
    r'propri[eé]taire|second\s+vin|œnologue|oenologue|'
    r'vendanges?|ramassage|fermentation|cueillette|'
    r'notes?\s*:|degr[eé]\s*:|production\s*:|score\s*:|'
    r'parker|suckling|galloni|jane\s+anson|neal\s+martin|'
    r'jancis\s+robinson|decanter|vinous|wine\s+doctor|le\s+monde|'
    r'\d{2,3}\s*/\s*100|\brobe\b|\bnez\b|'
    r'(?:janvier|f[eé]vrier|mars|avril|juin|juillet|septembre|octobre|'
    r'novembre|d[eé]cembre|january|february|april|june|july|august|'
    r'september|october|november|december)\s+\d{4})')

# A drinking window is really two years. Where the sheet gives them -
# "2026-2046", "2012 et 2024", "a boire entre 2006 a 2015" - they go to
# wy, which is the field this file already has for exactly that, and the
# prose is kept only when no pair can be read.
WY = re.compile(r'\b(19[89]\d|20[0-5]\d)\s*(?:-|–|—|/|[aà]|et|'
                r'to|and)\s*(19[89]\d|20[0-6]\d)\b')


def read_advice(text):
    """The drinking window, the decanting and the food, where stated."""
    out, how = {}, {}
    for field, lab in ADVICE:
        m = None
        for cand in lab.finditer(text):
            if _is_heading(text, cand):
                m = cand
                break
        if not m:
            continue
        win = text[m.end():m.end() + 320]
        s = ADVICE_STOP.search(win)
        if s:
            win = win[:s.start()]
        win = ' '.join(win.split()).lstrip(' :-–—/&.,')
        # Dot leaders: Beau-Sejour Becot's sheet rules a line of them
        # under the heading, which is a form to be filled in and not a
        # pairing.
        if len(re.findall(r'[.…]', win)) > len(win) * 0.2:
            continue
        cut = max(win.rfind('. '), win.rfind('! '), win.rfind('? '))
        if cut >= 20:
            win = win[:cut + 1]
        # Short by nature, and the connective test that guards a
        # paragraph is wrong here. La Tour Blanche's whole drinking
        # window is "Des aujourd'hui. Apogee vers 2020." - thirty-four
        # characters with not one of "de la et the and" in it - and
        # requiring a small word threw every window away. Length bounds
        # and a cap on digits are enough for a line of advice; what
        # matters is that it is a line and not a table.
        if field == 'window':
            y = WY.search(win)
            if y:
                a, b = int(y.group(1)), int(y.group(2))
                if 1980 <= a < b <= 2070:
                    out['wy'] = [a, b]
                    how['wy'] = (m.group(0) + y.group(0))[:48]
                    continue
        digits = sum(c.isdigit() for c in win)
        words = len([w for w in win.split() if len(w) > 2])
        if 12 <= len(win) <= 300 and digits <= len(win) * 0.3 \
                and words >= 3:
            out[field] = win
            how[field] = m.group(0)[:36]
    return out, how


# Words a filename uses for the paperwork rather than the wine.
FILING = set("""fiche fiches technique techniques sheet technical fact
millesime vintage vin vins chateau clos domaine grand grands cru crus
classe fra fre eng ang anglais francais english french web pdf doc
primeur primeurs bordeaux rouge blanc rose red white sec dry""".split())


def abbreviates_other_wine(filename, grand, others=()):
    """Does the filename shorten one of the estate's other wines?

    A cuvee is often filed under the first letters of its name - VIB
    for Vibrato - which no name matching will find, because the name
    is not there to match. What is there is a word that begins it.

    The estate's own name comes first: Kirwan files its sheets as
    ChateauKirwan, and that begins "Chateau Kirwan Blanc" too.

    Returns the wine, or None.
    """
    def wds(s):
        return [w for w in re.split(r'[^a-z0-9]+', norm(s or '')) if w]

    mine = set(w for w in wds(grand) if len(w) > 2)
    fw = [w for w in wds(filename)
          if len(w) > 2 and not w.isdigit() and w not in FILING]
    if not fw or (mine & set(fw)):
        return None
    nb = bare_name(grand)
    if nb and nb in bare_name(filename):
        return None
    for nm in others or ():
        mark = mark_of(nm, grand)
        if not mark:
            continue
        mk = ''.join(wds(mark))
        if len(mk) < 4:
            continue
        for w in fw:
            if len(w) >= 3 and w != mk and mk.startswith(w):
                return nm
    return None


# A long run of hex is a hash, and four digits inside one are not a
# year. Croix de Labrie "2079" is the tail of
# 266fad379e514e6c8dabd7d076602079.
HASHRUN = re.compile(r'(?i)[0-9a-f]{16,}')


def year_said(year, filename, text=None):
    """Does the filename or the document state this vintage?

    The vintage does not come from the filename - that rule this
    project has paid for, and harvest.py keeps it when it decides what
    a document is. This is the weaker question asked afterwards, of a
    sheet already filed under an estate and a year by hand: does
    anything at all say that year? A year nothing states is a year
    somebody's regular expression found in a hash.
    """
    if not year:
        return None
    rx = re.compile(r'(?<!\d)%d(?!\d)' % int(year))
    clean = HASHRUN.sub(lambda m: '#' * len(m.group(0)), filename or '')
    if rx.search(clean):
        return 'the filename'
    if text and rx.search(text):
        return 'the document'
    return None


# A filename that says the document is press. is_dossier reads the body
# and catches a press pack by its contents; this catches the ones whose
# contents are a magazine page - a review, a listing, a clipping - and
# whose only tell is the name they were filed under.
PRESS_NAME = re.compile(r'(?i)(?<![a-z])('
                        r'revue[-_ ]?de[-_ ]?presse|press[-_ ]?review|'
                        r'tv[-_ ]?magazine|magazine|gault|millau|'
                        r'figaro|sud[-_ ]?ouest|terre[-_ ]?de[-_ ]?vins|'
                        r'rvf|wine[-_ ]?spectator|wine[-_ ]?enthusiast|'
                        r'decanter|bettane|desseauve|jancis|parker|'
                        r'suckling|galloni|vinous|france\s?[0-9]|'
                        r'journal|presse|article|interview|communique'
                        r')(?![a-z])')


def is_press_name(filename):
    """Does the filename say this is press rather than a sheet?"""
    m = PRESS_NAME.search(filename or '')
    return m.group(1) if m else None


# Words that belong to every name in Bordeaux and so distinguish none.
NAME_COMMON = set("""chateau ch clos domaine de du des la le les et en
aux au vin vins grand grands cru crus classe classes bordeaux fiche
technique sheet technical millesime vintage fiches pdf web site uk
gb fr en es nl rouge blanc rose red white dry sec""".split())
NAME_LEAD = re.compile(r'(?i)^(?:chateau|clos|domaine|ch)(?=[a-z])')
NAME_ART = re.compile(r'^(?:de|du|des|la|le|les|l|d)(?=[a-z]{4})')
# "chateau beau secret 2014" - the name a filename spells out.
NAME_SPELLS = re.compile(
    r'(?<![a-z])(?:chateau|clos|domaine)'
    r'[^a-z0-9]*([a-z0-9]+(?:[^a-z0-9]+[a-z0-9]+){0,3})')


def bare_name(s):
    """The letters of a name, separators and leading articles gone.

    Filenames drop the apostrophe and run the article into the name -
    levangile, daiguilhe, loratoire, couhinslurton, grandcorbin - so a
    word-by-word comparison with Chateau L'Evangile finds nothing in
    common. Compared as letters, levangile contains evangile.
    """
    b = re.sub(r'[^a-z0-9]+', '', norm(s or ''))
    was = None
    while was != b:
        was = b
        b = NAME_ART.sub('', NAME_LEAD.sub('', b))
    return b


def names_other_chateau(filename, grand, others=(), second=None):
    """Does the filename spell a chateau that is none of this estate's?

    Chateau du Moulin Rouge's folder holds Beau-Secret, Moulin de
    Bayron, L'Ecuyer du Moulin Rouge and L'Aventurine: one owner's
    whole range, as Chateau d'Argan's did. Beau-Secret is not the
    recorded second wine and not a sibling estate in the data, so
    neither names_another_wine nor confirms_estate had anything to
    test it against, and technical-sheet-chateau-beau-secret-2014.pdf
    gave Moulin Rouge 2014 its tasting note.

    All that is left to go on is the filename, and the filename says
    whose wine it is. Where it spells out "chateau X" and the estate's
    own name is nowhere in it, the sheet is another property's.

    The allowances are the three ways a filename writes a name it does
    own: the elided article (levangile for L'Evangile), the estate's
    own misspelling (comensac for Camensac), and the house
    abbreviation - Haut-Brion files thirty-seven vintages as
    Chateau-HBR-2010 and its neighbours' as Carmes-Haut-Brion.

    Returns the other name, or None.
    """
    m = NAME_SPELLS.search(norm(filename or ''))
    if not m:
        return None
    spelled = [w for w in re.split(r'[^a-z0-9]+', norm(m.group(1)))
               if w and w not in NAME_COMMON and not w.isdigit()]
    if not spelled or max(len(w) for w in spelled) < 4:
        return None
    sp = bare_name(' '.join(spelled))
    fb = bare_name(filename)
    for nm in (grand, second) + tuple(others or ()):
        nb = bare_name(nm)
        if not nb or len(nb) < 4:
            continue
        if nb in fb or fb in nb:
            return None
        # A long name need not be spelled in full: Smith Haut Lafitte's
        # filenames say smith-haut-lafitte, Rauzan-Segla's rauzansegla,
        # Malartic-Lagraviere's malartic. One word of the estate's own
        # name, four letters or more, is enough.
        for w in re.split(r'[^a-z0-9]+', norm(nm)):
            if len(w) > 3 and w not in NAME_COMMON and w in fb:
                return None
        if difflib.SequenceMatcher(None, sp, nb).ratio() >= 0.8:
            return None
        if len(sp) <= 4 and re.search('.*?'.join(re.escape(c)
                                                 for c in sp), nb):
            return None
    return ' '.join(spelled)


def fields_of(path, grand=None, others=(), second=None, cat=None,
              filename=None, year=None):
    """Everything a sheet states, or nothing if it is not this wine's.

    The guards run first and in the order that has earned its place:
    a press dossier describes a property and not a vintage; a sheet
    naming another of the estate's wines is that wine's; a filename
    naming the other colour is the other colour; a sheet naming a
    sibling property is the sibling's. Only then is anything read.

    Returns (fields, how) where `how` holds, for each field, the words
    the sheet said it in - so a figure can be checked against its own
    sentence without opening the document again.
    """
    filename = filename or os.path.basename(path)
    try:
        if year and not year_said(year, filename):
            try:
                if not year_said(year, filename,
                                 ' '.join(flat(path).split())):
                    return {}, {'refused': 'nothing states this vintage'}
            except Exception:
                return {}, {'refused': 'nothing states this vintage'}
        if is_press_name(filename):
            return {}, {'refused': 'the filename says it is press'}
        if is_dossier(path):
            return {}, {'refused': 'a press dossier, not a vintage’s sheet'}
        # Every wine the estate is recorded as making, not only the
        # second. This tested `second` alone, and Clos Puy Arnaud's
        # Fiche-technique-VIB-2024-FR.pdf - "CLOS PUY ARNAUD VIBRATO
        # 2024 VIN DE FRANCE" - gave the grand vin its pH and its
        # picking date, although Vibrato has been in the estate's
        # cuvees all along. The blend reader has looped over them since
        # it was written; this one never did.
        for nm in (second,) + tuple(others or ()):
            if nm and names_another_wine(path, filename, grand, nm):
                return {}, {'refused': 'the sheet names another of the '
                                       'estate’s wines'}
        other_wine = abbreviates_other_wine(filename, grand, others)
        if other_wine:
            return {}, {'refused': 'the filename abbreviates another of '
                                   'the estate’s wines'}
        if names_other_chateau(filename, grand, others, second):
            return {}, {'refused': 'the filename names another '
                                   'château'}
        if wrong_colour(filename, None, cat):
            return {}, {'refused': 'the filename says another colour'}
        if confirms_estate(path, filename, grand, others) == 'other':
            return {}, {'refused': 'the sheet names a sibling property'}
    except Exception as e:
        return {}, {'refused': 'a guard could not read it: %s' % str(e)[:40]}

    try:
        text = ' '.join(flat(path).split())
    except Exception:
        return {}, {'refused': 'unreadable'}

    got, how = read_numbers(text)
    for fn in (read_prose, read_advice):
        more, howm = fn(text)
        got.update(more)
        how.update(howm)
    return got, how
