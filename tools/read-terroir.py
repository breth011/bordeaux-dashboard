# -*- coding: utf-8 -*-
"""The ground an estate sits on, and what it did in its cellar that year.

    python tools/read-terroir.py                 every estate
    python tools/read-terroir.py --estate dauzac
    python tools/read-terroir.py --dry-run       print, write nothing
    python tools/read-terroir.py --show 40       the passages themselves

Writes data/terroir.js (per estate) and data/cellar.js (per vintage).


WHY THIS EXISTS

tools/datapoints.py counted every label a Bordeaux fiche prints
against the fields this dataset keeps. Of 30,613 datapoints printed
across 3,815 documents it held 10,688, and the two biggest things it
had never held at all were at the top of that list: terroir, printed
on 2,506 sheets, and vinification on 1,776. Not missed by a reader -
never asked for.


WHY ONE IS PER ESTATE AND THE OTHER PER VINTAGE

Because they are different kinds of fact, and the sheets show it.

A soil does not move. Lafite prints one soil sentence on 48 of its 53
sheets, word for word from 1968 to 1979. Gruaud-Larose prints one from
1988 to 2024, and its forty dissenting sheets are the French edition
of the same fact, stop-list leakage, and thirty-three copies of an
assemblage off a flattened column. So the soil belongs to the
property and is written against it, in data/terroir.js.

A cellar moves:

    franc-mayne  2 sheets 2000-2004  Encuvage en cuves ciment
                 2 sheets 2013-2014  Encuvage par gravite en cuves inox
    dauzac       4 sheets 2000-2003  Fermentation en cuves inox
                 7 sheets 2004-2019  Utilisation d'un chai gravitaire
    rieussec    15 sheets 1989-2016  All batches were pressed ...
                 3 sheets 2021-2023  The grapes are harvested by hand

Franc-Mayne replaced concrete vats with gravity-fed stainless. That is
not a disagreement between sheets to be settled - it is two true
statements about two different decades, and an estate-level field can
hold only one of them. Taking the most recent would present a 2013
cellar as though it had always been there; taking the most agreed
would do the same for the 2000s. So the cellar is recorded against
the vintage whose sheet stated it, in data/cellar.js, keyed as
data/fiches.js is.

That also retires the two-sheet agreement rule for the cellar. It
existed because a passage seen once might be that year's specifics
rather than the house method - and per vintage, that year's specifics
are exactly what is wanted. A year with no sheet gets no cellar note,
which is the honest answer rather than the nearest one.


HOW A SOIL IS CHOSEN

Two or more of the estate's sheets must agree on a passage before any
of it is written, which is tools/read-plantings.py's rule for a
planting and is here for the same reason: a passage read off one sheet
may be that one sheet's mistake. Among the passages that clear it, the
most recent wins - an estate that rewrites its own description of its
ground is correcting it, and the newest wording is the one it stands
behind. English is preferred where English qualifies, because the
dashboard shows English prose and a French passage can only be shown
as French.

`seen` is how many sheets gave that passage and `of` how many gave any
passage at all, so a soil read off two sheets does not look like one
read off forty-one. `from` and `to` are the years of the sheets that
agree.
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

OUT_SOIL = 'data/terroir.js'
OUT_CELLAR = 'data/cellar.js'
READABLE = ('grand', 'combined', 'page')
# Two sheets, as read-plantings.py requires for a planting: one sheet's
# passage may be one sheet's mistake. The cellar needs no such rule -
# see the note above.
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


HEAD_SOIL = (
    '/* ========================================================='
    '================',
    '   Bordeaux Dashboard — the ground each estate sits on',
    '   --------------------------------------------------------'
    '-----------------',
    '   Built by tools/read-terroir.py. Do not edit by hand.',
    '',
    '   A soil does not belong to a vintage. Lafite prints one soil',
    '   sentence on 48 of its 53 sheets, word for word from 1968 to',
    '   1979; Gruaud-Larose one from 1988 to 2024. Where a soil looks',
    '   as though it moved it is two languages, not two soils.',
    '',
    '   What the estate did in its cellar is NOT here, because that',
    '   does move — Franc-Mayne replaced concrete vats with',
    '   gravity-fed stainless. It is in data/cellar.js, per vintage.',
    '',
    '     v          the passage, as the estate printed it',
    '     seen / of  sheets agreeing on it / sheets stating any',
    '     from, to   the years of the sheets that agree',
    '     src        one sheet that gave it',
    '     label      the words the sheet filed it under',
    '     lang       en or fr, by the passage and not the filename',
    '',
    '   Nothing is written that fewer than two sheets agree on, and',
    '   among those that clear it the most recent wins: an estate',
    '   that rewrites its own description is correcting it.',
    '   =========================================================='
    '================ */',
    'var BDX_TERROIR = {',
)
HEAD_CELLAR = (
    '/* ========================================================='
    '================',
    '   Bordeaux Dashboard — what each estate did in its cellar,'
    ' per vintage',
    '   --------------------------------------------------------'
    '-----------------',
    '   Built by tools/read-terroir.py. Do not edit by hand.',
    '',
    '   Keyed estate|year, as data/fiches.js is, and per vintage for',
    '   a reason. A cellar is re-equipped:',
    '',
    '     franc-mayne  2000-2004  Encuvage en cuves ciment',
    '                  2013-2014  Encuvage par gravité en cuves inox',
    '     dauzac       2000-2003  Fermentation en cuves inox',
    '                  2004-2019  Utilisation d’un chai gravitaire',
    '',
    '   Those are not two readings to be reconciled but two true',
    '   statements about two decades, so each vintage carries what',
    '   its own sheet said. A year with no sheet carries nothing.',
    '',
    '     v      the passage, as the sheet printed it',
    '     src    the sheet it came from',
    '     label  the words the sheet filed it under',
    '     lang   en or fr, by the passage and not the filename',
    '   =========================================================='
    '================ */',
    'var BDX_CELLAR = {',
)
TAIL = ('};',)


def write(path, head, body, what):
    lines = list(head) + body + list(TAIL)
    name = 'BDX_TERROIR' if 'TERROIR' in head[-1] else 'BDX_CELLAR'
    lines.append("if (typeof window !== 'undefined') "
                 'window.%s = %s;' % (name, name))
    io.open(ROOT + path, 'w', encoding='utf-8', newline='').write(
        '\n'.join(lines) + '\n')
    print('wrote %s - %d %s' % (path, len(body), what))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[])
    ap.add_argument('--dry-run', action='store_true')
    # Accepted and ignored: four of this repo's six tools are dry
    # until told otherwise and spell it --apply, and this one
    # acts unless told --dry-run. Passing the habit from the
    # majority should not kill a run on an argument.
    ap.add_argument('--apply', action='store_true',
                    help=argparse.SUPPRESS)
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

    # estate -> agreement key -> [(year, surface, file, label)]
    soils = collections.defaultdict(
        lambda: collections.defaultdict(list))
    carried = collections.Counter()
    # (estate, year) -> [(surface, file, label)]
    cellars = collections.defaultdict(list)

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
        eid, yr = s['estate'], s.get('year')
        if 'soil' in got:
            carried[eid] += 1
            soils[eid][agreement_key(got['soil'])].append(
                (yr, got['soil'], s.get('file'), how.get('soil')))
        # The cellar needs a year to be filed against. A sheet with
        # no vintage says nothing about which cellar it describes.
        if 'making' in got and yr:
            cellars[(eid, int(yr))].append(
                (got['making'], s.get('file'), how.get('making')))

    # ---- the soil, settled per estate ----------------------------
    soil_out, tally = {}, collections.Counter()
    for eid in sorted(soils):
        groups = soils[eid]
        ok = [(k, v) for k, v in groups.items() if len(v) >= a.agree]
        if not ok:
            tally['only one sheet'] += 1
            continue
        # English where English qualifies: the dashboard shows
        # English prose and a French passage can only be shown as
        # French.
        en = [(k, v) for k, v in ok if english(v[0][1])]
        run = en or ok

        def newest(kv):
            return max([y for y, _, _, _ in kv[1] if y] or [0])

        # The most recent passage two sheets agree on. An estate that
        # rewrites its description of its own ground is correcting
        # it, and the agreement rule above is what keeps a single
        # mangled recent PDF from winning on its date alone.
        pick = max(run, key=lambda kv: (newest(kv), len(kv[1])))
        best = max(pick[1], key=lambda t: len(t[1]))
        yrs = sorted(y for y, _, _, _ in pick[1] if y)
        soil_out[eid] = {
            'v': best[1], 'seen': len(pick[1]), 'of': carried[eid],
            'src': best[2], 'label': best[3],
            'from': yrs[0] if yrs else None,
            'to': yrs[-1] if yrs else None,
            'lang': 'en' if english(best[1]) else 'fr'}
        tally['soil'] += 1

    # ---- the cellar, one per vintage -----------------------------
    cellar_out = {}
    for key in sorted(cellars):
        got = cellars[key]
        en = [t for t in got if english(t[0])]
        # One vintage can have several sheets - a French and an
        # English edition of the same fiche, most often. English
        # first, then the fullest.
        best = max(en or got, key=lambda t: len(t[0]))
        cellar_out[key] = {
            'v': best[0], 'src': best[1], 'label': best[2],
            'lang': 'en' if english(best[0]) else 'fr'}

    print()
    print('THE GROUND, per estate - %d sheet(s) must agree' % a.agree)
    for k, c in sorted(tally.items()):
        print('   %-24s %4d estate(s)' % (k, c))
    langs = collections.Counter(r['lang'] for r in soil_out.values())
    print('   %s' % ', '.join('%s %d' % (k, v)
                              for k, v in sorted(langs.items())))
    print()
    print('THE CELLAR, per vintage')
    print('   %-24s %4d record(s), %d estate(s)'
          % ('stated on a sheet', len(cellar_out),
             len(set(e for e, _ in cellar_out))))
    langs = collections.Counter(r['lang'] for r in cellar_out.values())
    print('   %s' % ', '.join('%s %d' % (k, v)
                              for k, v in sorted(langs.items())))
    # Where an estate's cellar description changes, which is the whole
    # argument for this being per vintage rather than per estate.
    moved = collections.Counter()
    byestate = collections.defaultdict(set)
    for (eid, yr), r in cellar_out.items():
        byestate[eid].add(agreement_key(r['v']))
    for eid, ks in byestate.items():
        if len(ks) > 1:
            moved[eid] = len(ks)
    print('   %d estate(s) describe their cellar more than one way; '
          'the ten most varied:' % len(moved))
    for eid, c in moved.most_common(10):
        print('      %-28s %2d description(s)' % (eid[:28], c))

    if a.show:
        print()
        print('THE GROUND')
        shown = 0
        for eid in sorted(soil_out, key=lambda e: -soil_out[e]['seen']):
            if shown >= a.show:
                break
            r = soil_out[eid]
            span = ('%s-%s' % (r['from'], r['to'])
                    if r['from'] and r['to'] else '')
            print('   %-26s %2d/%-3d %-9s %-13s %s'
                  % (eid[:26], r['seen'], r['of'], span,
                     (r['label'] or '')[:13], r['v'][:120]))
            shown += 1
        print()
        print('THE CELLAR, one estate that changed it')
        for eid, _ in moved.most_common(3):
            print('   --- %s' % eid)
            for (e, yr) in sorted(k for k in cellar_out if k[0] == eid):
                print('      %s  %s'
                      % (yr, cellar_out[(e, yr)]['v'][:104]))

    if a.dry_run:
        print()
        print('--dry-run: wrote nothing')
        return

    body = []
    for eid in sorted(soil_out):
        r = soil_out[eid]
        span = ''
        if r['from'] and r['to']:
            span = ',from:%d,to:%d' % (r['from'], r['to'])
        body.append("'%s':{v:%s,seen:%d,of:%d,src:%s,label:%s,"
                    "lang:%s%s},"
                    % (eid, js(r['v']), r['seen'], r['of'],
                       js(r['src'] or ''), js(r['label'] or ''),
                       js(r['lang']), span))
    write(OUT_SOIL, HEAD_SOIL, body, 'estate(s)')

    body = []
    for (eid, yr) in sorted(cellar_out):
        r = cellar_out[(eid, yr)]
        body.append("'%s|%d':{v:%s,src:%s,label:%s,lang:%s},"
                    % (eid, yr, js(r['v']), js(r['src'] or ''),
                       js(r['label'] or ''), js(r['lang'])))
    write(OUT_CELLAR, HEAD_CELLAR, body, 'record(s)')


if __name__ == '__main__':
    main()
