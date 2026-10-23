# -*- coding: utf-8 -*-
"""Every datapoint a sheet prints, and how few of them we keep.

    python tools/datapoints.py                     the whole archive
    python tools/datapoints.py --estate talbot --sheets
    python tools/datapoints.py --unmodelled        only what we drop

unread.py asks whether the reader got what it was looking for. This
asks a harder question: what is on the sheet at all.

The denominator matters. Talbot's 2018 fiche prints eighteen labelled
things - Proprietaire, Appellation, Superficie, Terroir, Densite de
plantation, Age moyen des vignes, Mode de taille, Culture, Vendanges,
Tri, Vinification, Assemblage, Degre, Rendement, Vendanges again for
the dates, Elevage carrying both the months and the share of new oak,
Mise en bouteille - and the dashboard models four of them. Scoring
that sheet against the nine fields the reader knows about says 4 of 9
and flatters us. Against what the estate actually published it is
4 of 18.

So the vocabulary is written out below rather than inferred: every
label a Bordeaux fiche uses, in both languages, each mapped to the
field it would become or to nothing at all. A label mapped to nothing
is one we have never harvested - not missed by a reader, never asked
for - and those are the ones worth seeing in bulk, because each is a
column the dashboard could have and does not.

What this cannot do is read a sheet's mind. It finds labels it knows;
a sheet that invents its own wording is undercounted, and the figure
is a floor. Where a label is found, the sentence is available with
--show, so a count can be checked rather than believed.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, ROOT + 'tools')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

# (what to call it, how it is written, the field it becomes or None)
#
# None means the dashboard has no field for it. That is the column
# this tool exists to count.
LABELS = (
    ('proprietor', r'propri[eé]taire|\bowner\b|propri[eé]t[eé]\s+de',
     None),
    ('appellation', r'\bappellation\b', None),
    ('area', r'superficie|surface\s+(?:du\s+vignoble|en\s+production)|'
             r'area\s+of\s+(?:vines|the\s+vineyard)|vineyard\s+area|'
             r'\bhectares?\b|\bha\b\s*(?:de|of)\b', None),
    ('terroir', r'\bterroirs?\b|\bsols?\b|\bsoils?\b|'
                r'nature\s+du\s+sol', None),
    ('density', r'densit[eé]\s+de\s+plantation|planting\s+density|'
                r'\d[\s.,\d]*(?:pieds|plants|vines)\s*/\s*ha', None),
    ('vine age', r'[aâ]ge\s+(?:moyen\s+)?des\s+vignes|'
                 r'age\s+of\s+(?:the\s+)?vines|vine\s+age|'
                 r'average\s+age', None),
    ('pruning', r'mode\s+de\s+taille|\btaille\b\s*:|\bpruning\b|'
                r'guyot', None),
    ('farming', r'\bculture\b\s*:|farming|viticulture|'
                r'agriculture\s+(?:biologique|raisonn)|'
                r'labour\s+traditionnel|certifi', None),
    ('harvest dates', r'vendanges?|r[eé]colte|harvests?\b|picking',
     'pick'),
    # Talbot prints Vendanges twice - once for how the fruit was
    # picked, once for when - so they are two datapoints, not one.
    ('harvest method',
     r'manuelles?\b|manual\s+(?:harvest|picking)|\bmachine\b|'
     r'[aà]\s+la\s+main|hand[- ]pick|hand[- ]harvest', None),
    ('sorting', r'\btri\b|triage|sorting|table\s+de\s+tri', None),
    ('winemaking', r'vinification|winemaking|cuves?\s+(?:bois|b[eé]ton|'
                   r'inox)|fermentation', None),
    ('blend', r'assemblage|\bblend\b|varietal\s+(?:mix|blend)|'
              r'c[eé]pages?|enc[eé]pagement', 'blend'),
    ('alcohol', r'degr[eé]|alcool|alcohol|%\s*vol', 'alc'),
    ('yield', r'rendement|\byield\b|hl\s*/\s*ha', 'yld'),
    ('ageing', r'[eé]levage|ageing|aging|barriques?|barrels?|'
               r'\bf[uû]ts?\b', 'months'),
    ('new oak', r'(?:bois|f[uû]ts?|barriques?)\s+neu|new\s+(?:oak|'
                r'barrel|wood|french\s+oak)|neuves?\s*[aà]\s*\d', 'oak'),
    ('bottling', r'mise\s+en\s+bouteille|bottl(?:ing|ed)\s*(?:date)?',
     None),
    ('production', r'production\s*:|bouteilles\s+produites|'
                   r'bottles\s+produced|\d[\s.,\d]{3,}\s*bouteilles',
     None),
    ('pH', r'\bpH\b', 'ph'),
    ('acidity', r'acidit[eé]\s+totale|total\s+acidity|\bTA\b\s*:',
     None),
    # Not a Sauternes field. A dry wine states it too - Pedesclaux's
    # Pauillac prints "Sucre residuel : < 2 g/l" - and a figure of
    # two is as much a fact as a figure of a hundred and fifty.
    ('residual sugar',
     r'sucres?\s*r[eé]siduels?|residual\s+sugars?|sugar\s+content|'
     r'teneur\s+en\s+sucres?|\bRS\s*=', None),
    ('consultant', r'oenologue|œnologue|consultant|conseil\s*:', None),
    ('tasting note', r'd[eé]gustation|tasting\s+note|commentaire', 'taste'),
    ('growing season', r'conditions?\s+climatiques?|climatolog|'
                       r'\bm[eé]t[eé]o\b|weather|growing\s+season', 'note'),
    ('serving temp', r'temp[eé]rature\s+de\s+service|serving\s+temp',
     'temp'),
    ('food pairing', r'accords?\s+mets|food\s+pairing|[aà]\s+servir\s+avec',
     'food'),
    ('drinking window', r'potentiel\s+de\s+garde|apog[eé]e|'
                        r'drinking\s+window|[aà]\s+boire\s+(?:entre|d[eè]s)',
     'window'),
    ('decanting', r'd[eé]cantation|carafage|decanting', 'decant'),
)
RX = tuple((name, re.compile(r'(?i)(?<![a-z])(?:' + pat + r')', re.I),
            field) for name, pat, field in LABELS)
READABLE = ('grand', 'combined', 'page')
NOT_A_FIELD = frozenset(('src', 'via', 'url', 'xsrc', 'ttl', 'ntl',
                         'wtl', 'dtl', 'ftl'))
ROW = re.compile(r"(?m)^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$")


def held_fields(body):
    out, depth, i = set(), 0, 0
    while i < len(body):
        c = body[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        elif c == "'":
            j = i + 1
            while j < len(body):
                if body[j] == '\\':
                    j += 2
                    continue
                if body[j] == "'":
                    break
                j += 1
            i = j + 1
            continue
        elif depth == 0 and (i == 0 or body[i - 1] == ','):
            m = re.match(r'([a-z]+)[:\{]', body[i:])
            if m:
                out.add(m.group(1))
        i += 1
    return out - NOT_A_FIELD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--sheets', action='store_true')
    ap.add_argument('--unmodelled', action='store_true',
                    help='only the labels no field exists for')
    ap.add_argument('--worst', type=int, default=30)
    ap.add_argument('--show', type=int, default=0)
    a = ap.parse_args()

    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))
    rows = [s for s in man['sheets'] if s.get('role') in READABLE
            and s.get('estate') and s.get('year')]
    if a.estate:
        rows = [s for s in rows if s.get('estate') in a.estate]

    recs = {}
    t = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
    for m in ROW.finditer(t):
        recs[(m.group(1), int(m.group(2)))] = held_fields(m.group(3))

    prints = collections.Counter()     # label -> sheets printing it
    kept = collections.Counter()       # label -> sheets where we hold it
    persheet, quote = [], {}
    print('reading %d document(s)' % len(rows))
    for n, s in enumerate(rows, 1):
        if n % 500 == 0:
            print('   ... %d' % n)
        path = sr.path_of(ROOT, s)
        if not path or not os.path.exists(path):
            continue
        try:
            text = ' '.join(sr.flat(path).split())
        except Exception:
            continue
        key = (s.get('estate'), int(s.get('year')))
        have = recs.get(key, set())
        on, got = [], []
        for name, rx, field in RX:
            m = rx.search(text)
            if not m:
                continue
            on.append(name)
            prints[name] += 1
            if field and field in have:
                got.append(name)
                kept[name] += 1
            quote.setdefault(name, (key[0], key[1], s.get('file'),
                                    text[max(0, m.start() - 50):
                                         m.end() + 50]))
        if on:
            persheet.append((len(got), len(on), key[0], key[1],
                             s.get('file'),
                             [x for x in on if x not in got]))

    used = sum(p[0] for p in persheet)
    tot = sum(p[1] for p in persheet)
    print()
    print('DATAPOINTS PRINTED, AND DATAPOINTS KEPT')
    print('   %d of %d across %d document(s) — %d%%'
          % (used, tot, len(persheet), round(100.0 * used / max(tot, 1))))
    print()
    print('   %-18s %8s %8s %8s   %s'
          % ('datapoint', 'sheets', 'kept', 'share', 'field'))
    for name, _, field in LABELS:
        if not prints.get(name):
            continue
        if a.unmodelled and field:
            continue
        print('   %-18s %8d %8d %7d%%   %s'
              % (name, prints[name], kept[name],
                 round(100.0 * kept[name] / prints[name]),
                 field or '— no field —'))
    print()
    never = [(prints[n], n) for n, _, f in LABELS
             if not f and prints.get(n)]
    never.sort(reverse=True)
    if never:
        print('   NEVER HARVESTED — printed on this many sheets, '
              'modelled by nothing:')
        for c, n in never:
            print('      %-18s %6d' % (n, c))
    if a.sheets:
        print()
        print('   EVERY SHEET: KEPT OF PRINTED, worst first')
        persheet.sort(key=lambda p: (-(p[1] - p[0]), p[0], p[2]))
        for u, n, eid, yr, fn, miss in persheet[:a.worst]:
            print('      %-22s %-5s %-30s %2d/%-3d %s'
                  % (eid[:22], yr, (fn or '')[:30], u, n,
                     ','.join(miss)[:60]))
    if a.show:
        print()
        for i, (name, (eid, yr, fn, q)) in enumerate(sorted(
                quote.items())):
            if i >= a.show:
                break
            print('   %-18s %s|%s  ...%s' % (name, eid, yr, q))


if __name__ == '__main__':
    main()
