# -*- coding: utf-8 -*-
"""Where a field jumps around in a way the sheets would not explain.

A chateau that publishes a technical sheet publishes the SAME sheet
every year. Lynch-Bages has done it unchanged for two decades:

    Surface: 90 hectares
    Terroir (soil): Garonne Gravel
    Harvest: Hand-picked and sorted at the vineyard
    Ageing: French oak barrels for 15 months (75% new wood)
    Blending: 78 % Cabernet Sauvignon, 13 % Merlot, ...
    Production: 65% of the total crop
    "Everything comes to him who wants"
    <the season, in prose>
    Lynch-Bages 2008 displays nice aromas of cranberry, dried floral
    notes, and tobacco. The palate has nice energy and acidity...
    Appellation Pauillac  Classification Grand Cru Classe  Vintage 2008

So its records should be uniform, and they are not: a growing-season
note on 10 of 31 vintages, and a tasting note on 0 of 31 - from sheets
that carry a tasting paragraph every single year. Nothing about the
documents explains that. The reader is label-driven and Lynch-Bages
labels neither paragraph, so a note was read only in the years where
some other word happened to trip a label.

That is a general fault and this is the general test for it. Two
signals, and they need different evidence:

  RAGGED    a field on some of a sheet family's records and not
            others. Needs no document: one family of sheets does not
            state the alcohol in 1998 and withhold it in 1999.

  ABSENT    a field on NONE of a large family's records. Presence
            alone cannot tell "the sheets do not state it" from "the
            sheets state it and we never read it", so this one asks
            the documents - with cues written NOT to share the
            reader's blind spot. A probe built the same way as the
            reader always agrees with the reader, and then reports
            nothing to fix on exactly the documents that have most to
            give.

A "sheet family" is the filename with its numbers removed, which is
what a chateau's own naming gives for free:

    Chateau-Lynch-Bages-2008-EN.pdf  -> chateau-lynch-bages-####-en
    Lynch-Bages-2012-FT-GB-122.pdf   -> lynch-bages-####-ft-gb-#

The two are different families on purpose. The first is the estate's
own sheet and states no alcohol; the second is the negociant's and
does. Alcohol appearing on 10 of Lynch-Bages' 31 vintages is then not
a reading fault at all - it is the years a negociant sheet exists -
and grouping by family is what tells the two apart instead of adding
them together into a mystery.

                              THE GUARD

Finding this once is worth little if next year's scrape quietly loses
it again. So an estate's established reading can be frozen:

    python tools/audit-consistency.py --estate lynch-bages --freeze

writes, into data/sheet-expectations.json, the fields each of that
estate's sheet families is KNOWN to yield and on how many records.
Afterwards any run reports a family that now yields fewer - a
regression - and check-data.py fails on one, which is the difference
between a fact established and a fact kept.

Freezing is deliberate and per estate: it records a reading someone
has looked at. Freezing a bad reading freezes the bug, so --freeze
prints what it is about to write and wants --yes to do it.

    python tools/audit-consistency.py                 the whole archive
    python tools/audit-consistency.py --estate lafite one estate, verbose
    python tools/audit-consistency.py --verify        read the documents
    python tools/audit-consistency.py --check         guard only, exit 1
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

EXPECT = os.path.join(ROOT, 'data', 'sheet-expectations.json')

# The fields worth holding a sheet family to. Deliberately not `src`,
# `via`, `url` or the translation flags: those are bookkeeping, not
# things a sheet states.
FIELDS = ('blend', 'taste', 'note', 'pick', 'alc', 'months', 'oak',
          'yld', 'ph', 'ta', 'sug', 'temp', 'food', 'decant', 'window')

# A cue that a document states something, written to be independent of
# the reader's own patterns - the point is to disagree with the reader,
# so a cue that reuses its regexes would be worthless.
#
# Loose on purpose. Nothing here is written anywhere; it is a list of
# places to look, and the count is printed beside the field so it can
# be checked rather than believed.
CUES = {
    'alc': re.compile(r'(?i)(?:\b1[0-6][.,]\d\s*(?:%|degr|\u00b0)'
                      r'|alcohol|alcool|titre\s+alcoom)'),
    'yld': re.compile(r'(?i)(?:\bhl\s*/\s*ha|hectolitres?\s+par\s+hectare'
                      r'|rendement)'),
    'ph': re.compile(r'(?:\bpH\b)'),
    'ta': re.compile(r'(?i)(?:acidit[e\u00e9]\s+totale|total\s+acidity'
                     r'|\bg\s*/\s*l\b)'),
    'months': re.compile(r'(?i)\b\d{1,2}\s*(?:mois|months)\b'),
    'oak': re.compile(r'(?i)(?:\d{1,3}\s*%\s*(?:of\s+)?'
                      r'(?:new|neuf|neuve)|new\s+(?:oak|wood|barrels?)'
                      r'|bois\s+neuf|f[u\u00fb]ts?\s+neufs?)'),
    'blend': re.compile(r'(?i)\d{1,3}\s*%[^%]{0,40}'
                        r'(?:cabernet|merlot|petit\s+verdot|malbec'
                        r'|s[e\u00e9]millon|sauvignon)'),
    'sug': re.compile(r'(?i)(?:sucres?\s+r[e\u00e9]siduels?'
                      r'|residual\s+sugar)'),
    'temp': re.compile(r'(?i)(?:servir|serve|service)[^.]{0,40}'
                       r'\d{1,2}\s*(?:\u00b0|degr)'),
    # Prose: the vocabulary of the thing itself, not a label, because
    # the whole fault being measured is that the label is missing.
    'taste': re.compile(r'(?i)(?:tannins?|palate|bouche|robe|nose|nez'
                        r'|finish|finale|aromas?|ar[o\u00f4]mes?'
                        r'|blackcurrant|cassis|velvet|velout)'),
    'note': re.compile(r'(?i)(?:d[e\u00e9]bourrement|budbreak|flowering'
                       r'|floraison|v[e\u00e9]raison|rainfall'
                       r'|pr[e\u00e9]cipitations?|drought|s[e\u00e9]cheresse'
                       r'|heatwave|canicule|winter|hiver|spring'
                       r'|printemps)'),
}

KEY = re.compile(r"^'([a-z0-9-]+)\|(\d{4})':\{(.*)\},$")
CKEY = re.compile(r"^'([a-z0-9-]+)\|([a-z0-9-]+)\|(\d{4})':\{(.*)\},$")
FIELD_IN = re.compile(r'(?:^|\{|,)([a-z][a-z0-9]*):')


def family(fn):
    """The filename with its numbers out: one chateau's sheet, any year.

    The estate's own sheet and a negociant's are different families and
    state different things, which is the whole reason for grouping -
    added together they look like one inconsistent source.
    """
    s = os.path.splitext(str(fn or ''))[0].lower()
    s = re.sub(r'(?:19|20)\d\d', '####', s)
    s = re.sub(r'\d+', '#', s)
    return re.sub(r'[\s_]+', '-', s).strip('-') or '?'


def load_records():
    """Every record, with the fields it holds and where each came from."""
    recs = {}
    for name, pat, nkey in (('fiches.js', KEY, 2),
                            ('cuvees.js', CKEY, 3)):
        p = os.path.join(ROOT, 'data', name)
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding='utf-8'):
            m = pat.match(line.rstrip())
            if not m:
                continue
            body = m.group(nkey + 1)
            eid = m.group(1)
            key = '|'.join(m.group(i + 1) for i in range(nkey))
            src = re.search(r"src:'([^']*)'", body)
            recs[key] = {
                'estate': eid,
                'fields': set(FIELD_IN.findall(body)),
                'src': src.group(1) if src else None,
                'per': {},
            }
    # Per-field provenance, which is what makes the grouping honest: a
    # record's alcohol may have come off a different document from its
    # blend, and crediting both to the record's `src` would invent a
    # family that never stated either.
    for name, store in (('field-src.js', recs), ('cuvee-src.js', recs)):
        p = os.path.join(ROOT, 'data', name)
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding='utf-8'):
            m = re.match(r"^'([^']+)':\{(.*)\},$", line.rstrip())
            if not m or m.group(1) not in store:
                continue
            for f, v in re.findall(r"([a-z]+):'([^']*)'", m.group(2)):
                store[m.group(1)]['per'][f] = v
    return recs


def group(recs, want=None):
    """For each estate and sheet family: which records, which fields.

    A record belongs to a family if any of its fields was read from a
    document in that family. A field counts for the family only where
    that family is what provided it.
    """
    fam = collections.defaultdict(
        lambda: {'recs': set(), 'got': collections.Counter(),
                 'files': set()})
    for key, r in recs.items():
        if want and r['estate'] != want:
            continue
        here = collections.defaultdict(set)
        for f in r['fields']:
            if f not in FIELDS:
                continue
            fn = r['per'].get(f) or r['src']
            here[family(fn)].add(f)
        if not here and r['src']:
            here[family(r['src'])] = set()
        for fm, fields in here.items():
            g = fam[(r['estate'], fm)]
            g['recs'].add(key)
            g['files'].add(r['per'].get(next(iter(fields)), r['src'])
                           if fields else r['src'])
            for f in fields:
                g['got'][f] += 1
    return fam


def ragged(fam, min_recs=4, floor=0.15, ceil=0.85):
    """Fields a family yields on some of its records and not others."""
    out = []
    for (eid, fm), g in fam.items():
        n = len(g['recs'])
        if n < min_recs:
            continue
        for f in FIELDS:
            c = g['got'][f]
            if not c:
                continue
            share = c / float(n)
            if floor <= share <= ceil:
                out.append((eid, fm, f, c, n, share))
    out.sort(key=lambda r: -(r[4] - r[3]))
    return out


def absent(fam, recs, min_recs=6):
    """Fields a large family never yields AND its records do not hold.

    The second half is not a refinement, it is the difference between a
    gap and a bookkeeping detail. A family "never yielding" a field
    usually means another family provided it first - --apply never
    overwrites, so the earliest document to state a blend keeps it -
    and the record is complete. Lynch-Bages' French sheets look as if
    they yield no blend on 11 records, and all 11 have a blend, off the
    English sheet.

    What matters is a field NO document gave the record at all. That is
    something the dashboard does not know, and if the family's own
    documents carry a cue for it, something it could have known.
    """
    out = []
    for (eid, fm), g in fam.items():
        n = len(g['recs'])
        if n < min_recs:
            continue
        for f in FIELDS:
            if f not in CUES or g['got'][f]:
                continue
            held = sum(1 for k in g['recs'] if f in recs[k]['fields'])
            if held:
                continue
            out.append((eid, fm, f, n))
    out.sort(key=lambda r: -r[3])
    return out


def read_cues(eid, fm, fields, limit=8):
    """Do the family's own documents carry a cue for these fields?

    Answered off the raw text with patterns that are not the reader's,
    so the answer can disagree with it.
    """
    import sheetreader as sr
    try:
        S = json.load(io.open(os.path.join(ROOT, 'data', 'sources.json'),
                              encoding='utf-8'))
    except Exception:
        return {}
    where = {}
    for root, dirs, files in os.walk(os.path.join(ROOT, 'sources')):
        for f in files:
            where.setdefault(f, os.path.join(root, f))
    seen = collections.Counter()
    docs = 0
    for s in S.get('sheets', []):
        if s.get('estate') != eid or family(s.get('file')) != fm:
            continue
        p = where.get(s['file'])
        if not p:
            continue
        try:
            t = ' '.join(sr.flat(p).split())
        except Exception:
            continue
        docs += 1
        for f in fields:
            if f in CUES and CUES[f].search(t):
                seen[f] += 1
        if docs >= limit:
            break
    seen['_docs'] = docs
    return seen


def load_expect():
    if os.path.exists(EXPECT):
        try:
            return json.load(io.open(EXPECT, encoding='utf-8'))
        except Exception:
            return {}
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--verify', action='store_true',
                    help='read the documents for the ABSENT list')
    ap.add_argument('--freeze', action='store_true',
                    help="record this estate's reading as the expectation")
    ap.add_argument('--yes', action='store_true')
    ap.add_argument('--check', action='store_true',
                    help='guard only: report regressions and exit 1')
    ap.add_argument('--limit', type=int, default=24)
    args = ap.parse_args()

    recs = load_records()
    fam = group(recs, args.estate)

    exp = load_expect()

    # ---------------------------------------------------------- the guard
    lost = []
    for eid_fm, want in sorted(exp.items()):
        eid, fm = eid_fm.split('||', 1)
        if args.estate and eid != args.estate:
            continue
        g = fam.get((eid, fm))
        if not g:
            lost.append((eid, fm, 'the family is gone entirely', None, None))
            continue
        for f, n in sorted(want.get('fields', {}).items()):
            now = g['got'][f]
            if now < n:
                lost.append((eid, fm, f, n, now))

    if lost:
        print('REGRESSION against data/sheet-expectations.json: %d\n'
              % len(lost))
        for eid, fm, f, was, now in lost:
            if was is None:
                print('   %-26s %-40s %s' % (eid[:26], fm[:40], f))
            else:
                print('   %-26s %-34s %-7s was on %d records, now %d'
                      % (eid[:26], fm[:34], f, was, now))
        print()
    elif exp:
        print('%d frozen sheet family/ies, all still reading as recorded\n'
              % len(exp))

    if args.check:
        sys.exit(1 if lost else 0)

    # --------------------------------------------------------- the report
    if args.freeze:
        if not args.estate:
            print('--freeze needs --estate: a reading is frozen once '
                  'someone has looked at it')
            sys.exit(2)
        new = dict(exp)
        for (eid, fm), g in sorted(fam.items()):
            if not g['got']:
                continue
            new['%s||%s' % (eid, fm)] = {
                'records': len(g['recs']),
                'fields': dict((f, g['got'][f]) for f in FIELDS
                               if g['got'][f]),
            }
        print('would freeze %d family/ies for %s:\n'
              % (len(fam), args.estate))
        for (eid, fm), g in sorted(fam.items()):
            if not g['got']:
                continue
            print('   %s  (%d records)' % (fm, len(g['recs'])))
            print('      ' + ', '.join(
                '%s %d' % (f, g['got'][f]) for f in FIELDS if g['got'][f]))
        if not args.yes:
            print('\nnothing written; pass --yes to write it. Freezing a '
                  'bad reading freezes the bug,\nso read the two lists '
                  'below first.')
        else:
            io.open(EXPECT, 'w', encoding='utf-8', newline='').write(
                json.dumps(new, indent=1, sort_keys=True,
                           ensure_ascii=False) + '\n')
            print('\nwritten to data/sheet-expectations.json')

    rag = ragged(fam)
    print('=' * 76)
    print('RAGGED - a field on some of a sheet family\'s records, not others')
    print('=' * 76)
    print('One family of sheets does not state the alcohol in 1998 and')
    print('withhold it in 1999, so these want a reason.\n')
    print('%-24s %-30s %-7s %s' % ('estate', 'sheet family', 'field',
                                   'on'))
    print('-' * 76)
    for eid, fm, f, c, n, share in rag[:args.limit]:
        print('%-24s %-30s %-7s %d of %d  (%.0f%%)'
              % (eid[:24], fm[:30], f, c, n, 100 * share))
    if len(rag) > args.limit:
        print('   ... and %d more' % (len(rag) - args.limit))
    print('\n%d ragged field(s) across %d sheet family/ies'
          % (len(rag), len(set((r[0], r[1]) for r in rag))))

    ab = absent(fam, recs)
    if args.estate or args.verify:
        print()
        print('=' * 76)
        print('ABSENT - a field a large family never yields')
        print('=' * 76)
        print('Presence alone cannot tell "the sheets do not state it"')
        print('from "they state it and we never read it", so the')
        print('documents are asked, with cues that are not the')
        print("reader's own.\n")
        byfam = collections.defaultdict(list)
        for eid, fm, f, n in ab:
            byfam[(eid, fm)].append(f)
        shown = 0
        for (eid, fm), fields in sorted(byfam.items(),
                                        key=lambda kv: -len(
                                            fam[kv[0]]['recs'])):
            n = len(fam[(eid, fm)]['recs'])
            cues = read_cues(eid, fm, fields) if args.verify else {}
            hits = [(f, cues.get(f, 0)) for f in fields
                    if cues.get(f, 0)]
            if args.verify and not hits:
                continue
            print('   %s  %s  (%d records)' % (eid, fm, n))
            if args.verify:
                print('      %d document(s) read' % cues.get('_docs', 0))
                for f, c in sorted(hits, key=lambda x: -x[1]):
                    print('      %-7s no record holds it, yet %d of the '
                          'documents carry a cue for it' % (f, c))
            else:
                print('      never yields: ' + ', '.join(sorted(fields)))
            shown += 1
            if shown >= args.limit:
                print('   ... and more')
                break
        if args.verify:
            print('\nA cue is not a field. It says the words are on the '
                  'page, which is\nwhere to look - not that the reader '
                  'is wrong.')


if __name__ == '__main__':
    main()
