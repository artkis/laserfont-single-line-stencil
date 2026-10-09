# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
"""Generate LaserFont 3 IDs with a mandatory arrow before the readable ID.

Glyph and key designs are OFL-1.1; this utility is MIT. See LICENSING.md.
The code characters retain their version 2 shapes. The complete version 3
label includes a full-height upward arrow. Read the arrow and ID together;
the arrow alone is symmetric and does not identify the viewing face.
"""
from pathlib import Path
import argparse
import json
import math

import generate_laserfont2 as legacy

ROOT = Path(__file__).resolve().parent
VERSION = "3.0.3"
KEY = json.loads((ROOT / "orientation-key.json").read_text(encoding="utf-8"))
new_drawing = legacy.new_drawing


def load_glyphs(mode="bezier"):
    if mode not in ("bezier", "polyline"):
        raise ValueError("Mode must be bezier or polyline")
    name = "glyphs-v2.json" if mode == "bezier" else "glyphs-v2-polyline.json"
    return json.loads((ROOT / name).read_text(encoding="utf-8"))["glyphs"]


def add_text(msp, glyphs, text, x=0, y=0, height=5, rotation=0,
             layer="ID_CUT_SINGLELINE", mode="bezier"):
    """Return the two arrow paths, then glyphs, in one anonymous DXF group.

    (x, y) is the arrow's left baseline, not the first character. At height
    5 mm, the arrow is 3 mm wide, followed by a 1.5 mm clear gap. It points
    toward the top of the readable lettering, not the top of the assembly.
    A rigid rotation applies to the entire label. The arrow cannot be disabled.
    No sheet outline, fold or final-assembly exterior is inferred here.
    """
    if mode not in ("bezier", "polyline"):
        raise ValueError("Mode must be bezier or polyline")
    if not all(isinstance(v, (int, float)) and math.isfinite(v)
               for v in (x, y, height, rotation)) or height <= 0:
        raise ValueError("Finite coordinates/rotation and positive finite height required")
    if not isinstance(text, str) or not text.isascii() or not any(c.isalnum() for c in text):
        raise ValueError("ID must contain an ASCII letter or digit")
    text = text.upper()
    unsupported = sorted(set(text) - set(glyphs))
    if unsupported:
        raise ValueError("Unsupported characters: " + repr(unsupported))
    if not layer or not isinstance(layer, str):
        raise ValueError("A nonempty layer name is required")
    scale = height / KEY["height_mm"]
    before = {e.dxf.handle for e in msp}
    group = None
    try:
        arrow = []
        for path in KEY["paths_mm"]:
            vertices = [legacy.transform(p, x, y, scale, rotation)[:2] for p in path]
            arrow.append(msp.add_lwpolyline(vertices, format="xy", close=False,
                                           dxfattribs={"layer": layer, "const_width": 0}))
        tx, ty, _ = legacy.transform((KEY["text_origin_x_mm"], 0), x, y, scale, rotation)
        if mode == "bezier":
            characters = legacy.add_text(msp, glyphs, text, tx, ty, height, rotation, layer)
        else:
            characters = legacy.add_poly_text(msp, glyphs, text, tx, ty, height, rotation)
            for e in characters:
                e.dxf.layer = layer
        entities = arrow + characters
        group = msp.doc.groups.new(description="LaserFont 3 outside-face ID: " + text)
        group.set_data(entities)
        return entities
    except Exception:
        if group is not None:
            msp.doc.groups.delete(group)
        for e in list(msp):
            if e.dxf.handle not in before:
                msp.delete_entity(e)
        raise


def build_samples(output_dir):
    """Make lettering-only samples, without a fictitious production part outline."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = ["H3", "I3", "H1", "J1", "M17", "B8-S5-O0", "A1", "N6"]
    paths = []
    for mode in ("bezier", "polyline"):
        data = load_glyphs(mode)
        doc = new_drawing()
        for i, text in enumerate(samples):
            add_text(doc.modelspace(), data, text, y=-10*i, mode=mode)
        target = output_dir / ("laserfont3-H5-samples-" + mode + ".dxf")
        doc.saveas(target)
        paths.append(target)
    doc = new_drawing()
    data = load_glyphs()
    for i, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"):
        # Hyphen is shown in a real identifier; punctuation alone is not an ID.
        text = char if char != "-" else "A-1"
        add_text(doc.modelspace(), data, text, x=(i % 8)*18, y=-(i // 8)*12)
    target = output_dir / "laserfont3-H5-character-samples.dxf"
    doc.saveas(target)
    paths.append(target)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--height", type=float, default=5)
    parser.add_argument("--x", type=float, default=0)
    parser.add_argument("--y", type=float, default=0)
    parser.add_argument("--rotation", type=float, default=0)
    parser.add_argument("--mode", choices=("bezier", "polyline"), default="bezier")
    parser.add_argument("--samples", type=Path, metavar="DIRECTORY")
    args = parser.parse_args()
    if args.samples:
        print(json.dumps({"samples": [str(p) for p in build_samples(args.samples)]}))
    if args.text is not None:
        if args.output is None:
            parser.error("--text requires --output")
        if args.output.exists():
            parser.error("Output exists; choose a new filename")
        doc = new_drawing()
        try:
            entities = add_text(doc.modelspace(), load_glyphs(args.mode), args.text,
                                args.x, args.y, args.height, args.rotation, mode=args.mode)
        except ValueError as exc:
            parser.error(str(exc))
        doc.saveas(args.output)
        print(json.dumps({"output": str(args.output), "version": VERSION,
                          "height_mm": args.height, "units": "mm",
                          "cut_paths": len(entities), "orientation_key": "mandatory",
                          "mode": args.mode, "grouped": True}))
    if args.text is None and args.samples is None:
        parser.error("Use --text with --output, or --samples DIRECTORY")


if __name__ == "__main__":
    main()
