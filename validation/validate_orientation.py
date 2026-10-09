"""Run independent orientation tests and write a portable geometry report.

Usage: python validation/validate_orientation.py
The report contains generic label fixtures and repository-relative filenames.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import importlib.util
import io
import json
import platform
import sys
import unittest

import ezdxf
import shapely


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report_path = args.report or root / "validation" / "orientation-report.json"
    spec = importlib.util.spec_from_file_location("laserfont_orientation_tests", root / "tests" / "test_orientation.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(module))
    names = ("generate_laserfont3.py", "orientation-key.json", "glyphs-v2.json",
             "glyphs-v2-polyline.json", "tests/test_orientation.py",
             "render_orientation.py", "validation/validate_orientation.py")
    report = {
        "schema": 1,
        "font_version": module.oriented.VERSION,
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failure_count": len(result.failures),
        "error_count": len(result.errors),
        "failed_tests": [test.id() for test, _ in result.failures + result.errors],
        "dependencies": {"python": platform.python_version(), "ezdxf": ezdxf.__version__, "shapely": shapely.__version__},
        "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names},
        "source_content_sha256_lf_normalized": {
            name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in names
        },
        "source_hash_note": "Raw hashes record the tested checkout; LF-normalized hashes allow content comparison across Git line-ending conversions.",
        "scope": {
            "output_modes": ["bezier", "polyline"],
            "cap_heights_mm": [5, 10, 20],
            "glyphs": "A-Z, 0-9, hyphen, space",
            "round_trip": "DXF save/reopen with two separate label groups, millimetres and transformed geometry",
            "reflection_checks": "Saved and reopened complete arrow-plus-ID labels: all A-Z and 0-9 characters, hyphen in A-1, and representative IDs including H3/I3, against four D4 reflections and front rotated 180 degrees",
            "reflection_fixture_count_per_mode": len(module.DIAGNOSTICS.get("complete_label_reflected_D4_hausdorff_mm_at_height5_saved_DXF", {})) // 2,
            "reflection_height_mm": 5,
            "sample_flattening_distance_mm": 0.0001,
            "numeric_geometry_tolerance_mm": 1e-8,
        },
        "results": module.DIAGNOSTICS,
        "limitations": [
            "D4 samples compare four rotations of a reflection; they are not a continuous-angle proof for the entire label.",
            "The arrow alone is horizontally symmetric. The cue is its before-ID placement and direction toward the top of readable lettering; it is not an assembly UP instruction.",
            "Human recognition, actual CAM import, kerf, piercing and physical cut readability are not tested.",
            "A label cannot prove correct placement on the exterior of a finished part or assembly; that requires a separate placement check.",
            "DXF groups preserve membership, but downstream software may ignore or remove grouping.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "tests_run", "failure_count", "error_count", "failed_tests")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
