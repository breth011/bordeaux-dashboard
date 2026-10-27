"""M3.10A: register the four Durfort-Vivens documents M3.9 accepted as model artifacts - the audited input
the migration reads, for documents acquired outside the discovery crawl.

    python tools/m310a-register.py           write data/audit/m3.10a-external-artifact-registration.jsonl
    python tools/m310a-register.py --check   recompute and compare, byte for byte

The model mints artifacts from four inputs: data/sources.json, the generated discovery manifest, the paths
the evidence reader hashed, and - from this phase - audited registrations of externally acquired documents.
The discovery manifest stays its generator's: nothing is added to data/discovery, and no crawl fact is
written. An external registration says what M3.8 established and nothing more: the URL it fetched, when,
the HTTP status, the bytes' sha256, size and media type, and that M3.8 - not the crawler - acquired it.

THE INPUT is exactly M3.9's SAFE_TO_MAP documents of Château Durfort-Vivens (four), each matched to its M3.8
item and to its held file (sources/acquisition/m3.8/blobs/<sha256>), whose sha256 and size are checked. Any
other count, an unmatched candidate, a missing or changed file stops the run.

THE RECORDS: one `registration` row per document - the only rows the migration reads
(tools/mig_m2_identity.py mints the artifact by sha256 through the same path as every other input;
tools/mig_m6_provenance.py places it at its URL in M3.2B's shape) - and one `result` row per document, read
back from the model: the artifact, whether it was minted or an existing one reused, the placement. Every row
states what registration is not: no evidence decision, no attribution, no value.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'data/audit/m3.10a-external-artifact-registration.jsonl'
DOC = L.ROOT + 'docs/PHASE-M3.10A-ARTIFACT-REGISTRATION.md'
M39 = L.ROOT + 'data/audit/m3.9-evidence-review.jsonl'
M38 = L.ROOT + 'data/audit/m3.8-acquisition-pilot.jsonl'
M37 = L.ROOT + 'data/audit/m3.7-source-confirmation.jsonl'
STORE = 'sources/acquisition/m3.8/blobs/'
ESTATE = 'es_00263'
RETRIEVAL = 'confirmed-source acquisition (tools/m38-acquire.py, the discovery fetch discover/1.0)'
NOT_YET = {'evidence_decision': 'NONE', 'attribution': 'NONE', 'value_application': 'NONE'}


class Stop(Exception):
    pass


def registrations():
    """The four registration rows, in M3.9's order."""
    acc = [r for r in L.jsonl_lines(M39) if r['record'] == 'review' and r['disposition'] == 'SAFE_TO_MAP'
           and r['estate'] == ESTATE]
    if len(acc) != 4 or len([r for r in L.jsonl_lines(M39) if r['record'] == 'review'
                             and r['disposition'] == 'SAFE_TO_MAP']) != 4:
        raise Stop('M3.9 accepts %d Durfort-Vivens documents, expected exactly 4 and no other' % len(acc))
    items = {r['n']: r for r in L.jsonl_lines(M38) if r['record'] == 'item'}
    rel = [r for r in L.jsonl_lines(M37) if r['record'] == 'relationship' and r['estate'] == ESTATE
           and r['status'].startswith('CONFIRMED_')]
    if len(rel) != 1:
        raise Stop('M3.7 confirms %d sources for %s, expected 1' % (len(rel), ESTATE))
    out = []
    for r in acc:
        it = items.get(r['m38_item'])
        if not it or it['url'] != r['url'] or it['sha256'] != r['sha256'] or it['retrieval'] != 'OK':
            raise Stop('M3.9 review %d does not match one acquired M3.8 item' % r['n'])
        path = L.ROOT + STORE + it['sha256']
        if not os.path.exists(path):
            raise Stop('the held file of %s is missing' % it['url'])
        data = open(path, 'rb').read()
        if hashlib.sha256(data).hexdigest() != it['sha256'] or len(data) != it['bytes']:
            raise Stop('the held file of %s no longer hashes to M3.8\'s record' % it['url'])
        if it['content_type'] != 'application/pdf' or data[:5] != b'%PDF-':
            raise Stop('%s: the media type is not established consistently' % it['url'])
        out.append(dict({'record': 'registration', 'candidate': 'm3.9:%d' % r['n'], 'm38_item': it['n'],
                         'url': it['url'], 'final_url': it['final_url'], 'http_status': it['status'],
                         'fetched_at': it['at'], 'sha256': it['sha256'], 'bytes': it['bytes'],
                         'media_type': it['content_type'], 'acquisition_path': STORE + it['sha256'],
                         'acquired_by': 'M3.8', 'origin': 'EXTERNAL_ACQUISITION', 'retrieval_method': RETRIEVAL,
                         'source': rel[0]['source'], 'source_relationship': rel[0]['id'],
                         'intended': 'REGISTER_ARTIFACT'}, **NOT_YET))
    return out


def results(regs):
    """What the migration made of each registration: read back from the model, never written to it."""
    idmap = {r['legacy_key']: r for r in L.read_table('identity/identity-map.jsonl') if r['namespace'] == 'artifact-by-sha256'}
    arts = {a['id']: a for a in L.read_table('identity/artifacts.jsonl')}
    pl = {}
    prov = {p['id']: p for p in L.read_table('cross/provenance.jsonl')}
    for p in L.read_table('document/placements.jsonl'):
        if (prov.get(p['provenance'], {}).get('code_state') or {}).get('stream') == 'M3.10A':
            pl[(p['artifact'], p['locator']['value'])] = p
    out = []
    for g in regs:
        m = idmap.get(g['sha256'])
        if not m:
            continue                                  # not yet migrated: the results follow the migration
        a = arts[m['stable_id']]
        p = pl.get((a['id'], g['url']))
        minted = (prov.get(m['provenance'], {}).get('quote') or '').startswith('one Artifact per digest')
        out.append(dict({'record': 'result', 'candidate': g['candidate'], 'artifact': a['id'],
                         'artifact_row': a, 'minted': minted, 'reused': False,
                         'placement': p['id'] if p else None, 'locator': p['locator'] if p else None,
                         'placement_source': p.get('source') if p else None}, **NOT_YET))
    return out


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def report(regs, res):
    """docs/PHASE-M3.10A-ARTIFACT-REGISTRATION.md, from the manifest's rows alone."""
    by = {r['candidate']: r for r in res}
    out = []
    w = out.append
    w('# Phase M3.10A — External acquisition artifact registration\n')
    w('Generated by `python tools/m310a-register.py` (`%s`); never edited by hand. **Registration only: the four '
      'documents exist as model artifacts, and nothing more.** No evidence decision, attribution, observation, '
      'reconciliation, canonical value or gap resolution was created; the discovery manifest and its location logs '
      'are untouched; no crawl was run.\n' % OUT[len(L.ROOT):])
    w('## 1. The fourth artifact input\n')
    w('The model mints artifacts from `data/sources.json`, the generated discovery manifest, the paths the evidence '
      'reader hashed, and - from this phase - **audited registrations of externally acquired documents**. The '
      'discovery manifest stays its generator\'s: externally acquired is not discovered by the crawler, and no crawl '
      'fact is written.\n')
    w('- `tools/mig_m2_identity.py` reads the manifest\'s `registration` rows (`external_registrations`) and mints '
      'each document by its sha256 through the same call as every other digest, after all of them, so that no '
      'existing artifact\'s id moves when the model is built from scratch.')
    w('- `tools/mig_m6_provenance.py` places each at its URL in M3.2B\'s shape (`external_placements`): a URL '
      'locator, the confirmed source, the fetch day, `retrieval_method`, and a DOCUMENT provenance whose '
      '`code_state` names the stream, the M3.8 acquisition and `EXTERNAL_ACQUISITION`.\n')
    w('## 2. The four documents\n')
    w('Exactly M3.9\'s SAFE_TO_MAP documents of Château Durfort-Vivens, each checked against its held file and '
      'M3.8\'s record (sha256, size, URL, media type).\n')
    w('| Candidate | Document | sha256 | Bytes | Fetched (M3.8) | Artifact | Minted / reused | Placement |')
    w('|---|---|---|---:|---|---|---|---|')
    for g in regs:
        r = by.get(g['candidate']) or {}
        w('| %s | %s | `%s…` | %d | %s | `%s` | %s | `%s` |' % (
            g['candidate'], g['url'].rsplit('/', 1)[-1], g['sha256'][:12], g['bytes'], g['fetched_at'],
            r.get('artifact'), 'reused' if r.get('reused') else 'minted' if r.get('minted') else '—', r.get('placement')))
    w('\nEach placement is on `%s` (the source M3.7 confirmed for Château Durfort-Vivens), with retrieval method '
      '"%s".\n' % (regs[0]['source'], regs[0]['retrieval_method']))
    w('## 3. What registration is not\n')
    w('| | Status |')
    w('|---|---|')
    for k in ('artifact exists', 'evidence decision', 'attribution', 'observation', 'canonical value',
              'reconciliation', 'gap resolution'):
        w('| %s | %s |' % (k, 'yes, %d' % len(res) if k == 'artifact exists' else '**NONE**'))
    w('\nO1 holds: a document never put to the evidence store has no accepted decision, and is not attributed. '
      'M3.10B is where these four go through the evidence decision path.\n')
    w('## 4. Earlier phases\' checks\n')
    w('The suites and audits that compare the model with an earlier state set M3.10A\'s rows aside, as they set '
      'aside M3.6D\'s and M3.6F\'s: `historical_m2_scope` recognises exactly the registered documents\' artifacts, '
      'sha256 keys, URL locators, placements and provenance (`is_m310a_row`, `unchanged_but_m310a`), and the dated '
      'audits read the model as they did (`extract-document-dates.py`, `m38-acquisition-pilot.py`).\n')
    return ('\n'.join(out) + '\n').encode('utf-8')


def main():
    try:
        regs = registrations()
    except Stop as s:
        print('BLOCKED - %s' % s)
        sys.exit(2)
    res = results(regs)
    b, doc = body(regs + res), report(regs, res)
    if '--check' in sys.argv:
        bad = [p[len(L.ROOT):] for p, x in ((OUT, b), (DOC, doc)) if not os.path.exists(p) or open(p, 'rb').read() != x]
        print('M3.10A outputs ' + ('are current' if not bad else 'differ: %s' % bad))
        sys.exit(1 if bad else 0)
    open(OUT, 'wb').write(b)
    open(DOC, 'wb').write(doc)
    print('%s written (%d registration(s), %d result(s)); %s written' % (OUT[len(L.ROOT):], len(regs), len(res),
                                                                        DOC[len(L.ROOT):]))


if __name__ == '__main__':
    main()
