# -*- coding: utf-8 -*-
"""Phase 2.8: can the grand-vin check tell each estate's other wines from
its grand vin? A measurement, read-only.

    python tools/audit-grand-marks.py
    python tools/audit-grand-marks.py --write    data/phase28-grand-audit.jsonl
    python tools/audit-grand-marks.py --trace du-tertre "Les Hauts du Tertre"

Changes nothing: no reader code, no canonical data, no evidence. It calls
the reader's own functions, so it measures the implementation as it is.

                       WHAT THE GRAND-VIN CHECK USES

In grand-vin mode whose_sheet() judges another of the estate's wines in
four places, every one of them through mark_of(other, grand) WITHOUT
siblings:

  naming_spells_cuvee   the other name's letters (bare_name), when they
                        are longer than the grand vin's and contain them
  abbreviates_other_wine  a filename word that begins the other mark
  names_another_wine    the mark in the filename (says_in_name), then a
                        one-letter-initial rule, then the title's
                        first-named wine
  is_second_wine        the generic "second vin" phrase, for any second
                        wine

_mark_of() keeps, in order: the first single word of 4+ letters that is
not COMMON and not inside the grand vin's packed name; else the first
adjacent pair with no article and a non-COMMON second word; else the
name's non-COMMON words; else the whole name. COMMON words, articles,
house words and words inside the grand vin's name are what it drops.

                              THE AUDIT

For every estate and every listed wine other than the grand vin:

  identity   the wine's words, those beyond the grand vin's (own), and of
             those the ones COMMON removes - and the mark the grand-vin
             check builds
  category   A safe, B exact collision (no word beyond the grand vin's),
             D common-word loss (only COMMON words beyond it), C partial
             (a distinctive word survives, yet a name written for the
             wine passes), F runtime-dependent (written forms disagree);
             E is reported separately, between two of an estate's OTHER
             wines (the same identifying words, or the same mark)
  probe      file names written for the wine - in full, without its
             leading article, run together - put to the grand-vin
             check's name tests, as whose_sheet(names_only=True) plus the
             filename-mark test of names_another_wine
  v4         the v4 decisions on documents whose filename carries the
             wine's own words: accepted as the grand vin, accepted as
             grand and second for one vintage, refused, or none
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
import sheetreader as sr

OUT = ROOT + 'data/phase28-grand-audit.jsonl'
IGNORED = ('COMMON', 'ARTICLES', 'HOUSE_WORDS')


def collections_of():
    """id -> collection, from the data files (sr.estates() carries none)."""
    out = {}
    # chateaux.js and sauternes.js hold the 1855 lists and write no cls.
    by_file = {'chateaux.js': '1855', 'sauternes.js': 'sauternes'}
    for f in sorted(os.listdir(ROOT + 'data')):
        if not f.endswith('.js'):
            continue
        t = io.open(ROOT + 'data/' + f, encoding='utf-8').read()
        for m in re.finditer(r"\{id:'([a-z0-9-]+)'([^}]{0,200})", t):
            c = re.search(r"cls:'([a-z0-9-]+)'", m.group(2))
            if c:
                out.setdefault(m.group(1), c.group(1))
            elif f in by_file:
                out.setdefault(m.group(1), by_file[f])
    return out


def collection(eid, cls):
    if eid in cls:
        return cls[eid]
    for pre in ('bourgeois', 'artisan', 'stem', 'pomerol'):
        if eid.startswith(pre + '-'):
            return pre
    return 'unknown'


def fwords(s):
    return set(sr.packed(w) for w in re.split(r'[^A-Za-z0-9À-ÿ]+',
                                              s or '') if w)


def identity(other, grand):
    words = sr._name_words(other)
    gw = sr.wset(grand)
    own = sr.wset(other) - gw
    return {
        'tokens': words,
        'wset': sorted(sr.wset(other)),
        'grand_wset': sorted(gw),
        'own': sorted(own),
        'own_common': sorted(own & sr.COMMON),
        'own_short': sorted(w for w in own - sr.COMMON if len(w) < 4),
        'distinct': sorted(w for w in own - sr.COMMON if len(w) >= 4),
        'mark': sr.mark_of(other, grand),
        'bare': sr.bare_name(other),
        'grand_bare': sr.bare_name(grand),
    }


def forms(other):
    """File names a sheet for this wine is really given: in full, without
    its leading article, without its house word as well ("Le G de
    Chateau Guiraud" is filed G-DE-GUIRAUD-2025-EN.pdf), and run
    together."""
    name = re.sub(r'\s*\([^)]*\)', '', other).strip()
    # A whole leading article only: "La" of "Lagrave-Martillac" is not one.
    bare = re.sub(r"(?i)^(?:(?:les|le|la)\s+|l['’]\s*)", '', name)
    nohouse = re.sub(r'(?i)\b(?:ch[aâ]teau|clos|domaine)\b\s*', '', bare)
    out = []
    for n in (name, bare, nohouse):
        out.append(re.sub(r'[^A-Za-z0-9À-ÿ]+', '-', n).strip('-')
                   + '-2017.pdf')
    out.append(sr.packed(name) + '2017.pdf')
    return list(dict.fromkeys(f for f in out if f != '-2017.pdf'))


def probe(fn, e, others):
    """What the grand-vin check's name tests say of a file name."""
    grand = e['name']
    v = sr.whose_sheet(None, fn, grand, e.get('cuvees') or (),
                       e.get('second'), e.get('cat'), names_only=True)
    if v:
        return v.get('why')
    for o in [e.get('second')] + list(others):
        if not o:
            continue
        mk = sr.mark_of(o, grand)
        if mk and sr.says_in_name(fn, mk):
            return 'names_another_wine (filename): %s' % o
    return None


def explain_mark(other, grand):
    """_mark_of's steps, word by word, for one name. Mirrors the
    implementation's tests (COMMON, ARTICLES, length, inside the grand
    vin) and is checked against mark_of() itself."""
    g = sr.packed(grand)
    other = re.sub(r'\s*\([^)]*\)', '', other or '').strip()
    words = [w for w in re.split(r'[^A-Za-z0-9À-ÿ]+', other) if w]
    steps = []
    for w in words:
        p = sr.packed(w)
        why = []
        if len(p) < 4:
            why.append('shorter than 4 letters')
        if p in g:
            why.append('inside the grand vin\'s name "%s"' % g)
        if p in sr.COMMON:
            why.append('in COMMON')
        if not re.search(r'[a-z]{3}', p):
            why.append('not a word')
        steps.append(('word', w, 'kept as the mark' if not why else
                      'rejected: ' + ', '.join(why)))
        if not why:
            return steps, p
    for a, b in zip(words, words[1:]):
        pa, pb = sr.packed(a), sr.packed(b)
        if pa in sr.ARTICLES or pb in sr.ARTICLES:
            steps.append(('pair', a + ' ' + b, 'rejected: contains an '
                                                'article'))
            continue
        if pb in sr.COMMON:
            steps.append(('pair', a + ' ' + b, 'rejected: second word in '
                                                'COMMON'))
            continue
        pair = sr.packed(a + b)
        if len(pair) >= 8 and pair not in g and re.search(r'[a-z]{3}', pair):
            steps.append(('pair', a + ' ' + b, 'kept as the mark'))
            return steps, '%s %s' % (a.lower(), b.lower())
        steps.append(('pair', a + ' ' + b, 'rejected: short or inside the '
                                            'grand vin'))
    kept = [w for w in words if sr.packed(w) not in sr.COMMON]
    dropped = [w for w in words if sr.packed(w) in sr.COMMON]
    if kept and sr.packed(''.join(kept)) not in g:
        steps.append(('fallback', ' '.join(words),
                      'COMMON words dropped: %s -> "%s"'
                      % (', '.join(dropped) or 'none',
                         ' '.join(kept).lower())))
        return steps, ' '.join(kept).lower()
    if sr.packed(''.join(words)) not in g:
        steps.append(('fallback', ' '.join(words), 'whole name'))
        return steps, ' '.join(words).lower()
    steps.append(('fallback', ' '.join(words), 'no mark: every form is '
                                                'inside the grand vin'))
    return steps, None


def pattern(other, grand):
    n = sr.norm(other)
    pats = []
    if re.search(r' (les|le|la)? ?hauts? (de|du|d) ', n):
        pats.append('hauts de X')
    if re.search(r' (le|la)? ?petite? ', n):
        pats.append('petit X')
    if re.search(r' tours? (de|du|d) ', n):
        pats.append('tours de X')
    if re.search(r' croix (de|du|d) ', n):
        pats.append('croix de X')
    if re.search(r' (ii|2|iii|3) $', n):
        pats.append('numbered (II)')
    if re.search(r' (blanc|blanche|rouge|rose) ', n):
        pats.append('colour word')
    gw, ow = sr.wset(grand), sr.wset(other)
    if ow and ow <= gw:
        pats.append('inside the grand vin\'s name')
    elif gw and gw <= ow:
        pats.append('grand vin\'s name plus a modifier')
    if re.search(r'^ ?[a-z] (de|d|du) ', n):
        pats.append('one-letter name (Y, G, D, R)')
    return pats or ['X de <estate> / other']


def audit():
    E = sr.estates(ROOT)
    cls = collections_of()
    v4 = collections.defaultdict(list)
    try:
        import evidence_store as ST
        for d in ST.iter_rows([4]):
            c = d.get('ctx') or {}
            eid = c.get('estate') or c.get('target_estate')
            v4[eid].append(d)
    except Exception:
        pass
    rows, aliases = [], []
    for eid in sorted(E):
        e = E[eid]
        grand = e.get('name')
        if not grand:
            continue
        others = list(dict.fromkeys(
            [w for w in (e.get('cuvees') or ()) if w]
            + ([e['second']] if e.get('second') else [])))
        others = [o for o in others if o != grand]
        # E: two OTHER wines with the same identifying words or mark
        for i, a in enumerate(others):
            for b in others[i + 1:]:
                same_w = sr.wset(a) == sr.wset(b)
                ma, mb = sr.mark_of(a, grand), sr.mark_of(b, grand)
                if same_w or (ma and ma == mb):
                    aliases.append({'estate': eid, 'a': a, 'b': b,
                                    'why': 'same identifying words'
                                    if same_w else 'same mark %r' % ma})
        for o in others:
            idt = identity(o, grand)
            pr = dict((fn, probe(fn, e, others)) for fn in forms(o))
            passes = [fn for fn, v in pr.items() if not v]
            mark_seen = bool(idt['mark']) and sr.says(o, idt['mark'])
            # B and D are static: what the identity keeps. D is split by
            # the probe, because another name test (a colour word, a
            # distinctive pair, the spelled-out name) can still catch a
            # wine whose own words are all COMMON: D1 is not caught,
            # D2 is caught - weakened, not lost.
            if not idt['own']:
                cat = 'B'
            elif not idt['distinct'] and not idt['own_short']:
                cat = 'D1' if passes else 'D2'
            elif passes and len(passes) < len(pr):
                cat = 'F'
            elif passes:
                cat = 'C'
            else:
                cat = 'A'
            # V4: documents named for this wine
            own = set(idt['own'])
            gwords = set(idt['grand_wset'])
            docs = collections.defaultdict(list)
            for d in v4.get(eid, ()):
                fw = fwords(d['artifact'])
                hit = (own and own <= fw) or (
                    not own and set(idt['wset']) <= fw
                    and not gwords <= fw)
                if hit:
                    docs[(d['ctx'].get('folder'), d['artifact'])].append(d)
            g_acc, multi, g_ref = 0, 0, 0
            for ds in docs.values():
                ga = set(x['ctx'].get('target_vintage') for x in ds
                         if x['ctx'].get('target_role') == 'grand'
                         and x['code'] == 'ACCEPTED')
                sa = set(x['ctx'].get('target_vintage') for x in ds
                         if x['ctx'].get('target_role') == 'second'
                         and x['code'] == 'ACCEPTED')
                g_acc += sum(1 for x in ds
                             if x['ctx'].get('target_role') == 'grand'
                             and x['code'] == 'ACCEPTED')
                g_ref += sum(1 for x in ds
                             if x['ctx'].get('target_role') == 'grand'
                             and x['code'] != 'ACCEPTED')
                multi += len(ga & sa)
            implicated = sorted(
                '%s|%s|%s' % (x['ctx'].get('folder'), x['artifact'],
                              x['ctx'].get('target_vintage'))
                for ds in docs.values() for x in ds
                if x['ctx'].get('target_role') == 'grand'
                and x['code'] == 'ACCEPTED')
            all_grand = sorted(
                '%s|%s|%s' % (x['ctx'].get('folder'), x['artifact'],
                              x['ctx'].get('target_vintage'))
                for ds in docs.values() for x in ds
                if x['ctx'].get('target_role') == 'grand')
            if not docs:
                status = 'no relevant evidence'
            elif multi:
                status = 'multi-target accepted (grand + second)'
            elif g_acc:
                status = 'accepted as the grand vin'
            elif g_ref:
                status = 'refused as the grand vin'
            else:
                status = 'insufficient (no grand-vin decision)'
            rows.append({
                'estate': eid, 'collection': collection(eid, cls),
                'grand': grand, 'wine': o,
                'role': 'second' if o == e.get('second') else 'other',
                'category': cat, 'identity': idt,
                'mark_in_own_name': mark_seen,
                'probe': pr, 'probe_passes': passes,
                'patterns': pattern(o, grand),
                'v4': {'documents': len(docs),
                       'grand_accepted': g_acc, 'grand_refused': g_ref,
                       'multi_target_vintages': multi, 'status': status,
                       'grand_accepted_ids': implicated,
                       'grand_decision_ids': all_grand,
                       'examples': sorted(a for _, a in docs)[:4]},
            })
    return E, rows, aliases


def common_impact(rows):
    """Every ignored token that occurs in a real wine name, and what it
    does there."""
    out = {}
    sets = dict((k, getattr(sr, k)) for k in IGNORED)
    for r in rows:
        toks = set(sr.packed(w) for w in r['identity']['tokens'])
        for setname, s in sets.items():
            for t in toks & s:
                d = out.setdefault((t, setname), {
                    'token': t, 'set': setname, 'estates': set(),
                    'wines': set(), 'collisions': 0, 'partial': 0,
                    'only_distinguishing_token': 0, 'examples': []})
                d['estates'].add(r['estate'])
                d['wines'].add((r['estate'], r['wine']))
                if r['category'] in ('B', 'D1') and t in r['identity']['own']:
                    d['collisions'] += 1
                if r['category'] == 'D2' and t in r['identity']['own']:
                    d['weakened'] = d.get('weakened', 0) + 1
                if r['category'] in ('C', 'F') and t in r['identity']['own']:
                    d['partial'] += 1
                if r['identity']['own'] == [t]:
                    d['only_distinguishing_token'] += 1
                if len(d['examples']) < 3:
                    d['examples'].append(r['wine'])
    res = []
    for d in out.values():
        d['estates'] = len(d['estates'])
        d['wines'] = len(d['wines'])
        res.append(d)
    return sorted(res, key=lambda d: (-d['collisions'], -d['wines'],
                                      d['token']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--trace', nargs=2, metavar=('ESTATE', 'WINE'))
    a = ap.parse_args()
    if a.trace:
        E = sr.estates(ROOT)
        grand = E[a.trace[0]]['name']
        steps, mk = explain_mark(a.trace[1], grand)
        print('grand vin: %s   packed: %s' % (grand, sr.packed(grand)))
        print('wine:      %s   tokens: %s' % (a.trace[1],
                                             sr._name_words(a.trace[1])))
        for kind, what, res in steps:
            print('   %-8s %-28s %s' % (kind, what, res))
        print('mark: %r   (mark_of says %r)' % (mk, sr.mark_of(a.trace[1],
                                                               grand)))
        return
    E, rows, aliases = audit()
    est = sorted(set(r['estate'] for r in rows))
    print('%d estates in the reader\'s universe, %d with other wines, '
          '%d other wines' % (len(E), len(est), len(rows)))
    cats = collections.Counter(r['category'] for r in rows)
    print('categories: %s   E (other-vs-other): %d'
          % (dict(sorted(cats.items())), len(aliases)))
    st = collections.Counter(r['v4']['status'] for r in rows
                             if r['category'] != 'A')
    print('v4 status of the non-A wines: %s' % dict(st))
    # Each grand-vin decision once: sibling wines can claim one document.
    for label, want in (('defect categories B/C/D1/F', ('B', 'C', 'D1', 'F')),
                        ('all categories', None)):
        ids = set(i for r in rows if want is None or r['category'] in want
                  for i in r['v4']['grand_accepted_ids'])
        print('distinct v4 grand-vin ACCEPTED decisions on documents named '
              'for another wine, %s: %d on %d documents'
              % (label, len(ids), len(set(i.rsplit('|', 1)[0]
                                          for i in ids))))
    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Phase 2.8 grand-vin identity audit. Read-only '
                     'measurement of the reader at the commit it ran on; '
                     'not evidence, not canonical. '
                     'tools/audit-grand-marks.py.',
                'estates': len(E), 'estates_with_other_wines': len(est),
                'wines': len(rows), 'categories': dict(sorted(cats.items())),
                'aliases': aliases,
                'common_impact': common_impact(rows)},
                ensure_ascii=False, sort_keys=True) + '\n')
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True)
                        + '\n')
        print('written to data/phase28-grand-audit.jsonl')


if __name__ == '__main__':
    main()
