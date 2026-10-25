"""Phase 4 M1: the raw store, addressed by digest, outside git.

The bytes are not copied (the raw store is some 21 GB and the disk has
less than that free). An artifact is found by its digest in one of two
places that already exist under the gitignored sources/:

  sources/discovery/blobs/<aa>/<sha256>[.gz]   content-addressed already
                                               (tools/discover.py)
  sources/fiches/<folder>/<file>               the legacy corpus, by the
  sources/pages/<estate>/<file>                manifest row's path; the
                                               digest is checked on read

A legacy path holds whatever was last written there, so a path is only
returned for a digest when the bytes there still hash to it; an
overwritten version (a sha1 the manifest remembers) is BYTES_UNAVAILABLE.
"""
import gzip
import hashlib
import os

import migration_lib as L

SRC = L.ROOT + 'sources/'
BLOBS = SRC + 'discovery/blobs/'


def legacy_path(folder, file):
    """Where a manifest row's bytes are on disk, by the corpus layout."""
    if folder.startswith('pages/'):
        return SRC + folder + '/' + file
    return SRC + 'fiches/' + folder + '/' + file


def blob_path(sha256):
    p = '%s%s/%s' % (BLOBS, sha256[:2], sha256)
    if os.path.exists(p):
        return p
    return p + '.gz' if os.path.exists(p + '.gz') else None


def read_blob(sha256):
    p = blob_path(sha256)
    if not p:
        return None
    with open(p, 'rb') as f:
        data = f.read()
    return gzip.decompress(data) if p.endswith('.gz') else data


def digests(path):
    h1, h2 = hashlib.sha1(), hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h1.update(chunk)
            h2.update(chunk)
    return h1.hexdigest(), h2.hexdigest()


def locate(sha256=None, sha1=None, folder=None, file=None):
    """A readable path holding exactly these bytes, or None."""
    if sha256:
        p = blob_path(sha256)
        if p:
            return p
    if folder is not None and file is not None:
        p = legacy_path(folder, file)
        if os.path.exists(p):
            s1, s256 = digests(p)
            if (sha1 and s1 == sha1) or (sha256 and s256 == sha256):
                return p
    return None
