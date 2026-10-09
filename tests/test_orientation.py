"""Independent geometry checks for the complete arrow-plus-ID label.

Run: python -m unittest discover -s tests -v
Dependencies: requirements.txt and validation/requirements-validation.txt.
These are geometry tests, not a human readability or physical cutting test.
"""
from pathlib import Path
import json
import math
import subprocess
import sys
import tempfile
import unittest

import ezdxf
from ezdxf.path import make_path
from shapely import affinity
from shapely.geometry import LineString
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate_laserfont2 as legacy
import generate_laserfont3 as oriented

ARROW_PATHS = [[(6, 0), (6, 20)], [(0, 14), (6, 20), (12, 14)]]
TEXT_OFFSET = 18.0
TOLERANCE = 1e-8
DIAGNOSTICS = {}


def transform(point, x, y, height, rotation):
    """Independent scalar transform, with a 20-unit design height."""
    angle = math.radians(rotation)
    cosine, sine = math.cos(angle), math.sin(angle)
    u, v = point
    scale = height / 20
    return (x + scale * (u * cosine - v * sine),
            y + scale * (u * sine + v * cosine), 0.0)


def source(mode):
    name = "glyphs-v2.json" if mode == "bezier" else "glyphs-v2-polyline.json"
    return json.loads((ROOT / name).read_text(encoding="utf-8"))["glyphs"]


def geometry(entities):
    """Sample saved DXF curves independently from the author's renderer."""
    lines = []
    for entity in entities:
        vertices = list(make_path(entity).flattening(distance=0.0001, segments=16))
        if len(vertices) > 1:
            lines.append(LineString([(p.x, p.y) for p in vertices]))
    return unary_union(lines)


def centered(shape):
    xmin, ymin, xmax, ymax = shape.bounds
    return affinity.translate(shape, -(xmin + xmax) / 2, -(ymin + ymax) / 2)


def reflected_distances(shape):
    original = centered(shape)
    mirror = affinity.scale(original, xfact=-1, yfact=1, origin=(0, 0))
    return [original.hausdorff_distance(affinity.rotate(mirror, angle, origin=(0, 0)))
            for angle in (0, 90, 180, 270)]


class OrientationTests(unittest.TestCase):
    def assertPoint(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(float(a), float(e), delta=TOLERANCE)

    def make_label(self, text="A1", mode="bezier", **kwargs):
        document = oriented.new_drawing()
        entities = oriented.add_text(document.modelspace(), oriented.load_glyphs(mode),
                                     text, mode=mode, **kwargs)
        return document, entities

    def test_legacy_counterexamples_really_are_reflection_ambiguous(self):
        results = {}
        for text in ("H3", "I3"):
            with self.subTest(text=text):
                document = legacy.new_drawing()
                entities = legacy.add_text(document.modelspace(), source("bezier"), text)
                distances = reflected_distances(geometry(entities))
                self.assertLess(min(distances), 0.0002)
                results[text] = distances
        DIAGNOSTICS["legacy_reflected_D4_hausdorff_mm_at_height20"] = results

    def test_oriented_labels_differ_from_all_four_rotated_reflections(self):
        results = {}
        upside_down = {}
        fixtures = list(dict.fromkeys(
            ["H3", "I3", "H1", "J1", "M17", "B8-S5-O0", "A1", "N6", "HOH", "A-1"]
            + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")))
        for mode in ("bezier", "polyline"):
            with tempfile.TemporaryDirectory() as temporary:
                document = oriented.new_drawing()
                for index, text in enumerate(fixtures):
                    oriented.add_text(document.modelspace(), oriented.load_glyphs(mode),
                                      text, y=-10*index, height=5, mode=mode)
                filename = Path(temporary) / "complete-labels.dxf"
                document.saveas(filename)
                reopened = ezdxf.readfile(filename)
                self.assertEqual(len(reopened.groups), len(fixtures))
                for text, (_, group) in zip(fixtures, reopened.groups):
                    with self.subTest(mode=mode, text=text):
                        shape = centered(geometry(group))
                        distances = reflected_distances(shape)
                        self.assertGreater(min(distances), 0.125)
                        front180 = shape.hausdorff_distance(affinity.rotate(shape, 180, origin=(0, 0)))
                        self.assertGreater(front180, 0.125)
                        results[mode + ":" + text] = distances
                        upside_down[mode + ":" + text] = front180
        DIAGNOSTICS["complete_label_reflected_D4_hausdorff_mm_at_height5_saved_DXF"] = results
        DIAGNOSTICS["complete_label_front180_hausdorff_mm_at_height5_saved_DXF"] = upside_down

    def test_arrow_is_two_open_zero_width_unbulged_paths(self):
        for mode in ("bezier", "polyline"):
            with self.subTest(mode=mode):
                _, entities = self.make_label("H3", mode, height=20)
                for marker, expected_path in zip(entities[:2], ARROW_PATHS):
                    self.assertEqual(marker.dxftype(), "LWPOLYLINE")
                    self.assertFalse(marker.closed)
                    self.assertEqual(marker.dxf.const_width, 0)
                    self.assertEqual(len(marker), len(expected_path))
                    for actual, expected in zip(marker.get_points("xyseb"), expected_path):
                        self.assertPoint(actual[:2], expected)
                        self.assertPoint(actual[2:], (0, 0, 0))
                    self.assertPoint(tuple(marker.dxf.extrusion), (0, 0, 1))
                    self.assertEqual(marker.dxf.layer, "ID_CUT_SINGLELINE")

    def test_marker_has_no_duplicate_or_zero_length_segments(self):
        edges = [edge for path in ARROW_PATHS for edge in zip(path, path[1:])]
        unique = {tuple(sorted(edge)) for edge in edges}
        self.assertEqual(len(unique), len(edges))
        self.assertTrue(all(math.dist(a, b) > 0 for a, b in edges))
        for path in ARROW_PATHS:
            line = LineString(path)
            self.assertTrue(line.is_simple)
            self.assertFalse(line.is_ring)

    def test_arrow_alone_is_symmetric_and_is_not_a_face_proof(self):
        _, entities = self.make_label("H3", height=20)
        arrow = centered(geometry(entities[:2]))
        distance = arrow.hausdorff_distance(affinity.scale(arrow, xfact=-1, yfact=1, origin=(0, 0)))
        self.assertLess(distance, TOLERANCE)
        DIAGNOSTICS["isolated_arrow_horizontal_reflection_hausdorff_mm_at_height20"] = distance
        DIAGNOSTICS["arrow_reading_rule"] = "Read the complete label: arrow before ID, pointing toward the top of readable lettering. The arrow alone is symmetric."

    def test_exact_glyph_geometry_preserved_after_key_for_every_character(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- "
        for mode in ("bezier", "polyline"):
            data = source(mode)
            for height, x, y, rotation in ((5, 0, 0, 0), (10, 31, -19, 37), (20, -7, 4, 213)):
                with self.subTest(mode=mode, height=height):
                    loaded = oriented.load_glyphs(mode)
                    before = json.dumps(loaded, sort_keys=True)
                    document = oriented.new_drawing()
                    entities = oriented.add_text(document.modelspace(), loaded, text, mode=mode,
                                                 height=height, x=x, y=y, rotation=rotation)
                    offset = TEXT_OFFSET
                    expected_count = 2
                    entity_index = 2
                    for char in text:
                        glyph = data[char]
                        paths = glyph["paths"] if mode == "bezier" else glyph["paths_xyb"]
                        expected_count += len(paths)
                        for path in paths:
                            actual = entities[entity_index]
                            entity_index += 1
                            def transformed(point):
                                return transform((point[0] + offset, point[1]), x, y, height, rotation)
                            if mode == "polyline":
                                self.assertEqual(actual.dxftype(), "LWPOLYLINE")
                                self.assertFalse(actual.closed)
                                self.assertEqual(actual.dxf.const_width, 0)
                                points = list(actual.get_points("xyb"))
                                self.assertEqual(len(points), len(path))
                                for got, want in zip(points, path):
                                    self.assertPoint(got[:2], transformed(want)[:2])
                                    self.assertAlmostEqual(got[2], want[2], delta=TOLERANCE)
                            elif len(path) == 1 and path[0]["type"] == "LINE":
                                self.assertEqual(actual.dxftype(), "LINE")
                                self.assertPoint(tuple(actual.dxf.start), transformed(path[0]["p"]))
                                self.assertPoint(tuple(actual.dxf.end), transformed(path[0]["q"]))
                            else:
                                self.assertEqual(actual.dxftype(), "SPLINE")
                                self.assertEqual(actual.dxf.degree, 3)
                                self.assertFalse(actual.closed)
                                controls = []
                                for segment in path:
                                    p, q = segment["p"], segment["q"]
                                    if segment["type"] == "CUBIC":
                                        part = [p, segment["c1"], segment["c2"], q]
                                    else:
                                        part = [p, [(2*a+b)/3 for a,b in zip(p,q)],
                                                [(a+2*b)/3 for a,b in zip(p,q)], q]
                                    controls.extend(part if not controls else part[1:])
                                self.assertEqual(len(actual.control_points), len(controls))
                                for got, want in zip(actual.control_points, controls):
                                    self.assertPoint(tuple(got), transformed(want))
                                n = len(path)
                                knots = [0.0]*4 + [float(i) for i in range(1,n) for _ in range(3)] + [float(n)]*4
                                self.assertEqual(list(actual.knots), knots)
                        offset += glyph["advance_mm"]
                    self.assertEqual(len(entities), expected_count)
                    self.assertEqual(json.dumps(loaded, sort_keys=True), before)

    def test_marker_transform_and_cap_height(self):
        for mode in ("bezier", "polyline"):
            for height in (5, 10, 20):
                for angle in (0, 37, 90, 180, 270):
                    with self.subTest(mode=mode, height=height, angle=angle):
                        _, entities = self.make_label("H3", mode, x=31, y=-17, height=height, rotation=angle)
                        for entity, expected_path in zip(entities[:2], ARROW_PATHS):
                            vertices = list(entity.vertices_in_wcs())
                            for actual, expected in zip(vertices, expected_path):
                                self.assertPoint(tuple(actual), transform(expected, 31, -17, height, angle))
                        shaft = list(entities[0].vertices_in_wcs())
                        self.assertAlmostEqual(math.dist(shaft[0], shaft[1]), height)

    def test_groups_units_and_geometry_survive_save_reopen(self):
        for mode in ("bezier", "polyline"):
            for height in (5, 10, 20):
                with self.subTest(mode=mode, height=height), tempfile.TemporaryDirectory() as temporary:
                    document, first = self.make_label("H3", mode, x=10, y=-3, height=height, rotation=37)
                    second = oriented.add_text(document.modelspace(), oriented.load_glyphs(mode), "I3",
                                               x=-20, y=30, height=height, rotation=213, mode=mode)
                    expected_groups = {frozenset(e.dxf.handle for e in first), frozenset(e.dxf.handle for e in second)}
                    self.assertEqual(len(document.groups), 2)
                    filename = Path(temporary) / "labels.dxf"
                    document.saveas(filename)
                    reopened = ezdxf.readfile(filename)
                    self.assertEqual(reopened.units, 4)
                    self.assertEqual(reopened.header["$INSUNITS"], 4)
                    self.assertEqual(len(reopened.groups), 2)
                    actual_groups = {frozenset(e.dxf.handle for e in group) for _, group in reopened.groups}
                    self.assertEqual(actual_groups, expected_groups)
                    self.assertEqual(len(reopened.modelspace()), len(first) + len(second))
                    self.assertLess(geometry(document.modelspace()).hausdorff_distance(geometry(reopened.modelspace())), 1e-8)
                    for _, group in reopened.groups:
                        self.assertEqual(len(set(e.dxf.handle for e in group)), len(group))
                        self.assertTrue(all(e.dxftype() not in ("TEXT", "MTEXT", "INSERT") for e in group))

    def test_invalid_numeric_arguments_leave_no_partial_geometry(self):
        for mode in ("bezier", "polyline"):
            for name in ("x", "y", "height", "rotation"):
                for value in (math.nan, math.inf, -math.inf):
                    with self.subTest(mode=mode, name=name, value=value):
                        document = oriented.new_drawing()
                        msp = document.modelspace()
                        sentinel = msp.add_line((100,100),(101,101))
                        handles = [e.dxf.handle for e in msp]
                        with self.assertRaises((ValueError, TypeError)):
                            oriented.add_text(msp, oriented.load_glyphs(mode), "A1", mode=mode, **{name:value})
                        self.assertEqual([e.dxf.handle for e in msp], handles)
                        self.assertTrue(sentinel.is_alive)
                        self.assertEqual(len(document.groups), 0)

    def test_invalid_label_arguments_leave_no_partial_geometry(self):
        cases = [({"text":""}), ({"text":"   "}), ({"text":"A?"}), ({"text":"A\n1"}),
                 ({"text":"Aß"}), ({"text":"Aı"}),
                 ({"text":None}), ({"text":"-"}), ({"height":0}), ({"height":-1}),
                 ({"mode":"unknown"}), ({"layer":""}), ({"layer":None})]
        for case in cases:
            with self.subTest(case=case):
                document = oriented.new_drawing()
                kwargs = {"text":"A1", **case}
                with self.assertRaises((ValueError, TypeError)):
                    oriented.add_text(document.modelspace(), oriented.load_glyphs(), **kwargs)
                self.assertEqual(len(document.modelspace()), 0)
                self.assertEqual(len(document.groups), 0)

    def test_source_error_rolls_back_new_entities_and_preserves_previous_label(self):
        for mode in ("bezier", "polyline"):
            with self.subTest(mode=mode):
                document, original = self.make_label("A1", mode)
                before_handles = [e.dxf.handle for e in document.modelspace()]
                before_groups = {name: [e.dxf.handle for e in group] for name, group in document.groups}
                broken = oriented.load_glyphs(mode)
                del broken["B"]["paths" if mode == "bezier" else "paths_xyb"]
                with self.assertRaises(KeyError):
                    # The second character fails after the arrow and A are made.
                    oriented.add_text(document.modelspace(), broken, "AB", mode=mode)
                self.assertEqual([e.dxf.handle for e in document.modelspace()], before_handles)
                self.assertEqual({name: [e.dxf.handle for e in group] for name, group in document.groups}, before_groups)
                self.assertTrue(all(e.is_alive for e in original))

    def test_lowercase_maps_to_the_same_geometry(self):
        for mode in ("bezier", "polyline"):
            with self.subTest(mode=mode):
                _, lower = self.make_label("a1", mode)
                _, upper = self.make_label("A1", mode)
                self.assertLess(geometry(lower).hausdorff_distance(geometry(upper)), 1e-8)

    def test_custom_layer_applies_to_key_and_all_glyph_paths(self):
        for mode in ("bezier", "polyline"):
            with self.subTest(mode=mode):
                document = oriented.new_drawing()
                document.layers.new("CUSTOM_IDS")
                entities = oriented.add_text(document.modelspace(), oriented.load_glyphs(mode),
                                             "A1", layer="CUSTOM_IDS", mode=mode)
                self.assertTrue(all(e.dxf.layer == "CUSTOM_IDS" for e in entities))

    def test_cli_both_modes_default_height_and_refusal_to_overwrite(self):
        for mode in ("bezier", "polyline"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "id.dxf"
                command = [sys.executable, str(ROOT / "generate_laserfont3.py"),
                           "--text", "A1", "--mode", mode, "--output", str(target)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                metadata = json.loads(result.stdout)
                self.assertEqual(metadata["height_mm"], 5)
                self.assertEqual(metadata["mode"], mode)
                self.assertEqual(metadata["units"], "mm")
                self.assertEqual(metadata["orientation_key"], "mandatory")
                self.assertTrue(metadata["grouped"])
                reopened = ezdxf.readfile(target)
                self.assertEqual(reopened.units, 4)
                self.assertEqual(len(reopened.groups), 1)
                self.assertEqual(len(reopened.modelspace()), metadata["cut_paths"])
                for marker, expected_path in zip(list(reopened.modelspace())[:2], ARROW_PATHS):
                    self.assertEqual(marker.dxftype(), "LWPOLYLINE")
                    for point, expected in zip(marker.vertices_in_wcs(), expected_path):
                        self.assertPoint(tuple(point), transform(expected, 0, 0, 5, 0))
                existing = target.read_bytes()
                refused = subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn("Output exists", refused.stderr)
                self.assertEqual(target.read_bytes(), existing)


if __name__ == "__main__":
    unittest.main()
