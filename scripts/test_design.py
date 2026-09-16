#!/usr/bin/env python3
"""Portable V2 regression tests; native cadnano integration is separate."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import template_design as td
from validation import validate, preservation


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def generate(self, name="rectangle", **params):
        result = td.create_design(name, str(self.root / name), **params)
        self.assertEqual(result["design_status"], "GENERATED", result)
        self.assertEqual(result["validation_report"]["errors"], [])
        full = json.loads(Path(result["full_path"]).read_text(encoding="utf-8"))
        compact = json.loads(Path(result["cando_compact_path"]).read_text(encoding="utf-8"))
        self.assertEqual(full, compact)
        self.assertEqual(result["validation_status"], "CANDO_INPUT_GENERATED")
        return result, full

    def test_all_supported_defaults(self):
        for shape in td.SUPPORTED:
            with self.subTest(shape=shape):
                self.generate(shape)

    def test_honeycomb_planar_and_square_bundles(self):
        for shape in ("rectangle", "2_helix_bundle", "4_helix_bundle", "6_helix_bundle"):
            with self.subTest(shape=shape):
                self.generate(shape, user_lattice="honeycomb" if shape == "rectangle" else "square")

    def test_odd_helix_count(self):
        self.generate(num_helices=5, bases_per_helix=150)

    def test_unambiguous_lattice_storage(self):
        for shape, lattice in (("rectangle", "square"), ("2_helix_bundle", "honeycomb")):
            _, data = self.generate(shape, bases_per_helix=672)
            size = len(data["vstrands"][0]["scaf"])
            self.assertEqual(size % (32 if lattice == "square" else 21), 0)
            self.assertNotEqual(size % (21 if lattice == "square" else 32), 0)

    def test_tube_has_staple_seam(self):
        _, data = self.generate("regular_tube")
        last = len(data["vstrands"]) - 1
        self.assertTrue(any(r[0] == last or r[2] == last for r in data["vstrands"][0]["stap"]))

    def test_reject_shape_parameter_mismatch_and_unknowns(self):
        cases = [("2_helix_bundle", {"num_helices": 6}),
                 ("4_helix_bundle", {"num_helices": 2}),
                 ("square", {"num_helices": 8, "bases_per_helix": 128}),
                 ("long_strip", {"num_helices": 24, "bases_per_helix": 128}),
                 ("planar_plate", {"num_helices": 4, "bases_per_helix": 128}),
                 ("regular_tube", {"user_lattice": "honeycomb"}),
                 ("rectangle", {"side_helices": 4}),
                 ("rectangle", {"lenth": 128}),
                 ("rectangle", {"num_helices": 0}),
                 ("rectangle", {"num_helices": True}),
                 ("rectangle", {"bases_per_helix": 1}),
                 ("rectangle", {"scaffold_length": 100})]
        for i, (shape, params) in enumerate(cases):
            with self.subTest(shape=shape, params=params):
                basename = self.root / str(i)
                result = td.create_design(shape, str(basename), **params)
                self.assertEqual(result["design_status"], "GENERATION_FAILED")
                self.assertIsNone(result["full_path"])
                self.assertEqual(list(self.root.glob(str(i) + ".*")), [])

    def test_all_unimplemented_refused(self):
        for shape in td.UNSUPPORTED + ("flower",):
            with self.subTest(shape=shape):
                result = td.create_design(shape, str(self.root / shape))
                self.assertEqual(result["design_status"], "UNSUPPORTED_REQUEST")
                self.assertIsNone(result["full_path"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_no_overwrite(self):
        result, _ = self.generate()
        before = Path(result["full_path"]).read_bytes()
        again = td.create_design("rectangle", str(self.root / "rectangle"))
        self.assertEqual(again["design_status"], "GENERATION_FAILED")
        self.assertEqual(Path(result["full_path"]).read_bytes(), before)

    def test_nonsequential_ids_and_reordered_vstrands(self):
        _, data = self.generate()
        for vh in data["vstrands"]:
            vh["num"] += 10
            for kind in ("scaf", "stap"):
                for rec in vh[kind]:
                    for side in (0, 2):
                        if rec[side] >= 0:
                            rec[side] += 10
        data["vstrands"].reverse()
        self.assertEqual(validate(data, "square")["status"], "PASS")

    def test_malformed_schema_and_references_rejected(self):
        _, original = self.generate()
        for mutation in ("short_record", "string_record", "dangling", "nonreciprocal",
                         "same_helix_jump", "wrong_polarity", "color", "missing_colors", "duplicate_num",
                         "duplicate_coord", "bad_length", "loop", "skip", "non_neighbor"):
            with self.subTest(mutation=mutation):
                data = copy.deepcopy(original)
                a = data["vstrands"][0]
                if mutation == "short_record": a["scaf"][10] = [-1]
                elif mutation == "string_record": a["stap"][10] = "invalid"
                elif mutation == "dangling": a["scaf"][10][2:] = [9999, 11]
                elif mutation == "nonreciprocal": a["scaf"][10][:2] = [-1, -1]
                elif mutation == "same_helix_jump": a["scaf"][10][3] = 12
                elif mutation == "wrong_polarity": a["scaf"][10] = a["scaf"][10][2:] + a["scaf"][10][:2]
                elif mutation == "color": a["stap_colors"] = [[-1, 0]]
                elif mutation == "missing_colors": del a["stap_colors"]
                elif mutation == "duplicate_num": data["vstrands"][1]["num"] = 0
                elif mutation == "duplicate_coord": data["vstrands"][2]["col"] = a["col"]
                elif mutation == "bad_length": a["skip"].pop()
                elif mutation == "loop": a["loop"][10] = 1
                elif mutation == "skip": a["skip"][10] = -1
                elif mutation == "non_neighbor": a["row"] += 200
                self.assertEqual(validate(data, "square")["status"], "FAIL")

    def test_phase_shift_rejected_with_reciprocity_preserved(self):
        _, data = self.generate()
        # Translate all occupied bases one position right. Connectivity and
        # topology remain identical, but direction-specific phase is wrong.
        for vh in data["vstrands"]:
            for kind in ("scaf", "stap"):
                vh[kind] = [[-1, -1, -1, -1]] + vh[kind][:-1]
                for rec in vh[kind]:
                    for side in (0, 2):
                        if rec[side] >= 0: rec[side + 1] += 1
            for color in vh["stap_colors"]: color[0] += 1
        result = validate(data, "square")
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("illegal lattice crossover" in e for e in result["errors"]))

    def test_disconnected_scaffold_rejected(self):
        _, data = self.generate()
        by_id = {vh["num"]: vh for vh in data["vstrands"]}
        for h, vh in by_id.items():
            for i, rec in enumerate(vh["scaf"]):
                if rec[2] >= 0 and rec[2] != h:
                    th, ti = rec[2:]
                    by_id[th]["scaf"][ti][:2] = [-1, -1]
                    rec[2:] = [-1, -1]
                    result = validate(data, "square")
                    self.assertIn("scaffold must be exactly one connected oligo", result["errors"])
                    return
        self.fail("fixture missing scaffold crossover")

    def test_preservation_includes_all_metadata(self):
        _, data = self.generate()
        for field in ("num", "row", "col", "scaf", "stap", "loop", "skip", "stap_colors"):
            changed = copy.deepcopy(data)
            changed["vstrands"][0][field] = None
            self.assertEqual(preservation(data, changed)["status"], "FAIL")

    def test_failed_validation_blocks_all_exports(self):
        from unittest.mock import patch
        with patch.object(td, "validate", return_value={"status": "FAIL", "errors": ["injected failure"]}):
            result = td.create_design("rectangle", str(self.root / "fail"))
        self.assertEqual(result["design_status"], "GENERATION_FAILED")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_cli_exit_code(self):
        proc = subprocess.run([sys.executable, str(Path(td.__file__)), "2_helix_bundle",
                               "--num-helices", "6", "-o", str(self.root / "cli")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stdout)["design_status"], "GENERATION_FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
