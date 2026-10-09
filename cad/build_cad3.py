# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
"""Build the standalone LASEROUT command without rewriting any v2 artifact.

The original glyph designs and the mandatory orientation key remain OFL-1.1.
Only LASER3.lsp is written. Use --check for a read-only reproducibility check.
"""
from pathlib import Path
import argparse
import hashlib
import json

from build_cad import exact_path, lisp

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent


def build():
    raw = (ROOT / 'glyphs-v2.json').read_bytes()
    src = json.loads(raw)
    glyphs = src['glyphs']
    exact = [[ch, g['advance_mm'], [exact_path(p) for p in g['paths']]]
             for ch, g in glyphs.items()]
    space = float(glyphs.get(' ', {}).get(
        'advance_mm', src.get('metadata', {}).get('space_advance_mm', 8.0)))

    poly = json.loads((ROOT / 'glyphs-v2-polyline.json').read_text(encoding='utf-8'))
    canonical_raw = raw.replace(b'\r\n', b'\n')
    source_hash = hashlib.sha256(canonical_raw).hexdigest()
    source_hashes = {hashlib.sha256(form).hexdigest() for form in (
        raw, canonical_raw, canonical_raw.replace(b'\n', b'\r\n'))}
    assert poly['metadata']['source_sha256'] in source_hashes, 'Arc-fit source revision mismatch'
    assert set(poly['glyphs']) == set(glyphs), 'Arc-fit glyph coverage mismatch'
    polylines = []
    for ch, g in poly['glyphs'].items():
        assert abs(g['advance_mm'] - glyphs[ch]['advance_mm']) < 1e-9
        assert len(g['paths_xyb']) == len(glyphs[ch]['paths'])
        polylines.append([ch, g['advance_mm'], g['paths_xyb']])

    key_raw = (ROOT / 'orientation-key.json').read_bytes()
    key = json.loads(key_raw)
    assert key['height_mm'] == 20, 'The glyph/key normalization must be 20'
    assert key['vertices_mm'] == [[0, 20], [0, 3.2], [3.2, 0], [12, 0], [12, 6]]
    assert key['text_origin_x_mm'] == 18
    assert key['license'] == 'OFL-1.1'
    points = [[*p, 0.0] for p in key['vertices_mm']]

    header = (
        ';;; LaserFont3 orientation-key labels using original laserfont2 glyphs.\n'
        ';;; Copyright (c) 2026 Artkis.\n'
        ';;; Mixed-license file: embedded glyph/key designs are OFL-1.1 (OFL.txt);\n'
        ';;; the AutoLISP utility program is MIT (LICENSE-MIT.txt).\n'
        ';;; Self-contained: no Python, font or external JSON needed for LASEROUT.\n'
        ';;; Native validation scope is recorded separately; see native-test-report-v3.json.\n'
        f';;; Glyph source SHA-256: {source_hash}\n'
        f';;; Key source SHA-256: {hashlib.sha256(key_raw.replace(bytes([13, 10]), bytes([10]))).hexdigest()}\n'
        ';;; BEGIN FONT DATA -- SPDX-License-Identifier: OFL-1.1\n')
    data = (
        "(setq *lf3:glyphs* '" + lisp(exact) + ')\n'
        '(setq *lf3:space* ' + lisp(space) + ')\n'
        "(setq *lf3:poly-glyphs* '" + lisp(polylines) + ')\n'
        "(setq *lf3:key-points* '" + lisp(points) + ')\n'
        '(setq *lf3:text-origin* ' + lisp(key['text_origin_x_mm']) + ')\n')
    program = (header + data + ';;; END FONT DATA\n\n'
               + (OUT / 'runtime3.lsp').read_text(encoding='utf-8')
               + '\n;;; DISPLAY SETUP AND CANONICAL COMMAND\n'
               + (OUT / 'integration3.lsp').read_text(encoding='utf-8'))
    return program, source_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check the generated file without writing')
    args = parser.parse_args()
    program, source_hash = build()
    target = OUT / 'LASER3.lsp'
    if args.check:
        if not target.exists() or target.read_bytes() != program.encode('ascii'):
            raise SystemExit('LASER3.lsp differs from its sources; run python cad/build_cad3.py')
    else:
        target.write_bytes(program.encode('ascii'))
    native_report = OUT / 'native-test-report-v3.json'
    native = json.loads(native_report.read_text(encoding='utf-8')) if native_report.exists() else {}
    print(json.dumps({'file': str(target), 'check_only': args.check,
                      'glyph_source_sha256': source_hash,
                      'generated_sha256': hashlib.sha256(program.encode('ascii')).hexdigest(),
                      'key_required': True,
                      'native_report': native_report.name if native else None,
                      'native_report_matches_generated_file': native.get('laser3_sha256') == hashlib.sha256(program.encode('ascii')).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
