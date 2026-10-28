"""The estate-supplied acquisition mode (tools/apply-artifact-registration-manifest.py, ESTATE_SUPPLIED;
tools/record-estate-supplied-acquisition.py; data/audit/estate-supplied-acquisitions.jsonl).

    python tools/test-estate-supplied-acquisition.py

Read-only for the repository. Both production files stay empty. Everything supplied here is synthetic: a generated
test PDF in a fabricated message from a confirmed first-party estate other than any V2 target (Château Calon-Ségur,
m37:sr_00014:es_00220), recorded into a temporary audit and a temporary sources/ root, and registered only on an
isolated copy of the model (BDX_MODEL_DIR, in a subprocess). The HTTP mode is checked against M3.8's real records.
"""
import copy
import email.message
import email.utils
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402
import model_schema as S  # noqa: E402

REG = L.ROOT + 'tools/apply-artifact-registration-manifest.py'
REC = L.ROOT + 'tools/record-estate-supplied-acquisition.py'
M38 = 'data/audit/m3.8-acquisition-pilot.jsonl'
REL, HOST, ESTATE, SOURCE = 'm37:sr_00014:es_00220', 'calon-segur.fr', 'es_00220', 'sr_00014'
OTHER_REL = 'm37:sr_00004:es_00035'                 # confirmed, but batailley.com's
PROBABLE_REL = 'm37:sr_00262:es_00281'              # PROBABLE_FIRST_PARTY: not confirmed
PDF = b'%PDF-1.4\n% synthetic test document for tools/test-estate-supplied-acquisition.py\n%%EOF\n'
NAME = 'Fiche technique test 2099.pdf'
CHECKS, TMP, BASE = [], [], []


def check(f):
    CHECKS.append(f)
    return f


def load(path, name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RA = load(REG, 'apply_artifact_registration_manifest_st')
RC = load(REC, 'record_estate_supplied_acquisition_st')
CONF = RA.ACQUISITION_AUDITS[RA.SUPPLIED_AUDIT]
ITEMS = {r['n']: r for r in L.jsonl_lines(L.ROOT + M38) if r['record'] == 'item'}
VIEW = RA.View()


def git(*a):
    return subprocess.check_output(['git'] + list(a), cwd=L.ROOT)


def tmpdir(prefix):
    d = tempfile.mkdtemp(prefix=prefix)
    TMP.append(d)
    return d


def eml(path, frm='Estate <office@%s>' % HOST, date='Tue, 03 Mar 2026 10:15:00 +0100', name=NAME, data=PDF):
    m = email.message.EmailMessage()
    m['From'], m['To'], m['Date'], m['Subject'] = frm, 'someone@example.org', date, 'synthetic'
    m['Message-ID'] = email.utils.make_msgid(domain='example.org')
    m.set_content('synthetic body')
    m.add_attachment(data, maintype='application', subtype='pdf', filename=name)
    open(path, 'wb').write(bytes(m))
    return path


def recorded(**kw):
    """(root, audit, item): one synthetic file recorded into a temporary sources/ root and audit."""
    root = tmpdir('sup-root-') + os.sep
    audit = os.path.join(root, 'audit.jsonl')
    it = RC.record(eml(os.path.join(root, 'msg.eml'), **kw), kw.get('name', NAME), REL, audit, root)
    return root, audit, it


def reg_row(it, **kw):
    r = {'registration_id': 'arm_000001', 'sha256': it['sha256'], 'bytes': it['bytes'], 'media_type': it['content_type'],
         'held_path': it['held_path'], 'retrieval_method': CONF['retrieval_method'] % it['supply_channel'],
         'acquired_by': CONF['acquired_by'], 'origin': RA.SUPPLIED,
         'acquisition': {'audit': RA.SUPPLIED_AUDIT, 'row': 'sup:%d' % it['n']},
         'received_at': it['received_at'], 'original_filename': it['original_filename'],
         'supply_channel': it['supply_channel'], 'source': it['supplier']['source'],
         'source_relationship': it['supplier']['relationship']}
    r.update(kw)
    return r


class Supplied:
    """The registrar pointed at a temporary supplied audit and sources/ root; restored on exit."""

    def __init__(self, root, audit):
        self.root, self.audit = root, audit

    def __enter__(self):
        CONF['file'], RA.HELD_ROOT[0] = self.audit, self.root
        return self

    def __exit__(self, *a):
        CONF.pop('file', None)
        RA.HELD_ROOT[0] = L.ROOT


class Fixed(RA.Acquisitions):
    def __init__(self, extra):
        super().__init__()
        self.extra = extra

    def get(self, audit, row):
        return copy.deepcopy(self.extra[(audit, row)]) if (audit, row) in self.extra else super().get(audit, row)


def errors(rows, acq=None, view=None, read_bytes=True):
    return RA.validate_manifest(rows, view or VIEW, acq, None, read_bytes)[0]


def http_row(i, n, **kw):
    it = ITEMS[n]
    conf = RA.ACQUISITION_AUDITS[M38]
    r = {'registration_id': 'arm_%06d' % i, 'sha256': it['sha256'], 'bytes': it['bytes'],
         'media_type': it['content_type'], 'held_path': conf['held'] + it['sha256'], 'url': it['url'],
         'final_url': it['final_url'], 'http_status': it['status'], 'fetched_at': it['at'],
         'retrieval_method': conf['retrieval_method'], 'acquired_by': conf['acquired_by'], 'origin': RA.ORIGIN,
         'acquisition': {'audit': M38, 'row': 'm3.8:%d' % n}}
    if it.get('attributed_to'):
        r['source_relationship'] = it['attributed_to']
        r['source'] = it['attributed_to'].split(':')[1]
    r.update(kw)
    return r


def unheld():
    have = set(VIEW.index()['by_sha'])
    return sorted(n for n, it in ITEMS.items() if it['retrieval'] == 'OK' and it['sha256'] not in have
                  and os.path.exists(L.ROOT + 'sources/acquisition/m3.8/blobs/' + it['sha256']))


def one(e, needle):
    assert len(e) == 1 and needle in e[0], e


# ---------------------------------------------------------------- the recorder and a valid supplied row

@check
def s01_valid_supplied_record_and_registration():
    root, audit, it = recorded()
    assert it['received_at'] == '2026-03-03' and it['sender_domain'] == HOST and it['original_filename'] == NAME
    assert it['sha256'] == hashlib.sha256(PDF).hexdigest() and it['bytes'] == len(PDF) and it['content_type'] == 'application/pdf'
    assert it['supplier'] == {'estate': ESTATE, 'source': SOURCE, 'relationship': REL}
    assert it['held_path'] == 'sources/acquisition/supplied/%s/%s' % (it['sha256'], NAME)
    assert not {'url', 'final_url', 'status', 'at', 'http_status', 'fetched_at'} & set(it)
    receipt = json.load(open(os.path.join(root, it['receipt']['held']), encoding='utf-8'))
    assert 'office@' not in json.dumps(receipt) and 'synthetic body' not in json.dumps(receipt)
    assert RC.check(audit, root) == []
    with Supplied(root, audit):
        e, ok = RA.validate_manifest([reg_row(it)], VIEW)
        assert e == [], e
        plan = RA.plan_manifest(ok, VIEW)
        [p] = plan['rows']
        assert (p['action'], p['mode'], p['locator']) == ('CREATE', RA.SUPPLIED, {
            'kind': 'LOCAL_PATH', 'value': it['held_path'][len('sources/'):]}), p


@check
def s02_valid_http_record_unchanged():
    n = unheld()[0]
    assert errors([http_row(1, n)]) == []
    m310a = [r for r in L.jsonl_lines(L.ROOT + 'data/audit/m3.10a-external-artifact-registration.jsonl')
             if r['record'] == 'registration']
    rows = [http_row(i, r['m38_item']) for i, r in enumerate(m310a, 1)]
    e, ok = RA.validate_manifest(rows, VIEW)
    plan = RA.plan_manifest(ok, VIEW)
    assert e == [] and plan['actions'] == {'CREATE': 0, 'REUSE': 0, 'NOOP': 4, 'CONFLICT': 0}, plan['actions']
    assert all(p['mode'] == 'HTTP' and p['locator']['kind'] == 'URL' for p in plan['rows'])
    r = http_row(1, n)
    assert RA.placement_id(r, 'ar_000001') == S.hid('Placement', 'URL', r['url'], 'ar_000001', 'arm')


@check
def s03_s06_supplied_row_with_any_http_field_rejected():
    root, audit, it = recorded()
    with Supplied(root, audit):
        for k, v in (('url', 'https://%s/x.pdf' % HOST), ('final_url', 'https://%s/x.pdf' % HOST), ('http_status', 200),
                     ('fetched_at', '2026-03-03T10:00:00Z')):
            one(errors([reg_row(it, **{k: v})]), "['%s'] in a ESTATE_SUPPLIED acquisition: forbidden" % k)


@check
def s07_http_row_with_supplied_fields_rejected():
    n = unheld()[0]
    for k, v in (('received_at', '2026-03-03'), ('original_filename', 'x.pdf'), ('supply_channel', 'EMAIL_ATTACHMENT')):
        one(errors([http_row(1, n, **{k: v})]), "['%s'] in a HTTP acquisition: forbidden" % k)
    one(errors([http_row(1, n, origin=RA.SUPPLIED)]), 'only EXTERNAL_ACQUISITION')


@check
def s08_s13_supplier_identity():
    root, audit, it = recorded()
    key = (RA.SUPPLIED_AUDIT, 'sup:%d' % it['n'])
    with Supplied(root, audit):
        # 8: the record's supplier estate is not the relationship's estate
        one(errors([reg_row(it)], Fixed({key: dict(it, supplier=dict(it['supplier'], estate='es_00035'))})),
            "the supplier estate 'es_00035' is not")
        # 9: the row names another source than the record
        one(errors([reg_row(it, source='sr_00004')]), 'not what the acquisition record establishes: source')
        # 10: a relationship M3.7 did not confirm (record and row agree on it)
        x = dict(it, supplier={'estate': 'es_00281', 'source': 'sr_00262', 'relationship': PROBABLE_REL})
        one(errors([reg_row(it, source='sr_00262', source_relationship=PROBABLE_REL)], Fixed({key: x})),
            'is not a confirmed first-party or estate-controlled relationship')
        # 11: another estate's confirmed relationship
        x = dict(it, supplier={'estate': ESTATE, 'source': 'sr_00004', 'relationship': OTHER_REL})
        e = errors([reg_row(it, source='sr_00004', source_relationship=OTHER_REL)], Fixed({key: x}))
        one(e, "the supplier estate 'es_00220' is not")
        # 12: the sender's domain is not the source's host
        one(errors([reg_row(it)], Fixed({key: dict(it, sender_domain='gmail.com')})),
            "the sender domain 'gmail.com' is not the host of source sr_00014")
        # 13: the source is not in the model
        class NoSource(RA.View):
            def index(self):
                ix = dict(super().index())
                ix['sources'] = ix['sources'] - {SOURCE}
                return ix
        one(errors([reg_row(it)], view=NoSource()), 'source sr_00014 is not in the model')
    # the recorder refuses the same supplier problems before writing anything
    d = tmpdir('sup-refuse-') + os.sep
    for kw, why in (({'frm': 'x <a@gmail.com>'}, 'not the first party'),):
        try:
            RC.record(eml(os.path.join(d, 'm.eml'), **kw), NAME, REL, os.path.join(d, 'a.jsonl'), d)
            raise AssertionError('recorded')
        except RC.Refused as x:
            assert why in str(x), x
    for rel in (PROBABLE_REL, 'm37:sr_99999:es_00001'):
        try:
            RC.record(eml(os.path.join(d, 'm.eml')), NAME, rel, os.path.join(d, 'a.jsonl'), d)
            raise AssertionError('recorded')
        except RC.Refused as x:
            assert 'not a confirmed' in str(x), x
    assert sorted(os.listdir(d)) == ['m.eml'], os.listdir(d)


@check
def s14_s15_retrieval_must_be_the_modes():
    root, audit, it = recorded()
    key = (RA.SUPPLIED_AUDIT, 'sup:%d' % it['n'])
    with Supplied(root, audit):
        one(errors([reg_row(it)], Fixed({key: dict(it, retrieval='OK')})), 'not an estate-supplied one')
        one(errors([reg_row(it)], Fixed({key: dict(it, origin=RA.ORIGIN)})), 'not an estate-supplied one')
    n = unheld()[0]
    one(errors([http_row(1, n)], Fixed({(M38, 'm3.8:%d' % n): dict(ITEMS[n], retrieval='SUPPLIED')})),
        'did not retrieve it (SUPPLIED)')


@check
def s16_s17_wrong_sha256_or_size():
    root, audit, it = recorded()
    with Supplied(root, audit):
        one(errors([reg_row(it, sha256='0' * 64)]), 'not what the acquisition record establishes: sha256')
        one(errors([reg_row(it, bytes=it['bytes'] + 1)]), 'not what the acquisition record establishes: bytes')
        held = os.path.join(root, it['held_path'])
        open(held, 'ab').write(b'x')
        one(errors([reg_row(it)]), 'does not hash to the row')
    assert any('does not hash as recorded' in x for x in RC.check(audit, root))


@check
def s18_unsafe_filenames_rejected():
    for bad in ('../x.pdf', 'a/b.pdf', 'a\\b.pdf', 'con:x.pdf', '.', 'x.pdf.', ' x.pdf', 'a\x00.pdf'):
        assert not RA.safe_segment(bad), bad
    assert RA.safe_segment(NAME) and RA.safe_segment('Fiche-chateau-de-X_2023 (FR).pdf')
    root, audit, it = recorded()
    with Supplied(root, audit):
        e = errors([reg_row(it, original_filename='../x.pdf')])
        assert len(e) == 1 and 'is not one safe path segment' in e[0], e
    d = tmpdir('sup-unsafe-') + os.sep
    try:
        RC.record(eml(os.path.join(d, 'm.eml'), name='x:y.pdf'), 'x:y.pdf', REL, os.path.join(d, 'a.jsonl'), d)
        raise AssertionError('recorded')
    except RC.Refused as x:
        assert 'not one safe path segment' in str(x), x


@check
def s19_s22_local_path_placement_rebuild_and_history():
    """On an isolated copy, in a subprocess: the supplied row CREATEs one artifact after every existing id and one
    LOCAL_PATH placement; the migration rebuilds exactly that from scratch and with the registry; every earlier
    LOCAL_PATH and URL placement is unchanged; the acceptance runner's artifact side reads it unchanged."""
    root, audit, it = recorded()
    d = tmpdir('sup-model-')
    shutil.rmtree(d)
    shutil.copytree(L.MODEL, d)
    man = os.path.join(root, 'manifest.jsonl')
    open(man, 'w', encoding='utf-8', newline='\n').write(L.dumps(reg_row(it)) + '\n')
    out = subprocess.run([sys.executable, os.path.abspath(__file__), '--apply-copy', d, root, audit, man], cwd=L.ROOT,
                         env=dict(os.environ, BDX_MODEL_DIR=d), capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip().endswith('apply-copy: all pass'), (out.stdout + out.stderr)[-2000:]


@check
def s23_production_files_empty_and_model_unchanged():
    assert os.path.getsize(L.ROOT + RA.SUPPLIED_AUDIT) == 0 and os.path.getsize(L.ROOT + RA.MANIFEST) == 0
    out = subprocess.run([sys.executable, REC, '--check'], cwd=L.ROOT, capture_output=True, text=True)
    assert out.returncode == 0 and '0 item(s), sound' in out.stdout, out.stdout + out.stderr
    assert not os.path.exists(L.ROOT + 'sources/acquisition/supplied')
    assert not git('status', '--porcelain', '--', 'data/model', 'data/app', 'data/evidence', 'data/discovery').strip()


# ---------------------------------------------------------------- the subprocess

def apply_copy(d, root, audit, man):
    import mig_m2_identity as M2
    import migrate
    assert L.MODEL.rstrip('/') == d.replace('\\', '/').rstrip('/')
    R2 = M2.artifact_registrar()
    R2.PATH[0] = man
    R2.ACQUISITION_AUDITS[R2.SUPPLIED_AUDIT]['file'] = audit
    R2.HELD_ROOT[0] = root
    [row] = L.jsonl_lines(man)
    before = {rel: [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines()]
              for rel in R2.TABLES}
    view = R2.View()
    e, ok = R2.validate_manifest([row], view)
    assert e == [], e
    plan = R2.plan_manifest(ok, view)
    assert plan['actions'] == {'CREATE': 1, 'REUSE': 0, 'NOOP': 0, 'CONFLICT': 0}, plan['actions']
    files = R2.apply_manifest(plan)
    assert set(files) == set(R2.TABLES) | {'manifest.json'}, sorted(files)
    after = {rel: [json.loads(x) for x in open(os.path.join(d, rel), encoding='utf-8').read().splitlines()]
             for rel in R2.TABLES}
    last = max(int(a['id'].split('_')[1]) for a in before['identity/artifacts.jsonl'])
    [art] = [a for a in after['identity/artifacts.jsonl'] if a.get('sha256') == row['sha256']]
    assert art == {'id': 'ar_%06d' % (last + 1), 'sha256': row['sha256'], 'bytes': row['bytes'], 'bytes_available': True,
                   'media_type': 'application/pdf', 'extraction_status': 'PENDING'}, art
    value = row['held_path'][len('sources/'):]
    [pl] = [p for p in after['document/placements.jsonl'] if p.get('artifact') == art['id']]
    assert pl['locator'] == {'kind': 'LOCAL_PATH', 'value': value} and pl['status'] == 'PRESENT' and pl['source'] == SOURCE
    assert pl['id'] == S.hid('Placement', 'LOCAL_PATH', value, art['id'], 'arm')
    assert pl['observed']['valid_from']['value'] == row['received_at'] == pl['observed']['valid_to']['value']
    prov = {p['id']: p for p in after['cross/provenance.jsonl']}
    p = prov[pl['provenance']]
    assert p['kind'] == 'DOCUMENT' and p['actor'] == R2.ACTOR and p['code_state']['origin'] == R2.SUPPLIED
    assert not {'url', 'fetched_at', 'http_status'} & set(p['code_state'])
    assert {L.dumps(x) for x in after['document/locators.jsonl']} - {L.dumps(x) for x in before['document/locators.jsonl']} \
        == {L.dumps({'kind': 'LOCAL_PATH', 'value': value})}
    # every earlier placement - legacy LOCAL_PATH, URL - unchanged
    old = {L.dumps(x) for x in before['document/placements.jsonl']}
    new = {L.dumps(x) for x in after['document/placements.jsonl']}
    assert old <= new and len(new - old) == 1
    # the rebuild, from scratch and with the registry, is what --apply wrote
    for reg in (None, migrate.load_registry()):
        built = migrate.render(migrate.run('M7', reg), 'M7')
        for rel, b in built.items():
            assert open(os.path.join(d, rel), 'rb').read() == b, ('the rebuild differs', rel, reg is None)
    view = R2.View()
    e, ok = R2.validate_manifest([row], view)
    assert R2.plan_manifest(ok, view)['actions']['NOOP'] == 1 and R2.check(R2.plan_manifest(ok, view)) == []
    # the acceptance runner, unchanged, reads the supplied artifact: its name, its folder, its held bytes
    EA = load(L.ROOT + 'tools/apply-evidence-acceptance-manifest.py', 'apply_evidence_acceptance_manifest_st')
    av = EA.V.View()
    assert row['original_filename'] in EA.names_of(av)[art['id']]
    assert value.split('/', 1)[0] in EA.FOLDER_STORES
    real = EA.L.ROOT
    EA.L.ROOT = root
    try:
        assert hashlib.sha256(EA.held(value)).hexdigest() == row['sha256']
    finally:
        EA.L.ROOT = real
    print('apply-copy: all pass')


def main():
    fails = 0
    try:
        if '--apply-copy' in sys.argv:
            i = sys.argv.index('--apply-copy')
            return apply_copy(*sys.argv[i + 1:i + 5])
        for f in CHECKS:
            try:
                f()
                print('ok   %s' % f.__name__)
            except Exception as ex:
                fails += 1
                print('FAIL %s: %s' % (f.__name__, (str(ex) or repr(ex))[:600]))
    finally:
        for p in TMP:
            shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else os.path.exists(p) and os.remove(p)
    print('%d check(s), %s' % (len(CHECKS), 'all pass' if not fails else '%d FAIL' % fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
