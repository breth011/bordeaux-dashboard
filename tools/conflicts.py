# -*- coding: utf-8 -*-
"""Two documents, one field, different answers - written down.

Imported by read-fiches.py. Writes data/field-conflicts.jsonl and
nothing else.

                       WHERE THE LOSS HAPPENS

Phase 1 reported that disagreement between sources "cannot be
quantified because the losing value was never written", and that is
true of the history. It is NOT true going forward, and this corrects
the claim: at the moment a value is dropped, both values are in hand.

Two places drop one. In read-fiches.py:

    best.setdefault(key, {}).setdefault(f, (r['got'][f], r['src']))

The first document in the sort order takes the field and every later
document's value for it vanishes - no count, no note, nothing. The
incumbent is in best[key][f] and the challenger is in r['got'][f],
right there.

    for f, (v, src) in sorted(best[key].items()):
        if f in held:          # never overwrite
            continue

And here the record's existing value beats the document's, which is
the behaviour that makes re-reads safe and is worth keeping. But the
document's value is discarded with it.

                      FIVE RELATIONS, NOT ONE

The specification is right that these must not be confused, and the
distinction is cheap to compute:

  AGREE                 same value from two documents. Not a conflict
                        - it is corroboration, and worth knowing
                        because a figure two estates' sheets agree on
                        is firmer than one.

  SAME_VALUE_DIFFERENT_FORM
                        "13.5" and "13,5"; 18 and "18". The same fact
                        written twice, which a naive comparison calls
                        a conflict and which is not one.

  DISAGREE              genuinely different values. The real case.

  INCUMBENT_HELD        the record already had a value and the
                        document offered another. Which won is known:
                        the record's.

  SUPERSEDED            a later document offered a value for a field
                        an earlier document had already filled.

Nothing is resolved here. `winner` records which value is on the
record and `why` records the rule that put it there - "first in the
sort order" or "already on the record" - so the choice is inspectable
rather than invisible.
"""
import datetime
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
OUT = ROOT + 'data/field-conflicts.jsonl'
MODEL_VERSION = 1

_rows = []
_seen = set()

NUM = re.compile(r'^-?\d+(?:[.,]\d+)?$')


def _norm(v):
    """The value as a comparable string, so form is not substance."""
    s = v if isinstance(v, str) else json.dumps(v, sort_keys=True)
    s = s.strip().strip("'\"")
    if NUM.match(s.replace(',', '.')):
        try:
            return '%g' % float(s.replace(',', '.'))
        except Exception:
            return s
    return ' '.join(s.lower().split())


def relation(a, b):
    """How two values for one field stand to each other."""
    if a == b:
        return 'AGREE'
    if _norm(a) == _norm(b):
        return 'SAME_VALUE_DIFFERENT_FORM'
    return 'DISAGREE'


def note(record, field, incumbent, inc_src, challenger, chal_src,
         why, kind='SUPERSEDED'):
    """Record that two documents offered different things.

    Called at the point of loss. Collects in memory; flush() writes.
    Deduplicated on (record, field, both sources), so a re-run does
    not multiply rows.
    """
    rel = relation(incumbent, challenger)
    key = (record, field, inc_src, chal_src, MODEL_VERSION)
    if key in _seen:
        return rel
    _seen.add(key)
    _rows.append({
        'record': record,
        'field': field,
        'relation': rel,
        'kind': kind,
        'a': {'value': incumbent, 'source': inc_src, 'on_record': True},
        'b': {'value': challenger, 'source': chal_src,
              'on_record': False},
        'winner': 'a',
        'why': why,
        'state': ('RESOLVED_BY_RULE'
                  if rel in ('AGREE', 'SAME_VALUE_DIFFERENT_FORM')
                  else 'UNRESOLVED'),
        'v': MODEL_VERSION,
        'at': datetime.date.today().isoformat(),
    })
    return rel


def flush(quiet=False):
    """Append what was collected. Nothing in the file is rewritten."""
    if not _rows:
        return 0
    new = not os.path.exists(OUT)
    have = set()
    if not new:
        with io.open(OUT, encoding='utf-8') as f:
            for line in f:
                if line.startswith('{"_"'):
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                have.add((d.get('record'), d.get('field'),
                          d.get('a', {}).get('source'),
                          d.get('b', {}).get('source'), d.get('v')))
    fresh = [r for r in _rows
             if (r['record'], r['field'], r['a']['source'],
                 r['b']['source'], r['v']) not in have]
    with io.open(OUT, 'a', encoding='utf-8', newline='') as f:
        if new:
            f.write(json.dumps({
                '_': 'Two documents, one field, different answers. '
                     'Append-only. Nothing here is resolved: `winner` '
                     'records which value is on the record and `why` '
                     'the rule that put it there. An analysis, not a '
                     'source of truth.',
                'model_version': MODEL_VERSION,
            }, ensure_ascii=False, sort_keys=True) + '\n')
        for r in fresh:
            f.write(json.dumps(r, ensure_ascii=False,
                               sort_keys=True) + '\n')
    if not quiet:
        import collections
        c = collections.Counter(r['relation'] for r in fresh)
        print('%d field conflict(s) recorded in '
              'data/field-conflicts.jsonl' % len(fresh))
        for k, n in c.most_common():
            print('   %-30s %d' % (k, n))
    n = len(fresh)
    del _rows[:]
    return n
