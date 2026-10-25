"""Historical model M0: validate the M1 schema proposal. Read-only; documentation-level.

    python docs/schema/check_historical_m1_proposal.py

Not one of the production test suites (tools/test-*.py), and it writes nothing.
It checks four things about docs/schema/historical-m1-proposal.json:

  1. fit      the proposal extends docs/phase34-model.json without a collision:
              no added enum or field name already exists, every added field is
              optional, every type it uses is known;
  2. rules    the invariants it marks as schema rules are machine-checkable:
              prototype checks (here, not in tools/) give each synthetic fixture
              its expected verdict;
  3. compat   every existing row of data/model/ gives the same validation result
              under the extended contract as under today's (tools/model_schema.py
              check_row), so no row needs rewriting;
  4. inert    data/model/ and data/app/ hash the same before and after.
"""
import copy
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)) + os.sep
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

PROPOSAL = json.load(open(os.path.join(HERE, 'historical-m1-proposal.json'), encoding='utf-8'))
CONTRACT = json.load(open(ROOT + 'docs/phase34-model.json', encoding='utf-8'))
fails = []


def say(ok, name, detail=''):
    print('%s %s%s' % ('ok  ' if ok else 'FAIL', name, (' - ' + detail) if detail else ''))
    if not ok:
        fails.append(name)


def tree_hash(rel):
    h = hashlib.sha256()
    for d, dirs, files in sorted(os.walk(ROOT + rel)):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, ROOT).replace(os.sep, '/').encode())
            h.update(open(p, 'rb').read())
    return h.hexdigest()


before = {r: tree_hash(r) for r in ('data/model', 'data/app')}

# ---------------------------------------------------------------- 1. fit
enums = CONTRACT['enums']
added_enums = PROPOSAL['enums_added']
say(not (set(added_enums) & set(enums)), 'fit: added enums are new', ', '.join(sorted(set(added_enums) & set(enums))))
for e, spec in PROPOSAL['enum_values_added'].items():
    clash = set(spec['add']) & set(enums[e]['values'])
    say(e in enums and not clash, 'fit: %s gains %s, none present' % (e, spec['add']))
known_types = set(CONTRACT['value_types']) | set(PROPOSAL['value_types_added']) | {'object', 'text', 'date', 'any'}
for ent, fields in PROPOSAL['entity_fields_added'].items():
    have = set(CONTRACT['entities'][ent]['fields'])
    say(not (set(fields) & have), 'fit: %s fields %s are new' % (ent, sorted(fields)))
    for f, spec in fields.items():
        t = spec['type']
        ok_type = t in known_types or (t.startswith('enum:') and (t[5:] in enums or t[5:] in added_enums))
        say(spec['required'] is False and ok_type, 'fit: %s.%s optional, type %s known' % (ent, f, t))
for path, spec in PROPOSAL['entity_fields_changed'].items():
    ent, f = path.split('.')
    say(CONTRACT['entities'][ent]['fields'][f]['required'] is spec['required'][0] and spec['required'][1] is False,
        'fit: %s required %s -> %s (loosened only)' % (path, spec['required'][0], spec['required'][1]))
say(len(PROPOSAL['invariants']) >= 20, 'fit: %d invariants' % len(PROPOSAL['invariants']))

# ---------------------------------------------------------------- 2. rules (prototypes of M1 checks)
DATED = ('EXACT', 'APPROXIMATE', 'NO_LATER_THAN', 'NO_EARLIER_THAN')
PRECISION = {'DAY': r'^\d{4}-\d{2}-\d{2}$', 'MONTH': r'^\d{4}-\d{2}$', 'YEAR': r'^\d{4}$', 'DECADE': r'^\d{3}0s$'}


def key(v):
    """Comparable parts of a bound value: (year[, month[, day]]); a decade is its first year."""
    v = str(v)
    if v.endswith('s'):
        return (int(v[:4]),)
    return tuple(int(x) for x in v.split('-'))


def bound_errs(b, where):
    errs = S.check_bound(b, where)                                          # S1 (existing)
    if b.get('kind') in DATED:
        p, v, ax = b.get('precision'), str(b.get('value')), b.get('axis')
        if ax == 'VINTAGE' and not (p == 'VINTAGE' and re.match(r'^\d{4}$', v)):
            errs.append('%s: VINTAGE value %r precision %r' % (where, v, p))   # S2
        if ax == 'CALENDAR' and not (p in PRECISION and re.match(PRECISION[p], v)):
            errs.append('%s: CALENDAR value %r precision %r' % (where, v, p))  # S2
    return errs


def pair_errs(lo, hi, where):
    errs = []
    if lo.get('kind') in DATED and hi.get('kind') in DATED:
        if lo.get('axis') != hi.get('axis'):
            errs.append('%s: axes differ, %s and %s' % (where, lo.get('axis'), hi.get('axis')))   # S3
        else:
            a, b = key(lo['value']), key(hi['value'])
            n = min(len(a), len(b))
            if a[:n] > b[:n]:
                errs.append('%s: lower %s after upper %s' % (where, lo['value'], hi['value']))     # S4
    return errs


def validity_errs(v, where='validity'):
    errs = S.check_validity(v, where)                                       # existing shape and OPEN rule
    for side in ('valid_from', 'valid_to'):
        errs += bound_errs(v.get(side) or {}, where + '.' + side)
    return errs + pair_errs(v.get('valid_from') or {}, v.get('valid_to') or {}, where)


def window_errs(w, where='window'):
    if not isinstance(w, dict) or set(w) != {'earliest', 'latest'}:
        return ['%s: shape %r' % (where, w)]
    errs = []
    for side in ('earliest', 'latest'):
        if w[side].get('kind') in ('OPEN', 'NOT_APPLICABLE'):
            errs.append('%s.%s: %s in a window' % (where, side, w[side]['kind']))   # S5
        errs += bound_errs(w[side], where + '.' + side)
    return errs + pair_errs(w['earliest'], w['latest'], where)


def claim_errs(r):
    errs = []
    cv, cw = r.get('claimed_validity'), r.get('claimed_window')
    if cv is not None and cw is not None:
        errs.append('claim: both a claimed validity and a claimed window')       # S7
    if (cv is not None or cw is not None):
        if r.get('statement_mode') not in PROPOSAL['enums_added']['StatementMode']['values']:
            errs.append('claim: statement_mode required')                       # S7
        if not r.get('artifact') and not r.get('quote'):
            errs.append('claim: no artifact and no quote')                     # S18
    if cv is not None:
        errs += validity_errs(cv, 'claimed_validity')
    if cw is not None:
        errs += window_errs(cw, 'claimed_window')
    # S6: a bound taken from the document's own date (basis an ArtifactDate; the fixtures
    # mark that basis ARTIFACT_DATE) is only ever IMPLIED.
    bounds = list((cv or {}).values()) + list((cw or {}).values())
    if any(isinstance(b, dict) and b.get('basis') == 'ARTIFACT_DATE' for b in bounds) and \
            r.get('statement_mode') != 'IMPLIED':
        errs.append('claim: a bound from the document date is not IMPLIED')
    return errs


def transition_errs(r):
    errs = []
    kind, a, b = r['kind'], r['from'], r['to']
    if kind not in set(CONTRACT['enums']['TransitionKind']['values']) | set(
            PROPOSAL['enum_values_added']['TransitionKind']['add']):
        errs.append('transition: kind %r' % kind)
    if kind == 'RENAMED' and a != b:
        errs.append('transition: RENAMED relates one subject to itself')               # S8
    if kind == 'SUCCEEDED_BY' and (a == b or S.ref_entity(a) != S.ref_entity(b)):
        errs.append('transition: SUCCEEDED_BY relates two subjects of one type')        # S8
    if kind in ('RELATED_UNSPECIFIED', 'POSSIBLY_SAME') and r['certainty'] != 'UNRESOLVED':
        errs.append('transition: %s must be UNRESOLVED' % kind)                        # S9
    if 'at' in r and 'occurred' in r:
        errs.append('transition: both at and occurred')                               # O4
    if 'occurred' in r:
        errs += window_errs(r['occurred'], 'occurred')
    return errs


def reconciliation_errs(r):
    errs = []
    historical = r['field'] in PROPOSAL['historical_reconciliation_fields']
    disp = r.get('dispositions') or {}
    cands = set(r['candidates'])
    if set(disp) - cands:
        errs.append('reconciliation: dispositions for non-candidates %s' % sorted(set(disp) - cands))   # S14
    sel = [k for k, d in disp.items() if d.get('disposition') == 'SELECTED']
    if disp and r.get('selected') and sel != [r['selected']]:
        errs.append('reconciliation: the selected candidate is not the one SELECTED')                  # S14
    if any(d.get('disposition') == 'REJECTED' and not d.get('reason') for d in disp.values()):
        errs.append('reconciliation: REJECTED without a reason')                                      # S14
    if r['status'] in ('CONFLICT_OPEN', 'DEFERRED') and (r.get('selected') or sel):
        errs.append('reconciliation: a selection while %s' % r['status'])                              # S15
    if historical and r['rule'] not in PROPOSAL['historical_reconciliation_rules_allowed_before_D5']:
        errs.append('reconciliation: rule %s before D5' % r['rule'])                                    # S16
    return errs


def fixture_errs(fx):
    kind, row = fx.get('kind', 'entity'), fx['row']
    if kind == 'bound':
        return bound_errs(row, 'bound')
    if kind == 'validity':
        return validity_errs(row)
    if kind == 'window':
        return window_errs(row)
    if kind == 'claim':
        return claim_errs(row)
    if kind == 'transition':
        return transition_errs(row)
    if kind == 'reconciliation':
        return reconciliation_errs(row)
    return claim_errs(row)        # an Observation with no historical field is never a claim error


for fx in PROPOSAL['fixtures']:
    errs = fixture_errs(fx)
    got = 'invalid' if errs else 'valid'
    say(got == fx['expect'], 'rules: %s (%s) %s' % (fx['id'], fx['invariant'], fx['expect']), '; '.join(errs)[:120])

# ---------------------------------------------------------------- 3. compat with the existing model
def extended():
    ents, ens = copy.deepcopy(S.ENTITIES), {k: set(v) for k, v in S.ENUMS.items()}
    for ent, fields in PROPOSAL['entity_fields_added'].items():
        for f, spec in fields.items():
            ents[ent]['fields'][f] = {'type': spec['type'], 'required': False}
    for path, spec in PROPOSAL['entity_fields_changed'].items():
        ent, f = path.split('.')
        ents[ent]['fields'][f]['required'] = spec['required'][1]
    for e, spec in PROPOSAL['enums_added'].items():
        ens[e] = set(spec['values'])
    for e, spec in PROPOSAL['enum_values_added'].items():
        ens[e] |= set(spec['add'])
    return ents, ens


rows_checked, differ = 0, []
orig = (S.ENTITIES, S.ENUMS)
ext = extended()
for rel, (entity, _, _) in sorted(S.LAYOUT.items()):
    if not rel.endswith('.jsonl') or entity not in S.ENTITIES:
        continue
    for row in L.read_table(rel):
        rows_checked += 1
        S.ENTITIES, S.ENUMS = orig
        a = S.check_row(entity, row)
        S.ENTITIES, S.ENUMS = ext
        b = S.check_row(entity, row)
        S.ENTITIES, S.ENUMS = orig
        if a != b:
            differ.append((rel, row.get('id'), a, b))
total = sum(sum(1 for _ in open(L.MODEL + rel, encoding='utf-8') if _.strip())
            for rel, (entity, _, _) in S.LAYOUT.items()
            if rel.endswith('.jsonl') and entity in S.ENTITIES and os.path.exists(L.MODEL + rel))
say(rows_checked == total and rows_checked > 0 and not differ,
    'compat: all %d existing rows (of %d), same result under the extended contract' % (rows_checked, total),
    '' if not differ else repr(differ[:2]))
recs = L.read_table('reconciliation/reconciliations.jsonl')
say(all('dispositions' not in r for r in recs) and
    not [r for r in recs if r['field'] in PROPOSAL['historical_reconciliation_fields']],
    'compat: %d reconciliations carry no disposition and no historical field (S22 read rule applies)' % len(recs))
state = [r for rel in ('identity/names.jsonl', 'state/estate-wine.jsonl', 'state/rank-assertions.jsonl',
                       'state/rank-absences.jsonl', 'state/classification-memberships.jsonl',
                       'state/appellation-memberships.jsonl', 'state/estate-locations.jsonl',
                       'state/source-estate.jsonl') for r in L.read_table(rel)]
undated = sum(1 for r in state if r['validity']['valid_from']['kind'] == 'UNKNOWN')
say(undated == len(state), 'compat: all %d state records start UNKNOWN, so S21 makes none historical' % len(state))
say(not L.read_table('identity/transitions.jsonl'), 'compat: 0 IdentityTransitions, so at -> occurred rewrites nothing')

# ---------------------------------------------------------------- 4. inert
after = {r: tree_hash(r) for r in ('data/model', 'data/app')}
say(before == after, 'inert: data/model and data/app unchanged by this check')

print('\n%s' % ('all pass' if not fails else '%d FAIL: %s' % (len(fails), ', '.join(fails[:5]))))
sys.exit(1 if fails else 0)
