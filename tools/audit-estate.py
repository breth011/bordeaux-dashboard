# -*- coding: utf-8 -*-
"""One estate, vintage by vintage: what is held, what is wrong with it.

    python tools/audit-estate.py --estate talbot
    python tools/audit-estate.py --estate talbot --wines
    python tools/audit-estate.py --estate talbot --quiet

Writes reports/estates/<estate>.txt and prints the same thing.

WHY THIS EXISTS, BESIDE THE TOOLS THAT ARE ALREADY HERE

unread.py asks what a document states that the record does not hold.
datapoints.py asks what is on the sheet at all. Both are about absence,
and both are archive-wide.

This asks the other question, about presence: of what the record does
hold, is any of it the wrong thing? Every defect this pipeline has
shipped was plausible on its face and obvious in the document - a
masthead read as a tasting note, a planting read as an assemblage, a
dry white's note under a red grand vin, a publication date read as a
vintage - and none of them is visible in a count. They are visible in
a vintage's own block, with the prose quoted and the provenance beside
it.

So this prints one block per vintage, for the grand vin and for each
of the estate's other wines, and runs a named suspicion over each
field. A suspicion is not a verdict: it says which sentence to read.

WHAT IT CHECKS

The prose, field by field:
    opens on a label      one of the twelve welded labels found so far
    all-capitals opening  a headline, not a sentence
    names another wine    the estate's own cuvee named inside the note
    another vintage       a year that is not this record's
    contact details       a fax number, an e-mail, a web address
    repeated verbatim     the same passage on another vintage, which
                          makes it the site's standing description
    wrong field           a drinking window holding a paragraph, a food
                          pairing holding vinification

The figures:
    outside the band      narrower than the reader's gate, which is
                          deliberately generous: a Bordeaux red is not
                          11% and a pH is not 2.8
    blend does not sum    to 100, within a point
    blend is the planting  exactly what plantings.js says, variety for
                          variety, which is a different claim
    picked out of season   a date outside August to November
    the same every year    a figure that does not move across a decade
                           is the wine's usual, not a vintage's

And the record itself:
    no document           a record whose cited source is not on disk
    document unread       a document for a vintage with no record
    no address            a record that cannot link to its source
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PROSE = ('taste', 'note', 'window', 'decant', 'food')
FIELD = re.compile(r"(?:\{|,)([a-z]+[a-z0-9]*)"
                   r"(:'(?:[^'\\]|\\.)*'|:\{[^}]*\}|:\[[^\]]*\]|:[\d.]+)")

# Narrower than GATES in sheetreader, which has to let through whatever
# a sheet in any appellation might state. These are what a Bordeaux
# record should look like, and a value outside one is worth a look
# rather than a refusal.
BAND = {
    'alc': (11.0, 16.5),
    'ph': (3.0, 4.2),
    'yld': (8.0, 70.0),
    'months': (4.0, 36.0),
    'oak': (0.0, 100.0),
    'temp': (12.0, 20.0),
    'ta': (2.0, 8.0),
}

# The welded labels found so far, as one question: does this field open
# on something that is not a word about the wine?
LEADS = ('LEAD_MASTHEAD', 'LEAD_SIGNATURE', 'LEAD_PRIMEURS',
         'LEAD_CLIMATE', 'LEAD_CREDIT', 'TAIL_DECANT')

CAPS = re.compile(r'^(?:[A-ZÀ-Ý][A-ZÀ-Ý\'’-]*'
                  r'(?:\s+|$)){3,}')
CONTACT = re.compile(r'(?i)\b(?:fax|t[eé]l[eé]phone|e-?mail|courriel|'
                     r'www\.|https?://|@[a-z0-9-]+\.[a-z]{2,})')
MIDLABEL = re.compile(
    r'(?i)\b(?:alcool|alcohol|rendement|yield|assemblage|blend|'
    r'[eé]levage|ageing|vendanges?|harvest|pH|acidit[eé]|'
    r'sucres?\s+r[eé]siduels?)\s*:\s*\d')
YEARS = re.compile(r'\b(19[2-9]\d|20[0-2]\d)\b')

# A sentence about the glass rather than the year. Several of
# these in a season note, with no tasting note on the record,
# means one paragraph is doing both jobs and wants splitting:
# Margaux's vintage pages write the year's story and the wine's
# tasting as one block.
TASTING_WORDS = re.compile(
    r'(?i)\b(?:on\s+the\s+(?:nose|palate)|the\s+nose\s+'
    r'(?:reveals|shows|offers)|reveals\s+a\s+[^.]{0,30}nose|'
    r'tannic\s+structure|the\s+finish|aromas?\s+of|bouquet|'
    r'velvety|silky\s+tannins?|in\s+the\s+mouth)\b')


def rows(path, parts):
    """Every record in a data file, keyed by its own key."""
    out = {}
    if not os.path.exists(ROOT + path):
        return out
    rx = re.compile(r"^'(" + r'\|'.join(parts) + r")':\{(.*)\},$")
    for line in io.open(ROOT + path, encoding='utf-8'):
        m = rx.match(line.rstrip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def fields_of(body):
    out = {}
    for m in FIELD.finditer(body):
        v = m.group(2)[1:]
        if v.startswith("'"):
            v = re.sub(r'\\(.)', r'\1', v[1:-1])
        out[m.group(1)] = v
    return out


def provenance(path, parts):
    out = {}
    if not os.path.exists(ROOT + path):
        return out
    rx = re.compile(r"^'(" + r'\|'.join(parts) + r")':\{(.*)\},$")
    for line in io.open(ROOT + path, encoding='utf-8'):
        m = rx.match(line.rstrip())
        if m:
            out[m.group(1)] = dict(
                re.findall(r"([a-z]+[a-z0-9]*):'([^']*)'", m.group(2)))
    return out


def wines_of(eid):
    """The estate's other wines, from cuvees.js, which is the authority."""
    p = ROOT + 'data/cuvees.js'
    if not os.path.exists(p):
        return []
    body = io.open(p, encoding='utf-8').read()
    body = body.split('window.BDX_CUVEE_WINES', 1)[-1].split(
        'window.BDX_CUVEES', 1)[0]
    m = re.search(r"(?m)^'" + re.escape(eid) + r"':\[(.*)\],$", body)
    if not m:
        return []
    out = []
    for w in re.finditer(r"\{slug:'((?:[^'\\]|\\.)*)',name:'"
                         r"((?:[^'\\]|\\.)*)',role:'([a-z]*)',"
                         r"colour:'([a-z]*)'\}", m.group(1)):
        out.append({'slug': w.group(1),
                    'name': w.group(2).replace("\\'", "'"),
                    'role': w.group(3), 'colour': w.group(4)})
    return out


def suspicions(key, yr, flds, seen_prose, plant):
    """Named doubts about one record. Each says which sentence to read."""
    out = []
    for f in PROSE:
        v = flds.get(f)
        if not v:
            continue
        for nm in LEADS:
            rx = getattr(sr, nm, None)
            if rx is not None and rx.search(v):
                out.append('%s opens on %s: %s' % (f, nm, v[:70]))
                break
        if CAPS.match(v) and len(CAPS.match(v).group(0)) > 12:
            out.append('%s opens on capitals: %s' % (f, v[:70]))
        if CONTACT.search(v):
            out.append('%s holds contact details: %s'
                       % (f, CONTACT.search(v).group(0)))
        if MIDLABEL.search(v):
            out.append('%s holds a labelled figure: %s'
                       % (f, MIDLABEL.search(v).group(0)))
        # Only the shape that is actually a defect: the record's own
        # year nowhere in the passage, and another year in its opening.
        # That is a publication date read as a vintage, or another
        # vintage's note. Margaux compares vintages in almost every
        # note it writes - "reminiscent of the 1986", "as in 1996 and
        # 2000" - and flagging those buries the real thing.
        if f in ('note', 'taste') and str(yr) not in v:
            lead = set(YEARS.findall(v[:60]))
            if lead:
                out.append('%s never says %s and opens on %s'
                           % (f, yr, ', '.join(sorted(lead))))
        if f in ('window', 'decant', 'food') and len(v) > 220:
            out.append('%s is a paragraph (%d chars), not a line'
                       % (f, len(v)))
        if f == 'note' and not flds.get('taste'):
            hits = TASTING_WORDS.findall(v)
            if len(hits) >= 2:
                out.append('note reads as a tasting note (%s) and '
                           'there is no taste field: one paragraph '
                           'doing both jobs'
                           % ', '.join(sorted(set(
                               h.lower() for h in hits))[:3]))
        other = seen_prose.get((f, v[:120]))
        if other and other != key:
            out.append('%s is word for word %s’s' % (f, other))
        else:
            seen_prose[(f, v[:120])] = key

    for f, (lo, hi) in BAND.items():
        v = flds.get(f)
        if v is None:
            continue
        try:
            n = float(str(v).split(',')[0].strip('[]'))
        except ValueError:
            continue
        if not (lo <= n <= hi):
            out.append('%s is %s, outside %g-%g' % (f, v, lo, hi))

    b = flds.get('blend')
    if b:
        nums = [float(x) for x in re.findall(r':([\d.]+)', b)]
        if nums and abs(sum(nums) - 100.0) > 1.0:
            out.append('blend sums to %g, not 100' % sum(nums))
        if plant and b:
            mine = dict(re.findall(r'([A-Z]+):([\d.]+)', b))
            if mine and mine == plant:
                out.append('blend is exactly the planting, '
                           'which is a different claim')

    p = flds.get('pick')
    if p:
        for d in re.findall(r"'(\d{2})-(\d{2})", p):
            if not (8 <= int(d[0]) <= 11):
                out.append('picked in month %s' % d[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate', action='append', default=[],
                    required=True)
    ap.add_argument('--wines', action='store_true',
                    help="the estate's other wines as well")
    ap.add_argument('--quiet', action='store_true',
                    help='only the vintages with something to say')
    a = ap.parse_args()

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    F = rows('data/fiches.js', [r'[a-z0-9-]+', r'\d{4}'])
    C = rows('data/cuvees.js', [r'[a-z0-9-]+', r'[a-z0-9-]+', r'\d{4}'])
    FS = provenance('data/field-src.js', [r'[a-z0-9-]+', r'\d{4}'])
    CS = provenance('data/cuvee-src.js',
                    [r'[a-z0-9-]+', r'[a-z0-9-]+', r'\d{4}'])
    URL = {}
    for p, var in (('data/fiches-url.js', 1), ('data/cuvee-url.js', 2)):
        if os.path.exists(ROOT + p):
            for line in io.open(ROOT + p, encoding='utf-8'):
                m = re.match(r"^'([^']+)':'([^']*)',$", line.rstrip())
                if m:
                    URL[m.group(1)] = m.group(2)

    PL = {}
    pp = ROOT + 'data/plantings.js'
    if os.path.exists(pp):
        t = io.open(pp, encoding='utf-8').read()
        for m in re.finditer(r"^'([a-z0-9-]+)':\{(.*)\},$", t, re.M):
            bm = re.search(r'blend:\{([^}]*)\}', m.group(2))
            # Only a real planting. Where plantings.js says
            # how:'declared' the figure came from chateaux.js and is the
            # estate's typical assemblage, not what the vineyard holds -
            # so a vintage matching it is unremarkable, and Margaux's
            # 2015 and 2021 were flagged for agreeing with their own
            # house blend.
            how = re.search(r"how:'([a-z]+)'", m.group(2))
            if bm and (not how or how.group(1) != 'declared'):
                PL[m.group(1)] = dict(
                    re.findall(r'([A-Z]+):([\d.]+)', bm.group(1)))

    on_disk = set()
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            on_disk.add(f)

    out = []

    def say(s=''):
        out.append(s)
        if not a.quiet or s.strip():
            print(s)

    for eid in a.estate:
        docs = collections.defaultdict(list)
        for s in man['sheets']:
            if s.get('estate') != eid:
                continue
            docs[s.get('year')].append(s)

        wines = wines_of(eid)
        say('=' * 72)
        say('%s' % eid)
        say('=' * 72)
        say('%d document(s) in the manifest, %d vintage(s) of them'
            % (sum(len(v) for v in docs.values()),
               len([k for k in docs if k])))
        say("the estate's other wines, from cuvees.js:")
        if not wines:
            say('   none listed - if the estate makes any, that is the '
                'first thing to fix')
        for w in wines:
            n = len([k for k in C if k.startswith('%s|%s|'
                                                  % (eid, w['slug']))])
            say('   %-34s %-7s %-6s %3d record(s)'
                % (w['name'][:34], w['role'], w['colour'], n))

        targets = [('grand', None)]
        if a.wines:
            targets += [(w['slug'], w) for w in wines]

        for slug, w in targets:
            if w:
                say('')
                say('-' * 72)
                say('%s  (%s, %s)' % (w['name'], w['role'], w['colour']))
                say('-' * 72)
            store = F if slug == 'grand' else C
            prov = FS if slug == 'grand' else CS
            pre = '%s|' % eid if slug == 'grand' else '%s|%s|' % (eid, slug)
            mine = sorted(k for k in store if k.startswith(pre)
                          and re.match(r'^\d{4}$', k.rsplit('|', 1)[-1]))
            yrs = sorted(set([int(k.rsplit('|', 1)[-1]) for k in mine]
                             + [int(y) for y in docs if y
                                and slug == 'grand']))
            seen_prose = {}
            flagged = 0
            for yr in yrs:
                key = pre + str(yr)
                body = store.get(key)
                mydocs = [s for s in docs.get(yr, [])
                          if (slug == 'grand'
                              and s.get('role') in ('grand', 'combined',
                                                    'page', 'unknown'))
                          or (w and sr.packed(s.get('wine') or '')
                              == sr.packed(w['name']))]
                notes = []
                if body is None:
                    if mydocs:
                        notes.append('NO RECORD, %d document(s) on disk: %s'
                                     % (len(mydocs),
                                        mydocs[0]['file'][:52]))
                    if not notes:
                        continue
                    flds = {}
                else:
                    flds = fields_of(body)
                    if not mydocs and slug == 'grand':
                        notes.append('no document of its own in the '
                                     'manifest for this vintage')
                    if key not in URL:
                        notes.append('no address: cannot link to its source')
                    src = flds.get('src') or ''
                    for nm in [x.strip() for x in src.split(',') if x.strip()]:
                        if nm not in on_disk and not nm.startswith('http'):
                            notes.append('cited source not on disk: %s'
                                         % nm[:52])
                    notes += suspicions(key, yr, flds, seen_prose,
                                        PL.get(eid))
                if not notes and a.quiet:
                    continue
                flagged += 1 if notes else 0
                held = ','.join(k for k in sorted(flds)
                                if k not in ('src', 'url'))
                say('')
                say('%s   %s' % (key, held or '(no record)'))
                for f in PROSE:
                    if flds.get(f):
                        say('    %-7s %s' % (f, flds[f][:150]))
                for n in notes:
                    say('    !! %s' % n)
                if body is not None and prov.get(key):
                    say('    from  %s' % ', '.join(
                        '%s=%s' % (k, v[:34])
                        for k, v in sorted(prov[key].items())))
            say('')
            say('%s: %d vintage(s) with something to look at'
                % (slug, flagged))

    d = ROOT + 'reports/estates'
    if not os.path.isdir(d):
        os.makedirs(d)
    p = os.path.join(d, '-'.join(a.estate)[:60] + '.txt')
    io.open(p, 'w', encoding='utf-8', newline='').write(
        '\n'.join(out) + '\n')
    print('\nreport in %s' % os.path.relpath(p, ROOT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
