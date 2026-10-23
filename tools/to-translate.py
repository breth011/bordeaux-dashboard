# -*- coding: utf-8 -*-
"""What still needs Dutch, and which text to translate from.

    python tools/to-translate.py --classified --limit 20
    python tools/to-translate.py --estate margaux
    python tools/to-translate.py --field note

data/fiches-nl.js says how this is to be done:

    Waar het chateau in het Frans publiceerde, is uit het Frans
    vertaald en niet uit het Engels van fiches.js - zo staat er een
    vertaling tussen de wijnboer en de lezer in plaats van twee.

So the thing to translate is not always what fiches.js holds. The
record says which: ttl and ntl mark a tasting note or a season note
whose English is itself the reader's translation of the estate's
French. Where one of those flags is set, this goes back to the
document the field came from - field-src.js names it - and prints the
French, so the Dutch is made from the grower's own words.

Where the estate published in English, that English is the original
and is printed as it stands.

It writes nothing. It prints the key, the field, which language the
source is, and the text - so that translating is reading and typing,
not hunting through a manifest.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sheetreader as sr

PROSE = ('taste', 'note', 'food', 'window', 'decant')
# The flag that says this field's English is a translation.
TRANSLATED = {'taste': 'ttl', 'note': 'ntl', 'window': 'wtl',
              'decant': 'dtl', 'food': 'ftl'}
ROW = re.compile(r"(?m)^'([a-z0-9-]+\|\d{4})':\{(.*)\},$")
# Which language a passage is in, by the little words. The flags
# say whether the reader translated it; they do not say what is
# stored. Batailley 2019's tasting note is French and carries no
# ttl, so the flag alone would call it English.
FRENCH = re.compile(
    r'(?i)\b(le|la|les|des|du|et|dans|avec|sur|une?|aux?|'
    r'nous|cette|ce|qui|sont|est|plus|tr[eè]s|ann[eé]e|'
    r'mill[eé]sime|robe|nez|bouche|vendanges?)\b')
ENGLISH = re.compile(
    r'(?i)\b(the|and|with|of|from|which|this|that|are|is|was|'
    r'were|have|has|its|vintage|wine|palate|nose|harvest)\b')


def looks_french(t):
    return len(FRENCH.findall(t)) > len(ENGLISH.findall(t))


def fields_of(body):
    """{name: value} for the top-level fields of a record line."""
    out, depth, i = {}, 0, 0
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
            m = re.match(r"([a-z]+):'((?:[^'\\]|\\.)*)'", body[i:])
            if m:
                out[m.group(1)] = m.group(2)
            else:
                m = re.match(r'([a-z]+):(\d+)', body[i:])
                if m:
                    out[m.group(1)] = m.group(2)
        i += 1
    return out


def french_of(key, field, prov, man):
    """The estate's own French for this field, if it can be found.

    field-src.js names the document each field came from. A sheet
    published in both languages is held twice, and the French one is
    its sibling: the same name with FR where the English has EN.
    """
    src = (prov.get(key) or {}).get(field)
    if not src:
        return None, None
    eid = key.split('|')[0]
    mine = [s for s in man['sheets'] if s.get('estate') == eid]
    byname = dict((s.get('file'), s) for s in mine)
    cands = []
    for pat, rep in (('EN', 'FR'), ('en', 'fr'), ('ENG', 'FRA'),
                     ('english', 'francais'), ('-uk', '-fr'),
                     ('_UK', '_FR'), ('GB', 'FR')):
        if pat in src:
            cands.append(src.replace(pat, rep))
    for c in cands:
        s = byname.get(c)
        if not s:
            continue
        p = sr.path_of(ROOT, s)
        if p and os.path.exists(p):
            return c, ' '.join(sr.flat(p).split())
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--classified', action='store_true')
    ap.add_argument('--field', action='append', default=[])
    ap.add_argument('--limit', type=int, default=25)
    ap.add_argument('--chars', type=int, default=0,
                    help='only fields at most this long')
    a = ap.parse_args()

    en = io.open(ROOT + 'data/fiches.js', encoding='utf-8').read()
    nl = io.open(ROOT + 'data/fiches-nl.js', encoding='utf-8').read()
    done = {}
    for m in ROW.finditer(nl):
        done[m.group(1)] = set(fields_of(m.group(2)))

    want = set(a.field) or set(PROSE)
    ids = None
    if a.classified:
        ch = io.open(ROOT + 'data/chateaux.js', encoding='utf-8').read()
        ids = set(re.findall(r"id:'([a-z0-9-]+)'", ch))

    prov = {}
    pf = ROOT + 'data/field-src.js'
    if os.path.exists(pf):
        for line in io.open(pf, encoding='utf-8'):
            m = re.match(r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$",
                         line.rstrip())
            if m:
                prov[m.group(1)] = dict(
                    re.findall(r"([a-z]+[a-z0-9]*):'([^']*)'",
                               m.group(2)))

    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))

    rows, tally = [], collections.Counter()
    for m in ROW.finditer(en):
        key, body = m.group(1), m.group(2)
        eid = key.split('|')[0]
        if ids is not None and eid not in ids:
            continue
        if a.estate and eid not in a.estate:
            continue
        f = fields_of(body)
        for name in PROSE:
            if name not in f or name not in want:
                continue
            if name in done.get(key, ()):
                continue
            text = f[name]
            if a.chars and len(text) > a.chars:
                continue
            tally[name] += 1
            rows.append((key, name, f.get(TRANSLATED[name]), text))

    print('%d field(s) need Dutch: %s'
          % (len(rows), ', '.join('%s %d' % (k, v)
                                  for k, v in tally.most_common())))
    print()
    shown = 0
    for key, name, flag, text in rows:
        if shown >= a.limit:
            break
        src, fr = (None, None)
        if flag:
            src, fr = french_of(key, name, prov, man)
        print('=' * 66)
        print('%s   %s' % (key, name))
        if fr:
            i = fr.find(text[:28]) if text[:28] else -1
            print('   the estate’s French, from %s:' % src[:52])
            print('   %s' % fr[max(0, i - 40):i + len(text) + 120][:900])
        else:
            lang = 'French' if looks_french(text) else 'English'
            print('   the estate’s own %s%s:'
                  % (lang,
                     ', and the reader translated it - the French'
                     ' sheet was not found' if flag else ''))
            print('   %s' % text[:900])
        shown += 1


if __name__ == '__main__':
    main()
