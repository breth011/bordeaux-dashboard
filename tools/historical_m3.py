"""Historical model M3: the eligibility gate for explicit, already-reviewed historical claims.

Pure rules, no I/O. tools/extract-historical-m3.py gathers the facts about each candidate
(is the artifact held, is the passage there, what did the evidence store decide about the
document, does the subject resolve) and calls gate(); the audit records every verdict.

A candidate is eligible only when all eight hold (the M3 brief, section 2):

    E1 artifact     the document is held (an Artifact of the model)
    E2 provenance   its passage is found in the held text, and its provenance is not LEGACY_UNSOURCED
    E3 reviewed     the evidence store ACCEPTED the document for the candidate's own estate
    E4 explicit     the source states the historical fact in words (statement_mode EXPLICIT)
    E5 subject      the subject resolves to one model id (the identity map is not AMBIGUOUS)
    E6 temporal     the time is stated, on a stated axis - not taken from the document's framing
    E7 decisions    it depends on no undecided decision (D2, D5, an identity decision)
    E8 schema       it is representable in the M1 schema without a new concept

An eligible candidate is then reconciled without choosing a winner (section 10): one claim
(ONLY_CANDIDATE, SINGLE), several agreeing claims (UNANIMOUS, AGREED), or an existing manual
decision (MANUAL_DECISION, RESOLVED). Disagreeing eligible claims are CONFLICT_OPEN.
"""
import model_schema as S

VERSION = 'historical-m3/1'
ACTOR = 'tools/historical_m3.py'

ACCEPTED = 'ACCEPTED'
CATEGORIES = [
    ACCEPTED,
    'BLOCKED_D2',                      # depends on D2 (Echo: rename or succession)
    'BLOCKED_IDENTITY_DECISION',       # depends on an identity decision not taken (La Parde)
    'CONFLICT_OPEN',                   # eligible, but eligible claims disagree
    'EXCLUDED_CURRENT_STATEMENT',      # a current fact, no claimed time: not history
    'EXCLUDED_ABSENCE',                # inferred from a missing sheet, listing or record (H2)
    'EXCLUDED_NOT_HISTORICAL',         # no temporal content at all
    'EXCLUDED_NOT_IDENTITY',           # a label or presentation change (3.4 section 7)
    'EXCLUDED_IMPLIED',                # the time comes from the document's framing (S6, H3)
    'REJECTED_EVIDENCE_REFUSED',       # the evidence store refused the document
    'REJECTED_NO_PROVENANCE',          # no artifact, no passage, or LEGACY_UNSOURCED
    'REJECTED_NOT_REVIEWED',           # held and quoted, never reviewed by the evidence store
    'REJECTED_AMBIGUOUS_SUBJECT',      # the subject does not resolve to one model id
    'REJECTED_TEMPORAL_UNCLEAR',       # explicit, but the axis or the bound is not stated
    'REJECTED_NOT_REPRESENTABLE',      # would need a concept the M1 schema lacks
]
GATES = ('E1_artifact', 'E2_provenance', 'E3_reviewed', 'E4_explicit', 'E5_subject', 'E6_temporal',
         'E7_decisions', 'E8_schema')


def gates(c):
    """{gate: bool} for one candidate's gathered facts."""
    return {
        'E1_artifact': bool(c.get('artifact_present')),
        'E2_provenance': bool(c.get('artifact_present') and c.get('passage_found')
                              and c.get('provenance_kind') != 'LEGACY_UNSOURCED'),
        'E3_reviewed': c.get('evidence') == 'ACCEPTED',
        'E4_explicit': c.get('statement_mode') == 'EXPLICIT',
        'E5_subject': c.get('subject_status') == 'RESOLVED',
        'E6_temporal': c.get('temporal') == 'STATED',
        'E7_decisions': not c.get('depends_on'),
        'E8_schema': c.get('representable', True),
    }


def gate(c, eligible_peers=()):
    """{category, failed, rule?, status?} for one candidate. eligible_peers: the other eligible
    candidates about the same subject, property and time, each {key, value}."""
    g = gates(c)
    failed = [k for k in GATES if not g[k]]
    deps = c.get('depends_on') or []
    out = {'failed': failed}
    if 'D2' in deps:
        out['category'] = 'BLOCKED_D2'
    elif any(d.startswith('IDENTITY') for d in deps):
        out['category'] = 'BLOCKED_IDENTITY_DECISION'
    elif c.get('excluded_as'):
        out['category'] = 'EXCLUDED_' + c['excluded_as']
    elif c.get('evidence') == 'REFUSED':
        out['category'] = 'REJECTED_EVIDENCE_REFUSED'
    elif not g['E2_provenance']:
        out['category'] = 'REJECTED_NO_PROVENANCE'
    elif not g['E3_reviewed']:
        out['category'] = 'REJECTED_NOT_REVIEWED'
    elif not g['E5_subject']:
        out['category'] = 'REJECTED_AMBIGUOUS_SUBJECT'
    elif not g['E4_explicit'] or c.get('temporal') == 'FRAMING':
        out['category'] = 'EXCLUDED_IMPLIED'
    elif not g['E6_temporal']:
        out['category'] = 'REJECTED_TEMPORAL_UNCLEAR'
    elif not g['E8_schema']:
        out['category'] = 'REJECTED_NOT_REPRESENTABLE'
    elif deps:
        out['category'] = 'BLOCKED_IDENTITY_DECISION' if any('IDENTITY' in d for d in deps) else 'BLOCKED_D2'
    else:
        values = {repr(p['value']) for p in eligible_peers} | {repr(c.get('value'))}
        if len(values) > 1:
            out.update(category='CONFLICT_OPEN', rule=None, status='CONFLICT_OPEN')
        elif c.get('manual_decision'):
            out.update(category=ACCEPTED, rule='MANUAL_DECISION', status='RESOLVED')
        elif eligible_peers:
            out.update(category=ACCEPTED, rule='UNANIMOUS', status='AGREED')
        else:
            out.update(category=ACCEPTED, rule='ONLY_CANDIDATE', status='SINGLE')
    assert out['category'] in CATEGORIES
    if out['category'] != ACCEPTED and not failed and out['category'] != 'CONFLICT_OPEN':
        out['failed'] = ['excluded: ' + out['category']]
    return out


# -- representation (used to prove E8 and by the tests; M3 writes nothing while BLOCKED) ----------

def rows_for(claims, record, observed_at, decision=None):
    """The model rows one historical fact would add, all in the M1 schema.

    claims: [{artifact, quote, locus, lang, subject, field, value, claimed_validity | claimed_window}],
            each an EXPLICIT statement from a reviewed document.
    record: {'entity': 'VintageStatement' | 'NameRecord' | 'RankAbsence' | 'Ownership', ...fields}
            whose bounds' basis (or provenance, for a point record) is filled in here.
    decision: an existing manual decision {resolver, reason} (case C), or None.

    Returns {rel: [rows]}. Nothing here decides anything a source did not say: the
    reconciliation's rule follows from the claims (one, several agreeing) or the decision."""
    rows = {'cross/provenance.jsonl': [], 'observation/observations.jsonl': [],
            'reconciliation/reconciliations.jsonl': []}

    def prov(kind, **kw):
        row = {'kind': kind, 'actor': ACTOR}
        row.update({k: v for k, v in kw.items() if v is not None})
        row['id'] = S.hid('Provenance', repr(sorted(row.items())))
        rows['cross/provenance.jsonl'].append(row)
        return row['id']

    obs_ids = []
    for c in claims:
        pid = prov('DOCUMENT', artifact=c['artifact'], quote=c['quote'], code_state={'locus': c['locus'], 'extractor': VERSION})
        o = {'id': S.hid('Observation', c['artifact'], c['field'], repr(c['value']), c['locus']),
             'subject': c['subject'], 'field': c['field'], 'value': c['value'], 'artifact': c['artifact'],
             'locus': c['locus'], 'lang': c.get('lang'), 'extraction': {'method': VERSION},
             'confidence': 'EXPLICIT_STATEMENT', 'observed_at': observed_at, 'provenance': pid,
             'subject_status': 'ESTABLISHED', 'statement_mode': 'EXPLICIT'}
        for k in ('claimed_validity', 'claimed_window'):
            if k in c:
                o[k] = _with_basis(c[k], pid)
        o = {k: v for k, v in o.items() if v is not None}
        rows['observation/observations.jsonl'].append(o)
        obs_ids.append(o['id'])
    values = {repr(c['value']) for c in claims}
    rec_entity = record['entity']
    rid = S.hid(rec_entity, repr(sorted((k, repr(v)) for k, v in record.items())))
    if len(values) > 1:
        rule, status, selected = None, 'CONFLICT_OPEN', None
    elif decision:
        rule, status, selected = 'MANUAL_DECISION', 'RESOLVED', obs_ids[0]
    elif len(obs_ids) > 1:
        rule, status, selected = 'UNANIMOUS', 'AGREED', obs_ids[0]
    else:
        rule, status, selected = 'ONLY_CANDIDATE', 'SINGLE', obs_ids[0]
    rprov = prov('DERIVATION', derived_from=sorted(obs_ids), code_state={'rule': rule or 'NONE'})
    rec = {'id': S.hid('Reconciliation', rid, 'exists'), 'subject': rid,
           'field': 'exists' if 'validity' not in record else 'valid_from',
           'candidates': obs_ids, 'rule': rule or 'MANUAL_DECISION', 'status': status,
           'reason': (decision or {}).get('reason') or ('%d explicit claim(s) from reviewed documents' % len(obs_ids)),
           'resolver': (decision or {}).get('resolver') or ACTOR, 'decided_at': observed_at, 'provenance': rprov}
    if selected:
        rec['selected'] = selected
        rec['dispositions'] = {o: {'disposition': 'SELECTED' if o == selected else 'CONSISTENT'} for o in obs_ids}
    else:
        rec['dispositions'] = {o: {'disposition': 'NOT_ASSESSED'} for o in obs_ids}
    rows['reconciliation/reconciliations.jsonl'].append(rec)
    basis = prov('EVIDENCE_DECISION', derived_from=[rec['id']])
    body = {k: v for k, v in record.items() if k != 'entity'}
    if 'validity' in body:
        body['validity'] = _with_basis(body['validity'], basis)
    body.update(id=rid, provenance=basis)
    rel = {'VintageStatement': 'state/vintage-statements.jsonl', 'NameRecord': 'identity/names.jsonl',
           'RankAbsence': 'state/rank-absences.jsonl', 'Ownership': 'state/ownership.jsonl'}[rec_entity]
    rows[rel] = [body]
    return rows


def _with_basis(v, basis):
    out = {}
    for k, b in v.items():
        b = dict(b) if isinstance(b, dict) else b
        if isinstance(b, dict) and 'value' in b:
            b['basis'] = basis
        out[k] = b
    return out
