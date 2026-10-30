"""R4 listing review: the 31 entries of the candidate rule R4 (identity_rules_candidate.FILE_SERIES_PAGES), reviewed again.

    python tools/r4-listing-review.py           write data/audit/r4-listing-review.jsonl and docs/PHASE-R4-LISTING-REVIEW.md
    python tools/r4-listing-review.py --check   recompute both and compare, byte for byte

A review, not an application: it reads the listing as R4 holds it and the evidence R4 itself reads (the held pages
under each entry and the documents they link, data/discovery), and changes nothing. The first review was the M3.12
rule audit's; this is the second, by a fixed checklist, and its dispositions are what an R4 identity may rest on
(docs/DECISION-RECORDING-POLICY.md).

THE CHECKLIST, per entry, from held evidence only - never from a file name, a URL's shape, a search result or today's
site:
  estate_controlled     the host's source has an OFFICIAL_SITE relationship with the wine's estate (the model's own)
  held_pages            pages under the entry that the discovery store holds; none, and there is no listing evidence
  page_names_the_wine   every held page's main heading (else its title) names the listed wine, and no other wine of
                        the estate
  estate_covered        every wine the model lists for the estate has its own entry on this host, so a document one
                        page shares with another wine's page can be seen at all
  shared_documents      linked files that another wine's entry also links (each establishes nothing: R4's own rule)
  locator_editions      linked files whose (host, file name) key stands for more than one held document - R4 matches a
                        link to a document by its file name on the host, a locator only; editions behind one name are
                        recorded, never used to choose a wine
DISPOSITIONS (the brief's five; an entry for a wine the model does not list is APPROVED_R4 with effect VETO_ONLY - it can
refuse a claim, never make one):
  REJECT_INSUFFICIENT_IDENTITY   no held page, not the estate's own site, or the page does not name its one wine
  REQUIRES_REVIEW                the page names its wine only in Japanese or Chinese script, which the checklist does
                                 not read; the wine's identity is itself deferred (La Clarte); the page shares documents with
                                 another wine's page (the site cross-links, so a page's links are not exclusive to its
                                 wine, and which page is the anomaly cannot be read without file names or document
                                 text), or the estate's wines are not all covered
  APPROVED_R4                    otherwise
  REJECT_SHARED_DOCUMENT and REJECT_OTHER_WINE are document-level here: a shared file, and a file another wine's
  approved entry lists, as each document row records.
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_gap_analysis as A  # noqa: E402
import identity_rules_candidate as I  # noqa: E402
import migration_lib as L  # noqa: E402

VERSION = 'r4-listing-review/1'
OUT = L.ROOT + 'data/audit/r4-listing-review.jsonl'
DOC = L.ROOT + 'docs/PHASE-R4-LISTING-REVIEW.md'
DRYRUN = L.ROOT + 'data/audit/integration-dryrun.jsonl'
DISPOSITIONS = ('APPROVED_R4', 'REJECT_SHARED_DOCUMENT', 'REJECT_OTHER_WINE', 'REJECT_INSUFFICIENT_IDENTITY',
                'REQUIRES_REVIEW')
DEFERRED_WINES = {'wn_00525': 'La Clarte de Haut-Brion: its double identity (haut-brion.com and mission-haut-brion.com '
                              'wine ids) is deferred',
                  'wn_00535': 'La Clarte de Haut-Brion Blanc: its double identity is deferred'}
NON_LATIN = re.compile('[぀-ヿ㐀-鿿]')   # kana and CJK ideographs
UNLISTED_ESTATE = {'UNLISTED:Rose de Desmirail': 'es_00254'}     # the page: "Rose de Desmirail - Vin rose de Chateau Desmirail"


def fold(s):
    """A.fold, with the typographic apostrophe as the plain one (the sites write d’Issan, the model d'Issan)."""
    return A.fold((s or '').replace('’', "'"))


def entry_id(host, pre):
    return '%s%s' % (host, pre)


def build():
    nm = {}
    for n in L.read_table('identity/names.jsonl'):
        if n['kind'] == 'CURRENT':
            nm.setdefault(n['subject'], n['name'])
    ew = collections.defaultdict(set)
    wine_estate = {}
    for r in L.read_table('state/estate-wine.jsonl'):
        if r.get('status') == 'ESTABLISHED':
            ew[r['estate']].add(r['wine'])
            wine_estate[r['wine']] = r['estate']
    official = collections.defaultdict(set)              # host -> estates whose OFFICIAL_SITE it is
    hosts = {}
    for s in L.read_table('identity/sources.jsonl'):
        hosts[s['id']] = {I.nurl(b)[0] for b in s.get('base_urls') or []}
    for r in L.read_table('state/source-estate.jsonl'):
        if r.get('kind') == 'OFFICIAL_SITE':
            for h in hosts.get(r['source'], ()):
                official[h].add(r['estate'])
    S = I.series()
    editions = collections.defaultdict(set)
    for sha, us in S.urls_of_sha.items():
        for u in us:
            editions[I.fkey(u)].add(sha)
    pages = collections.defaultdict(list)
    ex = L.ROOT + 'sources/discovery/extracted/'
    for r in L.jsonl_lines(L.ROOT + 'data/discovery/artifacts.jsonl'):
        if r.get('media') != 'html':
            continue
        h, p = I.nurl(r.get('first_url'))
        for host, pre, w in I.FILE_SERIES_PAGES:
            if h == host and p.startswith(pre) and os.path.exists(ex + r['sha256'] + '.json'):
                pages[(host, pre)].append(r)
    entries = {(h, p) for h, p, _ in I.FILE_SERIES_PAGES}
    host_wines = collections.defaultdict(set)
    for h, p, w in I.FILE_SERIES_PAGES:
        host_wines[h].add(w)
    rows = []
    for host, pre, w in I.FILE_SERIES_PAGES:
        e = wine_estate.get(w) or UNLISTED_ESTATE.get(w)
        wname = nm.get(w) or w.split(':', 1)[-1]
        others = [nm[s] for s in sorted(ew.get(e, set()) - {w}) if s in nm]
        held = []
        for r in sorted(pages[(host, pre)], key=lambda r: r['first_url']):
            x = json.load(open(ex + r['sha256'] + '.json', encoding='utf-8'))
            h1 = [h.get('text') or '' for h in x.get('headings') or [] if h.get('level') == 1 and (h.get('text') or '').strip()]
            head = h1[0] if h1 else (x.get('title') or '')
            fh = fold(head)
            names_it = fold(wname) in fh or fold(wname).replace('chateau ', '') in fh
            names_other = [o for o in others if fold(o) in fh and fold(o) not in fold(wname)]
            held.append({'url': r['first_url'], 'sha256': r['sha256'], 'heading': head[:120],
                         'heading_source': 'h1' if h1 else 'title', 'names_the_wine': names_it, 'names_other_wine': names_other,
                         'non_latin_heading': not names_it and bool(NON_LATIN.search(head))})
        docs = []
        for k in sorted(k for k, ws in S.linked.items()
                        if any(I.nurl(u)[0] == host and I.nurl(u)[1].startswith(pre) for pp in ws.values() for u in pp)):
            ws = sorted(S.linked[k])
            other = [x for x in ws if x != w]
            docs.append({'file': k[1], 'wines_linking': ws, 'held_documents': len(editions.get(k, ())),
                         'status': 'REJECT_SHARED_DOCUMENT' if other else
                                   ('EXCLUSIVE' if editions.get(k) else 'NOT_HELD'),
                         'editions': len(editions.get(k, ())) > 1})
        controlled = e in official.get(host, set())
        covered = (ew.get(e, set()) <= host_wines[host]) if e else False
        shared = [d['file'] for d in docs if d['status'] == 'REJECT_SHARED_DOCUMENT']
        names_ok = bool(held) and all(p['names_the_wine'] and not p['names_other_wine'] for p in held)
        unreadable = bool(held) and not names_ok and all(
            (p['names_the_wine'] or p['non_latin_heading']) and not p['names_other_wine'] for p in held)
        if not held:
            disp, why = 'REJECT_INSUFFICIENT_IDENTITY', 'no page under the entry is held: there is no listing evidence'
        elif not controlled:
            disp, why = 'REJECT_INSUFFICIENT_IDENTITY', 'the host is not an official site of the estate in the model'
        elif unreadable:
            disp, why = 'REQUIRES_REVIEW', ('a held page names its wine only in a script this checklist does not read '
                                            '(%s): a reader of the language must confirm it' % next(
                                                p['heading'] for p in held if p['non_latin_heading']))
        elif not names_ok:
            disp, why = 'REJECT_INSUFFICIENT_IDENTITY', 'a held page does not name exactly the listed wine'
        elif w in DEFERRED_WINES:
            disp, why = 'REQUIRES_REVIEW', DEFERRED_WINES[w]
        elif shared:
            disp, why = 'REQUIRES_REVIEW', ('the page links %d file(s) another wine\'s page also links (%s): the site '
                                            'cross-links, so this page\'s links are not exclusive to its wine' % (
                                                len(shared), ', '.join(shared[:3]) + (' ...' if len(shared) > 3 else '')))
        elif not covered:
            disp, why = 'REQUIRES_REVIEW', ('not every wine of the estate has an entry on this host (%s): a cross-link '
                                            'to an uncovered wine could not be seen' % ', '.join(
                                                nm.get(s, s) for s in sorted(ew.get(e, set()) - host_wines[host])))
        else:
            disp, why = 'APPROVED_R4', 'the estate\'s own page for one wine, naming it; no linked file shared with another ' \
                                       'wine\'s page; every wine of the estate covered'
        rows.append({'record': 'entry', 'entry': entry_id(host, pre), 'host': host, 'path_prefix': pre, 'wine': w,
                     'wine_name': wname, 'estate': e, 'estate_name': nm.get(e),
                     'checklist': {
                         'estate_controlled': controlled, 'held_pages': len(held), 'page_names_the_wine': names_ok,
                         'one_wine_per_entry': True, 'estate_covered': covered, 'shared_documents': len(shared),
                         'listing_identifies_wine': names_ok, 'filename_used_as_locator_only': True,
                         'locator_editions': sum(d['editions'] for d in docs), 'suitable_for_r4': disp == 'APPROVED_R4'},
                     'effect': 'VETO_ONLY' if w.startswith('UNLISTED:') and disp == 'APPROVED_R4' else
                               ('ATTRIBUTE_AND_VETO' if disp == 'APPROVED_R4' else 'NONE'),
                     'disposition': disp, 'reason': why, 'first_review': 'M3.12 rule audit (initial)',
                     'pages': held, 'documents': docs, 'version': VERSION})
    assert len(rows) == 31 and len(entries) == 31 and all(r['disposition'] in DISPOSITIONS for r in rows)
    return rows, effect_on_dryrun(rows)


def effect_on_dryrun(rows):
    """Which dry-run candidates rest on R4, and whether their listing entry is approved now (derived, not re-run)."""
    disp = {(r['host'], r['path_prefix']): r['disposition'] for r in rows}
    out = collections.Counter()
    lost = []
    for line in open(DRYRUN, encoding='utf-8'):
        r = json.loads(line)
        if r.get('record') != 'claim' or r['final']['disposition'] != 'ACCEPTABLE_TO_NEXT_STAGE':
            continue
        steps = [s for s in r['identity']['candidate']['trace'] if s[0] == 'R4']
        if not steps:
            out['candidates not resting on R4'] += 1
            continue
        ok = all(disp.get(next(((h, p) for h, p, _ in I.FILE_SERIES_PAGES if I.nurl(u)[0] == h and I.nurl(u)[1].startswith(p)),
                               None)) == 'APPROVED_R4' for s in steps for u in s[3])
        out['R4 candidates on approved entries' if ok else 'R4 candidates on entries not approved'] += 1
        if not ok:
            lost.append('%s %s %s %s' % (r['claim_id'], r['claim']['wine'], r['claim']['vintage'], r['claim']['field']))
    return {'record': 'dryrun_effect', 'counts': dict(sorted(out.items())), 'candidates_losing_r4': sorted(lost),
            'version': VERSION}


def report(rows, eff):
    C = collections.Counter(r['disposition'] for r in rows)
    md = ['# R4 listing review - the 31 entries, reviewed again', '',
          'Generated by `tools/r4-listing-review.py` from the listing R4 holds (`tools/identity_rules_candidate.py`, '
          '`FILE_SERIES_PAGES`) and the held evidence R4 reads. The M3.12 rule audit was the first review; this is the '
          'second, by a fixed checklist (see the tool). Nothing changed. Each entry, with its pages and linked documents, '
          'is in `data/audit/r4-listing-review.jsonl`.', '', '## Dispositions', '',
          '| disposition | entries |', '|---|---:|']
    md += ['| %s | %d |' % (d, C[d]) for d in DISPOSITIONS]
    md += ['', '## Entries', '', '| # | entry | wine | estate site | held pages | names the wine | estate covered | shared '
           'files | editions | disposition | reason |', '|---:|---|---|---|---:|---|---|---:|---:|---|---|']
    for i, r in enumerate(rows):
        c = r['checklist']
        md.append('| %d | `%s` | %s | %s | %d | %s | %s | %d | %d | %s%s | %s |' % (
            i, r['entry'], r['wine_name'], 'yes' if c['estate_controlled'] else 'no', c['held_pages'],
            'yes' if c['page_names_the_wine'] else 'no', 'yes' if c['estate_covered'] else 'no', c['shared_documents'],
            c['locator_editions'], r['disposition'], ' (veto only)' if r['effect'] == 'VETO_ONLY' else '',
            r['reason'].replace('|', '/')))
    md += ['', '## Effect on the integration dry-run (derived, not re-run)', '']
    md += ['- %s: %d' % kv for kv in eff['counts'].items()]
    if eff['candidates_losing_r4']:
        md += ['', 'Candidates whose R4 identity rests on an entry not approved:', '']
        md += ['- `%s`' % x for x in eff['candidates_losing_r4']]
    return '\n'.join(md) + '\n'


def body(rows, eff):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows + [eff]).encode('utf-8')


def main():
    rows, eff = build()
    b, md = body(rows, eff), report(rows, eff).encode('utf-8')
    if '--check' in sys.argv:
        same = (open(OUT, 'rb').read() == b, open(DOC, 'rb').read() == md)
        print('jsonl %s, report %s' % tuple('identical' if s else 'DIFFERS' for s in same))
        sys.exit(0 if all(same) else 1)
    with open(OUT, 'wb') as fh:
        fh.write(b)
    with open(DOC, 'wb') as fh:
        fh.write(md)
    print(dict(collections.Counter(r['disposition'] for r in rows)), eff['counts'])


if __name__ == '__main__':
    main()
