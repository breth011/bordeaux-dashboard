# -*- coding: utf-8 -*-
"""Dry-run proposals. Nothing here is applied, by design and by code.

    python tools/propose.py                 the report
    python tools/propose.py --write         data/proposals.jsonl
    python tools/propose.py --estate lynch-bages

This tool has no code path that writes sources.json, fiches.js,
cuvees.js, field-src.js or cuvee-src.js. It reads the three evidence
stores and writes one file of proposals.

A proposal is not a correction. It is a statement of what the evidence
suggests, with the evidence attached, so that the next phase can be
mechanical rather than investigative - and so that applying it is a
separate, reviewable act.

                              THE STATUSES

  PROPOSED_CORRECTION   two independent signals agree and the change
                        is narrow. The 50 Echo sheets: the filename
                        and the document text both name the Echo, the
                        manifest says the Blanc.

  PROPOSED_REVIEW       the evidence points somewhere but one signal
                        is missing or they disagree in a way a person
                        should look at.

  INSUFFICIENT_EVIDENCE a disagreement is visible and nothing settles
                        it. Recorded so it is not mistaken for
                        agreement.

  NO_CHANGE             the manifest is right. Worth emitting: four of
                        the 56 wine-identity cases are this, and
                        saying so stops them being "fixed".

Nothing is promoted to CONFIRMED here. That word belongs to a person.
"""
import argparse
import collections
import datetime
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TOOL_VERSION = 1
OUT = ROOT + 'data/proposals.jsonl'


def commit():
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def read_jsonl(name, skip_head=True):
    p = ROOT + 'data/' + name
    if not os.path.exists(p):
        return []
    out = []
    with io.open(p, encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                d = json.loads(line)
            except Exception:
                continue
            if '_' in d and ('rows' in d or 'decider_version' in d
                             or 'tool_version' in d):
                continue
            out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--estate')
    ap.add_argument('--limit', type=int, default=10)
    a = ap.parse_args()

    ident = read_jsonl('wine-identity.jsonl')
    attrib = read_jsonl('attribution-candidates.jsonl')
    dec = read_jsonl('evidence-decisions.jsonl')

    # What the contextual pass accepted, per artifact, so a proposal
    # can say whether the reader would actually take the document once
    # the manifest named the right wine.
    accepted = collections.defaultdict(set)
    vintage_refused = collections.defaultdict(set)
    # For the unattributed artifacts, keyed by folder/file, because a
    # basename occurs in more than one folder 888 times.
    ua_accepted = collections.defaultdict(set)
    ua_refused = collections.defaultdict(collections.Counter)
    for d in dec:
        if d.get('v') != 2:
            continue
        c = d.get('ctx') or {}
        if c.get('estate') is None and c.get('target_estate'):
            akey = (c.get('folder') or '') + '/' + d['artifact']
            if d.get('decision') == 'ACCEPTED':
                ua_accepted[akey].add((c.get('target_wine'),
                                       c.get('target_vintage')))
            elif d.get('decision') == 'REFUSED':
                ua_refused[akey][d.get('code')] += 1
            continue
        if d.get('decision') == 'ACCEPTED':
            accepted[d['artifact']].add((c.get('target_wine'),
                                         c.get('target_vintage')))
        elif d.get('code') == 'WRONG_VINTAGE':
            vintage_refused[d['artifact']].add(c.get('target_vintage'))

    rows = []

    # ---------------------------------------- wine identity proposals
    for r in ident:
        if a.estate and r['manifest']['estate'] != a.estate:
            continue
        o, m = r['observed'], r['manifest']
        ev = ['filename names %r' % o['wine_from_filename'],
              'document text names %s' % ', '.join(o['wine_from_text']),
              'rule: %s, neither name contains the other'
              % r['rule']['test']]
        if o.get('also_names_the_estate'):
            ev.append('also names the estate itself, which is the house '
                      'in the footer and not a second wine')
        if r['state'] == 'MANIFEST_METADATA_WRONG':
            status = 'PROPOSED_CORRECTION'
            action = ("set the manifest's `wine` to %r"
                      % o['wine_from_filename'])
            conf = 'HIGH'
            why = ('both the filename and the document name %r while '
                   'the manifest says %r'
                   % (o['wine_from_filename'], m['wine']))
        elif r['state'] == 'FILENAME_MISLEADING':
            status, action, conf = 'NO_CHANGE', 'none', 'HIGH'
            why = ('the document agrees with the manifest (%r); only '
                   'the filename names %r, and a filename is not '
                   'evidence against a document'
                   % (m['wine'], o['wine_from_filename']))
        elif r['state'] == 'MULTI_WINE_DOCUMENT':
            status, action, conf = 'PROPOSED_REVIEW', 'none', 'MEDIUM'
            why = ('the document covers more than one wine, so no '
                   'single `wine` value is right and the manifest '
                   'cannot express it')
        else:
            status, action, conf = 'INSUFFICIENT_EVIDENCE', 'none', 'LOW'
            why = r['why']
        rows.append({
            'artifact': r['artifact'],
            'kind': 'wine_identity',
            'current': {'estate': m['estate'], 'wine': m['wine'],
                        'vintage': m['vintage']},
            'observed': {'wine': o['wine_from_filename'],
                         'wine_from_text': o['wine_from_text'],
                         'vintage': o.get('vintage')},
            'proposed': ({'estate': m['estate'],
                          'wine': o['wine_from_filename'],
                          'vintage': m['vintage']}
                         if status == 'PROPOSED_CORRECTION' else None),
            'status': status, 'action': action, 'confidence': conf,
            'why': why, 'evidence': ev,
            'reader_would_accept': sorted(
                '%s @%s' % (w, y) for w, y in accepted.get(r['artifact'],
                                                           ())) or None,
            'v': TOOL_VERSION, 'at': datetime.date.today().isoformat(),
            'commit': commit(),
        })

    # ------------------------------------------ attribution proposals
    for r in attrib:
        fold = r['evidence']['folder_estate']
        if a.estate and fold != a.estate:
            continue
        st = r['state']
        akey = r['artifact']
        took = ua_accepted.get(akey)
        refused = ua_refused.get(akey) or collections.Counter()
        # The contextual pass outranks the census. The census decided
        # HIGH_CONFIDENCE when "the document names the folder's
        # estate" - and a group footer names EVERY property the group
        # owns. FICHE-PRODUIT-CHATEAU-LA-PATACHE-2019.pdf sits in
        # Bellefont-Belcier's folder and prints "CHATEAU
        # BELLEFONT-BELCIER - CHATEAU TOUR SAINT CHRISTOPHE - ENCLOS
        # TOURMALINE - CHATEAU HAUT-BRISSON - CHATEAU LA PATACHE" at
        # the foot, so the census saw the folder's estate named and
        # called it certain. The guard reads the filename and says La
        # Patache. 88 of the 244 HIGH_CONFIDENCE are refused this way.
        if st == 'HIGH_CONFIDENCE' and not took and refused:
            status = 'INSUFFICIENT_EVIDENCE'
            action = 'none'
            conf = 'LOW'
            top = refused.most_common(1)[0][0]
            why = ('the census called this certain because the document '
                   'names %s, but the reader refuses it for every '
                   'wine and vintage of that estate (%s) - a group '
                   'footer names every property, so naming the estate '
                   'is not evidence of being its document' % (fold, top))
        elif st == 'HIGH_CONFIDENCE':
            status = 'PROPOSED_CORRECTION'
            action = "set the manifest's `estate` to %r" % fold
            conf = 'HIGH'
            why = ('the manifest gives this artifact no estate; the '
                   'document names the one its folder does, and the '
                   'reader accepts it for %s'
                   % ', '.join('%s @%s' % (w, y)
                               for w, y in sorted(took, key=str)[:2]))
        elif st == 'CANDIDATE' and not took and refused:
            status, action, conf = 'INSUFFICIENT_EVIDENCE', 'none', 'LOW'
            why = ('only the folder names %s, and the reader refuses the '
                   'document for every wine and vintage of it (%s)'
                   % (fold, refused.most_common(1)[0][0]))
        elif st == 'CANDIDATE':
            # ACCEPTED from whose_sheet is an identity NON-OBJECTION,
            # not a confirmation that the document carries wine data:
            # a producer profile with no figures in it is accepted too,
            # because no guard objects to it. So a CANDIDATE the reader
            # accepts is still only for review.
            status, conf = 'PROPOSED_REVIEW', 'MEDIUM'
            action = "consider setting `estate` to %r" % fold
            why = ('the folder names %s and the document carries wine '
                   'data, but the document names no estate - the folder '
                   'is where the crawler put the file, which has been '
                   'wrong before' % fold)
        elif st == 'CONFLICT':
            status, action, conf = 'INSUFFICIENT_EVIDENCE', 'none', 'LOW'
            why = r['why']
        elif st == 'REJECTED':
            status, action, conf = 'NO_CHANGE', 'none', 'HIGH'
            why = r['why'] + ' - not wine evidence, so no estate is due'
        else:
            status, action, conf = 'INSUFFICIENT_EVIDENCE', 'none', 'LOW'
            why = r['why']
        rows.append({
            'artifact': r['artifact'],
            'kind': 'estate_attribution',
            'current': {'estate': None, 'wine': r['manifest'].get('wine'),
                        'vintage': r['manifest'].get('vintage')},
            'observed': {'estate_from_folder': fold,
                         'estate_from_document':
                             r['evidence']['document_estate'],
                         'vintage': r['evidence']['document_vintage'],
                         'document_type':
                             r['evidence']['document_type']},
            'proposed': ({'estate': fold, 'wine': None,
                          'vintage': r['proposed'].get('vintage')}
                         if status == 'PROPOSED_CORRECTION' else None),
            'status': status, 'action': action, 'confidence': conf,
            'why': why,
            'evidence': r['evidence']['notes'],
            'classified_estate': r.get('classified_estate'),
            'v': TOOL_VERSION, 'at': datetime.date.today().isoformat(),
            'commit': commit(),
        })

    # ------------------------------- manifest years the guard contradicts
    # A document the reader refuses as WRONG_VINTAGE for the very year
    # the manifest assigns it is the manifest disagreeing with the
    # document about the year.
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    for s in man.get('sheets', []):
        fn, my = s.get('file'), s.get('year')
        if not fn or not my:
            continue
        if a.estate and s.get('estate') != a.estate:
            continue
        try:
            my = int(my)
        except Exception:
            continue
        if my in vintage_refused.get(fn, ()) and not accepted.get(fn):
            rows.append({
                'artifact': fn,
                'kind': 'manifest_vintage',
                'current': {'estate': s.get('estate'),
                            'wine': s.get('wine'), 'vintage': my},
                'observed': {'vintage': 'the document contradicts %d'
                                        % my},
                'proposed': None,
                'status': 'PROPOSED_REVIEW',
                'action': 'none - the right year needs a person',
                'confidence': 'MEDIUM',
                'why': ('the reader refuses this document for the very '
                        'vintage the manifest assigns it, and accepts '
                        'it for no wine or year'),
                'evidence': ['whose_sheet returned WRONG_VINTAGE for '
                             'year=%d' % my],
                'v': TOOL_VERSION,
                'at': datetime.date.today().isoformat(),
                'commit': commit(),
            })

    byst = collections.Counter(r['status'] for r in rows)
    bykind = collections.Counter((r['kind'], r['status']) for r in rows)
    print('%d proposal(s)\n' % len(rows))
    print('%-26s %6s' % ('STATUS', 'n'))
    print('-' * 40)
    for k, c in byst.most_common():
        print('   %-24s %6d' % (k, c))
    print()
    print('%-22s %-24s %s' % ('KIND', 'STATUS', 'n'))
    print('-' * 56)
    for (k, st), c in sorted(bykind.items()):
        print('   %-20s %-24s %5d' % (k, st, c))

    print()
    print('PROPOSED_CORRECTION, by what it would change')
    print('-' * 56)
    corr = [r for r in rows if r['status'] == 'PROPOSED_CORRECTION']
    for k, c in collections.Counter(r['kind'] for r in corr).most_common():
        print('   %-26s %5d' % (k, c))
    print()
    for r in corr[:a.limit]:
        print('   %-44s %s' % (r['artifact'].split('/')[-1][:44],
                               r['kind']))
        print('      %s' % r['action'][:68])
        print('      %s' % r['why'][:68])

    if a.write:
        with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
            f.write(json.dumps({
                '_': 'Dry-run proposals. Nothing here has been applied; '
                     'this tool cannot apply anything. A proposal is '
                     'not a correction until it has been applied and '
                     'verified.',
                'tool_version': TOOL_VERSION, 'rows': len(rows),
                'statuses': dict(byst),
            }, ensure_ascii=False, sort_keys=True) + '\n')
            for r in sorted(rows, key=lambda x: (x['kind'],
                                                 x['artifact'])):
                f.write(json.dumps(r, ensure_ascii=False,
                                   sort_keys=True) + '\n')
        print('\nwritten to data/proposals.jsonl (%d)' % len(rows))
    else:
        print('\nnothing written; pass --write')


if __name__ == '__main__':
    main()
