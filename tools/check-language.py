# -*- coding: utf-8 -*-
"""Guards for the things nobody notices until they read the dashboard.

    python tools/check-language.py


Sjoerd kept seeing French come back in the descriptions, and asked for
guards rather than another pair of eyes. These are the ones that can be
checked mechanically:

  FRENCH LEFT IN AN ENGLISH FIELD. The estates write their sheets in
  French as often as not, and a note read off one and never translated
  reads as French to anyone using the dashboard in English. Counting
  words that are French and are not also English - le, des, qui, nous,
  tres, apres - separates a French paragraph from an English one that
  happens to say chateau.

  NOTHING IN DUTCH. data/fiches-nl.js holds the Dutch of each field. A
  record with an English note and no Dutch one shows the English, which
  is correct but not finished, and the only way to know how much is
  outstanding is to count it.

  THE WORKBOOK OLDER THAN THE DATA. reports/bordeaux-coverage.xlsx is
  built from data/, and for a day it was two hundred record changes
  behind without saying so.

  THE SERVICE WORKER NOT BUMPED. CACHE_NAME is what makes a phone fetch
  new data. If data/ has changed since the last commit that touched
  service-worker.js, nobody gets what changed.

Exit code 1 if anything wants attention, so it can gate a commit.
"""
import io, os, re, sys, json, subprocess, collections, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep

# Words that are French and are not English. A few can be chance - "la
# tour", "clos du" - so the test is how many.
FRENCH = re.compile(
    r'(?i)(?<![a-zà-ÿ])('
    r'le|la|les|des|du|qui|nous|très|avec|dans|sont|cette|cet|'
    r'ces|aux|leur|leurs|nos|notre|pour|bien|toute|toutes|ainsi|'
    r'puis|après|dès|chez|entre|alors|encore|depuis|pendant|'
    r'lors|comme|mais|donc|où|ont|été|'
    r'déjà|tandis|lorsque|afin|sous|elle|'
    r'elles|plutôt|ainsi|lorsqu|jusqu|étaient|avaient'
    r')(?![a-zà-ÿ])')
# Words taken out again because they are English too, and between them
# they flagged Latour's 2019 note - which is written in English - on
# "on 21st March", "on 28th March", "set in", "est":
#   on, en, est, y, car, se, ne, pas, il, ils, plus, tout, fait, peu,
#   sans, vers, sur
# A guard that cries wolf is worse than no guard, because the next
# person stops reading it.
FRENCH_MIN = 6
# A count of six works on a paragraph and fails on a sentence. Climens
# 2019's tasting note is "Quoique legerement reserve au tout premier
# nez, il s'impose d'emblee comme un grand vin, equilibre, long,
# complexe et d'une grande finesse." - 160 characters, French to anyone
# reading it, and three markers. Eleven fields were sitting under the
# threshold like that while this guard reported everything clean.
#
# So: six markers anywhere, or three in a field short enough that three
# is already a density. Measured over all 762 prose fields, this adds
# the eleven and flags nothing that is in English.
FRENCH_SHORT = 320
FRENCH_SHORT_MIN = 3
# A few words added with the same care as the ones taken out. Each is
# French and is not English, and none is wine vocabulary that English
# tasting notes borrow - "robe", "cru", "terroir" and "nez" are all
# used by the English notes in this file and are deliberately absent.
FRENCH_MORE = re.compile(
    r'(?i)(?<![a-zà-ÿ])('
    r'une|quoique|dont|dévoile|dévoilent|marquée|marqué|arômes|'
    r'fraîcheur|équilibre|équilibrée|puissance|généreuse|généreux|'
    r'irise|reflets|couleur|bouche|soyeux|soyeuse|velouté|'
    r'longue|frais|fraîche'
    r')(?![a-zà-ÿ])')
# "fine" and "finesse" were in that list for an hour and flagged three
# English notes - "the wines show a fine colour", "of fine precision".
# Both are ordinary English. The rule stands: a word goes in this list
# only if it is French and is NOT English, and wine writing in English
# has borrowed more French than it looks.

# The fields the dashboard shows as prose, and the key that says a Dutch
# version exists.
PROSE = ('note', 'taste', 'window', 'decant', 'food')
STR = r"((?:[^'\\]|\\.)*)"


def unesc(s):
    return re.sub(r'\\(.)', r'\1', s)


def records(path):
    out = {}
    for line in io.open(path, encoding='utf-8'):
        m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$", line.rstrip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def field(body, key):
    m = re.search(key + r":'" + STR + r"'", body)
    return unesc(m.group(1)) if m else None


fail = collections.OrderedDict()


def note(kind, msg):
    fail.setdefault(kind, []).append(msg)


en = records(ROOT + 'data/fiches.js')
nl = records(ROOT + 'data/fiches-nl.js')

# ------------------------------------------------ French in English
counts = collections.Counter()
for key, body in sorted(en.items()):
    for f in PROSE:
        v = field(body, f)
        if not v:
            continue
        counts[f] += 1
        n = len(FRENCH.findall(v)) + len(FRENCH_MORE.findall(v))
        if n >= FRENCH_MIN or (len(v) < FRENCH_SHORT
                               and n >= FRENCH_SHORT_MIN):
            note('French left in an English field',
                 '%-26s %-7s %2d French words: %s'
                 % (key, f, n, v[:64].replace('\n', ' ')))

# ------------------------------- a note that names another chateau
#
# Found by reading this tool's own output: Leboscq's tasting notes for
# 2020 to 2023 all begin "Chateau Tour de Capet ...", which is a
# Saint-Emilion and not a Medoc cru bourgeois - and its 2022 note is
# headed 2021 as well.
#
# The test is the word Chateau, Clos or Domaine followed by a name,
# because that is a wine being named. Matching estate names loose in the
# prose instead flagged seven and meant five things: "2018 a Margaux" is
# the appellation, "notes de violette" is a flower, and La Mission
# Haut-Brion contains Haut-Brion.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import sheetreader as _sr
    E = _sr.estates(ROOT)
except Exception:
    E = {}
# Capitalised, both the house word and the name after it. French uses
# "le chateau" as a common noun - "depuis le rachat par la famille" sits
# right after one on Pedesclaux's sheet - and a name does not begin in
# lower case.
CAP = r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'’-]*"
# A particle inside a name stays lower case - Tour de Capet, La Fleur du
# Roy - so requiring every word capitalised found "Tour" and stopped,
# which is too short to place and lost the four real findings.
PART = r"(?:de|du|des|la|le|les|d'|d’|l'|l’|et|aux?)"
HOUSE = re.compile(r"(?<![A-Za-z])(?:Ch[aâ]teau|CH[AÂ]TEAU|Clos|"
                   r"Domaine)\s+(" + CAP + r"(?:\s+(?:" + PART + r"|" + CAP
                   + r")){0,3})")


def depossess(s):
    """Chateau Coutet's terroirs is still Chateau Coutet."""
    return re.sub(r"(?:'|’)s\b", '', s)
if E:
    for key, body in sorted(en.items()):
        mine = E.get(key.split('|')[0]) or {}
        ours = [mine.get('name') or ''] + list(mine.get('cuvees') or ())
        for f in ('taste', 'note'):
            v = field(body, f)
            if not v:
                continue
            for m in HOUSE.finditer(v[:400]):
                said = depossess(' '.join(m.group(1).split()[:4]))
                if len(_sr.packed(said)) < 6:
                    continue
                # Longest prefix of what follows the house word that we
                # can place, so "Tour de Capet 2020 se distingue" is
                # tested as Tour de Capet and not as the whole sentence.
                words = said.split()
                if any(_sr.says_in_name(' '.join(words[:n]), o)
                       or _sr.says_in_name(o, ' '.join(words[:n]))
                       for n in range(len(words), 0, -1) for o in ours if o):
                    continue
                note('a description that names another château',
                     '%-26s %-6s says "%s": %s'
                     % (key, f, said[:26],
                        ' '.join(v[:46].split())))
                break

# ------------------------------- a data block left inside the prose
#
# rauzan-segla|2019 and canon|2019 - both Chanel properties, the same
# sheet template - kept the whole block in `note`: the season, then
# HARVEST TIME with the picking dates per variety, then YIELD 45hl/ha
# and AGEING 18 months, and only then the vintage's own description.
# Every other vintage of both estates was split, and these two were not,
# because their originals were already in English and so fell outside
# the pass that split the rest. The defect lands where nothing looks.
#
# The labels are matched CASE-SENSITIVELY, as the headings the sheets
# print. Lower-case "until harvest time" is ordinary English and occurs
# in Pontet-Canet's 2009 and 2010 notes, and "Technical Manager" is
# deliberately absent: Cos d'Estournel quotes its own technical director
# by name inside two tasting notes, which is prose and not a heading.
#
# The second half of this list came from reading the fields the first
# half did not catch. Vray-Croix-de-Gay's 2012 and 2017 tasting notes
# both ran on into "The Vineyard TERROIR : gravel, deep clays, sandy
# clays SURFACE AREA : 46,18 ha VITICULTURE BY PLOT : 40 plots", which
# is the property's description and identical on both; Valandraud's 2008
# note ended on "L VAL08 Alcool 15% 3380820046547 Mise en bouteille
# 24/09/2010" - the words off the back label, barcode and all. A run of
# thirteen digits is an EAN and has no business in prose.
BLOCK = re.compile(
    r'(HARVEST TIME|DATES DE VENDANGES?|YIELD \d|RENDEMENT\s*:?\s*\d|'
    r'AGEING \d+ months|[EÉ]LEVAGE\s*:?\s*\d+\s+mois|ANALYSE \d|'
    r'in a few points|en quelques mots|BOTTLING DATE|'
    r'Date de mise en bouteille|Mise en bouteille \d|'
    r'SURFACE AREA|VITICULTURE BY PLOT|TERROIR\s*:|'
    r'The Vineyard TERROIR|(?<!\d)\d{13}(?!\d))')
for name, recs in (('fiches.js', en), ('fiches-nl.js', nl)):
    for key, body in sorted(recs.items()):
        for f in PROSE:
            v = field(body, f)
            if not v:
                continue
            m = BLOCK.search(v)
            if m:
                note('a sheet’s data block left inside the prose',
                     '%-26s %-6s %s says "%s"'
                     % (key, f, name, m.group(1)[:24]))
                break

# ------------------------------------- typographic ligatures
#
# A PDF writes "confirme" as conﬁrme, one character for the fi, and
# the reader will never find it by searching for confirme. The aroma
# wheel, which matches words out of the tasting note, misses any word
# carrying one, and the Dutch files have none - so the two languages
# disagree about the same word. Found when one of them crashed a script
# that was printing French fields.
LIGATURES = {'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl',
             'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'st',
             'Œ': 'OE', 'œ': 'oe'}
for name, recs in (('fiches.js', en), ('fiches-nl.js', nl)):
    for key, body in sorted(recs.items()):
        for lig, plain in LIGATURES.items():
            if lig in body:
                note('a typographic ligature from a PDF',
                     '%-26s %s has U+%04X, which should be "%s"'
                     % (key, name, ord(lig), plain))
                break

# ------------------------- Dutch with nothing behind it in English
#
# The other direction, which nothing was watching. fiches.js is the
# record and fiches-nl.js holds "de Nederlandse tegenhanger" of each of
# its fields; what is missing there falls back to the English. The
# reverse was never considered, and it is not harmless: app.js builds
# the Dutch view by copying the English record and then overwriting
# each field the Dutch file has, so a Dutch note whose English
# counterpart does not exist is *shown* in Dutch and shown nowhere in
# English. The two languages then describe different wines.
#
# Twenty-five of these, and they are older than this repository's
# history: coutet|2010's Dutch note is there in the first commit that
# has the file and its English note is in none of them. So they came
# from somewhere other than fiches.js, and whether to translate them
# back into English or drop them is a judgement about provenance, not
# something a tool should decide. Hence: reported, with the count, and
# left alone.
orphan_rec = sorted(set(nl) - set(en))
for key in orphan_rec:
    note('Dutch for a record that does not exist in English',
         '%-26s %s' % (key, ' '.join(
             re.findall(r'([a-z]+):', nl[key]))[:46]))
for key in sorted(nl):
    if key not in en:
        continue
    for f in PROSE:
        if field(nl[key], f) and not field(en[key], f):
            note('Dutch for a field that does not exist in English',
                 '%-26s %-7s shows in Dutch and nowhere in English'
                 % (key, f))

# ------------------------------------------------ Dutch coverage
missing = collections.Counter()
for key, body in en.items():
    for f in PROSE:
        if field(body, f) and not (key in nl and field(nl[key], f)):
            missing[f] += 1

# ------------------------------------------------ derived artefacts
def mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0


wb = ROOT + 'reports/bordeaux-coverage.xlsx'
newest_data = max([mtime(ROOT + 'data/' + f)
                   for f in os.listdir(ROOT + 'data')
                   if f.endswith(('.js', '.json'))] or [0])
if not os.path.exists(wb):
    note('the coverage workbook', 'not built; run tools/build-workbook.py')
elif mtime(wb) < newest_data - 1:
    note('the coverage workbook',
         'older than data/ by %s; run tools/build-workbook.py'
         % str(datetime.timedelta(
             seconds=int(newest_data - mtime(wb)))))


def git(*args):
    try:
        return subprocess.run(('git', '-C', ROOT) + args, capture_output=True,
                              text=True, encoding='utf-8').stdout.strip()
    except Exception:
        return ''


sw_commit = git('log', '-1', '--format=%H', '--', 'service-worker.js')
data_commit = git('log', '-1', '--format=%H', '--', 'data')
if sw_commit and data_commit and sw_commit != data_commit:
    behind = git('rev-list', '--count', '%s..%s' % (sw_commit, data_commit))
    if behind and behind != '0':
        note('the service worker cache',
             'CACHE_NAME last changed %s commits before data/ last changed; '
             'bump it or nobody gets the new data' % behind)
if git('status', '--porcelain', '--', 'data') and not git(
        'status', '--porcelain', '--', 'service-worker.js'):
    note('the service worker cache',
         'data/ is modified and service-worker.js is not; bump CACHE_NAME')

# ------------------------------------------------ what it found
print('%d English records, %d with Dutch' % (len(en), len(nl)))
print()
print('%-10s %9s %9s %9s' % ('field', 'English', 'Dutch', 'to do'))
for f in PROSE:
    have = counts[f] - missing[f]
    print('%-10s %9d %9d %9d' % (f, counts[f], have, missing[f]))
print('%-10s %9d %9d %9d' % ('all', sum(counts.values()),
                             sum(counts.values()) - sum(missing.values()),
                             sum(missing.values())))

total = 0
for kind, rows in fail.items():
    print('\n%s: %d' % (kind, len(rows)))
    for r in rows[:16]:
        print('   ' + r)
    if len(rows) > 16:
        print('   ... and %d more' % (len(rows) - 16))
    total += len(rows)
if sum(missing.values()):
    print('\n%d prose fields have no Dutch yet' % sum(missing.values()))
print('\n%s' % ('every guard passes' if not total
                else '%d to look at' % total))
sys.exit(1 if total else 0)
