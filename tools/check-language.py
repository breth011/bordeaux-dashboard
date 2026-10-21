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
    r'le|la|les|des|du|qui|nous|très|avec|dans|sur|sont|cette|cet|'
    r'ces|aux|leur|leurs|nos|notre|pour|plus|bien|tout|toute|toutes|ainsi|'
    r'puis|après|dès|chez|entre|alors|encore|depuis|pendant|'
    r'lors|comme|mais|donc|car|où|est|ont|été|fait|peu|'
    r'déjà|tandis|lorsque|afin|sans|sous|vers|elle|il|ils|'
    r'elles|on|se|ne|pas|plutôt'
    r')(?![a-zà-ÿ])')
FRENCH_MIN = 6

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
        n = len(FRENCH.findall(v))
        if n >= FRENCH_MIN:
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
