# -*- coding: utf-8 -*-
"""A link, per vintage, to the sheet the record was read from.

    python tools/build-fiche-links.py
    python tools/build-fiche-links.py --dry-run

Writes data/fiches-url.js.


The sourcing line under each vintage says "this estate". This makes it
a link, so a reader can open the document the figures came from. The
app's own comment on that line is the reason: sourcing is kept quiet
because it should be checkable rather than loud, and a grey line you
can click is more checkable than a grey line you cannot.

WHY IT LINKS OUTWARD, AND NOT TO A LOCAL COPY

`sources/` is not committed. GitHub Pages serves this repository, so
anything in it is published, and none of those sheets is ours to
republish. The link therefore goes to the address the sheet was
fetched from - the chateau's own site, or the negociant's - which is
also the honest thing to point at: it is their document.

This has a consequence. A record can only carry a link if the manifest
recorded a `url` for the sheet it cites, and most do not: the addresses
were known when the files were fetched and thrown away. So this tool
reports how many records it could and could not link, and the number
rises as `harvest.py` (which now always writes a url) and
`promote-urls.py` (which fills blanks that can be recovered) do their
work. Run it after either of them.

WHICH SHEET, WHERE A RECORD NAMES SEVERAL

`src` may name several. The first one with a url wins, and a .pdf is
preferred over a page, because a technical sheet is what the reader is
being promised. A src that is itself a page address - Latour publishes
no sheets at all, so its records cite the page their prose came from -
is used as the link directly.
"""
import io, json, os, re, sys, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--cuvees', action='store_true',
                    help="the estate's other wines, from "
                         'data/cuvees.js into data/cuvee-url.js')
    a = ap.parse_args()

    # Which store. The join below is the same either way; what
    # changes is the file, the key shape and where it is written.
    DATA = 'data/cuvees.js' if a.cuvees else 'data/fiches.js'
    OUTF = 'data/cuvee-url.js' if a.cuvees else 'data/fiches-url.js'
    VAR = 'BDX_CUVEE_URL' if a.cuvees else 'BDX_FICHE_URL'
    WHAT = 'wine and vintage' if a.cuvees else 'vintage'
    ROW = re.compile(
        r"^'([a-z0-9-]+\|[a-z0-9-]+\|\d{4})':\{(.*)\},$"
        if a.cuvees else
        r"^'([a-z0-9-]+\|\d{4})':\{(.*)\},$")

    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    url, titled = {}, {}
    for s in man['sheets']:
        if s.get('url'):
            url.setdefault(s['file'], s['url'])
            titled.setdefault(s['file'], s.get('wine') or s.get('estateName'))

    out, why = {}, collections.Counter()
    for line in io.open(ROOT + DATA, encoding='utf-8'):
        m = ROW.match(line.rstrip())
        if not m:
            continue
        sm = re.search(r"src:'((?:[^'\\]|\\.)*)'", m.group(2))
        if not sm:
            why['the record names no source'] += 1
            continue
        names = [x.strip() for x in re.sub(r'\\(.)', r'\1',
                                           sm.group(1)).split(',')
                 if x.strip()]
        # A sheet with a recorded address, preferring a PDF.
        pick, page = None, False
        for want_pdf in (True, False):
            for n in names:
                u = url.get(n)
                if u and (n.lower().endswith('.pdf') == want_pdf):
                    pick = u
                    break
            if pick:
                break
        if not pick:
            # A src that is already an address, which is how the records
            # of an estate publishing no sheets cite their source.
            for n in names:
                if n.startswith('http') or (
                        '/' in n and not n.lower().endswith('.pdf')):
                    pick = n if n.startswith('http') else 'https://' + n
                    page = True
                    break
        if pick:
            out[m.group(1)] = pick
            why['the record cites a page, and it is used' if page
                else 'linked to the sheet it was read from'] += 1
        else:
            why['the sheet it cites has no address recorded'] += 1

    total = sum(why.values())
    print('%d records, %d can link to their sheet (%.0f%%)'
          % (total, len(out), 100.0 * len(out) / max(total, 1)))
    for k, n in why.most_common():
        print('   %-54s %d' % (k, n))
    print('%d of %d sheets in the manifest have a url'
          % (len(url), len(man['sheets'])))

    if a.dry_run:
        for k in sorted(out)[:16]:
            print('   %-34s %s' % (k, out[k][:88]))
        return 0

    o = io.open(ROOT + OUTF, 'w', encoding='utf-8',
                newline='')
    o.write('/* ======================================================'
            '===================\n'
            '   Bordeaux Dashboard — where each %s’s sheet '
            'can be read\n' % WHAT +
            '   -------------------------------------------------------'
            '------------------\n'
            '   Built by tools/build-fiche-links.py. Do not edit by hand.\n'
            '\n'
            '   One address per record: the sheet the figures were read\n'
            '   from, at the château’s or the négociant’s own site. The\n'
            '   sheets themselves are not in this repository and are not\n'
            '   ours to republish, so the link goes to whoever published\n'
            '   it. A record is here only if the manifest recorded an\n'
            '   address for the sheet it cites.\n'
            '   ========================================================'
            '================= */\n'
            'window.%s = {\n' % VAR)
    for k in sorted(out):
        o.write("'%s':'%s',\n" % (k, out[k].replace('\\', '\\\\')
                                 .replace("'", "\\'")))
    o.write('};\n')
    o.close()
    print('written to %s' % OUTF)
    return 0


if __name__ == '__main__':
    sys.exit(main())
