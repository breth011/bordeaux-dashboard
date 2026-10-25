# -*- coding: utf-8 -*-
"""Phase 3.3: the discovery inventory, failures, source profiles and label
catalogue, built from what the crawl and the extractor recorded.

    python -I tools/discover_report.py

Writes data/discovery/inventory.json, failures.jsonl, profiles.json,
labels.json and coverage.json. Reads only data/discovery/ and the local
crawl state (sources/discovery/state/, for robots and crawl outcomes).

Every profile fact says how it is known:
  OBSERVED   seen by this crawl (a response, a robots file, a count)
  INFERRED   derived (a domain serving several target estates, from
             websites.js plus names seen on its pages)
  UNKNOWN    not established
"""
import collections
import io
import json
import os
import re
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
OUT = ROOT + 'data/discovery/'
STORE = ROOT + 'sources/discovery/'
FAIL_KINDS = {'HTTP_ERROR', 'TIMEOUT', 'NETWORK_FAILURE', 'TLS_FAILURE', 'BLOCKED_CHALLENGE',
              'AUTH_REQUIRED', 'RATE_LIMITED', 'TOO_LARGE', 'MALFORMED', 'BAD_REDIRECT',
              'TOO_MANY_REDIRECTS', 'ROBOTS_DISALLOW', 'ROBOTS_DISALLOW_SITE',
              'ROBOTS_DISALLOW_REDIRECT', 'OFFSITE_REDIRECT', 'CRAWL_DELAY_TOO_LONG',
              'CRAWLER_CRASH'}


def jl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in io.open(p, encoding='utf-8') if l.strip()]


def key(s):
    import unicodedata
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return ' '.join(re.sub(r'[^a-z0-9一-鿿]+', ' ', s).split())


def main(out=OUT, store=STORE):
    T = json.load(io.open(out + 'targets.json', encoding='utf-8'))
    arts = {a['sha256']: a for a in jl(out + 'artifacts.jsonl')}
    attrib = {a['artifact']: a for a in jl(out + 'attribution.jsonl')}
    wines = jl(out + 'wines.jsonl')
    roles = jl(out + 'roles.jsonl')
    years = jl(store + 'derived/years.jsonl')      # local: the mentions with their context
    obs = []
    od = out + 'observations/'
    for f in sorted(os.listdir(od)) if os.path.isdir(od) else []:
        obs += jl(od + f)
    locs = {}
    for f in sorted(os.listdir(out + 'locations')):
        locs[f[:-6]] = jl(out + 'locations/' + f)

    failures = []
    for dom, rows in sorted(locs.items()):
        for r in rows:
            if r.get('kind') in FAIL_KINDS:
                failures.append({'domain': dom, 'url': r['url'], 'kind': r['kind'],
                                 'status': r.get('status'), 'error': r.get('error'), 'at': r.get('at')})
    with io.open(out + 'failures.jsonl', 'w', encoding='utf-8', newline='\n') as f:
        for r in failures:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')

    # ------------------------------------------------------------ profiles
    est_by_dom = {d['domain']: d['estates'] for d in T['domains']}
    names_seen = collections.defaultdict(collections.Counter)
    for sha, a in attrib.items():
        for c in a['candidates']:
            if any(e['kind'] in ('NAMED_IN_TITLE', 'NAMED_IN_FILENAME', 'NAMED_IN_HEADING')
                   for e in c['evidence']):
                for d in arts.get(sha, {}).get('domains', []):
                    names_seen[d][c['estate']] += 1
    profiles = {}
    for d in T['domains']:
        dom = d['domain']
        rows = locs.get(dom, [])
        st = None
        sp = store + 'state/%s.json' % dom
        if os.path.exists(sp):
            st = json.load(io.open(sp, encoding='utf-8'))
        ok = [r for r in rows if r.get('kind') == 'OK']
        shas = {r['sha256'] for r in ok if r.get('sha256')}
        langs = collections.Counter(arts[s]['lang_detected'] for s in shas
                                    if s in arts and arts[s].get('lang_detected'))
        paths = collections.Counter()
        docdirs = collections.Counter()
        exts = collections.Counter()
        for r in ok:
            u = urllib.parse.urlsplit(r.get('final_url') or r['url'])
            seg = [s for s in u.path.split('/') if s]
            paths['/' + seg[0] + '/' if seg else '/'] += 1
            m = re.search(r'\.([a-z0-9]{2,5})$', u.path.lower())
            if m and arts.get(r.get('sha256'), {}).get('media') not in ('html', 'sitemap', None):
                exts[m.group(1)] += 1
                docdirs['/'.join(u.path.split('/')[:-1])[:60] or '/'] += 1
        via = collections.Counter(r.get('discovered_via') for r in ok)
        fails = collections.Counter(r['kind'] for r in rows if r.get('kind') in FAIL_KINDS)
        named = names_seen.get(dom, collections.Counter())
        targets = est_by_dom.get(dom, [])
        others = [u for u, n in named.items() if u not in targets and n >= 2]
        rob = (st or {}).get('robots') or {}
        prof = {
            'domain': {'value': dom, 'basis': 'OBSERVED'},
            'target_estates': {'value': targets,
                               'basis': 'INFERRED (websites.js gives this site for these estates)'},
            'estates_named_in_titles': {'value': dict(named.most_common(15)), 'basis': 'OBSERVED'},
            'serves_several_target_estates': {
                'value': (len(targets) > 1) or (len([u for u in named if u in targets]) > 1) or None,
                'basis': 'INFERRED' if len(targets) > 1 or named else 'UNKNOWN'},
            'names_other_universe_estates': {'value': others[:20],
                                             'basis': 'OBSERVED' if others else 'UNKNOWN'},
            'robots': {'value': {k: rob.get(k) for k in ('status', 'kind', 'ai_refused', 'ai_input_no',
                                                         'delay', 'sitemaps', 'sha256', 'at')},
                       'basis': 'OBSERVED' if rob else 'UNKNOWN'},
            'moved_to': {'value': (st or {}).get('moved') or [],
                         'basis': 'OBSERVED' if st else 'UNKNOWN'},
            'languages': {'value': dict(langs.most_common()), 'basis': 'OBSERVED' if langs else 'UNKNOWN'},
            'sitemap': {'value': via.get('SITEMAP', 0) > 0, 'basis': 'OBSERVED' if st else 'UNKNOWN'},
            'wordpress_media_listing': {'value': via.get('WP_MEDIA', 0) > 0,
                                        'basis': 'OBSERVED' if st else 'UNKNOWN'},
            'discovery_methods': {'value': dict(via), 'basis': 'OBSERVED'},
            'url_patterns': {'value': dict(paths.most_common(12)), 'basis': 'OBSERVED'},
            'document_patterns': {'value': {'extensions': dict(exts.most_common()),
                                            'folders': dict(docdirs.most_common(8))},
                                  'basis': 'OBSERVED'},
            'retrievals': {'value': {'ok': len(ok), 'unique_artifacts': len(shas),
                                     'requests_logged': len(rows)}, 'basis': 'OBSERVED'},
            'failures': {'value': dict(fails), 'basis': 'OBSERVED'},
            'crawl': {'value': {k: (st or {}).get(k) for k in ('started', 'finished', 'stopped',
                                                                'counts', 'scraper')},
                      'basis': 'OBSERVED' if st else 'UNKNOWN'},
            'changes': {'value': dict(collections.Counter(r.get('change') for r in ok if r.get('change'))),
                        'basis': 'OBSERVED'},
        }
        profiles[dom] = prof
    io.open(out + 'profiles.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(profiles, ensure_ascii=False, indent=1, sort_keys=True) + '\n')

    # ------------------------------------------------------------ coverage
    coverage = []
    for e in T['estates']:
        if not e['site']:
            coverage.append({'estate': e['universe_id'], 'name': e['name'], 'status': 'NO_KNOWN_SITE',
                             'domain': None})
            continue
        dom = next((d['domain'] for d in T['domains'] if e['universe_id'] in d['estates']), None)
        p = profiles.get(dom, {})
        r = (p.get('retrievals') or {}).get('value', {})
        stopped = ((p.get('crawl') or {}).get('value') or {}).get('stopped')
        fails = (p.get('failures') or {}).get('value', {})
        texty = sum(1 for r2 in locs.get(dom, []) if r2.get('kind') == 'OK'
                    and arts.get(r2.get('sha256'), {}).get('text_chars', 0) > 200)
        crawled = ((p.get('crawl') or {}).get('value') or {}).get('started')
        if not crawled and not r.get('ok'):
            status = 'NOT_CRAWLED'
        elif stopped in ('ROBOTS_DISALLOW_SITE', 'CRAWL_DELAY_TOO_LONG'):
            status = 'BLOCKED_BY_POLICY'
        elif not r.get('ok'):
            status = 'UNREACHABLE'
        elif texty < 3 or (fails and r.get('ok', 0) < 5):
            status = 'PARTIAL'
        else:
            status = 'REACHED'
        coverage.append({'estate': e['universe_id'], 'name': e['name'], 'domain': dom,
                         'status': status, 'stopped': stopped, 'ok': r.get('ok', 0),
                         'text_artifacts': texty, 'failures': fails})
    io.open(out + 'coverage.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(coverage, ensure_ascii=False, indent=1) + '\n')

    # ------------------------------------------------------------ labels
    lab = {}
    for o in obs:
        k = key(o['label'])
        if not k:
            continue
        L = lab.setdefault(k, {'count': 0, 'forms': collections.Counter(), 'langs': collections.Counter(),
                               'methods': collections.Counter(), 'artifacts': set(),
                               'category': collections.Counter()})
        L['count'] += 1
        L['forms'][o['label']] += 1
        L['langs'][o.get('lang') or '?'] += 1
        L['methods'][o['method']] += 1
        L['artifacts'].add(o['artifact'])
        for c in o.get('category') or ['UNCATEGORISED']:
            L['category'][c] += 1
    adom = {s: a.get('domains', []) for s, a in arts.items()}
    labels = []
    for k, L in lab.items():
        doms = set()
        for s in L['artifacts']:
            doms |= set(adom.get(s, []))
        labels.append({'key': k, 'count': L['count'], 'artifacts': len(L['artifacts']),
                       'domains': len(doms), 'forms': [f for f, _ in L['forms'].most_common(5)],
                       'langs': dict(L['langs']), 'methods': dict(L['methods']),
                       'category_guess': [c for c, _ in L['category'].most_common(3)]})
    labels.sort(key=lambda r: (-r['domains'], -r['count'], r['key']))
    io.open(out + 'labels.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(labels, ensure_ascii=False, indent=1) + '\n')

    # ------------------------------------------------------------ inventory
    allrows = [r for rows in locs.values() for r in rows]
    okrows = [r for r in allrows if r.get('kind') == 'OK']
    media = collections.Counter(a['media'] for a in arts.values())
    by_path = collections.defaultdict(set)
    for r in okrows:
        if r.get('sha256'):
            by_path[r.get('final_url') or r['url']].add(r['sha256'])
    by_sha = collections.defaultdict(set)
    for r in okrows:
        if r.get('sha256'):
            by_sha[r['sha256']].add(r.get('final_url') or r['url'])
    status = collections.Counter(c['status'] for c in coverage)
    inv = {
        'phase': '3.3', 'built_by': 'tools/discover_report.py',
        'completeness': 'NOT COMPLETE: each site was crawled within a budget (pages, documents, '
                        'requests, time); a site whose frontier was not exhausted is listed with '
                        'stopped=BUDGET. Counts are of what was retrieved, not of what exists.',
        'targets': T['counts'],
        'estates': dict(status),
        'domains': {'targets': len(T['domains']), 'crawled': sum(1 for d in profiles.values()
                                                                if d['crawl']['value'].get('finished')),
                    'stopped': dict(collections.Counter(str(d['crawl']['value'].get('stopped')
                                                            or 'NOT_CRAWLED')
                                                        for d in profiles.values())),
                    'ai_refused_in_robots': sum(1 for d in profiles.values()
                                                if (d['robots']['value'] or {}).get('ai_refused')),
                    'moved': sum(1 for d in profiles.values() if d['moved_to']['value'])},
        'requests_logged': len(allrows),
        'retrieved_ok': len(okrows),
        'pages_retrieved': sum(1 for r in okrows if arts.get(r.get('sha256'), {}).get('media') == 'html'),
        'documents_retrieved': sum(1 for r in okrows if arts.get(r.get('sha256'), {}).get('media')
                                   in ('pdf', 'office', 'image', 'text', 'json', 'xml', 'other')),
        'unique_artifacts': len(arts),
        'artifacts_by_media': dict(media),
        'artifacts_at_several_urls': sum(1 for v in by_sha.values() if len(v) > 1),
        'urls_with_several_versions': sum(1 for v in by_path.values() if len(v) > 1),
        'languages': dict(collections.Counter(a.get('lang_detected') or 'undetected'
                                              for a in arts.values() if a['media'] in ('html', 'pdf', 'office', 'text'))),
        'extraction': dict(collections.Counter(str(a['status']) for a in arts.values())),
        'ocr': dict(collections.Counter(str(a.get('ocr') or 'NONE') for a in arts.values()
                                        if a['media'] == 'pdf')),
        'observations': len(obs),
        'observation_methods': dict(collections.Counter(o['method'] for o in obs)),
        'distinct_labels': len(labels),
        'labels_on_5_or_more_domains': sum(1 for l in labels if l['domains'] >= 5),
        'year_mentions': dict(collections.Counter(y['kind'] for y in years)),
        'role_statements': len(roles),
        'role_wordings': dict(collections.Counter(r['wording'].lower() for r in roles).most_common(30)),
        'wine_name_candidates': len(wines),
        'wine_name_candidates_not_in_canonical': sum(1 for w in wines if not w['known_in_canonical']),
        'multi_estate_artifacts': sum(1 for a in attrib.values() if a['multi_estate']),
        'failures': dict(collections.Counter(f['kind'] for f in failures)),
        'changed_on_recrawl': sum(1 for r in okrows if r.get('change') == 'CHANGED'),
    }
    io.open(out + 'inventory.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(inv, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: inv[k] for k in ('estates', 'unique_artifacts', 'observations',
                                          'distinct_labels', 'failures')}, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) > 2:
        main(sys.argv[1].rstrip('/') + '/', sys.argv[2].rstrip('/') + '/')
    else:
        main()
