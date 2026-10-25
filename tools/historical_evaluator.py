"""Historical model M3: the minimal evaluator. Pure, deterministic, read-only, no clock.

    evaluate(m, subject, prop, t, value=None) -> {status, value?, records, unreconciled, reasons}
    state_at(m, subject, t)                   -> {prop: evaluate(...)}
    changes(m, subject, t1, t2)               -> {changes, unresolved, not_established}

`m` is a Tables object over normalized-model rows: Tables.load() reads data/model/,
Tables(rows) takes rows built in memory (tests). `t` is {'axis': 'CALENDAR'|'VINTAGE',
'value': ...}; the axes are never converted (S3, H4).

Status (the M3 brief, amending PHASE-M0 section 6, where NOT_ESTABLISHED meant "no record"):

    ESTABLISHED      a reconciled record says it held at t
    NOT_ESTABLISHED  a reconciled record says it did not hold at t (an explicit not-made,
                     a reconciled bound that excludes t) - evidence of absence
    CONTESTED        a deciding reconciliation is CONFLICT_OPEN or DEFERRED
    UNDETERMINED     nothing decides t: no record, an unreconciled or legacy record, an
                     UNKNOWN bound, the other axis. Absence of a claim is UNDETERMINED.

A record is reconciled when every dated bound's basis (or, for a point record, its
provenance) is a Provenance whose derived_from names a Reconciliation that is SINGLE,
AGREED or RESOLVED under ONLY_CANDIDATE, UNANIMOUS or MANUAL_DECISION, every candidate of
which is an EXPLICIT claim. Legacy records (LEGACY_* provenance, no reconciliation) are
reported as unreconciled and decide nothing (S21, H11).

Snapshots and change lists are computed here and returned; nothing is written (S25).
"""
import json
import os

import migration_lib as L

HOLDS, DOES_NOT_HOLD, UNDET = 'HOLDS', 'DOES_NOT_HOLD', 'UNDETERMINED'
ESTABLISHED, NOT_ESTABLISHED, CONTESTED, UNDETERMINED = 'ESTABLISHED', 'NOT_ESTABLISHED', 'CONTESTED', 'UNDETERMINED'
DECIDING_RULES = ('ONLY_CANDIDATE', 'UNANIMOUS', 'MANUAL_DECISION')     # before D5 (S16)
DECIDED_STATUS = ('SINGLE', 'AGREED', 'RESOLVED')
OPEN_STATUS = ('CONFLICT_OPEN', 'DEFERRED')
PROPS = ('name', 'produced', 'owner', 'rank_absence')
TABLES = ('cross/provenance.jsonl', 'reconciliation/reconciliations.jsonl', 'observation/observations.jsonl',
          'identity/names.jsonl', 'identity/transitions.jsonl', 'state/vintage-statements.jsonl',
          'state/ownership.jsonl', 'state/rank-absences.jsonl')


class Tables:
    """Read-only indexes over model rows, keyed by table path."""

    def __init__(self, rows):
        get = lambda rel: list(rows.get(rel, []))
        self.prov = {r['id']: r for r in get('cross/provenance.jsonl')}
        self.rec = {r['id']: r for r in get('reconciliation/reconciliations.jsonl')}
        self.obs = {r['id']: r for r in get('observation/observations.jsonl')}
        self.names = get('identity/names.jsonl')
        self.transitions = get('identity/transitions.jsonl')
        self.statements = get('state/vintage-statements.jsonl')
        self.ownership = get('state/ownership.jsonl')
        self.absences = get('state/rank-absences.jsonl')

    @classmethod
    def load(cls):
        return cls({rel: L.read_table(rel) for rel in TABLES if os.path.exists(L.MODEL + rel)})


# -- time ------------------------------------------------------------------------------------------

def _key(value, axis):
    """A comparable tuple and its precision rank (year, month, day; a decade is its first year)."""
    v = str(value)
    if axis == 'VINTAGE':
        return (int(v),), 1
    if v.endswith('s'):                                   # YYY0s
        return (int(v[:4]),), 0
    parts = tuple(int(p) for p in v.split('-'))
    return parts, len(parts)


def _cmp(a, b, axis):
    """-1, 0, 1 at the coarser precision, or None when equal there but finer in one (undecided)."""
    ka, pa = _key(a, axis)
    kb, pb = _key(b, axis)
    n = min(len(ka), len(kb))
    if ka[:n] != kb[:n]:
        return -1 if ka[:n] < kb[:n] else 1
    return 0 if (pa == pb and pa > 0) or axis == 'VINTAGE' else None


def _side(bound, t, start):
    """True (consistent with holding at t), False (excludes t), None (undecided)."""
    k = bound.get('kind')
    if k in ('NOT_APPLICABLE',):
        return True
    if k == 'OPEN':
        return True if not start else None
    if k in ('UNKNOWN', 'APPROXIMATE') or 'value' not in bound:
        return None
    if bound.get('axis') != t['axis']:
        return None                                       # never converted
    c = _cmp(t['value'], bound['value'], t['axis'])       # t against the bound
    if c is None:
        return None
    if start:
        if k == 'EXACT':
            return c >= 0
        if k == 'NO_LATER_THAN':                          # began by the bound
            return True if c >= 0 else None
        if k == 'NO_EARLIER_THAN':                        # began no earlier than the bound
            return False if c < 0 else None
    else:
        if k == 'EXACT':
            return c <= 0
        if k == 'NO_LATER_THAN':                          # ended by the bound
            return False if c > 0 else None
        if k == 'NO_EARLIER_THAN':                        # ended no earlier than the bound
            return True if c <= 0 else None
    return None


def holds(validity, t):
    """HOLDS, DOES_NOT_HOLD or UNDETERMINED for an interval record at t."""
    a = _side(validity.get('valid_from', {'kind': 'UNKNOWN'}), t, True)
    b = _side(validity.get('valid_to', {'kind': 'UNKNOWN'}), t, False)
    if a is False or b is False:
        return DOES_NOT_HOLD
    return HOLDS if a and b else UNDET


# -- support ---------------------------------------------------------------------------------------

def _reconciliation_state(m, prov_id):
    """('DECIDED' | 'CONTESTED' | 'UNRECONCILED', [reconciliation ids])."""
    p = m.prov.get(prov_id) or {}
    recs = [m.rec[r] for r in p.get('derived_from') or [] if r in m.rec]
    if not recs:
        return 'UNRECONCILED', []
    ids = sorted(r['id'] for r in recs)
    if any(r['status'] in OPEN_STATUS for r in recs):
        return 'CONTESTED', ids
    for r in recs:
        explicit = all((m.obs.get(c) or {}).get('statement_mode') == 'EXPLICIT' for c in r['candidates'])
        if not (r['status'] in DECIDED_STATUS and r['rule'] in DECIDING_RULES and explicit):
            return 'UNRECONCILED', ids
    return 'DECIDED', ids


def _support(m, row):
    """How a record is backed: its dated bounds' bases, or for a point record its provenance."""
    bases = []
    for b in (row.get('validity') or {}).values():
        if isinstance(b, dict) and 'value' in b:
            bases.append(b.get('basis'))
    if not row.get('validity'):
        bases.append(row.get('provenance'))
    states = [_reconciliation_state(m, x) for x in bases]
    if not states:
        return 'UNRECONCILED', []
    ids = sorted({i for _, r in states for i in r})
    if any(s == 'CONTESTED' for s, _ in states):
        return 'CONTESTED', ids
    if all(s == 'DECIDED' for s, _ in states):
        return 'DECIDED', ids
    return 'UNRECONCILED', ids


def _records(m, subject, prop, t):
    """[(value, positive, hold, row)] for one property of one subject at t."""
    out = []
    if prop == 'name':
        for r in m.names:
            if r['subject'] == subject:
                out.append((r['name'], True, holds(r['validity'], t), r))
    elif prop == 'owner':
        for r in m.ownership:
            if r['estate'] == subject:
                out.append((r['party'], True, holds(r['validity'], t), r))
    elif prop == 'rank_absence':
        for r in m.absences:
            if r['estate'] == subject:
                out.append((r['tier'], True, holds(r['validity'], t), r))
    elif prop == 'produced':
        if t['axis'] == 'VINTAGE':                        # a vintage statement is about its vintage only (S26)
            vt = 'vt:%s:%s' % (subject, t['value'])
            for r in m.statements:
                if r['vintage'] == vt:
                    out.append((True, r['kind'] == 'PRODUCED', HOLDS, r))
    return out


def evaluate(m, subject, prop, t, value=None):
    if prop not in PROPS:
        raise ValueError('unknown property %r' % prop)
    decided, contested, unreconciled, reasons = [], [], [], []
    for v, positive, h, row in _records(m, subject, prop, t):
        if value is not None and v != value:
            continue
        state, recs = _support(m, row)
        if state == 'UNRECONCILED':
            unreconciled.append(row['id'])
        elif state == 'CONTESTED' and h != DOES_NOT_HOLD:
            contested.append((row['id'], recs))
        elif state == 'DECIDED':
            decided.append((v, positive, h, row['id'], recs))
    out = {'subject': subject, 'property': prop, 't': t, 'unreconciled': sorted(unreconciled)}
    if value is not None:
        out['value'] = value
    yes = sorted({(str(v), rid) for v, pos, h, rid, _ in decided if h == HOLDS and pos})
    no = sorted({(str(v), rid) for v, pos, h, rid, _ in decided
                 if (h == HOLDS and not pos) or (h == DOES_NOT_HOLD and value is not None)})
    if contested or (yes and no and {v for v, _ in yes} & {v for v, _ in no}):
        out['status'] = CONTESTED
        out['records'] = sorted([r for r, _ in contested] + [r for _, r in yes + no])
        reasons.append('a deciding reconciliation is open, or reconciled records disagree')
    elif yes:
        out['status'] = ESTABLISHED
        out['records'] = [r for _, r in yes]
        if value is None:
            out['values'] = sorted({v for v, _ in yes})
    elif no:
        out['status'] = NOT_ESTABLISHED
        out['records'] = [r for _, r in no]
    else:
        out['status'] = UNDETERMINED
        out['records'] = []
        reasons.append('no reconciled record decides t' if not unreconciled
                       else 'only unreconciled records (legacy or unsourced): they decide nothing')
    out['reasons'] = reasons
    return out


def state_at(m, subject, t):
    """What is established about a subject at t: every property, each with its status."""
    return {p: evaluate(m, subject, p, t) for p in PROPS}


def _within(window, t1, t2):
    """Whether a reconciled occurrence window lies inside (t1, t2] on t1's axis."""
    e, l = window.get('earliest') or {}, window.get('latest') or {}
    if any(b.get('axis') != t1['axis'] or b.get('kind') not in ('EXACT',) for b in (e, l)):
        return False
    c1, c2 = _cmp(e['value'], t1['value'], t1['axis']), _cmp(l['value'], t2['value'], t1['axis'])
    return c1 is not None and c2 is not None and c1 > 0 and c2 <= 0


def changes(m, subject, t1, t2):
    """What changed between t1 and t2, derived from the records; never stored.

    A change is a value whose status moves between ESTABLISHED and NOT_ESTABLISHED, or a
    reconciled CONFIRMED transition whose window lies inside (t1, t2]. A value UNDETERMINED at
    either end is 'not established', never a change. UNRESOLVED transitions are listed apart."""
    assert t1['axis'] == t2['axis'], 'the axes are never converted'
    out = {'subject': subject, 'from': t1, 'to': t2, 'changes': [], 'not_established': [], 'unresolved': []}
    for prop in PROPS:
        seen = sorted({str(v) for v, _, _, _ in _records(m, subject, prop, t1) + _records(m, subject, prop, t2)})
        for v in seen:
            vv = True if prop == 'produced' else v
            a = evaluate(m, subject, prop, t1, value=vv)['status']
            b = evaluate(m, subject, prop, t2, value=vv)['status']
            if {a, b} == {ESTABLISHED, NOT_ESTABLISHED}:
                out['changes'].append({'property': prop, 'value': v, 'before': a, 'after': b, 'kind': 'STATE_BOUNDARY'})
            elif a != b or UNDETERMINED in (a, b):
                out['not_established'].append({'property': prop, 'value': v, 'before': a, 'after': b})
    for tr in sorted(m.transitions, key=lambda r: r['id']):
        if subject not in (tr['from'], tr['to']):
            continue
        state, _ = _support(m, {'provenance': tr['provenance']})
        window = tr.get('occurred') or ({'earliest': tr['at'], 'latest': tr['at']} if tr.get('at') else None)
        if tr['certainty'] == 'UNRESOLVED' or tr['kind'] in ('RELATED_UNSPECIFIED', 'POSSIBLY_SAME'):
            out['unresolved'].append({'transition': tr['id'], 'kind': tr['kind']})
        elif tr['certainty'] == 'CONFIRMED' and state == 'DECIDED' and window and _within(window, t1, t2):
            out['changes'].append({'transition': tr['id'], 'kind': 'TRANSITION', 'transition_kind': tr['kind']})
    return out


def dumps(x):
    """The canonical text of an evaluator result: two runs compare byte for byte."""
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
