"""Record a document an estate itself supplied - the acquisition record an ESTATE_SUPPLIED registration rests on.

    python tools/record-estate-supplied-acquisition.py --eml <message.eml> --attachment <file name> \
        --relationship <m37 relationship id>
    python tools/record-estate-supplied-acquisition.py --check
  options: --audit <file> (default data/audit/estate-supplied-acquisitions.jsonl); --root <dir> (where sources/ is,
  default the repository)

docs/PHASE-V2-ESTATE-SUPPLIED-ACQUISITION.md is the contract. Every fact is read from the message the estate sent,
never typed in: the attachment's bytes (hashed and measured here), its file name exactly as sent, the day of the
message's Date header (UTC) and the domain of its From address. The relationship named must be a confirmed M3.7
first-party or estate-controlled one, and the sender's domain that source's own host, or nothing is written.

WHAT IS HELD, under sources/ (never committed): the attachment at sources/acquisition/supplied/<sha256>/<file name>
and, beside it, receipt.json - the Date header, the sender's domain, and hashes of the message, its Message-ID and the
attachment. No address, name, subject or body is kept anywhere. WHAT IS COMMITTED, the audit: one `scope` row and one
`item` row per received file (retrieval SUPPLIED, origin ESTATE_SUPPLIED), with the receipt's hash. No URL, HTTP
status or fetch time exists for a supplied file, and none is recorded.

--check: every item's held file and receipt hash as recorded, every item is still a valid supply under the
registration runner's own check (tools/apply-artifact-registration-manifest.py check_supplied), and the audit is in
its canonical form. An empty audit is valid.
"""
import datetime
import email
import email.policy
import email.utils
import hashlib
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

TOOL = 'tools/record-estate-supplied-acquisition.py'
CHANNEL = 'EMAIL_ATTACHMENT'
MAGIC = {b'%PDF-': 'application/pdf'}
STATEMENT = 'supplied directly by the estate; not fetched: no URL, HTTP status or fetch time exists'


def _registrar():
    spec = importlib.util.spec_from_file_location('apply_artifact_registration_manifest_rec',
                                                  L.ROOT + 'tools/apply-artifact-registration-manifest.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RA = _registrar()
CONF = RA.ACQUISITION_AUDITS[RA.SUPPLIED_AUDIT]


class Refused(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest()


def body(rows):
    return ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
                   for r in rows).encode('utf-8')


def scope():
    return {'record': 'scope', 'recorder': TOOL, 'mode': RA.SUPPLIED, 'channels': sorted(RA.SUPPLY_CHANNELS),
            'held': CONF['held'], 'contract': 'one item per file an estate itself sent; every fact read from the '
            'received message; the supplier a confirmed M3.7 first-party or estate-controlled relationship whose '
            'source host is the sender domain; no URL, HTTP status or fetch time'}


def load(path):
    return L.jsonl_lines(path) if os.path.exists(path) and os.path.getsize(path) else []


def media_of(data, declared):
    for magic, media in MAGIC.items():
        if data.startswith(magic):
            return media
    if declared in RA.media_types() and declared not in MAGIC.values():
        return declared
    raise Refused('the attachment is neither a recognised format nor a media type the model records (%s)' % declared)


def read_message(eml_bytes, attachment):
    """(attachment bytes, file name as sent, declared type, received day, sender domain, receipt) from the message."""
    msg = email.message_from_bytes(eml_bytes, policy=email.policy.default)
    parts = [p for p in msg.walk() if p.get_filename() == attachment]
    if len(parts) != 1:
        raise Refused('the message holds %d attachment(s) named %r' % (len(parts), attachment))
    data = parts[0].get_payload(decode=True)
    if not data:
        raise Refused('the attachment %r is empty' % attachment)
    if not msg['Date']:
        raise Refused('the message has no Date header: the day it was received is not established')
    when = email.utils.parsedate_to_datetime(str(msg['Date']))
    if when.tzinfo is None:
        raise Refused('the message Date has no time zone: the day is not established')
    day = when.astimezone(datetime.timezone.utc).date().isoformat()
    addrs = email.utils.getaddresses([str(msg['From'] or '')])
    if len(addrs) != 1 or '@' not in addrs[0][1]:
        raise Refused('the message has not exactly one From address')
    domain = addrs[0][1].rsplit('@', 1)[1].strip().lower()
    receipt = {'date_header': str(msg['Date']), 'received_at': day, 'sender_domain': domain,
               'message_sha256': sha(eml_bytes), 'message_id_sha256': sha(str(msg['Message-ID'] or '').encode('utf-8')),
               'attachment': attachment, 'attachment_sha256': sha(data)}
    return data, parts[0].get_filename(), parts[0].get_content_type(), day, domain, receipt


def item_row(n, data, name, media, day, domain, rel, receipt_held, receipt_sha):
    h = sha(data)
    return {'record': 'item', 'n': n, 'retrieval': 'SUPPLIED', 'origin': RA.SUPPLIED,
            'supplier': {'estate': rel['estate'], 'source': rel['source'], 'relationship': rel['id']},
            'supply_channel': CHANNEL, 'sender_domain': domain, 'received_at': day, 'original_filename': name,
            'sha256': h, 'bytes': len(data), 'content_type': media,
            'held_path': CONF['held'] + '%s/%s' % (h, name),
            'receipt': {'held': receipt_held, 'sha256': receipt_sha}, 'statement': STATEMENT}


def as_registration(it):
    """The registration row an item supports - what the runner's own supplied check is run on."""
    sup = it.get('supplier') or {}
    return {'sha256': it.get('sha256'), 'bytes': it.get('bytes'), 'media_type': it.get('content_type'),
            'held_path': it.get('held_path'), 'received_at': it.get('received_at'),
            'original_filename': it.get('original_filename'), 'supply_channel': it.get('supply_channel'),
            'source': sup.get('source'), 'source_relationship': sup.get('relationship'),
            'acquired_by': CONF['acquired_by'], 'retrieval_method': CONF['retrieval_method'] % it.get('supply_channel')}


def record(eml_path, attachment, relationship, audit, root):
    rels = RA.Relationships()
    rel = rels.get(relationship)
    if rel is None or rel.get('status') not in RA.SUPPLIER_STATUSES:
        raise Refused('%s is not a confirmed first-party or estate-controlled relationship (M3.7)' % relationship)
    eml = open(eml_path, 'rb').read()
    data, name, declared, day, domain, receipt = read_message(eml, attachment)
    if not RA.safe_segment(name):
        raise Refused('the file name %r is not one safe path segment' % name)
    host = rels.host(rel['source'])
    if not host or RA._host(domain) != RA._host(host):
        raise Refused('the sender domain %r is not the host of source %s (%r): not the first party' % (
            domain, rel['source'], host))
    media = media_of(data, declared)
    rows = load(audit)
    items = [r for r in rows if r.get('record') == 'item']
    h = sha(data)
    if any(r['sha256'] == h and r['original_filename'] == name for r in items):
        raise Refused('this file is already recorded')
    rb = (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=1) + '\n').encode('utf-8')
    it = item_row(max([r['n'] for r in items] + [0]) + 1, data, name, media, day, domain, rel,
                  CONF['held'] + '%s/receipt.json' % h, sha(rb))
    try:
        RA.check_supplied(as_registration(it), it, CONF, rels)          # before anything is written
    except RA.Invalid as x:
        raise Refused(str(x))
    folder = os.path.join(root, CONF['held'], h)
    held = os.path.join(folder, name)
    if os.path.exists(held) and sha(open(held, 'rb').read()) != h:
        raise Refused('%s holds other bytes' % held)
    os.makedirs(folder, exist_ok=True)
    open(held, 'wb').write(data)
    open(os.path.join(folder, 'receipt.json'), 'wb').write(rb)
    open(audit, 'wb').write(body([scope()] + sorted(items, key=lambda r: r['n']) + [it]))
    return it


def check(audit, root):
    """Every problem with the audit: [] when it is sound."""
    rows = load(audit)
    bad = []
    if not rows:
        return bad
    items = [r for r in rows if r.get('record') == 'item']
    if rows != [scope()] + sorted(items, key=lambda r: r['n']) or open(audit, 'rb').read() != body(rows):
        bad.append('the audit is not in its canonical form (one scope row, then the items by n)')
    rels = RA.Relationships()
    for it in items:
        try:
            RA.check_supplied(as_registration(it), it, CONF, rels)
            for rel, want in ((it['held_path'], it['sha256']), (it['receipt']['held'], it['receipt']['sha256'])):
                p = os.path.join(root, rel)
                if not os.path.isfile(p) or sha(open(p, 'rb').read()) != want:
                    raise RA.Invalid('%s is missing or does not hash as recorded' % rel)
            if os.path.getsize(os.path.join(root, it['held_path'])) != it['bytes']:
                raise RA.Invalid('the held file is not %d bytes' % it['bytes'])
        except (RA.Invalid, KeyError, TypeError) as x:
            bad.append('item %s: %s' % (it.get('n'), x))
    return bad


def main():
    a = sys.argv[1:]

    def opt(k, default=None):
        return a[a.index(k) + 1] if k in a else default
    audit = os.path.abspath(opt('--audit', L.ROOT + RA.SUPPLIED_AUDIT))
    root = os.path.abspath(opt('--root', L.ROOT)) + os.sep
    try:
        if '--check' in a:
            bad = check(audit, root)
            n = sum(1 for r in load(audit) if r.get('record') == 'item')
            L.out('estate-supplied acquisitions: %s' % ('%d item(s), sound' % n if not bad else '\n  '.join(bad)))
            sys.exit(1 if bad else 0)
        if not ('--eml' in a and '--attachment' in a and '--relationship' in a):
            print(__doc__)
            sys.exit(2)
        it = record(opt('--eml'), opt('--attachment'), opt('--relationship'), audit, root)
        L.out('recorded item %d: %s (%d bytes, %s), received %s from %s' % (
            it['n'], it['original_filename'], it['bytes'], it['sha256'][:12], it['received_at'], it['sender_domain']))
    except Refused as x:
        raise SystemExit('REFUSED - %s; nothing was written' % x)


if __name__ == '__main__':
    main()
