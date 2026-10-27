"""M3.10C: Château Durfort-Vivens' values from the four documents M3.10B accepted - the audited input the
migration reads (tools/mig_m7_observations.m310c_values).

    python tools/m310c-values.py           write data/audit/m3.10c-value-application.jsonl and
                                           docs/PHASE-M3.10C-VALUE-APPLICATION.md
    python tools/m310c-values.py --check   recompute both and compare, byte for byte

A CLOSED WORLD: exactly nine values, each a (vintage, field) of EXPECT, read from M3.10B's four accepted
artifacts and from nothing else. Each is read from the document's own statement - the lines under its own
heading (THE BLEND, THE AGEING, AGING OF DURFORT-VIVENS 2024, YIELD OF DURFORT-VIVENS IN 2024, ...), quoted
with their locus - and parsed into the field's existing representation:

  blend   {variety code: %}          oak    the share of new oak, %       months  text, as every months value
  alc     %                          yld    hl/ha                         pick    {"ALL": "MM-DD|MM-DD"}

What is read must equal EXPECT; any other value, any missing one, or a value the model already holds stops
the run. THE REPRESENTATION is M3.6F's and M3.2D's: each stating document one Observation with its own DOCUMENT
provenance quoting its lines; one Reconciliation, ONLY_CANDIDATE (one document) or UNANIMOUS (the 2014 English
and French sheets, agreeing); one canonical value, SOURCED. The 2014 pair is one fact - one reconciliation and
one value per field - from two accepted documents.

WITHHELD, each recorded: the reader's 2024 new-oak 30 (the document says "70% in new barrels and 30% in TAVA
amphorae"), the vineyard sections (a surface, no planting blend, no vineyard yield), the 2024 "aging potential"
(a drinking window, class B), bottle counts and a 2015 ageing statement (none in these four documents). No
evidence decision, attribution, identity or other value changes.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import m35_rubric as RB  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.10c-value-application.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.10C-VALUE-APPLICATION.md'
M310B = L.ROOT + 'data/audit/m3.10b-evidence-decisions.jsonl'
M39 = L.ROOT + 'data/audit/m3.9-evidence-review.jsonl'
ACQ = L.ROOT + 'sources/acquisition/m3.8/extracted/'
WINE = 'wn_00263'
EXPECT = {
    ('vt:wn_00263:2014', 'blend'): {'CS': 90, 'ME': 10},
    ('vt:wn_00263:2014', 'oak'): 50,
    ('vt:wn_00263:2014', 'months'): '18',
    ('vt:wn_00263:2021', 'alc'): 13.5,
    ('vt:wn_00263:2024', 'blend'): {'CS': 94.5, 'ME': 5, 'CF': 0.5},
    ('vt:wn_00263:2024', 'pick'): {'ALL': '09-23|10-08'},
    ('vt:wn_00263:2024', 'yld'): 37,
    ('vt:wn_00263:2024', 'oak'): 70,
    ('vt:wn_00263:2024', 'months'): '18',
}
UNIT = {'blend': '%', 'oak': '%', 'months': None, 'alc': '%', 'yld': 'hl/ha', 'pick': None}   # M3.2D's units
# (artifact, field) -> (page, first line, last line): the statement under its own heading
STATEMENTS = {
    ('ar_037069', 'blend'): (1, 16, 21), ('ar_037069', 'months'): (1, 36, 37), ('ar_037069', 'oak'): (1, 37, 38),
    ('ar_037068', 'blend'): (1, 16, 21), ('ar_037068', 'months'): (1, 41, 42), ('ar_037068', 'oak'): (1, 41, 43),
    ('ar_037070', 'alc'): (1, 14, 14),
    ('ar_037071', 'blend'): (2, 9, 12), ('ar_037071', 'pick'): (2, 7, 8), ('ar_037071', 'months'): (2, 17, 18),
    ('ar_037071', 'oak'): (2, 17, 18), ('ar_037071', 'yld'): (2, 19, 20),
}
VARIETY = {'CS': r'cabernet\s*(?:/\s*)?sauvignon', 'ME': r'merlot', 'CF': r'cabernet\s*(?:/\s*)?franc'}
MONTH = {m: '%02d' % i for i, m in enumerate(('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                              'september', 'october', 'november', 'december'), 1)}
NUM = r'(\d+(?:[.,]\d+)?)'


class Stop(Exception):
    pass


def number(s):
    v = float(s.replace(',', '.'))
    return int(v) if v.is_integer() else v


def parse(field, text):
    """The field's value as the statement gives it, in the field's existing representation, or None."""
    f = RB.fold(text)
    if field == 'blend':
        out = {}
        for code, rx in VARIETY.items():
            m = re.search(NUM + r'\s*%\s*(?:/\s*)?(?:\W\s*)?' + rx, f)
            if m:
                out[code] = number(m.group(1))
        return out or None
    if field == 'months':
        m = re.search(r'\b(\d{1,2})\s*(?:months|mois)\b', f)
        return str(int(m.group(1))) if m else None
    if field == 'oak':
        m = re.search(NUM + r'\s*%\s*(?:/\s*)?(?:in\s+|en\s+)?(?:new\s+(?:oak\s+)?barrels|barriques\s+neuves)', f)
        return number(m.group(1)) if m else None
    if field == 'alc':
        m = re.search(NUM + r'\s*%\s*alcohol', f)
        return number(m.group(1)) if m else None
    if field == 'yld':
        m = re.search(NUM + r'\s*hl\s*/\s*ha', f)
        return number(m.group(1)) if m else None
    if field == 'pick':
        m = re.search(r'from\s+([a-z]+)\s+(\d{1,2})\s+to\s+([a-z]+)\s+(\d{1,2})', f)
        if m and m.group(1) in MONTH and m.group(3) in MONTH:
            return {'ALL': '%s-%02d|%s-%02d' % (MONTH[m.group(1)], int(m.group(2)), MONTH[m.group(3)], int(m.group(4)))}
    return None


def lines_of(sha):
    x = json.load(open(ACQ + '%s.json' % sha, encoding='utf-8'))
    return [p.splitlines() for p in x['pages']], x


def build():
    decs = [r for r in L.jsonl_lines(M310B) if r['record'] == 'decision' and r['result'] == 'APPLIED']
    if len(decs) != 4 or {d['wine'] for d in decs} != {WINE}:
        raise Stop('M3.10B accepted %d documents, expected the four of %s' % (len(decs), WINE))
    by_art = {d['artifact']: d for d in decs}
    # a value the model holds from any other source stops the run (M3.10C's own, once migrated, do not)
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    canon = {(v['subject'], v['field']) for v in L.read_table('canonical/values.jsonl')
             if (prov.get(v['provenance']) or {}).get('actor') != 'tools/m310c-values.py'}
    held = sorted(k for k in EXPECT if k in canon)
    if held:
        raise Stop('the model already holds %s' % held)
    obs = {}
    for (aid, field), (page, a, b) in sorted(STATEMENTS.items()):
        d = by_art.get(aid)
        if not d:
            raise Stop('%s is not one of M3.10B\'s accepted artifacts' % aid)
        pages, x = lines_of(d['sha256'])
        quote = ' / '.join(l.strip() for l in pages[page - 1][a - 1:b] if l.strip())
        v = parse(field, quote)
        if v is None:
            raise Stop('%s %s: the statement at p%d:l%d-%d does not state it' % (aid, field, page, a, b))
        obs.setdefault((d['vintage_id'], field), []).append(
            {'artifact': aid, 'candidate': d['candidate'], 'quote': quote, 'locus': 'p%d:l%d-l%d' % (page, a, b),
             'value': v, 'lang': d['language'], 'evidence_decision': d['evidence_decision'],
             'evidence_version': d['evidence_version']})
    if set(obs) != set(EXPECT):
        raise Stop('read %s, expected %s' % (sorted(obs), sorted(EXPECT)))
    rows = [{'record': 'scope', 'phase': 'M3.10C', 'wine': WINE, 'artifacts': sorted(by_art),
             'expected': [{'vintage': k[0], 'field': k[1]} for k in sorted(EXPECT)],
             'representation': 'one Observation per stating document; one Reconciliation (ONLY_CANDIDATE or UNANIMOUS); '
                               'one canonical value, SOURCED'}]
    for k in sorted(EXPECT):
        os_ = sorted(obs[k], key=lambda o: o['artifact'])
        vals = [o['value'] for o in os_]
        if any(v != vals[0] for v in vals):
            raise Stop('%s %s: the documents disagree: %s' % (k[0], k[1], vals))
        if vals[0] != EXPECT[k]:
            raise Stop('%s %s: the documents state %s, not %s' % (k[0], k[1], vals[0], EXPECT[k]))
        rows.append({'record': 'value', 'vintage': k[0], 'field': k[1], 'value': EXPECT[k], 'unit': UNIT[k[1]],
                     'rule': 'UNANIMOUS' if len(os_) > 1 else 'ONLY_CANDIDATE', 'observations': os_,
                     'same_fact_in': [o['lang'] for o in os_] if len(os_) > 1 else None, 'applied': True})
    rows += withheld(by_art)
    return rows


def withheld(by_art):
    """What these documents state and this phase does not apply - audit explanations, not model facts."""
    m39 = {'m3.9:%d' % r['n']: r for r in L.jsonl_lines(M39) if r['record'] == 'review'}
    out = []
    brief = by_art['ar_037071']
    [oak] = [f for f in m39[brief['candidate']]['figures'] if f['field'] == 'oak']
    out.append({'record': 'withheld', 'vintage': brief['vintage_id'], 'field': 'oak', 'candidate': oak['value'],
                'status': 'REJECTED_READER_MISREAD', 'source': 'ar_037071',
                'why': 'the fiche reader read %s; the document states "%s" - the new-oak share is %s (applied)'
                       % (oak['value'], oak['statement'], oak['stated_value'])})
    vineyard = {'ar_037069': (1, 41, 43), 'ar_037068': (1, 44, 46), 'ar_037071': (2, 4, 5)}
    for aid, (page, a, b) in sorted(vineyard.items()):
        d = by_art[aid]
        pages, _ = lines_of(d['sha256'])
        quote = ' / '.join(l.strip() for l in pages[page - 1][a - 1:b] if l.strip())
        out.append({'record': 'withheld', 'vintage': d['vintage_id'], 'field': 'blend, yld', 'source': aid,
                    'status': 'REJECTED_VINEYARD_SECTION', 'quote': quote, 'locus': 'p%d:l%d-l%d' % (page, a, b),
                    'why': 'the vineyard section states the estate\'s surface and soil: no planting blend and no vineyard '
                           'yield, and nothing from it is the wine\'s'})
    pages, _ = lines_of(brief['sha256'])
    quote = ' / '.join(l.strip() for l in pages[0][38:40] if l.strip())
    out.append({'record': 'withheld', 'vintage': brief['vintage_id'], 'field': 'months', 'source': 'ar_037071',
                'status': 'WITHHELD_CLASS_B', 'quote': quote, 'locus': 'p1:l39-l40',
                'why': 'an "aging potential" is a drinking window (class B), not the wine\'s ageing in months'})
    out.append({'record': 'withheld', 'vintage': None, 'field': 'production', 'source': None,
                'status': 'WITHHELD_NOT_STATED',
                'why': 'none of the four documents states a bottle count; production is deferred as a model decision'})
    out.append({'record': 'withheld', 'vintage': 'vt:wn_00263:2015', 'field': 'months', 'source': None,
                'status': 'WITHHELD_NOT_IN_INPUT',
                'why': 'no 2015 document is among M3.10B\'s four; no generic ageing statement is applied to any vintage'})
    return out


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def fmt(v):
    if isinstance(v, dict) and 'ALL' in v:
        a, b = v['ALL'].split('|')
        return '%s to %s (MM-DD)' % (a, b)
    if isinstance(v, dict):
        return ' / '.join('%g%% %s' % (x, k) for k, x in sorted(v.items(), key=lambda kv: -kv[1]))
    return str(v)


def report(rows):
    vals = [r for r in rows if r['record'] == 'value']
    out = []
    w = out.append
    w('# Phase M3.10C — Durfort-Vivens value application\n')
    w('Generated by `python tools/m310c-values.py` (`data/audit/m3.10c-value-application.jsonl`); never edited by '
      'hand. **A closed world: exactly nine values**, read from the four documents M3.10B accepted for Château '
      'Durfort-Vivens (`%s`), each from its own statement. No evidence decision, attribution, identity or other value '
      'changes.\n' % WINE)
    w('## 1. The nine values\n')
    w('| Vintage | Field | Value | Unit | Rule | Documents | Statement |')
    w('|---|---|---|---|---|---|---|')
    for r in vals:
        w('| %s | %s | %s | %s | %s | %s | %s |' % (
            r['vintage'].rsplit(':', 1)[1], r['field'], fmt(r['value']), r['unit'] or '—', r['rule'],
            ', '.join('`%s`' % o['artifact'] for o in r['observations']),
            ' ‖ '.join('"%s" (%s)' % (o['quote'].replace('|', '/'), o['locus']) for o in r['observations'])))
    w('\n## 2. The 2014 English and French sheets\n')
    w('Two accepted documents, one fact per field: each sheet is an Observation with its own provenance quoting its own '
      'lines, the two agree, and one UNANIMOUS reconciliation selects one canonical value - as M3.6F did for the Cuvée '
      'Mongravey sheets and M3.2D for its recovered values. No conflict, no second canonical value.\n')
    w('## 3. The 2024 new oak\n')
    w('**70%.** "18 months, with 70% in new barrels and 30% in TAVA amphorae": the field\'s meaning is the share of new '
      'oak. The fiche reader\'s 30 stays in the M3.9 audit as its limitation; no observation of 30 exists.\n')
    w('## 4. Withheld and rejected\n')
    w('| Vintage | Field | Status | Why |')
    w('|---|---|---|---|')
    for r in rows:
        if r['record'] == 'withheld':
            w('| %s | %s | `%s` | %s |' % ((r['vintage'] or '—').rsplit(':', 1)[-1], r['field'], r['status'],
                                         r['why'].replace('|', '/')))
    w('\nThese are explanations, not model facts.\n')
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    try:
        rows = build()
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)
    b, doc = body(rows), report(rows)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.10C outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d values); %s written' % (OUT[len(L.ROOT):], sum(r['record'] == 'value' for r in rows),
                                                DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
