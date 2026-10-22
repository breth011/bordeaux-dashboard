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


def path_of(root, row, found=None):
    """The document a manifest row names.

    The manifest says which folder each row is in, and that is the
    answer: a basename is not a path. 888 filenames exist in more than
    one folder, because an owner publishes the same document under
    each of its properties.

    `found` is an optional basename map, used only for a row whose
    folder is not on disk.
    """
    folder = (row.get('folder') or '') if hasattr(row, 'get') else ''
    name = row['file'] if hasattr(row, 'get') else row
    if folder:
        p = os.path.join(root, 'sources',
                         folder if folder.startswith('pages')
                         else 'fiches/' + folder, name)
        if os.path.exists(p):
            return p
    if found:
        return found.get(name)
    return None


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
                                            'cuvees': [], 'cat': None,
                                            'app': None})
            nm = js_strings_after('name:', win)
            sc = js_strings_after('second:', win)
            ct = js_strings_after('cat:', win)
            ap = js_strings_after('appellation:', win)
            if nm and not e['name']:
                e['name'] = nm[0]
            if sc and not e['second']:
                e['second'] = sc[0]
            if ct and not e['cat']:
                e['cat'] = ct[0]
            if ap and not e.get('app'):
                e['app'] = ap[0]
    # The sparse lists. app.js builds these estates' ids itself, from
    # `cls + '-' + slug(name)` - so most of the dashboard's estates are
    # named nowhere as `id:'...', name:'...'`, and a loader that only
    # looked for that pattern found 160 of them instead of 500. Those
    # ids have to be derived the same way here or every one of their
    # sheets looks unattributable.
    sparse = [('crubourgeois.js', 'BDX_CRU_BOURGEOIS', 'bourgeois',
               None),
              ('cruartisan.js', 'BDX_CRU_ARTISAN', 'artisan', None),
              ('saintemilion.js', 'BDX_STEM_GCC', 'stem',
               'Saint-Émilion'),
              ('pomerol.js', 'BDX_POMEROL_OTHER', 'pomerol', 'Pomerol')]
    for f, var, cls, only in sparse:
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
        # A row is ['name', 'appellation']; a bare list is names only,
        # and then the file says which appellation they are all in.
        names = ([js_strings(r)[:2] for r in rows] if rows
                 else [[n] for n in js_strings(body)])
        for pair in names:
            app = pair[1] if len(pair) > 1 else only
            for nm in pair[:1]:
                if not nm or len(nm) < 5 or nm[0].islower():
                    continue
                e = out.setdefault(cls + '-' + slug(nm),
                                   {'name': None, 'second': None,
                                    'cuvees': [], 'cat': None,
                                    'app': None})
                if not e['name']:
                    e['name'] = nm
                if app and not e.get('app'):
                    e['app'] = app

    p = os.path.join(root, 'data', 'cuvees.js')
    if os.path.exists(p):
        t = io.open(p, encoding='utf-8').read()
        for m in re.finditer(r"^'([a-z0-9-]+)':\[(.*)\],?$", t, re.M):
            e = out.setdefault(m.group(1), {'name': None, 'second': None,
                                            'cuvees': [], 'cat': None,
                                            'app': None})
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


# ===========================================================================
#   A CRAWLED PAGE
#
# Some estates publish no fiche technique at all. Chateau Margaux
# publishes a page per vintage; so do Haut-Brion, Haut-Bailly,
# Leoville-Poyferre and fifty-four others, 1,673 pages in all. They are
# text, not PDF, and everything below treats them as one more kind of
# document rather than as a special case: flat() reads them, so every
# guard and every field reader works on them unchanged.
#
# What has to come off first is the furniture. These are the lines that
# appear on hundreds of pages at once, measured rather than guessed.
PAGE_FURNITURE = frozenset([
    # "Climate" is not here on purpose: it is the heading Margaux sets
    # over its growing season, and the only marker the note reader has
    # to find that paragraph by.
    '-->', '{title}', '0', 'learn more', 'additional',
    'discover other vintages', 'découvrir les autres millésimes',
    # A news heading, which Batailley's page opens on: "Actualités
    # Présentation de Château Batailley 2019 par Philippe Castéja."
    'actualités', 'actualites', 'news', 'presse', 'press',
    'top of page', 'haut de page',
    'remember me', 'france', 'international', 'chili', 'la boutique',
    'lire la suite', 'read more', 'en savoir plus', 'newsletter',
    's\u2019inscrire', 'subscribe', 'menu', 'close', 'fermer',
    'partager', 'share', 'suivant', 'next', 'pr\u00e9c\u00e9dent',
    'previous', 'accueil', 'home', 'contact', 'instagram', 'facebook',
    'linkedin', 'youtube', 'admin', 'r\u00e9ponses', '0 r\u00e9ponses',
])
# The headings that begin the footer and the navigation. Everything
# from the first of them is the website and not the wine.
PAGE_TAIL = re.compile(
    # "Discover other vintages" is NOT a tail marker: it is a strip of
    # links in the middle of the page, and Margaux prints the growing
    # season after it, under "Climate". Breaking there lost the season
    # on all 152 of its wine pages.
    r'(?i)^\s*(preservation|conservation\s*$|'
    r'service\s*&\s*tasting|service et d\u00e9gustation|'
    r'acc\u00e9der \u00e0 la boutique|la boutique|politique de cookies|'
    r'cookie|mentions l\u00e9gales|legal notice|'
    r'site institutionnel|nous suivre|follow us|'
    r'vous aimerez aussi|you may also like|'
    r'inscrivez-vous|sign up|newsletter)\b')
# A year alone on a line is the vintage navigation, and six hundred of
# these pages carry every year from 1990 to 2024 that way. Left in, it
# would answer "does anything state this vintage" for every vintage
# there is.
PAGE_YEAR_LINE = re.compile(r'^\s*(?:19|20)\d\d\s*$')
# Lines that are furniture by their shape rather than word for word.
# Jean Faure's pages open with the age and language gate, and three of
# its season notes were "Oui Non Votre langue : Francais English: Vous
# allez acceder a une version dont le contenu a ete limite par la
# legislation en vigueur dans votre pays. L'abus d'alcool est
# dangereux pour la sante". Haut-Bailly's carry the breadcrumb "Nos
# millesimes" between the title and the text, and it ended up inside
# the note.
PAGE_JUNK = re.compile(
    r'(?i)^\s*(?:oui|non|yes|no|ok|accepter|accept|refuser|decline'
    r'|nos\s+mill[eé]simes|our\s+vintages|the\s+vintages'
    r'|les\s+mill[eé]simes|nos\s+vins|our\s+wines|mon\s+vin'
    r'|votre\s+langue.*|vous\s+allez\s+acc[eé]der.*'
    r'|l[’\']abus\s+d[’\']alcool.*|[aà]\s+consommer\s+avec.*'
    r'|ajouter\s+au\s+panier|add\s+to\s+cart|rupture\s+de\s+stock'
    r'|out\s+of\s+stock|quand\s+\w+\s+\d{1,2}\s+\w+\s+\d{4}'
    r'|version\s+(?:fr|en|uk)\b.*)\s*[:.]?\s*$')


def is_page(path):
    """A crawled page rather than a document."""
    return not (path or '').lower().endswith(
        ('.pdf', '.doc', '.docx', '.xls', '.xlsx'))


def page_url(path):
    """The URL the crawler wrote on the first line, if it did."""
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            first = fh.readline().strip()
    except Exception:
        return ''
    return first if first[:4].lower() == 'http' else ''


def _page_body(path):
    """A page with its furniture, its footer and its year list gone."""
    try:
        raw = io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return ''
    lines = raw.split('\n')
    if lines and lines[0].strip()[:4].lower() == 'http':
        # The crawler writes the URL first and the page's <title>
        # second. A <title> is the browser tab, not the wine: Haut-
        # Bailly's reads "Millesime 1998 : Des Merlots benis des dieux
        # - Haut-Bailly", the label matched the year inside it, and
        # eleven season notes opened on the title and its own
        # repetition before reaching the prose.
        lines = lines[2:] if len(lines) > 1 else []
    keep, seen = [], set()
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if PAGE_TAIL.match(s):
            break
        if PAGE_YEAR_LINE.match(s):
            continue
        if s.lower() in PAGE_FURNITURE or PAGE_JUNK.match(s):
            continue
        # These pages render themselves twice: Margaux's 2015 carries
        # its eight paragraphs, the vintage strip, the climate section,
        # and then all of it again. A paragraph repeated word for word
        # is the crawl and not the estate saying it twice.
        if len(s) >= 60:
            if s in seen:
                continue
            seen.add(s)
        keep.append(s)
    # A heading on a page is a line of its own, and every reader in
    # this file flattens the text before looking at it - which throws
    # that away. Margaux's "Climate" sits between "(March 2025)" and
    # "Winter, which was appreciably colder", and once flattened
    # _is_heading cannot tell it from a word in a sentence: it is not
    # in capitals and no colon follows it.
    #
    # So the layout is carried into the text. A short line with no
    # sentence-ending punctuation, standing in front of a paragraph, is
    # a heading, and is written as one.
    out = []
    for i, s in enumerate(keep):
        nxt = keep[i + 1] if i + 1 < len(keep) else ''
        if (len(s) < 48 and len(nxt) >= 80
                and not re.search(r'[.!?:;,…]$', s)
                and not s.isdigit()):
            s += ':'
        out.append(s)
    # And a heading at the end, with nothing under it, is not a
    # heading: these pages repeat themselves, and the second copy of
    # "Climate" outlives the paragraph the de-duplication took.
    while out and len(out[-1]) < 48 and out[-1].endswith(':'):
        out.pop()
    return '\n'.join(out)


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
    # A page has no columns: the flat reading is the only reading.
    if is_page(path):
        return flat(path)
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
    return delig('\n'.join(out))


def flat(path, pages=0):
    return _cached(('flat', path, pages), lambda: _flat(path, pages))


# A PDF sets "fi" as one glyph and pymupdf hands it over as one
# character, U+FB01. It renders in a browser, so nothing looks wrong -
# but a search for "finesse" does not find "ﬁnesse", a regular
# expression for a letter does not match it, and seven of them reached
# the records before check-language named them one estate at a time.
# Undone on the way in, where every reading passes.
LIGATURES = ((u'ﬀ', 'ff'), (u'ﬁ', 'fi'), (u'ﬂ', 'fl'),
             (u'ﬃ', 'ffi'), (u'ﬄ', 'ffl'), (u'ﬅ', 'st'),
             (u'ﬆ', 'st'))


def delig(text):
    """The six Latin ligatures as the letters they stand for."""
    for ch, rep in LIGATURES:
        if ch in text:
            text = text.replace(ch, rep)
    return text


def _flat(path, pages):
    # A crawled page is read as text. Every guard and every field
    # reader goes through flat(), so this is the only place that has to
    # know the difference.
    if is_page(path):
        return delig(_page_body(path))
    d = pymupdf.open(path)
    n = d.page_count if not pages else min(pages, d.page_count)
    t = ' '.join(d[i].get_text() for i in range(n))
    d.close()
    return delig(t)


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

# The articles, which never begin a mark of their own: a pair starting
# on one carries no more than the word after it.
ARTICLES = set('le la les l d de du des et en au aux'.split())


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
    # No single word, then two together. "Le Petit Mouton de Mouton
    # Rothschild" has none: "petit" is in COMMON, so that a mark never
    # matches "2% Petit Verdot", and every other word of it is in
    # Mouton Rothschild's own name. The mark came back as "le mouton de
    # mouton rothschild", which no filename carries, and
    # 2025-LE-PETIT-MOUTON-DE-MOUTON-ROTHSCHILD_Fiche-Vin-FR.pdf gave
    # Mouton Rothschild 2025 its blend, its alcohol, its pH and the
    # second wine's tasting note. "petit mouton" is distinctive, and
    # says() requires the words whole and in order, so it cannot match
    # Petit Verdot either.
    # Neither word may be an article: a pair ending on one carries no
    # more than the word before it, and "Reserve de la Comtesse" and
    # "Les Fleurs de Malle" came back as "reserve de" and "fleurs de",
    # which would match any wine in Bordeaux whose name begins that
    # way.
    for a, b in zip(words, words[1:]):
        if packed(a) in ARTICLES or packed(b) in ARTICLES:
            continue
        # The second word has to be the distinctive one. A pair ending
        # on a word half of Bordeaux uses is no mark: "D de Dauzac
        # Blanc" gave "dauzac blanc", which its own sheets -
        # FT_D_DE_DAUZAC_2022_FR.pdf - do not carry, and the white's
        # fourteen sheets stopped being recognised as the white's.
        if packed(b) in COMMON:
            continue
        pair = packed(a + b)
        if len(pair) >= 8 and pair not in g and re.search(r'[a-z]{3}', pair):
            return '%s %s' % (a.lower(), b.lower())
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
    if is_page(path):
        n, text = 1, re.sub(r'\s+', ' ', flat(path))
    else:
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
    if is_page(path):
        got = [flat(path)]
    else:
        try:
            d = pymupdf.open(path)
            got = [d[i].get_text()
                   for i in range(min(pages, d.page_count))]
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
    # The consent banner and the age gate, which a crawled page
    # carries in its text. Lafon-Rochet 2019's tasting note was 913
    # characters and 710 of them were this. Never a bare "cookie": an
    # English note can say cookie dough, so each pattern carries the
    # furniture around it.
    r'politique\s+de\s+confidentialit|privacy\s+polic|'
    r'nous\s+utilisons\s+des\s+cookies|we\s+use\s+cookies|'
    r'pr[eé]f[eé]rences\s+en\s+mati[eè]re\s+de\s+cookies|'
    r'cookie\s+(?:polic|settings|preferences|consent)|'
    r'(?:accepte[rz]?|accept)\s+(?:all\s+|ces\s+)?'
    r'(?:cookies|termes|terms)|'
    r'terms\s+and\s+conditions|termes\s+et\s+conditions|'
    r'[aâ]ge\s+l[eé]gal\s+d|legal\s+drinking\s+age|'
    r'vous\s+devez\s+[eê]tre\s+[aâ]g|must\s+be\s+of\s+legal|'
    r'outdated\s+browser|navigateur\s+obsol[eè]te|'
    r'jean-ren[eé]\s+matignon|pierre\s+mont[eé]gut|directeur\s+technique|'
    r'technical\s+(?:manager|director)\s*[-–]|'
    r'date\s+de\s+mise\s+en\s+bouteille|mise\s+en\s+bouteille\s*:|'
    r'bottling\s+date|analyse\s|analyses\s*:|'
    r'harvest\s+time|dates?\s+de\s+vendanges?|'
    # Pavie-Macquin's 2012 and 2013 season notes were its picking
    # dates: "Dates de recolte : Merlots du 13 au 18 octobre Cabernets
    # du 17 au 18 octobre Production". Those dates are read into pick,
    # which is the field for them.
    r'dates?\s+de\s+r[eé]colte|harvest\s+dates?\s*:|'
    # The bare headings, in capitals, that Haut-Bailly sets over the
    # next section: its 2021 season note ran into "VENDANGES C'est la
    # premiere recolte vinifiee dans nos nouveaux chais" and its 2023
    # into "VINS A la satisfaction des epreuves surmontees".
    r'vendanges\s+[A-Z]|\bvins\s+[A-Z]|\bwines\s+[A-Z]|'
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
    # The cellar block. Ripeau's 2015, 2016, 2017 and 2018 season
    # notes were all the same text - "AU CHAI Vinification :
    # Fermentation alcoolique a basse temperature pour preserver la
    # fraicheur" - which is how the estate works every year and not
    # what any one season did.
    r'au\s+chai\b|vinification\s*:|fermentation\s+alcoolique|'
    # More of the cellar. Haut-Bailly's 2002 and 2003 season notes run
    # from the weather straight into the work: "La mise en place d'une
    # table vibrante equipee d'une grille de tamisage, situee juste
    # derriere l'erafloir", "Des remontages en douceur et des
    # macerations maitrisees". That is how the wine was made, not what
    # the year did.
    r'[eé]rafloir|remontages?\b|mac[eé]rations?\s+(?:pr[eé]|ma)|'
    r'table\s+vibrante|encuvage\b|'
    # And the page furniture that follows a tasting note on Batailley's
    # site: "Voir la video."
    r'voir\s+la\s+vid[eé]o|watch\s+the\s+video|'
    r'in\s+the\s+cellar\s*:|winemaking\s*:|'
    r'commentaires?\s+de\s+d[eé]gustation|'
    # The bare heading, which is what Domaine de Chevalier prints over
    # the tasting note: its 2014 and 2016 season notes both ran on into
    # "DEGUSTATION Couleur profonde et soutenue". A capital follows a
    # heading; in prose the word is followed by a lower-case one.
    r'd[eé]gustation\s+[A-Z]|tasting\s+[A-Z]|'
    r'[eé]levage\s+\d+\s+mois|assemblage\s+\d{1,3}\s*%|'
    # The same labels with a colon instead of a figure. Dauzac closes
    # six season notes with "Assemblage : Cabernet Sauvignon 62 %,
    # Merlot 38 %" and its 2002 with "Appellation : Margaux. Chateau :
    # Chateau Dauzac. Surface en production : 42,00 hectares. Type de
    # sol : Croupes de graves profondes de l'ere du quaternaire."
    r'assemblage\s*:|appellation\s*:|type\s+de\s+sol|'
    r'surface\s+en\s+production|ch[aâ]teau\s*:\s*ch[aâ]teau|'
    r'surface\s+area|viticulture\s+by\s+plot|'
    # The vineyard record, which a sheet prints in a column beside the
    # tasting note and which pymupdf interleaves with it line by line.
    # Dauzac 2014: "Meteo : Un climat atypique avec un Nez : delicat et
    # complexe Porte-greffes : 101-14, Riparia Gloire hiver doux et
    # pluvieux ... Densite de plantation : 10 000 pieds ... Age moyen
    # des vignes : 30-35 ans." Three columns, every sentence of it
    # real, and none of it a description of the wine. Stopping at the
    # first of these labels leaves too little to pass for prose, which
    # is the right answer; La Violette 2025 keeps the note it opens
    # with and loses the vineyard block it ran into.
    r'porte[-\s]?greffes?|densit[eé]\s+de\s+plantation|'
    r'[aâ]ge\s+moyen\s+des\s+vignes|superficie|rootstocks?|'
    r'plantation\s+density|vine\s+density|engrais\s*:|'
    r'enc[eé]pagement|grape\s+varieties|'
    r'\d{13}|'                              # an EAN barcode
    r'www\.|@|t[eé]l\.|\+\s*33|'            # contact details
    r'\d{5}\s+[A-Z][a-z]|'                  # a postcode and town
    r'scea\b|earl\b|sas\b|gfa\b|'           # the company
    r'accords?\s+mets|food\s+pairing|'      # belongs in food
    # "Food Matches:" is the label Magnol uses, and behind it its 2019
    # sheet prints two recipes in full - prunes wrapped in bacon, beef
    # pirogis, with the oven temperatures - all of which was in the
    # tasting note. The pairing itself is read into food.
    r'food\s+match(?:es)?|recipe\s+n|cooking\s+time|'
    r'preparation\s*:|ingredients\s*\.|'
    # L'Evangile's 2011 season note ran into "WINE MAKING SCHEME
    # Alcoholic fermentation took place in temperature-controlled
    # concrete vats".
    r'wine\s*making\s+scheme|'
    # Dauzac prints its own appendices under the tasting note, and four
    # vintages carried them: 2013 ran into "PERIODE DE CONSOMMATION
    # 2017 - 2030 NOS SUGGESTIONS - Viande blanche", 2017 and 2024 into
    # "POTENTIEL DE VIEILLISSEMENT S'exprime a son meilleur entre 5 et
    # 20 ans" and then "PRODUCTION CERTIFIEE 100 % VEGAN 100 ans dans
    # une bouteille", 2022 on into a page of press scores.
    r'potentiel\s+de\s+(?:vieillissement|garde)|'
    r'p[eé]riode\s+de\s+consommation|nos\s+suggestions|'
    r'production\s+certifi[eé]e|ageing\s+potential|'
    r'\d+\s*€|\d+\s*euros?|'           # a price list
    r'suivez-nous|follow\s+us|instagram|'
    # An event listing, which a crawled page can be: Grand Corbin-
    # Despagne's "Pre-primeurs au Palais de la Bourse a Bordeaux
    # Presentation du millesime 2021 aupres des professionnels de La
    # Place de Bordeaux | Chateau Grand Corbin-Despagne Version FR
    # Degustation | lundi 11 avril 2022". A weekday behind a pipe is a
    # diary entry and not a description of a wine.
    r'\|\s*(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|'
    r'monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|'
    r'palais\s+de\s+la\s+bourse|aupr[eè]s\s+des\s+professionnels|'
    r'la\s+place\s+de\s+bordeaux|'
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
    r'varietals?\s*:|'
    # Siaurac's 2017 note ran into the heading "Le Vignoble TERROIR",
    # so the heading went in the stop-list - and then cut Beychevelle's
    # 2023 note at "n'a pas eu d'impact sur le vignoble de Chateau
    # Beychevelle", which is a sentence about a vineyard and not a
    # heading over a table. A heading is followed by another heading in
    # capitals; prose is followed by "de".
    r'le\s+vignoble\s+[A-Z]{3,}|the\s+vineyard\s+[A-Z]{3,}|'
    r'gault\s*&?\s*millau|\brvf\b|guide\s+hachette|'
    # Beychevelle's 2013 tasting note ends at the critic who wrote it:
    # "finale legerement vegetale pour le moment, mais elle se
    # transformera en fraicheur. Bernard Burtschy - Le Figaro Ce 2013
    # s'articule autour du triptyque suivant : 55% de cabernet".
    r'le\s+figaro|burtschy|terre\s+de\s+vins|'
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
    # Bare "Tasting" counts only where a colon follows it, since the
    # word itself turns up in prose. Dauzac prints "taSting :" in small
    # caps over the English half of its 2025 sheet, and requiring a
    # noun after it meant the English was never a candidate at all.
    r'tasting\s*:|'
    r'fiche\s+de\s+d[eé]gustation)')
# The plural mattered. Beychevelle prints "DEGUSTATIONS 2004" and a
# pattern ending at "DEGUSTATION" left the S behind, so every tasting
# note it proposed began "S 2004 Sous sa robe grenat...".
# A year left at the front by a heading - "DEGUSTATIONS 2004 Sous sa
# robe grenat" becomes "2004 Sous sa robe grenat" once the label is
# off - and not a year that is the subject of the sentence. Margaux's
# pages open "1995 is a truly great vintage" and "2015 was a historic
# year", where the year is the first word of the prose and stripping it
# left a sentence beginning in lower case, which the slide then skipped
# over entirely.
# The leading junk a heading leaves behind - page numbers, table
# rulings, stray punctuation - but not a year that is the subject of
# the sentence. Margaux's pages open "1995 is a truly great vintage",
# and stripping the digits left a sentence beginning in lower case
# which the slide then skipped past, losing the first line of every
# tasting note it read from a page.
JUNK_HEAD = re.compile('^[\\s<>|/\u2022\u00b7\\-\u2013\u2014!?,;:\u0022\u0027\u2019\u2018\u201c\u201d\\d]{1,14}')
OPENS_ON_A_YEAR = re.compile(r'^(?:19|20)\d{2}\s+[a-zà-ÿ]')


def _strip_head(win):
    """Leading junk off, unless the text opens on a year and a verb."""
    return win if OPENS_ON_A_YEAR.match(win) else JUNK_HEAD.sub('', win)


# The lookahead sits immediately after the digits and looks past the
# separator itself. Behind the separator it backtracked: \s* gave the
# space back, the lookahead then examined the space rather than the
# letter after it, and "1995 is a truly great vintage" lost its year
# all the same.
LEADING_YEAR = re.compile(
    r'^(?:19|20)\d{2}(?!\s*[-:–]?\s*[a-zà-ÿ])\s*[-:–]?\s*')

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


BROKEN_RUN = re.compile(r'(?<![A-Za-zÀ-ÿ])'
                        r'[A-Za-zÀ-ÿ]{20,}'
                        r'(?![A-Za-zÀ-ÿ])')
BROKEN_CASE = re.compile(r'[a-zà-ÿ]{3}'
                         r'[A-ZÀ-Ý][a-zà-ÿ]{2}')


def looks_like_prose(s):
    if len(s) < 80:
        return False
    digits = sum(c.isdigit() for c in s)
    if digits > len(s) * 0.12:
        return False
    if len(re.findall(r'\d{1,2}\s*/\s*\d{1,2}', s)) >= 2:
        return False          # a column of dates
    # Extraction that lost its spaces. Batailley's sheet sets its
    # history beside its tasting note, and the two came out merged -
    # "MIS EN BOU deBorie-Manoux.Ildoitsonnomaladerniere Bataille en
    # Medoc de la guerre de cent ans Robe profonde et intense" - with
    # the spaces gone as well.
    #
    # Two facts about the text, not guesses about the layout: a word of
    # twenty letters does not exist in wine prose, French or English -
    # "exceptionnellement" is eighteen, which is why the threshold is
    # not eighteen - and a capital inside a word is two words run
    # together, as in "appellationPauillac". Each finds Batailley and
    # nothing else, in the proposals or in the records.
    if BROKEN_RUN.search(s) or BROKEN_CASE.search(s):
        return False
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

# The caption of a video, standing in front of the note transcribed
# from it: "Presentation de Chateau Batailley 2019 par Philippe
# Casteja." Who, which wine, which year - all three already in the
# record, and none of them a word about the wine.
#
# The whole shape is required, down to the full stop. Matching
# "presents" alone took the first sentence off Lafite 1990 - "The nose
# presents the classic aromas of cedar" - and off Ferrand 2006, where
# the wine presents itself in a robe with orange glints.
LEAD_CREDIT = re.compile(
    r'(?i)^\W*(?:pr[eé]sentation|commentaires?\s+de\s+d[eé]gustation)'
    r'\s+(?:de|du|des)\b[^.!?]{0,90}?\bpar\s+[^.!?]{0,40}[.!?]\s*')


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
    r'l[’\']ann[eé]e\s+viticole|the\s+(?:growing\s+)?year|'
    # The heading Margaux sets over the growing season on each of its
    # 152 vintage pages: "Climate / Winter, which was appreciably
    # colder than those of the previous years, caused late, but
    # perfectly regular bud-break". _is_heading still has to accept it,
    # so "the climate was mild" in the middle of a sentence is not one.
    r'\bclimate\b|\bclimat\b)')

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


# A heading in English, on a sheet that prints both languages. The
# estates translate their own descriptions and the reader was reading
# past the translation to take the French.
ENGLISH_LABEL = re.compile(r'(?i)(tasting|growing\s+season|'
                           r'the\s+\d{4}\s+vintage|the\s+(?:growing\s+)?year)')


# A match of nothing at the very start of the text, used as a label
# for a page, whose title is its label and whose title is furniture.
AT_START = re.compile(r'')


# A label that is also an ordinary subject of a sentence. Montrose
# prints "The year could have tipped into excess." and LABEL_NOTE
# matches "The year" in the middle of it.
LABEL_SUBJECT = re.compile(
    r"(?i)^(?:the|le|la|l[’']|this|ce|cette)\s*"
    r"(?:year|vintage|mill[eé]sime|ann[eé]e|season|saison|"
    r"harvest|r[eé]colte)$")
# The verb that follows a subject and never follows a heading. A
# closed list, because telling a verb from a noun needs a parser and
# this needs only to recognise the handful an estate writes.
LABEL_VERB = re.compile(
    r"(?i)^(?:could|can|would|will|shall|should|must|might|may|"
    r"was|were|is|are|has|have|had|began|begun|started|turned|"
    r"proved|brought|saw|gave|made|allowed|produced|"
    r"a|ont|est|sont|[eé]tait|[eé]taient|aura|aurait|"
    r"pourrait|peut|fut|furent|s[’']est|commence|commença|"
    r"d[eé]bute)\b")


def label_is_subject(text, m):
    """Is this label the subject of the sentence it stands in?

    True when the label reads as an article and a noun and the word
    after it is a verb carrying the sentence on - "The year could have
    tipped into excess". The window then has to start at the label and
    not after it, or the note opens on the middle of a sentence.

    A label in capitals, or followed by a colon, is a heading however
    it reads.
    """
    got = (m.group(0) or '').strip()
    if got.isupper() and len(got) > 3:
        return False
    after = text[m.end():m.end() + 30]
    if after.lstrip().startswith(':'):
        return False
    if not LABEL_SUBJECT.match(got):
        return False
    return bool(LABEL_VERB.match(after.lstrip(' \t')))


def _put_the_label_back(text, m, win):
    """The label's own sentence, back on the front of an approved note.

    `win` has passed every test. If the label read as the subject of
    the sentence it stood in, the words from the label up to `win` are
    the rest of that sentence, and the note should begin with them -
    "The year could have tipped into excess. Yet it found its balance"
    rather than "Yet it found its balance".

    Only when what is restored ends on a sentence boundary, so that it
    joins onto an opening which is itself the start of a sentence.
    Returns `win` unchanged whenever anything does not fit.
    """
    if not win or m is None or not m.group(0):
        return win
    if not label_is_subject(text, m):
        return win
    # Where the approved opening sits in the document.
    head = ' '.join(win[:60].split())
    tail = text[m.end():m.end() + 1400]
    flat_tail = ' '.join(tail.split())
    at = flat_tail.find(head)
    if at < 0:
        return win
    bridge = flat_tail[:at].strip()
    # It has to be the end of the label's sentence, and a short one:
    # anything long is a paragraph the tests never saw.
    if len(bridge) > 320:
        return win
    if bridge and not re.search(r'[.!?][\"\u201d\u2019\')\]]*$',
                                bridge):
        return win
    lead = (m.group(0).strip() + ' ' + bridge).strip()
    return (lead + ' ' + win).strip() if lead else win


def read_prose(text, page=False, shop=False):
    """The labelled tasting and season windows, cut at the stop-list."""
    out, how = {}, {}
    for field, lab in (('taste', LABEL_TASTE), ('note', LABEL_NOTE)):
        cands = [c for c in lab.finditer(text) if _is_heading(text, c)]
        # English first, then in the order the sheet prints them.
        cands.sort(key=lambda c: 0 if ENGLISH_LABEL.search(c.group(0))
                   else 1)
        # And last, for a page, the page itself: Margaux 1995 opens
        # "1995 is a truly great vintage ... Today the nose is not
        # exactly closed ... On the palate, it is obviously the power
        # that dominates", with no label over it because the page's
        # title is its label and the title is furniture. A labelled
        # tasting note still wins; this is only tried if none is
        # found, and it passes the same tests.
        if page and field == 'taste' and not shop:
            # Not on a shop listing, whose opening is its product
            # title: Chantegrive's reads "Magnum de Chantegrive Rouge -
            # 2020 CB | Chantegrive top of page Magnum Chateau de
            # Chantegrive rouge avec caisse bois".
            cands.append(AT_START.match(text))
        for m in cands:
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
            win = _strip_head(win)
            # A bilingual heading: Langoa-Barton and Leoville-Barton print
            # "DEGUSTATION / TASTING", so matching the French left "/
            # TASTING Robe dense de couleur pourpre" behind.
            # \d* because Giscours runs the heading into a page number:
            # "TASTING5 2 20 74 IM PER TUR BAB LE Audacieux Bold Precis".
            # In capitals only, so a sentence opening on the word
            # "millesime" is left alone - and repeatedly, because a
            # sheet may print its heading twice. Beychevelle's 2023
            # season note began "DE L'ANNEE MILLESIME 2023 CONDITIONS
            # CLIMATIQUES DE L'ANNEE Un printemps qui demarre", the
            # heading caught in the middle of its own repetition.
            for _ in range(5):
                # Not a year that is the subject of the sentence. This
                # loop strips a bare year because Beychevelle prints
                # "DE L'ANNEE MILLESIME 2023 CONDITIONS CLIMATIQUES"
                # and the year sits between two headings - but Margaux
                # 1995's page opens "1995 is a truly great vintage",
                # and stripping it there cost the note its first line.
                if OPENS_ON_A_YEAR.match(win):
                    break
                shorter = re.sub(
                    r'^(?:TASTING|DEGUSTATION|D\u00c9GUSTATION|VINTAGE|'
                    r'MILL\u00c9SIME|MILLESIME|CONDITIONS\s+CLIMATIQUES|'
                    # Figeac heads its season note "CLIMATOLOGIE ET
                    # CONDITIONS DE RECOLTE", the label matches the
                    # first word, and the rest of the heading was left
                    # at the front of every one of its notes.
                    r'ET\s+CONDITIONS\s+DE\s+R[E\u00c9]COLTE|'
                    r'CLIMATOLOGIE|DE\s+L[\u2019\']ANN\u00c9E|'
                    r'DE\s+L[\u2019\']ANNEE|(?:19|20)\d\d)\d*\b'
                    r'[\s:/–—-]*', '', win)
                if shorter == win:
                    break
                win = shorter
            # A date stamp: Villemaurine's note opens "AU 05/06/2014 Chateau
            # Villemaurine 2009, presente une robe".
            win = re.sub(r'^(?:AU|AS\s+OF|AT)\s+\d{1,2}[/.]\d{1,2}[/.]\d{2,4}'
                         r'[\s:,-]*', '', win, flags=re.I)
            # Once more, because taking the heading off can expose the page
            # numbers that were sitting behind it: "TASTING5 2 20 74 IM PER"
            # becomes "2 20 74 IM PER" and the first pass has already run.
            win = _strip_head(win)
            # The caption of the video the note was transcribed from,
            # and the quote mark an estate opens its note with. Last of
            # all, after _strip_head: the quote shields a number from
            # it, and taking the quote off first made Brane-Cantenac's
            # "« 05 + 10 = 15 »" - a pun on the vintage - open on
            # "+ 10 = 15", the 05 having looked like a page number.
            win = LEAD_CREDIT.sub('', win)
            win = win.lstrip(' :–-—«“”"')
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
            # An unlabelled opening that talks about the weather is the
            # year's story and not a note on the wine. Haut-Bailly's
            # vintage pages are articles about the year - "Spring was
            # wonderful and the budbreak, quick and even, was the first
            # factor in the vintage's overall regularity", "Apres trois
            # annees de faible production ... une recolte abondante" -
            # and offered as tasting notes they would say the same
            # thing as the note, in the wrong field. Margaux's openings
            # are about the wine and its season comes from under
            # "Climate", so the two never meet.
            #
            # Only for the unlabelled candidate: a note printed under
            # DEGUSTATION is the estate's own filing and is believed.
            if (field == 'taste' and not m.group(0)
                    and SEASON_OF.search(win[:300])):
                continue
            if field == 'note' and not SEASON_OF.search(win[:300]):
                continue
            # Every test above has run on the window as it was found.
            # Now, if the label was the subject of its own sentence,
            # that sentence goes back on the front: Montrose's season
            # note read "Yet it found its balance", with "The year
            # could have tipped into excess." sitting in front of it
            # where the label had matched.
            #
            # After the tests and not before, because the window's
            # first 300 characters are what the season test reads, and
            # moving the start pushed Kirwan 2017's "frost" past that
            # horizon and lost a note that was never in doubt.
            win = _put_the_label_back(text, m, win)
            out[field], how[field] = win, m.group(0)[:40]
            break
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
    r'(?i)('
    # The shop's own table, printed under the advice. Caillou's 2019
    # window is "10 a 12 ans apres la recolte" and ran on into
    # "Informations complementaires Poids ND Degre alcoolique".
    r'informations\s+compl[eé]mentaires|additional\s+information|'
    r'poids\s+ND\b|p[eé]riode\s+de\s+d[eé]gustation|d[eé]cantation|carafage|'
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


# A page that offers something for sale: a product path, a bottle
# count, a case, a gift box, a seasonal offer.
SHOP_PAGE = re.compile(
    r'(?i)(?:^|[_-])(produit|product|boutique|shop|panier|cart|'
    r'coffret|carton|lot-de|en-vente|magnum|magnums|'
    r'\d+-?bouteilles?|offre|offres)(?:[_-]|$)')
# The crawler truncates a long filename and the head goes first, so
# "produit" arrives as "roduit" or "duit": Paveil de Luze's
# 2020__duit-paveil-de-luze-2020-primeurs-cru-bourgeois-exceptionnel
# is a product page whose name no longer says so, and it offered the
# same CS80/ME20 as the twelve shop pages before it. Five filenames
# are docked this way. Only at the start, where the truncation
# happens, so an ordinary French word ending in "duit" is safe.
SHOP_DOCKED = re.compile(r'(?i)^\d{4}__[a-z]{0,6}(duit|roduct)[_-]')


def _is_shop(filename):
    """A page that offers something for sale, docked name or not."""
    f = filename or ''
    return bool(SHOP_PAGE.search(f) or SHOP_DOCKED.match(f))


def sells_another_wine(filename, grand):
    """A shop listing for a wine that is not this estate's.

    The page is for the product its URL names, so the product has to
    be the estate's. Dillon's own bottles are named - produit-6-
    bouteilles-chateau-dillon-2013 - and the rest of its shop is not:
    Leonie, Les Haldes de Luchey, Le Roman de Grand Baril, the summer
    offer of twenty-four bottles of Bordeaux.

    Only asked of a shop listing. A vintage page need not carry the
    estate's name in its URL and Margaux's do not.
    """
    if not (filename and grand) or not _is_shop(filename):
        return None
    fb = bare_name(filename)
    nb = bare_name(grand)
    if nb and nb in fb:
        return None
    for w in re.split(r'[^a-z0-9]+', norm(grand)):
        if len(w) > 3 and w not in NAME_COMMON and w in fb:
            return None
    return 'a shop listing that does not name the estate'


# The estate declaring which vintage a document is for.
VINTAGE_LABEL = re.compile(r'(?i)(?:mill[eé]sime|vintage)\s*:?\s*'
                           r'((?:19|20)\d\d)(?![0-9])')
# And the words that make it a mention rather than a declaration: an
# estate's first vintage ever, or a comparison with another year.
NOT_DECLARED = re.compile(
    r'(?i)(1\s*(?:st|er)|premier|first|depuis|since|rapproche|comme|'
    r'rappelle|proche\s+du|like\s+the|as\s+in|compared)\s*$')
# A declaration stands at the top. Further down, a year is something
# the wine is being compared to.
VINTAGE_HEAD = 300


def declares_another_vintage(year, text):
    """The vintage this document says it is for, if not `year`.

    None when the document declares nothing, declares the year asked
    for, or declares more than one so that no single year wins.
    """
    if not year or not text:
        return None
    said = set()
    for m in VINTAGE_LABEL.finditer(text[:VINTAGE_HEAD]):
        if NOT_DECLARED.search(text[max(0, m.start() - 14):m.start()]):
            continue
        said.add(int(m.group(1)))
    if len(said) != 1:
        return None
    got = said.pop()
    return None if got == int(year) else got


# The words that make the year beside them a vintage rather than a
# date. A page published in 2021 about the 2020 wine writes both.
VINTAGE_WORD = (r'mill[eé]sim\w*|vintage|primeurs?|vendanges?|'
                r'harvest|cuv[eé]e|ann[eé]e')
# The crawler's own prefix is the day the page went up, so it is cut
# off before anything is read from the name.
CRAWL_DATE = re.compile(r'^\d{4}__')
A_YEAR = re.compile(r'(?<!\d)((?:19|20)\d\d)(?!\d)')
# Two years joined by nothing but a dash: a vertical's span, not a
# claim about one wine. Leoville-Poyferre 1936-2018, tasted by Neal
# Martin, covers both ends and everything between.
YEAR_SPAN = re.compile(r'(?<!\d)((?:19|20)\d\d)\s*[-–—]\s*'
                       r'((?:19|20)\d\d)(?!\d)')
# How far either side of the year to look for the word that qualifies
# it. One separator, or three characters of one.
VINTAGE_NEAR = 26


def filename_vintage(year, filename, grand=None):
    """A vintage the filename names in words, if it is not `year`.

    None unless the filename calls some year a vintage and that year
    is not the one asked for. A year standing on its own says nothing:
    `top-100-wines-of-2021` is a list's year and `estivales-de-pessac
    -leognan-2020` is an event's, and neither is evidence about which
    wine a page describes.
    """
    if not year or not filename:
        return None
    # The crawler's prefix comes off the name as it is on disk: norm()
    # would have made it ` 2021 ...` and the anchor would never match.
    raw = CRAWL_DATE.sub('', filename)
    # A span the year asked for is an end of: the document covers it.
    # This one needs the dash, so it runs before the separators go.
    for m in YEAR_SPAN.finditer(raw):
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        if lo <= int(year) <= hi:
            return None
    stem = norm(raw)
    # The estate's own name, which puts a vintage after it: the words
    # that are this estate's and not every estate's.
    mine = [w for w in re.split(r'[^a-z0-9]+', norm(grand or ''))
            if len(w) > 3 and w not in NAME_COMMON]
    said = set()
    for m in A_YEAR.finditer(stem):
        before = stem[max(0, m.start() - VINTAGE_NEAR):m.start()]
        after = stem[m.end():m.end() + VINTAGE_NEAR]
        if (re.search(r'(?:' + VINTAGE_WORD + r')[^a-z0-9]{0,3}$',
                      before)
                or re.match(r'[^a-z0-9]{0,3}(?:' + VINTAGE_WORD + r')',
                            after)
                or any(re.search(w + r'[^a-z0-9]{0,3}$', before)
                       for w in mine)):
            said.add(int(m.group(1)))
    if not said or int(year) in said:
        return None
    # More than one and none of them ours: report the nearest, which
    # is the one a mis-filing is most likely to be about.
    return min(said, key=lambda y: abs(y - int(year)))


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


# Bordeaux's appellations, and the ways a sheet writes each one.
# Matched longest pattern first, so a compound name wins over the
# parent inside it.
APPS = {
    'Montagne-Saint-Émilion':
        r'montagne[\s-]+saint[\s-]*[eé]milion',
    'Lussac-Saint-Émilion': r'lussac[\s-]+saint[\s-]*[eé]milion',
    'Puisseguin-Saint-Émilion':
        r'puisseguin[\s-]+saint[\s-]*[eé]milion',
    'Saint-Georges-Saint-Émilion':
        r'saint[\s-]+georges[\s-]+saint[\s-]*[eé]milion',
    'Lalande-de-Pomerol': r'lalande[\s-]*(?:de)?[\s-]*pomerol',
    'Canon-Fronsac': r'canon[\s-]+fronsac',
    'Saint-Émilion': r'(?:st|saint)[\s.-]*[eé]milion',
    'Pomerol': r'pomerol',
    'Pauillac': r'pauillac',
    'Margaux': r'margaux',
    'Saint-Julien': r'(?:st|saint)[\s.-]*julien',
    'Saint-Estèphe': r'(?:st|saint)[\s.-]*est[eè]phe',
    'Moulis-en-Médoc': r'moulis(?:[\s-]+en[\s-]+m[eé]doc)?',
    'Listrac-Médoc': r'listrac(?:[\s-]+m[eé]doc)?',
    'Pessac-Léognan': r'pessac[\s-]+l[eé]ognan',
    'Sauternes': r'sauternes',
    'Barsac': r'barsac',
    'Cérons': r'c[eé]rons',
    'Fronsac': r'fronsac',
    'Castillon': r'castillon',
    'Blaye': r'blaye',
    'Côtes de Bourg': r'c[oô]tes\s+de\s+bourg',
    'Entre-deux-Mers': r'entre[\s-]+deux[\s-]+mers',
    'Loupiac': r'loupiac',
    'Sainte-Croix-du-Mont':
        r'sainte?[\s-]+croix[\s-]+du[\s-]+mont',
    'Cadillac': r'cadillac',
    'Haut-Médoc': r'haut[\s-]+m[eé]doc',
    'Médoc': r'm[eé]doc',
    'Graves': r'graves',
    'Bordeaux Supérieur': r'bordeaux\s+sup[eé]rieur',
    'Bordeaux': r'bordeaux',
    'Vin de France': r'vin\s+de\s+france',
}
# A parent region or a catch-all, which any estate may print and which
# therefore convicts nobody: Dauzac's 2008 note says "its rank as a Cru
# Classe of the Medoc", and Dauzac is Margaux.
APP_GENERIC = set(['Haut-Médoc', 'Médoc', 'Graves', 'Bordeaux',
                   'Bordeaux Supérieur', 'Vin de France'])
APP_ORDER = sorted(APPS, key=lambda k: -len(APPS[k]))
APP_RX = dict((k, re.compile(r'(?i)(?<![a-z])' + APPS[k] + r'(?![a-z])'))
              for k in APPS)


def apps_in(text):
    """Which appellations a text names, compounds before their parents.

    "Lalande de Pomerol" is Lalande-de-Pomerol and not Pomerol, so a
    match claims its span and a shorter name inside that span does not
    count.
    """
    found, taken = [], []
    for k in APP_ORDER:
        for m in APP_RX[k].finditer(text or ''):
            if any(m.start() < e and m.end() > s for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append(k)
            break
    return found


def app_canon(name):
    """An appellation as written, reduced to one of the canonical names."""
    got = apps_in(name)
    return got[0] if got else None


# A filename that says the document is press. is_dossier reads the body
# and catches a press pack by its contents; this catches the ones whose
# contents are a magazine page - a review, a listing, a clipping - and
# whose only tell is the name they were filed under.
PRESS_NAME = re.compile(r'(?i)(?<![a-z])('
                        r'revue[-_ ]?de[-_ ]?presse|press[-_ ]?review|'
                        # Clerc-Milon's planting came off
                        # Dossier-de-Presse-Chateau-Clerc-Milon_2025,
                        # which "presse" catches, and then off
                        # Press-Kit-Chateau-Clerc-Milon_2025, which it
                        # did not: the same document in English.
                        r'press[-_ ]?kit|dossier[-_ ]?de[-_ ]?presse|'
                        r'media[-_ ]?kit|'
                        r'tv[-_ ]?magazine|magazine|gault|millau|'
                        r'figaro|sud[-_ ]?ouest|terre[-_ ]?de[-_ ]?vins|'
                        r'rvf|wine[-_ ]?spectator|wine[-_ ]?enthusiast|'
                        r'decanter|bettane|desseauve|jancis|parker|'
                        r'suckling|galloni|vinous|france\s?[0-9]|'
                        r'journal|presse|article|interview|communique'
                        r')(?![a-z])')


# The filename calling itself the estate's own sheet. A document that
# says this is not press, however much press it also reprints.
SHEET_NAME = re.compile(
    r'(?i)(?<![a-z])(fiche[-_ ]?technique|technical[-_ ]?sheet|'
    r'tech[-_ ]?sheet|fact[-_ ]?sheet|fiche[-_ ]?de[-_ ]?degustation|'
    r'ft[-_ ])')


# Terms that describe a document someone named by hand but that are
# a section of a site when they come from a URL. A crawled page is
# named after its path, so `chateau-figeac.com/article/1971-une-
# revelation` arrives called `article-1971-une-revelation` - and
# `article` there is Figeac's own section, holding Figeac's own words
# about Figeac's wine. In a PDF called `Article-Sud-Ouest-22-juin-
# 2021.pdf` the same word is a description, and true.
PRESS_IF_NAMED = re.compile(r'(?i)^(?:article|interview)$')


def is_press_name(filename, page=False):
    """Does the filename say this is press rather than a sheet?

    None when the name also calls the document a technical sheet.
    Estates bind the two together and name both: Marquis de Terme
    publishes `MdT-2017-Fiche-technique-Revue-de-Presse-Marquis-de-
    Terme.pdf` for every vintage, and reading only the second half of
    that name put nine vintages out of reach.

    `page` says the filename came from a URL path rather than from
    somebody naming a file, which makes the terms in PRESS_IF_NAMED
    the name of a section of the estate's own site instead of a
    description of the document. The rest of the terms stand either
    way, so a page called `en-article-terre-de-vins-mars-2021` is
    still press - on `terre-de-vins`, which is the real evidence.
    """
    if SHEET_NAME.search(filename or ''):
        return None
    for m in PRESS_NAME.finditer(filename or ''):
        if page and PRESS_IF_NAMED.match(m.group(1)):
            continue
        return m.group(1)
    return None


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


# A blend written as a sentence, which is how an estate that publishes
# a page rather than a sheet states it.
BLEND_VARS = (
    ('CS', r'cabernets?[\s-]+sauvignons?'),
    ('CF', r'cabernets?[\s-]+francs?'),
    ('PV', r'petits?[\s-]+verdots?'),
    ('SB', r'sauvignons?[\s-]+blancs?'),
    ('SG', r'sauvignons?[\s-]+gris'),
    ('ME', r'merlots?'),
    ('MA', r'malbecs?|c[oô]ts?'),
    ('CM', r'carm[eé]n[eè]res?'),
    ('SEM', r's[eé]millons?'),
    ('MU', r'muscadelles?'),
    # Last, so "cabernets sauvignons" and "cabernets francs" are
    # matched by their own patterns above before this is reached.
    # Margaux writes "The cabernets (87% of the blend)" and lists the
    # franc separately a sentence later, so the plural on its own is
    # its cabernet sauvignon. The plural only: a bare singular
    # "cabernet" in Bordeaux could be either.
    ('CS', r'cabernets'),
)
BLEND_ANY = re.compile(r'(?i)(?<![a-z])(' + '|'.join(
    p for _, p in BLEND_VARS) + r')(?![a-z])')
BLEND_WHICH = tuple((k, re.compile(r'(?i)^(?:' + p + r')$'))
                    for k, p in BLEND_VARS)
BLEND_PCT = re.compile(r'(\d{1,3}(?:[.,]\d)?)\s*%')
# The words that mean this is the wine's assemblage.
BLEND_ANCHOR = re.compile(r'(?i)(assemblage|\bblend\b|grand\s+vin|'
                          r'went\s+into|composition\s+du\s+vin|'
                          # Margaux 2013 never says blend: "the
                          # proportions of the grape varieties are
                          # unusual: 94% cabernet sauvignon".
                          r'proportions?\s+of\s+the\s+grape\s+vari|'
                          r'proportions?\s+des\s+c[eé]pages)')
# And the words that mean it is what the vineyard is planted with,
# which is this dataset's commonest defect and not a blend at all.
BLEND_PLANTING = re.compile(
    r'(?i)(enc[eé]pagement|plant[eé]|planted|plantation|densit[eé]|'
    r'superficie|surface|hectares?|[aâ]ge\s+(?:moyen|des\s+vignes)|'
    r'average\s+age|vineyard\s+area)')
# "Merlot and cabernet franc, at 2% and 3% respectively": two
# varieties sharing one list of figures, in order. The word is what
# makes the order safe to trust - without it, pairing two names to two
# numbers is a guess, and a wrong guess still sums to 100.
BLEND_RESPECTIVE = re.compile(r'(?i)\brespectiv(?:ely|ement)\b')
BLEND_PAIR_BACK = 170   # how far back of "respectively" to read

BLEND_TOUCH = 3     # a figure standing beside its variety
BLEND_REACH = 90    # or further on, across words, in one sentence
BLEND_WINDOW = 320


def _blend_name(s):
    for k, rx in BLEND_WHICH:
        if rx.match(s.strip()):
            return k
    return None


def blend_in_prose(text, second=None):
    """A blend stated in sentences, or None.

    For pages only. Every way this was got wrong - and it was got
    wrong four times - came of a column flattened into a line, where
    each variety ends up beside its neighbour's figure. A page has no
    columns.

    A figure touching a variety belongs to it, on either side:
    "59% Cabernet Sauvignon", "Merlot 38%", "Cabernet franc (3%)".
    Only a variety with nothing beside it looks further on, and then
    only forwards and only if no other variety stands in between,
    which is how Margaux writes "cabernet sauvignon ... accounting
    for 87%".

    It stops at the second wine's name, because Haut-Bailly prints
    "Chateau Haut-Bailly : 59% Cabernet Sauvignon - 41% Merlot La
    Parde Haut-Bailly : 50% ..." and what follows is La Parde's.
    """
    text = ' '.join((text or '').split())
    if second:
        mark = mark_of(second, None)
        if mark:
            words = [w for w in re.split(r'[^a-z0-9]+', norm(mark)) if w]
            if words:
                rx = re.compile(r'(?i)(?<![a-z])'
                                + r'\s*'.join(re.escape(w)
                                               for w in words))
                m = rx.search(text)
                if m and m.start() > 40:
                    text = text[:m.start()]

    pcts = [(m.start(), m.end(), float(m.group(1).replace(',', '.')))
            for m in BLEND_PCT.finditer(text)]
    if not pcts:
        return None
    vs = []
    for m in BLEND_ANY.finditer(text):
        k = _blend_name(m.group(0))
        if k:
            vs.append((m.start(), m.end(), k))
    if len(vs) < 2:
        return None

    got, taken, used = {}, set(), []

    def claim(vi, pi):
        s, e, k = vs[vi]
        got.setdefault(k, pcts[pi][2])
        taken.add(pi)
        used.append((min(s, pcts[pi][0]), max(e, pcts[pi][1])))

    # A list of varieties sharing a list of figures, paired in the
    # order they are written, because the sentence says they are.
    # Margaux 2016: "Merlot and cabernet franc, at 2% and 3%
    # respectively". Taken first, so the touching rule cannot give
    # the 2% to the franc standing next to it.
    for r in BLEND_RESPECTIVE.finditer(text):
        lo = max(0, r.start() - BLEND_PAIR_BACK)
        # Within the sentence the word stands in, which is the list it
        # refers to. Margaux 2016 has "making up 94% of the blend."
        # immediately before "Merlot and cabernet franc, at 2% and 3%
        # respectively", and reading across that full stop found three
        # names for three figures and had to give up on all of them.
        stop = None
        for b in re.finditer(r'[.!?]\s', text[lo:r.start()]):
            stop = b.end()
        if stop is not None:
            lo += stop
        mine = [i for i, (s, e, k) in enumerate(vs)
                if lo <= s and e <= r.start()]
        theirs = [i for i, (ps, pe, v) in enumerate(pcts)
                  if lo <= ps and pe <= r.start() and i not in taken]
        # Equal counts, at least two, and every figure after every
        # name - which is what "respectively" describes.
        if len(mine) != len(theirs) or len(mine) < 2:
            continue
        if vs[mine[-1]][1] > pcts[theirs[0]][0]:
            continue
        for vi, pi in zip(mine, theirs):
            if vs[vi][2] not in got:
                claim(vi, pi)

    for vi, (s, e, k) in enumerate(vs):
        if k in got:
            continue
        for pi, (ps, pe, val) in enumerate(pcts):
            if pi in taken:
                continue
            if 0 <= s - pe <= BLEND_TOUCH or 0 <= ps - e <= BLEND_TOUCH:
                claim(vi, pi)
                break
    for vi, (s, e, k) in enumerate(vs):
        if k in got:
            continue
        for pi, (ps, pe, val) in enumerate(pcts):
            if pi in taken or ps < e or ps - e > BLEND_REACH:
                continue
            if BLEND_ANY.search(text[e:ps]):
                break
            claim(vi, pi)
            break

    if len(got) < 2 or abs(sum(got.values()) - 100) > 1.5:
        return None
    lo = max(0, min(s for s, e in used) - BLEND_WINDOW)
    hi = min(len(text), max(e for s, e in used) + BLEND_WINDOW)
    win = text[lo:hi]
    if not BLEND_ANCHOR.search(win) or BLEND_PLANTING.search(win):
        return None
    return got


def naming_of(path, filename=None):
    """Everything that names this document: its filename and its URL.

    A crawled page's filename is docked when the URL is long, and the
    head goes first - "rose-x-giscours-2020" becomes
    "se-x-giscours-2020" - which blinds every guard that reads the
    name. The URL survives on the page's first line, so both are
    handed to the guards together.
    """
    name = filename or os.path.basename(path or '')
    if not is_page(path):
        return name
    u = page_url(path)
    if not u:
        return name
    # The path and the last segment, without the scheme or the host,
    # which say nothing about the wine.
    tail = re.sub(r'^https?://[^/]+', '', u)
    return name + ' ' + tail.replace('/', ' ')


def naming_spells_cuvee(named, grand, others=(), second=None):
    """The estate's other wine whose name this document spells, or None.

    For the names that contain the estate's own. Margaux du Chateau
    Margaux spells `margauxduchateaumargaux`, which holds the grand
    vin's `margaux` inside it, so every test of whether the name
    belongs to the estate says yes. Compared by length, the cuvee
    wins, and the document is the cuvee's.

    Only when the cuvee's letters really are longer than the grand
    vin's: a cuvee whose name is shorter, or the same, says nothing
    this way and is left to the other guards.
    """
    if not named or not grand:
        return None
    mine = bare_name(grand)
    if not mine:
        return None
    letters = re.sub(r'[^a-z0-9]+', '', norm(named))
    best = None
    for nm in tuple(others or ()) + ((second,) if second else ()):
        if not nm:
            continue
        b = bare_name(nm)
        if not b or b == mine or len(b) <= len(mine):
            continue
        # The cuvee has to contain the estate's name, which is what
        # makes it the containment case this is for. A cuvee with an
        # unrelated name is caught by names_other_chateau already.
        if mine not in b:
            continue
        if b in letters and (best is None or len(b) > len(best[0])):
            best = (b, nm)
    return best[1] if best else None


def whose_sheet(path, filename=None, grand=None, others=(), second=None,
                cat=None, year=None, names_only=False):
    """Is this sheet the estate's grand vin for this vintage?

    None when it is. Otherwise a dict with

        why   what is wrong with it, in words fit for a report
        role  what the manifest should call it: skip, second, other,
              unknown
        wine  the other wine's name, where a guard identified one

    The order is the one each guard earned. Cheap filename tests before
    anything opens the document; the vintage first of all, because a
    sheet filed under a year nothing states is not evidence for that
    year whoever's wine it is; then the document's own claims.

    names_only stops before anything is opened, which is what
    tools/recheck-sources.py needs to ask the name guards about all
    12,393 documents twice over. It used to ask them by naming each
    one itself, and that copy fell behind the chain twice.
    """
    filename = filename or os.path.basename(path)
    # A docked filename names less than the URL it was made from.
    named = naming_of(path, filename)
    try:
        if year and not names_only and not year_said(year, named):
            if not year_said(year, filename,
                             ' '.join(flat(path).split())):
                return {'why': 'nothing states this vintage',
                        'role': 'unknown', 'wine': None}
        if year and not names_only:
            try:
                head = ' '.join(flat(path).split())
            except Exception:
                head = ''
            other = declares_another_vintage(year, head)
            if other:
                return {'why': 'the document declares the %d vintage'
                               % other, 'role': 'unknown', 'wine': None}
            # A page filed under the day it was published, about a
            # wine made the year before.
            named_year = filename_vintage(year, named, grand)
            if named_year:
                return {'why': 'the filename calls this the %d vintage'
                               % named_year,
                        'role': 'unknown', 'wine': None}
        press = is_press_name(named, page=is_page(path))
        if press:
            return {'why': 'the filename says it is press: %s' % press,
                    'role': 'skip', 'wine': None}
        spells = names_other_chateau(named, grand, others, second)
        if spells:
            return {'why': 'the filename names another château: %s'
                           % spells, 'role': 'other', 'wine': spells}
        sold = sells_another_wine(named, grand)
        if sold:
            return {'why': sold, 'role': 'other', 'wine': None}
        # A cuvee whose name contains the estate's own, spelled out in
        # full: Margaux du Chateau Margaux, on its own page.
        spelt = naming_spells_cuvee(named, grand, others, second)
        if spelt:
            return {'why': 'the name spells another of the estate’s '
                           'wines in full: %s' % spelt,
                    'role': ('second' if spelt == second else 'other'),
                    'wine': spelt}
        abbrev = abbreviates_other_wine(named, grand, others)
        if abbrev:
            return {'why': 'the filename abbreviates another of the '
                           'estate’s wines: %s' % abbrev,
                    'role': 'other', 'wine': abbrev}
        if wrong_colour(named, None, cat):
            return {'why': 'the filename says another colour',
                    'role': 'other', 'wine': None}
        # Everything from here needs the document itself.
        if names_only:
            return None
        if is_dossier(path):
            return {'why': 'a press dossier, not a vintage’s sheet',
                    'role': 'skip', 'wine': None}
        # The blend reader has asked this since it was written and the
        # field reader never did: a document that calls itself the
        # second wine is the second wine's, whatever its filename says.
        if is_second_wine(path):
            return {'why': 'the document calls itself the second wine',
                    'role': 'second', 'wine': second}
        for nm in (second,) + tuple(others or ()):
            if nm and names_another_wine(path, filename, grand, nm):
                return {'why': 'the sheet names another of the '
                               'estate’s wines: %s' % nm,
                        'role': ('second' if nm == second else 'other'),
                        'wine': nm}
        if confirms_estate(path, filename, grand, others) == 'other':
            return {'why': 'the sheet names a sibling property',
                    'role': 'unknown', 'wine': None}
    except Exception as e:
        return {'why': 'a guard could not read it: %s' % str(e)[:40],
                'role': 'unknown', 'wine': None}
    return None


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
    # Every reason a sheet is not this wine's lives in one place now,
    # so a guard added for one reader applies to all three.
    not_ours = whose_sheet(path, filename, grand, others, second, cat,
                           year)
    if not_ours:
        return {}, {'refused': not_ours['why']}

    try:
        text = ' '.join(flat(path).split())
    except Exception:
        return {}, {'refused': 'unreadable'}

    got, how = read_numbers(text)
    # A blend written as a sentence, which only a page is trusted for:
    # every way of reading one off a PDF came to grief on a flattened
    # column. On a PDF the blend is blend_of's business.
    # And not from a shop listing. Its description is written to sell a
    # bottle and is reused: Paveil de Luze's product pages state
    # "Assemblage : 70 % Cabernet Sauvignon - 30 % Merlot" for 1998
    # through 2009 and 80/20 for 2011 through 2016, which is a standard
    # description and not twelve assemblages. A figure that does not
    # move across a decade is not a vintage's - the lesson plantings.js
    # was built for - and here there is no planting on record to check
    # it against, so the source decides: an estate's own vintage page
    # states a vintage's blend, a shop's product page states the
    # wine's usual one.
    if is_page(path) and not _is_shop(filename):
        b = blend_in_prose(text, second)
        if b:
            got['blend'] = b
            how['blend'] = 'stated in prose'
    more, howm = read_prose(
        text, page=is_page(path),
        shop=_is_shop(filename))
    got.update(more)
    how.update(howm)
    more, howm = read_advice(text)
    got.update(more)
    how.update(howm)
    return got, how
