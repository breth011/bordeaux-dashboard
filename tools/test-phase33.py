# -*- coding: utf-8 -*-
"""Phase 3.3: the discovery harvest, checked.

    python tools/test-phase33.py

Two halves.

  BEHAVIOUR  A local web server serves a small crafted site (two estates on
             one host, a robots.txt that disallows a folder, a PDF published
             at two paths, a PDF that is later replaced, a broken PDF, French
             and English pages). The real crawler, extractor and report run
             against it into a temporary store, twice, and the properties the
             brief asks for are checked on what they wrote. Nothing in the
             repository is touched.
  HARVEST    The committed discovery outputs are checked for consistency, a
             sample of artifacts is re-extracted and compared, and the scope
             invariants (canonical, evidence, proposals) are verified.
"""
import functools
import hashlib
import http.server
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import discover as D
import discover_extract as X
import discover_report as REP
import sheetreader as sr
import evidence as EV
import evidence_store as ST
import historical_m2_scope as H  # noqa: E402

BASE = 'a112623'
CANON = ('data/fiches.js', 'data/field-src.js', 'data/cuvee-src.js', 'data/chateaux.js',
         'data/cuvees.js', 'data/sources.json', 'data/proposals.jsonl',
         'data/attribution-candidates.jsonl')
fails = []
checks = 0


def says(name, ok, shown=''):
    global checks
    checks += 1
    if not ok:
        fails.append(name)
    print('%-4s %-62s %s' % ('ok' if ok else 'FAIL', name[:62], shown))


def git(args):
    return subprocess.check_output(['git'] + args, cwd=ROOT, stderr=subprocess.DEVNULL).decode('utf-8')


def jl(p):
    return [json.loads(l) for l in io.open(p, encoding='utf-8') if l.strip()] if os.path.exists(p) else []


def pdf_bytes(text):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in text.split('\n'):
        page.insert_text((72, y), line)
        y += 16
    return doc.tobytes()


# ======================================================== BEHAVIOUR
tmp = tempfile.mkdtemp(prefix='p33-')
site = os.path.join(tmp, 'site')
store = os.path.join(tmp, 'store') + '/'
out = os.path.join(tmp, 'out') + '/'
for d in ('docs', 'copy', 'private', 'en'):
    os.makedirs(os.path.join(site, d))


def write(rel, data, mtime=None):
    p = os.path.join(site, rel)
    with open(p, 'wb') as f:
        f.write(data if isinstance(data, bytes) else data.encode('utf-8'))
    if mtime:
        os.utime(p, (mtime, mtime))


T0 = time.time() - 3600
write('robots.txt', 'User-agent: *\nDisallow: /private/\n', T0)
write('index.html', """<!doctype html><html lang="fr"><head><title>Château Testé - Vins</title>
<meta property="og:title" content="Château Testé"></head><body>
<h1>Château Testé</h1><h2>Le vignoble</h2>
<p>Superficie : 12 hectares</p><p>Sols : graves et argiles sur calcaire</p>
<table><tr><td>pH</td><td>3,6</td></tr><tr><td>Rendement</td><td>38 hl/ha</td></tr></table>
<p>Le second vin, Les Murets de Testé, est issu des jeunes vignes. Le domaine a été acquis en 1998
par la famille Exemple. Le millésime 2019 fut précoce. Classé en 1855.</p>
<p>Nos voisins du Château Autre partagent ce site.</p>
<a href="/docs/fiche-2019.pdf">Fiche technique 2019</a> <a href="/copy/fiche-2019.pdf">Copie</a>
<a href="/docs/broken.pdf">Fiche cassée</a> <a href="/private/secret.html">Privé</a>
<a href="/en/index.html">English</a> <img src="/photo.jpg" alt="Le chai" title="chai">
</body></html>""", T0)
write('en/index.html', """<!doctype html><html lang="en"><head><title>Chateau Teste - Wines</title></head>
<body><h1>Château Testé</h1><p>Vineyard area: 12 hectares</p>
<p>The second wine of the estate is Les Murets de Testé, made from the young vines and the
wine that is the estate's pride, which is the grand vin of the property.</p></body></html>""", T0)
FICHE_A = pdf_bytes('FICHE TECHNIQUE 2019\nChateau Teste\nAlcool : 13,5 % vol\nAssemblage : 80% Merlot')
write('docs/fiche-2019.pdf', FICHE_A, T0)
write('copy/fiche-2019.pdf', FICHE_A, T0)
write('docs/broken.pdf', b'%PDF-1.4\nthis is not a pdf at all\n', T0)
write('private/secret.html', '<html><body>secret</body></html>', T0)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
                                      functools.partial(Quiet, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
HOST = '127.0.0.1'
target = {'domain': HOST, 'seeds': ['http://%s:%d/' % (HOST, port)], 'estates': ['u-teste', 'u-autre']}
targets = {'counts': {}, 'domains': [target], 'estates': [
    {'universe_id': 'u-teste', 'name': 'Château Testé', 'canonical_names': ['Château Testé'],
     'site': target['seeds'][0], 'systems': ['test'], 'canonical_ids': ['teste'], 'status': 'TARGET'},
    {'universe_id': 'u-autre', 'name': 'Château Autre', 'canonical_names': ['Château Autre'],
     'site': target['seeds'][0], 'systems': ['test'], 'canonical_ids': ['autre'], 'status': 'TARGET'}]}
os.makedirs(out, exist_ok=True)
io.open(out + 'targets.json', 'w', encoding='utf-8').write(json.dumps(targets))
S = D.Store(store=store, out=out)
FAST = dict(D.BUDGET, seconds=120)


def run_all():
    st = D.crawl_site(S, target, budget=FAST, min_delay=0.0)
    subprocess.check_call([sys.executable, '-I', ROOT + 'tools/discover_extract.py', '--store',
                           store, '--out', out, '--workers', '2'], stdout=subprocess.DEVNULL)
    REP.main(out, store)
    return st


def snapshot():
    files = {}
    for dp, dn, fn in os.walk(out):
        for f in fn:
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, out).replace(os.sep, '/')
            if rel.startswith('locations/') or rel in ('profiles.json', 'inventory.json',
                                                         'failures.jsonl', 'coverage.json',
                                                         'targets.json'):
                continue
            files[rel] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    return files


def blobs():
    return {f for dp, dn, fn in os.walk(store + 'blobs') for f in fn}


try:
    st1 = run_all()
    rows1 = S.locations(HOST)
    arts = {a['sha256']: a for a in jl(out + 'artifacts.jsonl')}
    shaA = hashlib.sha256(FICHE_A).hexdigest()
    says('1 raw artifacts are preserved, byte for byte, by content address',
         S.has(shaA) and S.read(shaA) == FICHE_A)
    says('2 artifact identity is the content hash of the raw bytes (stored raw or gzipped)',
         all(hashlib.sha256(S.read(a)).hexdigest() == a for a in arts)
         and any(S.blob_path(a).endswith('.gz') for a in arts))
    locA = {r['url'] for r in rows1 if r.get('sha256') == shaA}
    says('4 identical bytes at two paths: one artifact, two locations',
         len(locA) == 2 and arts[shaA]['locations'] == 2)
    html_shas = [s for s, a in arts.items() if a['media'] == 'html']
    says('5 raw HTML stays available beside its extraction',
         html_shas and all(S.has(s) and os.path.exists(store + 'extracted/%s.json' % s) for s in html_shas))
    pdfs = [s for s, a in arts.items() if a['media'] == 'pdf' and a['status'] == 'EXTRACTED']
    says('6 original PDFs stay available beside their text', pdfs and all(S.has(s) for s in pdfs))
    bad = [s for s, a in arts.items() if a['status'] == 'EXTRACTION_FAILED']
    says('7 an extraction failure is recorded and the bytes are kept',
         len(bad) == 1 and S.has(bad[0]) and arts[bad[0]]['error'])
    says('18 a robots-disallowed URL is represented, not fetched',
         any(r['kind'] == 'ROBOTS_DISALLOW' and '/private/' in r['url'] for r in rows1)
         and not any(r.get('kind') == 'OK' and '/private/' in r['url'] for r in rows1))
    att = {a['artifact']: a for a in jl(out + 'attribution.jsonl')}
    idx = [s for s in html_shas if '"lang_declared": "fr"' in open(store + 'extracted/%s.json' % s,
                                                                    encoding='utf-8').read()][0]
    cands = {c['estate']: c for c in att[idx]['candidates']}
    says('8 attribution is a separate record of candidates, not the artifact\'s identity',
         set(arts) == set(att) and all(a['status'] == 'CANDIDATES_ONLY' for a in att.values())
         and 'estate' not in arts[idx])
    says('9 crawl context is only a weak candidate; a named estate is graded apart',
         any(e['kind'] == 'CRAWL_CONTEXT' and e['weight'] == 'WEAK' for e in cands['u-autre']['evidence'])
         and any(e['kind'].startswith('NAMED_IN_') for e in cands['u-teste']['evidence']))
    prof = json.load(io.open(out + 'profiles.json', encoding='utf-8'))[HOST]
    says('16 a shared source serves several estates (recorded as INFERRED)',
         prof['serves_several_target_estates']['value'] is True
         and prof['serves_several_target_estates']['basis'].startswith('INFERRED'))
    says('15 profiles mark each fact OBSERVED, INFERRED or UNKNOWN',
         all(v['basis'].split()[0] in ('OBSERVED', 'INFERRED', 'UNKNOWN') for v in prof.values())
         and prof['robots']['basis'] == 'OBSERVED')
    obs = [o for f in os.listdir(out + 'observations') for o in jl(out + 'observations/' + f)]
    says('14 raw labels and values are kept verbatim',
         any(o['label'] == 'Superficie' and o['value'] == '12 hectares' for o in obs)
         and any(o['label'] == 'Sols' and o['value'] == 'graves et argiles sur calcaire' for o in obs)
         and any(o['label'] == 'pH' and o['value'] == '3,6' for o in obs))
    says('...with any normalisation beside the raw value, never instead',
         any(o['label'] == 'Superficie' and o['normalized'] == [{'number': 12.0, 'unit': 'hectares'}]
             and o['value'] == '12 hectares' for o in obs))
    langs = {o['lang'] for o in obs}
    says('13 language is kept per artifact and observation (fr and en)', {'fr', 'en'} <= langs, str(langs))
    roles = jl(out + 'roles.jsonl')
    says('12 role wording is recorded as quoted evidence, not as a role',
         any(r['wording'].lower() == 'second vin' and 'Les Murets de Testé' in r['context'] for r in roles)
         and any(r['wording'].lower() == 'second wine' for r in roles))
    years = jl(store + 'derived/years.jsonl')
    vc = {v['artifact']: v for v in jl(out + 'vintage-candidates.jsonl')}
    kinds = {(y['year'], y['kind']) for y in years}
    says('17 years are kept by kind: harvest, ownership, classification, URL',
         (2019, 'HARVEST_OR_VINTAGE') in kinds and (1998, 'OWNERSHIP') in kinds
         and (1855, 'CLASSIFICATION') in kinds and (2019, 'URL_OR_FILENAME') in kinds)
    says('...and the committed vintage candidates separate URL years from prose by kind',
         any(2019 in v['url_years'] for v in vc.values())
         and any(v['prose_by_kind'].get('OWNERSHIP') for v in vc.values()))
    wn = {w['key']: w for w in jl(out + 'wines.jsonl')}
    says('10 a wine name not in canonical data is recorded UNRESOLVED',
         any('murets de teste' in k and w['status'] == 'UNRESOLVED' for k, w in wn.items()))
    blobs1 = blobs()
    snap1 = snapshot()
    # The same site again, unchanged: nothing new.
    st2 = run_all()
    says('20 rerunning unchanged inputs adds no artifact and changes no output',
         blobs() == blobs1 and snapshot() == snap1)
    rows2 = S.locations(HOST)[len(rows1):]
    says('19 the crawl resumes from saved state (validators reused: 304s)',
         any(r['kind'] == 'NOT_MODIFIED' for r in rows2) and S.load_state(HOST)['last_sha'])
    # Replace one document: same path, new bytes.
    FICHE_B = pdf_bytes('FICHE TECHNIQUE 2019 (revised)\nAlcool : 14 % vol')
    write('docs/fiche-2019.pdf', FICHE_B, time.time() + 60)
    run_all()
    shaB = hashlib.sha256(FICHE_B).hexdigest()
    says('3 same path, different bytes: two artifacts, the old one kept',
         S.has(shaA) and S.has(shaB) and shaA != shaB
         and any(r.get('sha256') == shaB and r.get('change') == 'CHANGED' for r in S.locations(HOST)))
    arts2 = {a['sha256'] for a in jl(out + 'artifacts.jsonl')}
    says('...and both stay in the artifact index', {shaA, shaB} <= arts2)
finally:
    srv.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

# ======================================================== HARVEST
OUT = ROOT + 'data/discovery/'
log = [l.split(' ', 1) for l in git(['log', '--format=%H %s', BASE + '..HEAD']).splitlines()]
mine = [h for h, s in log if s.startswith('Phase 3.3')]
changed = set()
for h in mine:
    changed |= set(git(['diff-tree', '--no-commit-id', '--name-only', '-r', h]).split())
if not mine:
    changed |= set(l[3:] for l in git(['status', '--porcelain=v1', '--untracked-files=all']).splitlines())
OWN_RE = re.compile(r'^(data/discovery/|tools/discover(_extract|_report)?\.py$|tools/test-phase33\.py$|'
                    r'docs/PHASE-3\.3-DISCOVERY-FINDINGS\.md$)')
says('Phase 3.3 changed only its discovery outputs, tools, test and findings',
     all(OWN_RE.match(f) for f in changed), ', '.join(f for f in sorted(changed) if not OWN_RE.match(f))[:40])
says('21 no canonical file, manifest or proposal changed since a112623',
     not git(['diff', '--name-only', BASE, '--'] + list(CANON)).strip())
says('22 v1-v5 evidence unchanged and verifying; 23 no v6',
     H.evidence_changes_are_m36b_only(BASE)
     and ST.verify() == [] and H.evidence_rows_before_m36b() == 177127
     and H.evidence_versions_before_m36b() == [1, 2, 3, 4, 5]
     and not any(re.match(r'(decisions|provenance-failures)-v6', f) and f != 'decisions-v6.jsonl'
                 for f in os.listdir(ROOT + 'data/evidence')))
says('the reader is still 7e8cfed1c24e', EV.reader_fingerprint() == '7e8cfed1c24e')
Es = sr.estates(ROOT)
SJ = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))['sheets']
says('24 no Phase 2 proposal applied: Terrasses, Echo (50 as Blanc), Murets',
     Es['stem-chateau-tour-saint-christophe']['second'] is None
     and sum(1 for r in SJ if r['estate'] == 'lynch-bages' and 'echo' in r['file'].lower()
             and r['wine'] == 'Blanc de Lynch-Bages') == 50
     and Es['caillou']['second'] == 'Les Erables de Caillou')
says('10-12 discovery never writes wine, vintage or role data (canonical files untouched)',
     not git(['status', '--porcelain', '--', 'data/cuvees.js', 'data/fiches.js', 'data/chateaux.js'
              ]).strip())
inv = json.load(io.open(OUT + 'inventory.json', encoding='utf-8'))
says('the inventory exists and says it is not a complete census',
     inv['completeness'].startswith('NOT COMPLETE') and inv['unique_artifacts'] > 0)
says('every target estate has a coverage status',
     len(json.load(io.open(OUT + 'coverage.json', encoding='utf-8')))
     == json.load(io.open(OUT + 'targets.json', encoding='utf-8'))['counts']['estates'])
arts = jl(OUT + 'artifacts.jsonl')
loc_shas = set()
for f in os.listdir(OUT + 'locations'):
    for r in jl(OUT + 'locations/' + f):
        if r.get('kind') == 'OK' and r.get('sha256'):
            loc_shas.add(r['sha256'])
says('every retrieved location has an artifact, and every artifact a location',
     loc_shas == {a['sha256'] for a in arts}, '%d artifacts' % len(arts))
blocked = [f for f in jl(OUT + 'failures.jsonl') if f['kind'].startswith(('ROBOTS', 'BLOCKED'))]
says('18 blocked sources are represented in the failures and profiles',
     blocked and all(f['domain'] in json.load(io.open(OUT + 'profiles.json', encoding='utf-8'))
                     for f in blocked[:50]))
if os.path.isdir(ROOT + 'sources/discovery/blobs'):
    random.seed(33)
    sample = random.sample(arts, min(25, len(arts)))
    RS = D.Store()
    missing = [a['sha256'] for a in sample
               if not RS.has(a['sha256']) or hashlib.sha256(RS.read(a['sha256'])).hexdigest() != a['sha256']]
    says('1 a sample of committed artifacts has its exact raw bytes in the store', not missing)
    shards = {}
    diff = []
    # Re-extract the sample with the URLs the index used, compare observations.
    locmap = {}
    for f in os.listdir(OUT + 'locations'):
        for r in jl(OUT + 'locations/' + f):
            if r.get('kind') in ('OK', 'NOT_MODIFIED') and r.get('sha256'):
                L = locmap.setdefault(r['sha256'], [set(), set()])
                if r.get('content_type'):
                    L[0].add(r['content_type'])
                L[1].add(r.get('final_url') or r['url'])
    for a in sample:
        L = locmap[a['sha256']]
        res = X.extract_one((a['sha256'], sorted(L[0]), sorted(L[1]), ROOT + 'sources/discovery/'))
        sh = shards.setdefault(a['sha256'][:2], jl(OUT + 'observations/%s.jsonl' % a['sha256'][:2]))
        mine = sorted((o for o in sh if o['artifact'] == a['sha256']),
                      key=lambda r: (r['artifact'], r['locus'], r['label']))
        theirs = sorted(res['observations'], key=lambda r: (r['artifact'], r['locus'], r['label']))
        if json.dumps(mine, sort_keys=True) != json.dumps(theirs, sort_keys=True):
            diff.append(a['sha256'][:10])
    says('25 the committed observations are reproduced from the stored bytes (sample of 25)',
         not diff, ', '.join(diff[:3]))
else:
    print('MISSING  sources/discovery (byte-level checks)')

print('\n%d check(s), %s' % (checks, 'all pass' if not fails else '%d FAILED: %s'
                                % (len(fails), '; '.join(fails[:4]))))
sys.exit(1 if fails else 0)
