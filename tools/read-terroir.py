# -*- coding: utf-8 -*-
"""The ground each estate sits on and what it does in its cellar.

    python tools/read-terroir.py                 every estate
    python tools/read-terroir.py --estate talbot
    python tools/read-terroir.py --dry-run       print, write nothing
    python tools/read-terroir.py --show 40       the passages themselves

Writes data/terroir.js.


WHY THIS EXISTS

tools/datapoints.py counted every label a Bordeaux fiche prints
against the fields this dataset keeps. Of 30,613 datapoints printed
across 3,815 documents it holds 10,688, and the two biggest things it
has never held at all are at the top of the list: terroir, printed on
2,506 sheets, and vinification on 1,776. Not missed by a reader -
never asked for.


WHY PER ESTATE AND NOT PER VINTAGE

Because that is what the sheets do. Taking every estate with three or
more vintages on file and comparing the passage under each label from
one year to the next:

  Lafite prints one soil sentence on 48 of its 53 sheets, word for
  word from 1968 to 1979. Gruaud-Larose prints one cellar paragraph on
  33 of 41, Lascombes on 26 of 31, Domaine de Chevalier on 20 of 43.

Where a soil appears to move it is this archive and not the estate.
Leoville-Poyferre scored 34 distinct soils over 63 sheets, and among
them are "Terraces of Mindel gravel, sandy-clay subsoil" and
"Terrasses de graves Mindel, sous-sol sablo-argileux" - one fact in
two languages. No estate's ground changed between 2005 and 2006.

So a soil is a fact about the property, and it is recorded against the
property. The sheet and the vintage that gave it are recorded beside
it, because provenance is the thing this dataset is for.

The cellar needs one more guard. Most of it is the house method and
repeats like the soil does, but some sheets describe that particular
year's vinification, and Grand-Corbin-Despagne's says so in as many
words - "variables selon les lots parcellaires et le millesime". A
passage seen on one sheet alone might be that year's specifics. So
nothing is written that fewer than two of the estate's sheets agree
on, which is the same rule tools/read-plantings.py settled on for the
same reason.


HOW A PASSAGE IS CHOSEN

Agreement, then language. Passages are grouped by the words that
survive normalising, and the group the most sheets agree on wins -
except that an English group with two or more sheets behind it beats a
larger French one, because the dashboard shows English prose and a
French passage can only be shown translated. Which happened is in the
file as `lang`.

`seen` is how many of the estate's sheets gave that passage and `of`
is how many gave any passage at all. A soil read off one sheet is
worth less than one read off nine, and the file says which it is
rather than leaving them to look alike.
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

OUT = 'data/terroir.js'
READABLE = ('grand', 'combined', 'page')
FIELDS = ('soil', 'making')
# Two sheets, as read-plantings.py requires for a planting and for the
# same reason: one sheet's passage may be one sheet's mistake, or one
# year's specifics standing in for the house method.
AGREE = 2

# Which language a passage is in, by the little words. Not by the
# estate and not by the filename - a French estate publishes English
# sheets, and this archive is full of files named _EN holding French.
EN_WORDS = re.compile(
    r'(?i)\b(the|and|with|of|on|from|which|this|its|are|is|was|'
    r'gravel|clay|sand|limestone|soil|subsoil|slopes?|vats?|'
    r'barrels?|ageing|aged|vineyard|hectares?)\b')
FR_WORDS = re.compile(
    r'(?i)\b(le|la|les|des|du|de|et|sur|avec|dans|une?|aux?|'
    r'graves?|argil\w+|sabl\w+|calcaire|sols?|sous-sol|cuves?|'
    r'barriques?|[eé]levage|vignoble|hectares?)\b')


def english(s):
    return len(EN_WORDS.findall(s)) > len(FR_WORDS.findall(s))


def agreement_key(s):
    """Two passages are the same answer if the same words survive.

    Word order and punctuation go, because the same sentence is
    reprinted with a comma moved and a capital changed often enough
    that treating those as different answers splits an estate's vote
    against itself.
    """
    return ' '.join(sorted(set(
        w for w in re.findall(r'[a-z]{4,}', sr.norm(s)))))


def js(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--show', type=int, default=0,
                    help='print this many passages in full')
    ap.add_argument('--agree', type=int, default=AGREE)
    a = ap.parse_args()

    man = json.load(io.open(ROOT + 'data/sources.json',
                            encoding='utf-8'))
    rows = [s for s in man['sheets'] if s.get('role') in READABLE
            and s.get('estate')]
    if a.estate:
        rows = [s for s in rows if s.get('estate') in a.estate]

    # estate -> field -> agreement key -> [(surface, file, year)]
    seen = collections.defaultdict(
        lambda: collections.defaultdict(
            lambda: collections.defaultdict(list)))
    carried = collections.defaultdict(collections.Counter)
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
        got, how = sr.read_estate_prose(text)
        eid = s['estate']
        for f in FIELDS:
            if f not in got:
                continue
            carried[eid][f] += 1
            seen[eid][f][agreement_key(got[f])].append(
                (got[f], s.get('file'), s.get('year'), how.get(f)))

    out, tally = {}, collections.Counter()
    for eid in sorted(seen):
        for f in FIELDS:
            groups = seen[eid][f]
            if not groups:
                continue
            ok = [(k, v) for k, v in groups.items()
                  if len(v) >= a.agree]
            if not ok:
                tally[f + ' : only one sheet'] += 1
                continue
            # English with two sheets behind it beats a larger French
            # group: the dashboard shows English prose, and a French
            # passage can only be shown translated.
            en = [(k, v) for k, v in ok if english(v[0][0])]
            pick = max(en or ok, key=lambda kv: len(kv[1]))
            # Within the winning group, the fullest surface form -
            # the same sentence survives a flattened column at
            # different lengths and the longest lost the least.
            best = max(pick[1], key=lambda t: len(t[0]))
            rec = out.setdefault(eid, {})
            rec[f] = {'v': best[0], 'seen': len(pick[1]),
                      'of': carried[eid][f], 'src': best[1],
                      'label': best[3],
                      'lang': 'en' if english(best[0]) else 'fr'}
            tally[f] += 1

    print()
    print('WHAT IS AGREED, %d sheet(s) or more' % a.agree)
    for k, c in sorted(tally.items()):
        print('   %-28s %4d estate(s)' % (k, c))
    print('   %-28s %4d estate(s)' % ('holding either', len(out)))
    langs = collections.Counter(
        r[f]['lang'] for r in out.values() for f in FIELDS if f in r)
    print('   %s' % ', '.join('%s %d' % (k, v)
                              for k, v in sorted(langs.items())))

    if a.show:
        print()
        print('THE PASSAGES')
        shown = 0
        for eid in sorted(out, key=lambda e: -max(
                out[e][f]['seen'] for f in FIELDS if f in out[e])):
            for f in FIELDS:
                if f not in out[eid] or shown >= a.show:
                    continue
                r = out[eid][f]
                print('   %-26s %-7s %2d/%-3d %-14s %s'
                      % (eid[:26], f, r['seen'], r['of'],
                         (r['label'] or '')[:14], r['v'][:150]))
                shown += 1

    if a.dry_run:
        print()
        print('--dry-run: wrote nothing')
        return

    lines = [
        '/* ====================================================='
        '====================',
        '   Bordeaux Dashboard — the ground and the cellar, per estate',
        '   ----------------------------------------------------'
        '---------------------',
        '   Built by tools/read-terroir.py. Do not edit by hand.',
        '',
        '   Neither of these belongs to a vintage. Lafite prints one',
        '   soil sentence on 48 of its 53 sheets, word for word from',
        '   1968 to 1979; Gruaud-Larose one cellar paragraph on 33 of',
        '   41. Where a soil appears to move it is two languages, not',
        '   two soils. See the tool for the measurement.',
        '',
        '     v      the passage, as the estate printed it',
        '     seen   how many of the estate’s sheets agree on it',
        '     of     how many gave any passage at all',
        '     src    one sheet that gave it',
        '     label  the words the sheet filed it under',
        '     lang   en or fr, by the passage and not the filename',
        '',
        '   Nothing is written that fewer than two sheets agree on: a',
        '   cellar paragraph seen once may be that year’s vinification',
        '   rather than the house method, and one sheet says so —',
        '   “variables selon les lots parcellaires et le millésime”.',
        '   ======================================================'
        '==================== */',
        'var BDX_TERROIR = {',
    ]
    for eid in sorted(out):
        parts = []
        for f in FIELDS:
            if f not in out[eid]:
                continue
            r = out[eid][f]
            parts.append('%s:{v:%s,seen:%d,of:%d,src:%s,label:%s,'
                         'lang:%s}'
                         % (f, js(r['v']), r['seen'], r['of'],
                            js(r['src'] or ''), js(r['label'] or ''),
                            js(r['lang'])))
        lines.append("'%s':{%s}," % (eid, ','.join(parts)))
    lines.append('};')
    lines.append('if (typeof window !== \'undefined\') '
                 'window.BDX_TERROIR = BDX_TERROIR;')
    io.open(ROOT + OUT, 'w', encoding='utf-8', newline='').write(
        '\n'.join(lines) + '\n')
    print()
    print('wrote %s - %d estate(s)' % (OUT, len(out)))


if __name__ == '__main__':
    main()
