# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Artkis
"""Build LaserFont 3 SHP without changing any legacy character encoding.

Font data is OFL-1.1. This utility is MIT. The reserved ASCII tilde displays
the full-height orientation arrow. It may occur once before each complete ID;
ordinary SHX per-character rendering cannot infer label boundaries.

Run this builder, then COMPILE laserfont3.shp in AutoCAD. This module does not
install fonts, change profiles, launch AutoCAD, or modify version 2 files.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import build_cad as legacy

ROOT = Path(__file__).resolve().parent
VERSION = "3.0.3"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lf_bytes(data):
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def records(text):
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.startswith("*")]
    result = {}
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        name = lines[start].split(",", 1)[0][1:]
        result[name] = "".join(lines[start:end])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check deterministic LF source and report without writing")
    args = parser.parse_args()
    source = ROOT / "laserfont2.shp"
    key_path = ROOT.parent / "orientation-key.json"
    original = source.read_bytes()
    text = lf_bytes(original).decode("ascii")
    key = json.loads(key_path.read_text(encoding="utf-8"))
    if key["height_mm"] != 20:
        raise ValueError("Display font requires the existing 20-unit design height")
    paths = key["paths_mm"]
    if not paths or any(len(path) < 2 for path in paths):
        raise ValueError("The orientation arrow requires nonempty open paths")
    if any(len(point) != 2 or not all(math.isfinite(value) for value in point)
           for path in paths for point in path):
        raise ValueError("Arrow coordinates must be finite XY pairs")
    shape = legacy.Shape()
    for path in paths:
        # start() lifts the pen and returns to the glyph origin. This preserves
        # the shaft and arrowhead as separate strokes without a connecting cut.
        shape.start(path[0])
        for point in path[1:]:
            shape.move(point, True)
    codes = shape.finish(key["text_origin_x_mm"])
    new_record = "\n".join(legacy.record(ord("~"), codes, "orientation_arrow")) + "\n"
    old_records = records(text)
    if "0007E" not in old_records or "UNIFONT" not in old_records:
        raise ValueError("Unexpected legacy SHP record layout")
    result = text.replace(old_records["0007E"], new_record, 1)
    result = result.replace("*UNIFONT,6,laserfont2", "*UNIFONT,6,laserfont3", 1)
    result = result.replace(
        "; laserfont2 display only. Exact Bezier cutting geometry: LASER2 / LASEROUT2.",
        "; laserfont3 display only. Optional ~ displays the arrow. Convert to cut paths with LASEROUT.", 1)
    new_records = records(result)
    preserved = [name for name in old_records if name not in ("UNIFONT", "0007E")]
    assert all(old_records[name] == new_records[name] for name in preserved)
    assert source.read_bytes() == original
    destination = ROOT / "laserfont3.shp"
    report_path = ROOT / "display-build-report-v3.json"
    previous_bytes = destination.read_bytes() if destination.exists() else None
    previous_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    output_bytes = result.encode("ascii")
    assert b"\r" not in output_bytes
    compiled = ROOT / "laserfont3.shx"
    native_proof_reusable = bool(
        previous_bytes is not None
        and previous_report.get("compile_status") == "AUTOCAD_2023_COMPILE_SUCCESS"
        and digest(previous_bytes) == previous_report.get("output_sha256")
        and lf_bytes(previous_bytes) == output_bytes
        and compiled.exists()
        and sha(compiled) == previous_report.get("compiled_output_sha256"))
    if args.check:
        assert previous_bytes == output_bytes, "Generated SHP differs or contains non-LF newlines"
        assert previous_report.get("version") == VERSION, "Build report version differs"
        assert previous_report.get("output_sha256") == digest(output_bytes), "SHP hash differs from report"
        assert previous_report.get("source_lf_canonical_sha256") == digest(lf_bytes(original)), "Legacy source canonical hash differs"
        if previous_report.get("compile_status") == "AUTOCAD_2023_COMPILE_SUCCESS":
            assert native_proof_reusable, "Compiled proof does not match delivered source or SHX"
            assert previous_report.get("native_compiled_input_shp_lf_canonical_sha256") == digest(output_bytes)
        print(json.dumps({"check": "PASS", "version": VERSION, "output_sha256": digest(output_bytes), "source_newlines": "LF", "native_proof_retained": native_proof_reusable}))
        return
    destination.write_bytes(output_bytes)
    decoded = shape.decoded
    ymin = min(point[1] for segment in decoded for point in segment)
    ymax = max(point[1] for segment in decoded for point in segment)
    xmin = min(point[0] for segment in decoded for point in segment)
    xmax = max(point[0] for segment in decoded for point in segment)
    assert abs(ymax - ymin - 20) < 1e-9
    assert abs(xmax - xmin - 12) < 1e-9
    report = {
        "font_name": "laserfont3", "version": VERSION,
        "font_license": "OFL-1.1", "utility_license": "MIT",
        "source": "laserfont2.shp", "source_sha256": sha(source),
        "source_lf_canonical_sha256": digest(lf_bytes(original)),
        "key_source": "../orientation-key.json", "key_source_sha256": sha(key_path),
        "output": "laserfont3.shp", "output_sha256": sha(destination),
        "output_lf_canonical_sha256": digest(output_bytes), "output_newlines": "LF",
        "cap_height_design_units": 20,
        "reserved_character": "~", "reserved_codepoint": 126,
        "orientation_symbol": "up arrow", "key_open_paths": len(paths),
        "key_paths_design_units": paths,
        "key_advance_design_units": key["text_origin_x_mm"],
        "key_width_at_height5_mm": (xmax - xmin) / 4,
        "key_height_at_height5_mm": (ymax - ymin) / 4,
        "key_advance_at_height5_mm": key["text_origin_x_mm"] / 4,
        "legacy_records_preserved_lf_canonically": len(preserved),
        "legacy_record_names_preserved": preserved,
        "legacy_character_encoding_unchanged_except_reserved_tilde": True,
        "key_shape_bytes": len(codes), "key_display_segments": len(decoded),
        "display_only": True,
        "display_bound_from_legacy_at_height5_mm": (legacy.CHORD_TOL + 2 ** 0.5 / legacy.GRID / 2) / 4,
        "compile_status": "NOT_RUN_BY_SOURCE_BUILDER",
        "limits": ["SHX is an editable display approximation, not a cutting path.",
                   "A leading tilde displays one arrow; LASEROUT adds the arrow automatically to bare labels.",
                   "Final outside-face placement and physical readability require separate checks."]}
    if native_proof_reusable:
        for name, value in previous_report.items():
            if name.startswith(("native_", "compiled_")) or name in ("compile_status", "display_review"):
                report[name] = value
        report["native_compiled_input_shp_raw_sha256"] = previous_report.get("native_compiled_input_shp_raw_sha256", digest(previous_bytes))
        report["native_compiled_input_shp_lf_canonical_sha256"] = previous_report.get("native_compiled_input_shp_lf_canonical_sha256", digest(lf_bytes(previous_bytes)))
        report["delivered_shp_equivalent_to_native_compile_input_after_lf_normalization"] = True
        report["compiled_binary_preserved_without_recompile"] = True
        report["compile_proof_continuity"] = "Native compilation used the recorded raw SHP; delivered LF source has identical canonical content and font records. SHX bytes are unchanged."
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k != "legacy_record_names_preserved"}, indent=2))


if __name__ == "__main__":
    main()
