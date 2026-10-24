# -*- coding: utf-8 -*-
"""Which file a decision read, which bytes, and which code - established,
not assumed.

Phase 2.4 found three things the evidence writers recorded and could
not stand behind:

  1. `observed.sha1` was copied from sources.json, not computed. For 204
     folder/file pairs the manifest holds two hashes and the disk one
     file.
  2. Documents were found by basename across every folder. 917 rows
     were read from another folder's file of the same name; 48 of them
     with different bytes.
  3. `commit` was HEAD when the run started, even when the code that
     decided had not been committed.

This module is what the writers use instead. It has four parts.

                                RESOLVE

A manifest row names a folder and a file. The folder is either a fiche
library, sources/fiches/<folder>, or a crawled site,
sources/pages/<estate> (written in the manifest as "pages/<estate>").
Both candidate paths are built from the row itself, and:

  - exactly one exists  -> that file;
  - none exists         -> ARTIFACT_NOT_FOUND;
  - both exist          -> ARTIFACT_AMBIGUOUS;
  - only a differently written name exists - other letter case, or a
    trailing dot - -> ARTIFACT_NAME_MISMATCH.

"Exists" means the directory lists that exact name. Windows answers
isfile() for a name in any case and with its trailing dots dropped, so
on this machine "domaine-de-chevalier-blanc-2025-primeur-francais.pdf"
opened "Domaine-de-Chevalier-Blanc-2025-Primeur-Francais.pdf", and on
Linux it would open nothing: a resolution that depends on the operating
system is not an identity. The near-miss is named in the failure, so it
can be put right in the manifest, but it is not read.

There is no search by basename and no "first match". A folder or file
that would leave sources/ is refused.

                                 READ

The file is hashed (SHA-256) immediately before the reader is called and
again after it returns. The reader opens the path itself (pymupdf, or
the page text), so this is how "the bytes read" is pinned: if the two
hashes differ, the file changed under the reader, and nothing it said
is recorded (ARTIFACT_CHANGED_DURING_READ). A file that cannot be
opened is ARTIFACT_UNREADABLE.

                                 GIT

Taken once per run, and again before anything is written:

  git.commit       the full HEAD sha
  git.dirty        whether the working tree differed from HEAD in any
                   tracked file or any untracked, unignored file
  git.status_hash  when dirty: SHA-256 of `git status --porcelain`,
                   `git diff HEAD --binary` and the bytes of every
                   untracked file - it identifies the exact uncommitted
                   state; when clean: null

A clean run means "the code at git.commit produced this". A dirty run
means "git.commit plus the changes status_hash names", and the writers
refuse to append it unless told --allow-dirty. If the state changes
during the run, nothing is written.

                                FAILURES

A provenance failure is not a verdict. It never becomes ACCEPTED,
WRONG_WINE or any reader code. It goes to its own file
(evidence_store.append_failures), with `kind: provenance_failure`, a
code from FAILURES and no `decision` field at all.
"""
import datetime
import hashlib
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep

FAILURES = ('ARTIFACT_NOT_FOUND', 'ARTIFACT_AMBIGUOUS', 'ARTIFACT_UNREADABLE',
            'ARTIFACT_CHANGED_DURING_READ', 'ARTIFACT_OUTSIDE_SOURCES',
            'ARTIFACT_NAME_MISMATCH')

# Below this version, rows keep the provenance fields as v1-v3 defined
# them; evidence_store.PROVENANCE_FROM must agree.
NEW_FROM = 4


class ProvenanceFailure(Exception):
    def __init__(self, code, detail):
        Exception.__init__(self, '%s: %s' % (code, detail))
        self.code = code
        self.detail = detail


class Artifact(object):
    """One file, resolved and hashed."""

    def __init__(self, path, rel, sha256, size):
        self.path = path
        self.rel = rel
        self.sha256 = sha256
        self.size = size


def candidates(folder, file, sources):
    folder = (folder or '').replace('\\', '/').strip('/')
    roots = []
    if folder:
        roots.append(os.path.join(sources, 'fiches', *folder.split('/')))
        if '/' in folder:
            roots.append(os.path.join(sources, *folder.split('/')))
    return [os.path.join(r, file) for r in roots]


_LISTED = {}


def _listing(d):
    if d not in _LISTED:
        try:
            _LISTED[d] = set(os.listdir(d))
        except OSError:
            _LISTED[d] = set()
    return _LISTED[d]


def _near(name, listed):
    k = name.rstrip('. ').lower()
    return sorted(x for x in listed if x != name
                  and x.rstrip('. ').lower() == k)


def hash_file(path):
    h = hashlib.sha256()
    n = 0
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def resolve(folder, file, root=None):
    """The one file a manifest row names, hashed, or ProvenanceFailure."""
    root = root or ROOT
    sources = os.path.realpath(os.path.join(root, 'sources'))
    if not file or os.path.basename(file) != file or file in ('.', '..') \
            or '..' in (folder or '').replace('\\', '/').split('/'):
        raise ProvenanceFailure('ARTIFACT_OUTSIDE_SOURCES',
                                '%r in %r' % (file, folder))
    hits, near = [], []
    for p in candidates(folder, file, sources):
        d = os.path.realpath(os.path.dirname(p))
        if not (d + os.sep).startswith(sources + os.sep):
            raise ProvenanceFailure('ARTIFACT_OUTSIDE_SOURCES', p)
        listed = _listing(d)
        rp = os.path.join(d, file)
        if file in listed and os.path.isfile(rp):
            if rp not in hits:
                hits.append(rp)
        else:
            near += [os.path.relpath(os.path.join(d, x), sources)
                     for x in _near(file, listed)]
    if not hits and near:
        raise ProvenanceFailure('ARTIFACT_NAME_MISMATCH',
                                '%s/%s is not on disk; %s is'
                                % (folder, file, ' and '.join(near)))
    if not hits:
        raise ProvenanceFailure('ARTIFACT_NOT_FOUND',
                                '%s/%s' % (folder, file))
    if len(hits) > 1:
        raise ProvenanceFailure(
            'ARTIFACT_AMBIGUOUS', '%s/%s is at %s'
            % (folder, file, ' and '.join(os.path.relpath(h, sources)
                                          for h in hits)))
    try:
        sha, size = hash_file(hits[0])
    except (IOError, OSError) as e:
        raise ProvenanceFailure('ARTIFACT_UNREADABLE', str(e)[:120])
    return Artifact(hits[0],
                    os.path.relpath(hits[0], sources).replace(os.sep, '/'),
                    sha, size)


def confirm(art):
    """After the reader: are the bytes still the ones hashed before it?"""
    try:
        sha, size = hash_file(art.path)
    except (IOError, OSError) as e:
        raise ProvenanceFailure('ARTIFACT_UNREADABLE', str(e)[:120])
    if sha != art.sha256:
        raise ProvenanceFailure('ARTIFACT_CHANGED_DURING_READ',
                                '%s: %s before, %s after'
                                % (art.rel, art.sha256[:12], sha[:12]))


def _git(args, root):
    return subprocess.check_output(['git'] + args, cwd=root,
                                   stderr=subprocess.DEVNULL)


# The evidence store is what a run WRITES, not code that runs: no verdict
# reads it, only the store's own duplicate check does. It lives in the
# repository, so without this the first writer of a pass made the tree
# "dirty" for the second (Phase 2.7: recharacterize.py refused to run
# after evidence-wines.py had written), and no exact rerun could ever
# start clean. Everything else - code, data/*.js, the manifest - counts.
OUTPUT_PATHS = ('data/evidence',)


def git_state(root=None):
    """{'commit', 'dirty', 'status_hash'} for the repository at root."""
    root = root or ROOT
    commit = _git(['rev-parse', 'HEAD'], root).decode().strip()
    spec = ['--', '.'] + [':(exclude)%s' % p for p in OUTPUT_PATHS]
    status = _git(['status', '--porcelain=v1', '-z',
                   '--untracked-files=all'] + spec, root)
    if not status:
        return {'commit': commit, 'dirty': False, 'status_hash': None}
    h = hashlib.sha256()
    h.update(status)
    h.update(_git(['diff', 'HEAD', '--binary'] + spec, root))
    for entry in status.split(b'\0'):
        if entry.startswith(b'?? '):
            rel = entry[3:].decode('utf-8', 'replace')
            p = os.path.join(root, rel)
            h.update(b'\0' + entry[3:] + b'\0')
            if os.path.isfile(p):
                with open(p, 'rb') as f:
                    h.update(f.read())
    return {'commit': commit, 'dirty': True, 'status_hash': h.hexdigest()}


def short_head(root=None):
    """HEAD abbreviated - what v1-v3 recorded as `commit`, kept for them."""
    try:
        return _git(['rev-parse', '--short', 'HEAD'],
                    root or ROOT).decode().strip()
    except Exception:
        return None


class Run(object):
    """One evidence run's provenance: its git state, and its failures."""

    def __init__(self, version, root=None):
        self.root = root or ROOT
        self.version = int(version)
        self.git = git_state(self.root)
        self.legacy_commit = short_head(self.root)
        self.failures = []

    def resolve(self, sheet, ctx):
        """The sheet's artifact, or None with the failure recorded."""
        try:
            return resolve(sheet.get('folder'), sheet.get('file'), self.root)
        except ProvenanceFailure as f:
            self.fail(sheet, ctx, f)
            return None

    def confirm(self, art, sheet, ctx):
        try:
            confirm(art)
            return True
        except ProvenanceFailure as f:
            self.fail(sheet, ctx, f)
            return False

    def fail(self, sheet, ctx, f):
        self.failures.append({
            'kind': 'provenance_failure',
            'code': f.code,
            'detail': f.detail,
            'artifact': sheet.get('file'),
            'ctx': dict(ctx or {}),
            'manifest_sha1': sheet.get('sha1'),
            'v': self.version,
            'git': dict(self.git),
            'at': datetime.date.today().isoformat(),
        })

    def stamp(self, sheet, art, legacy_observed=True):
        """The provenance fields of one decision row.

        Below NEW_FROM, exactly what that version always wrote, so a row
        appended to v3 today means what every other v3 row means:
        `observed.sha1` is the manifest's claim, `commit` is HEAD at run
        time. From NEW_FROM on, the fields say what was established:
        `read` is the file and the hash of its bytes, `git` the code
        state, and the manifest's hash is kept beside it, named as the
        claim it is.
        """
        if self.version < NEW_FROM:
            out = {'commit': self.legacy_commit}
            if legacy_observed:
                out['observed'] = {'sha1': sheet.get('sha1')}
            return out
        return {'read': {'path': art.rel, 'sha256': art.sha256,
                         'bytes': art.size},
                'git': dict(self.git),
                'manifest_sha1': sheet.get('sha1')}

    def unchanged(self):
        """Is the repository still in the state the run started in?"""
        return git_state(self.root) == self.git


def write(run, rows, allow_dirty=False):
    """Append a run's decisions and failures, if its provenance holds.

    Returns (decisions written, failures written). Refuses - writes
    nothing - when the repository changed during the run, or when a
    v4+ run was dirty and allow_dirty was not given.
    """
    import evidence_store as ST
    if not run.unchanged():
        raise SystemExit('refused: the repository changed during the run, '
                         'so no single code state produced these '
                         'decisions. Nothing written.')
    if run.version >= NEW_FROM and run.git['dirty'] and not allow_dirty:
        raise SystemExit('refused: the working tree differs from %s. '
                         'Commit, or pass --allow-dirty to record the run '
                         'as dirty (git.status_hash %s).'
                         % (run.git['commit'][:12],
                            (run.git['status_hash'] or '')[:12]))
    n = ST.append(rows, run.version)
    f = ST.append_failures(run.failures, run.version) \
        if run.version >= NEW_FROM else 0
    return n, f


def report(run):
    """One line per failure code, for the runner's summary."""
    import collections
    c = collections.Counter(f['code'] for f in run.failures)
    if not c:
        return 'provenance: every artifact resolved to one file'
    return 'provenance failures (not decisions): ' + ', '.join(
        '%s %d' % kv for kv in c.most_common())
