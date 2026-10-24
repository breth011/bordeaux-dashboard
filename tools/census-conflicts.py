# -*- coding: utf-8 -*-
"""The conflicts, sorted into kinds. Metadata only, writes nothing.

    python tools/census-conflicts.py              all of it
    python tools/census-conflicts.py --years      the 67 year conflicts
    python tools/census-conflicts.py --estates    the 107 estate conflicts
    python tools/census-conflicts.py --dups       the 839 byte-groups
    python tools/census-conflicts.py --weak       the 44 weak records
    python tools/census-conflicts.py --field-conflicts
    python tools/census-conflicts.py --text-layer PDF/.txt pairs

The implementation audit counted these. This asks what they ARE,
because a count is not a finding: of 67 year conflicts some are
off-by-one bugs and some are a filename carrying a product code, and
the two want opposite responses.

Nothing here reads a document. It works on the manifest, the
provenance files and the filenames, so it runs in seconds and can be
re-run after every merge.
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

YEAR_IN = re.compile(r'(?<!\d)((?:1[89]|20)\d\d)(?!\d)')
# A number that is next to a word making it not a year.
CODE_NEAR = re.compile(
    r'(?i)(?:c|ref|code|no|n[o°]|id|lot|item|art)[\s_-]?0*(\d{3,5})')


def years(s):
    return set(int(y) for y in YEAR_IN.findall(str(s or '')))


def load():
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    sheets = man.get('sheets', [])
    recs, per = {}, collections.defaultdict(dict)
    for name, nkey in (('fiches.js', 2), ('cuvees.js', 3)):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        pat = re.compile(r"^'([a-z0-9-]+)\|" +
                         (r"([a-z0-9-]+)\|" if nkey == 3 else '') +
                         r"(\d{4})':\{(.*)\},$")
        for line in io.open(p, encoding='utf-8'):
            m = pat.match(line.rstrip())
            if not m:
                continue
            key = '|'.join(m.group(i + 1) for i in range(nkey))
            body = m.group(nkey + 1)
            s = re.search(r"src:'([^']*)'", body)
            recs[key] = {'estate': m.group(1), 'year': int(m.group(nkey)),
                         'src': s.group(1) if s else None, 'body': body}
    for name in ('field-src.js', 'cuvee-src.js'):
        p = ROOT + 'data/' + name
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding='utf-8'):
            m = re.match(r"^'([^']+)':\{(.*)\},$", line.rstrip())
            if not m or m.group(1) not in recs:
                continue
            for f, v in re.findall(r"([a-z]+):'([^']*)'", m.group(2)):
                per[m.group(1)][f] = v
    return sheets, recs, per


def cited_map(recs, per):
    cited = collections.defaultdict(set)
    for k, r in recs.items():
        if r['src']:
            cited[r['src']].add(k)
        for f, v in per.get(k, {}).items():
            cited[v].add(k)
    return cited


def main():
    ap = argparse.ArgumentParser()
    for f in ('years', 'estates', 'dups', 'weak', 'field_conflicts',
              'text_layer'):
        ap.add_argument('--' + f.replace('_', '-'), action='store_true')
    ap.add_argument('--limit', type=int, default=14)
    a = ap.parse_args()
    allof = not any((a.years, a.estates, a.dups, a.weak,
                     a.field_conflicts, a.text_layer))

    sheets, recs, per = load()
    cited = cited_map(recs, per)
    byfile = dict((s['file'], s) for s in sheets if s.get('file'))
    disk = set()
    for root, dirs, files in os.walk(ROOT + 'sources'):
        disk.update(files)

    # ---------------------------------------------------- year conflicts
    if allof or a.years:
        kinds = collections.Counter()
        ex = collections.defaultdict(list)
        for fn, keys in cited.items():
            s = byfile.get(fn)
            if not s:
                continue
            fy, uy = years(fn), years(s.get('url'))
            if not fy:
                continue
            for k in keys:
                ry = recs[k]['year']
                if ry in fy or (s.get('year') and
                                int(s['year']) in fy):
                    continue
                d = min(fy) - ry
                code = CODE_NEAR.search(fn)
                # Which kind of conflict is this?
                if code and int(code.group(1)) in fy:
                    kind = 'FILENAME_CODE_NOT_YEAR'
                elif abs(d) > 12:
                    kind = 'FILENAME_CODE_NOT_YEAR'
                elif uy and ry in uy:
                    kind = 'URL_YEAR_VS_DOCUMENT_YEAR'
                elif d == 1 and re.search(
                        r'(?i)primeur', fn):
                    kind = 'DOCUMENT_DATE_NOT_VINTAGE'
                elif abs(d) == 1:
                    kind = 'TRUE_VINTAGE_CONFLICT'
                else:
                    kind = 'AMBIGUOUS'
                kinds[kind] += 1
                if len(ex[kind]) < a.limit:
                    ex[kind].append((k, ry, sorted(fy), fn))
        print('=' * 72)
        print('YEAR CONFLICTS, by kind')
        print('=' * 72)
        for kind, c in kinds.most_common():
            print('\n   %-30s %d' % (kind, c))
            for k, ry, fy, fn in ex[kind][:4]:
                print('      %-26s record %d, filename %s'
                      % (k, ry, ','.join(map(str, fy))))
                print('         %s' % fn[:62])

    # -------------------------------------------------- estate conflicts
    if allof or a.estates:
        pairs = collections.Counter()
        detail = collections.defaultdict(list)
        for fn, keys in cited.items():
            s = byfile.get(fn)
            if not s or not s.get('estate'):
                continue
            for k in keys:
                if recs[k]['estate'] != s['estate']:
                    pairs[(s['estate'], recs[k]['estate'])] += 1
                    detail[(s['estate'], recs[k]['estate'])].append(
                        (fn, k, s.get('folder'), s.get('url')))
        print()
        print('=' * 72)
        print('ESTATE CONFLICTS - a record citing a document filed '
              'elsewhere')
        print('=' * 72)
        print('%d edge(s), %d pairs. Both directions of a pair means the '
              'two share\ndocuments rather than one borrowing from the '
              'other.\n' % (sum(pairs.values()), len(pairs)))
        shown = set()
        for (x, y), n in pairs.most_common(a.limit):
            back = pairs.get((y, x), 0)
            tag = 'BOTH WAYS (%d/%d)' % (n, back) if back else 'one way'
            if (y, x) in shown:
                continue
            shown.add((x, y))
            print('   %-26s -> %-26s %-18s' % (x[:26], y[:26], tag))
            fn, k, folder, url = detail[(x, y)][0]
            print('      e.g. %s' % fn[:60])
            print('           filed in %s, cited by %s'
                  % (folder or '?', k))
            if url:
                print('           %s' % url[:62])

    # ----------------------------------------------------- duplicates
    if allof or a.dups:
        byh = collections.defaultdict(list)
        for s in sheets:
            if s.get('sha1'):
                byh[s['sha1']].append(s)
        groups = [(h, v) for h, v in byh.items() if len(v) > 1]
        kinds = collections.Counter()
        ex = collections.defaultdict(list)
        for h, v in groups:
            est = set(x.get('estate') for x in v)
            win = set(x.get('wine') for x in v)
            yrs = set(x.get('year') for x in v)
            names = set(x.get('file') for x in v)
            if len(est) > 1:
                kind = 'SAME_BYTES_DIFFERENT_ESTATES'
            elif len(win) > 1:
                kind = 'SAME_BYTES_DIFFERENT_WINES'
            elif len(yrs) > 1:
                kind = 'SAME_BYTES_DIFFERENT_VINTAGES'
            elif len(names) > 1:
                kind = 'SAME_BYTES_RENAMED_COPY'
            else:
                kind = 'SAME_BYTES_SAME_IDENTITY'
            kinds[kind] += 1
            if len(ex[kind]) < a.limit:
                ex[kind].append(v)
        print()
        print('=' * 72)
        print('IDENTICAL BYTES - %d group(s)' % len(groups))
        print('=' * 72)
        for kind, c in kinds.most_common():
            print('\n   %-34s %d group(s)' % (kind, c))
            for v in ex[kind][:3]:
                for x in v[:3]:
                    print('      %-44s %-20s %s'
                          % ((x.get('file') or '')[:44],
                             (x.get('wine') or x.get('role') or '')[:20],
                             x.get('estate')))
                print('      ---')

    # ------------------------------------------------- weak records
    if allof or a.weak:
        weak = []
        for k, r in sorted(recs.items()):
            srcs = set(v for v in per.get(k, {}).values() if v)
            if r['src']:
                srcs.add(r['src'])
            if not srcs:
                weak.append((k, 'cites no document'))
            elif not (srcs & set(byfile)):
                weak.append((k, 'cites %s, not in the manifest'
                             % ', '.join(sorted(srcs)[:2])))
            elif not (srcs & disk):
                weak.append((k, 'cites %s, not on disk'
                             % ', '.join(sorted(srcs)[:2])))
        print()
        print('=' * 72)
        print('RECORDS WITH WEAK OR NO SUPPORT - %d' % len(weak))
        print('=' * 72)
        kinds = collections.Counter(w[1].split(',')[0] for w in weak)
        for kind, c in kinds.most_common():
            print('   %-40s %d' % (kind[:40], c))
        print()
        for k, why in weak[:a.limit * 2]:
            print('   %-28s %s' % (k, why[:48]))

    # -------------------------------- more than one source for a field
    if allof or a.field_conflicts:
        multi = collections.Counter()
        print()
        print('=' * 72)
        print('ONE FIELD, MORE THAN ONE DOCUMENT')
        print('=' * 72)
        print('field-src.js stores ONE filename per field, so a second')
        print('document that stated the same field left no trace. What')
        print('can still be counted is how often a record\'s fields come')
        print('from several documents at all, which is where a conflict')
        print('would have been.\n')
        for k in recs:
            srcs = set(per.get(k, {}).values())
            if len(srcs) > 1:
                multi[len(srcs)] += 1
        for n in sorted(multi):
            print('   %d record(s) draw their fields from %d documents'
                  % (multi[n], n))
        print('\n   %d record(s) draw from more than one document'
              % sum(multi.values()))
        print('   Agreement cannot be measured from the data as stored:')
        print('   the losing value was never written. This is the')
        print('   quantification the audit asked for - the answer is')
        print('   that the information needed does not exist yet.')

    # --------------------------------------------- PDF vs text layer
    if allof or a.text_layer:
        stems = collections.defaultdict(list)
        for s in sheets:
            fn = s.get('file') or ''
            stem = re.sub(r'\.(ocr\.txt|txt|pdf)$', '', fn,
                          flags=re.I).lower()
            stems[stem].append(fn)
        pairs, lone_txt, lone_pdf = 0, 0, 0
        for stem, fns in stems.items():
            has_pdf = any(f.lower().endswith('.pdf') for f in fns)
            has_txt = any(f.lower().endswith('.txt') for f in fns)
            if has_pdf and has_txt:
                pairs += 1
            elif has_txt:
                lone_txt += 1
            elif has_pdf:
                lone_pdf += 1
        txt = [s for s in sheets
               if (s.get('file') or '').lower().endswith('.txt')]
        ocr = [s for s in txt
               if (s.get('file') or '').lower().endswith('.ocr.txt')]
        print()
        print('=' * 72)
        print('TEXT LAYER vs PDF')
        print('=' * 72)
        print('   %-40s %d' % ('.txt artifacts in the manifest',
                               len(txt)))
        print('   %-40s %d' % ('of those, .ocr.txt', len(ocr)))
        print('   %-40s %d' % ('stems with both a PDF and a .txt',
                               pairs))
        print('   %-40s %d' % ('.txt with no PDF of the same stem',
                               lone_txt))
        print('   %-40s %d' % ('PDF with no .txt of the same stem',
                               lone_pdf))
        print()
        print('   A .txt with no PDF beside it is not a duplicate of')
        print('   anything - it is a crawled page, and the only')
        print('   representation there is.')

    print()
    print('Nothing was written.')


if __name__ == '__main__':
    main()
