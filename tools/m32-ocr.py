"""M3.2E: OCR of the image-only sheets that are the only document of a vintage - and only those.

    python tools/m32-ocr.py AID [AID ...]          OCR each held PDF, write the derived extraction
    python tools/m32-ocr.py --check AID [AID ...]  OCR again and compare with what is stored

The engine is the one already installed (rapidocr_onnxruntime, CPU); nothing is installed. Each
page is rendered by pymupdf at a fixed 200 dpi and read; the text lines are kept, in reading order,
with their confidence. The output is a derived extraction, stored beside the other extraction text
under sources/discovery/ocr/<sha256>.json (local, gitignored: the text is the estate's, not ours to
republish). The source PDF is only read. Nothing here reaches the model: OCR text is evidence for
review (tools/m32-recovery.py stream E), never a model value by itself.
"""
import hashlib
import importlib.metadata as md
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import migration_lib as L  # noqa: E402

OUT = L.ROOT + 'sources/discovery/ocr/'
DPI = 200


def held_pdf(aid):
    import data_gap_analysis as A
    for pl in sorted(A.placements_of(aid), key=lambda p: p['locator']['value']):
        q = L.ROOT + 'sources/' + pl['locator']['value']
        if pl['locator']['kind'] == 'LOCAL_PATH' and q.lower().endswith('.pdf') and os.path.exists(q):
            return q
    return None


def ocr(path):
    import numpy as np
    import pymupdf
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    doc = pymupdf.open(path)
    pages = []
    for page in doc:
        pix = page.get_pixmap(dpi=DPI)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        result, _ = engine(img)
        lines = []
        for box, text, score in result or []:
            y, x = min(p[1] for p in box), min(p[0] for p in box)
            lines.append((round(y / 8), x, text, round(float(score), 3)))
        lines.sort()                                         # reading order: rows, then left to right
        pages.append([{'text': t, 'confidence': s} for _, _, t, s in lines])
    doc.close()
    return pages


def record(aid):
    import data_gap_analysis as A
    a = A.by_id('identity/artifacts.jsonl')[aid]
    path = held_pdf(aid)
    with open(path, 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == a['sha256'], 'the held bytes are not the artifact'
    pages = ocr(path)
    text = '\n'.join(l['text'] for p in pages for l in p)
    return {'artifact': aid, 'sha256': a['sha256'], 'source': os.path.relpath(path, L.ROOT).replace('\\', '/'),
            'engine': 'rapidocr_onnxruntime %s, onnxruntime %s' % (md.version('rapidocr_onnxruntime'), md.version('onnxruntime')),
            'dpi': DPI, 'pages': pages, 'chars': len(text),
            'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}


def main():
    check = '--check' in sys.argv
    aids = [a for a in sys.argv[1:] if not a.startswith('--')]
    os.makedirs(OUT, exist_ok=True)
    bad = 0
    for aid in aids:
        r = record(aid)
        p = OUT + r['sha256'] + '.json'
        body = json.dumps(r, ensure_ascii=False, sort_keys=True, indent=1)
        if check:
            same = os.path.exists(p) and open(p, encoding='utf-8').read() == body
            bad += not same
            print('%s %s' % (aid, 'reproduces' if same else 'DIFFERS'))
        else:
            with open(p, 'w', encoding='utf-8', newline='\n') as f:
                f.write(body)
            print('%s %d page(s), %d chars' % (aid, len(r['pages']), r['chars']))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
