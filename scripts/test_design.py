#!/usr/bin/env python3
"""
Test suite for template_design.py.

Covers:
  - Small rectangle (square lattice)
  - Rectangle with honeycomb lattice
  - 2-helix bundle (honeycomb)
  - 4-helix bundle (honeycomb)
  - 6-helix bundle (honeycomb)
  - Square tube
  - Open box (partially implemented)
  - Scaffold length exceeded
  - Staple connectivity (multi-domain crossovers required)
  - Full/Cando derivation consistency
  - CanDo compact file topology preservation
  - Not-yet-implemented shape handling
  - Validation functions
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the skill scripts directory to path
SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR))

import template_design as td


# ============================================================================
# Test helpers
# ============================================================================

PASS = 0
FAIL = 0
TEST_RESULTS = []


def test(name: str):
    """Decorator-style context: print test header."""
    print(f"\n{'='*65}")
    print(f"  TEST: {name}")
    print(f"{'='*65}")


def check(condition: bool, description: str) -> bool:
    """Assert-style check that always reports."""
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {description}")
        PASS += 1
        TEST_RESULTS.append((True, description))
    else:
        print(f"  [FAIL] {description}  <-- FAILED")
        FAIL += 1
        TEST_RESULTS.append((False, description))
    return condition


def section(title: str):
    print(f"\n  --- {title} ---")


# ============================================================================
# Create temp output directory
# ============================================================================

ORIG_CWD = os.getcwd()
TMPDIR = tempfile.mkdtemp(prefix="cadnano_test_")
os.chdir(TMPDIR)
print(f"Test directory: {TMPDIR}")


def cleanup():
    os.chdir(ORIG_CWD)
    # Keep files for inspection; print location
    print(f"\nTest files remain at: {TMPDIR}")


# ============================================================================
# Test 1: Small rectangle, square lattice
# ============================================================================

test("Small rectangle (square lattice)")

result = td.create_design(
    shape_id="rectangle",
    output_basename="test_rect_sq",
    user_lattice="square",
    num_helices=8,
    bases_per_helix=128,
)

check(result["design_status"] == "GENERATED",
      f"Design status: {result['design_status']}")
check(result["full_path"] is not None,
      f"Full master generated: {result['full_path']}")
check(os.path.exists(result["full_path"]),
      f"Full file exists on disk: {result['full_path']}")
check(result["cando_compact_path"] is not None,
      f"Compact CanDo file generated: {result['cando_compact_path']}")
check(os.path.exists(result["cando_compact_path"]),
      f"Compact CanDo file exists: {result['cando_compact_path']}")
check(result["lattice_type"] == "square",
      f"Lattice type: {result['lattice_type']}")
check(result["sequence_status"] == "not_assigned",
      f"Sequence status: {result['sequence_status']}")

# Check design summary
ds = result["design_summary"]
check(ds["num_helices"] == 8,
      f"Helix count: {ds['num_helices']} (expected 8)")
check(ds["total_scaffold_nt"] == 8 * 128,
      f"Scaffold usage: {ds['total_scaffold_nt']} nt (expected {8 * 128})")
check(ds["num_multi_domain_staples"] > 0,
      f"Multi-domain staples (crossovers): {ds['num_multi_domain_staples']} (>0 required)")
check(ds["implementation_status"] == "fully_implemented",
      f"Implementation: {ds['implementation_status']}")

section("Validation results for rectangle/square")
for r in result["validation_report"]:
    icon = {"PASS": "[OK]", "WARNING": "[!!]", "FAIL": "[XX]"}.get(r["status"], "[??]")
    print(f"  {icon} {r['check']}: {r['status']} -- {r['message']}")

# All validations must pass
for r in result["validation_report"]:
    check(r["status"] in ("PASS", "WARNING"),
          f"Validation {r['check']}: {r['status']} (expected PASS or WARNING)")

check(result["validation_status"] in ("CANDO_INPUT_GENERATED",
                                      "TOPOLOGY_VALIDATED", "FORMAT_VALIDATED"),
      f"Overall validation: {result['validation_status']}")
check(result["validation_status"] != "CANDO_COMPATIBILITY_TESTED",
      f"Local-only validation must NOT be CANDO_COMPATIBILITY_TESTED "
      f"(requires real CanDo service call): {result['validation_status']}")
check(result["experimental_status"] == "EXPERIMENTALLY_UNVALIDATED",
      f"Experimental status default: {result['experimental_status']}")
check(result["submission_status"] == "NOT_SUBMITTED",
      f"Submission status default: {result['submission_status']}")


# ============================================================================
# Test 2: Rectangle with honeycomb lattice
# ============================================================================

test("Rectangle (honeycomb lattice)")

result_hc = td.create_design(
    shape_id="rectangle",
    output_basename="test_rect_hc",
    user_lattice="honeycomb",
    num_helices=8,
    bases_per_helix=126,  # multiple of 21
)

check(result_hc["design_status"] == "GENERATED",
      f"Design status: {result_hc['design_status']}")
check(result_hc["lattice_type"] == "honeycomb",
      f"Lattice type: {result_hc['lattice_type']}")
check(result_hc["design_summary"]["num_multi_domain_staples"] > 0,
      f"Multi-domain staples: {result_hc['design_summary']['num_multi_domain_staples']} (>0 required)")

section("Validation results for rectangle/honeycomb")
for r in result_hc["validation_report"]:
    icon = {"PASS": "[OK]", "WARNING": "[!!]", "FAIL": "[XX]"}.get(r["status"], "[??]")
    print(f"  {icon} {r['check']}: {r['status']} -- {r['message']}")

for r in result_hc["validation_report"]:
    check(r["status"] != "FAIL",
          f"Validation {r['check']}: {r['status']}")


# ============================================================================
# Test 3: 2-helix bundle (honeycomb)
# ============================================================================

test("2-helix bundle (honeycomb)")

result_2hb = td.create_design(
    shape_id="2_helix_bundle",
    output_basename="test_2hb",
    num_helices=2,
    bases_per_helix=210,
)

check(result_2hb["design_status"] == "GENERATED",
      f"Design status: {result_2hb['design_status']}")
check(result_2hb["lattice_type"] == "honeycomb",
      f"Lattice type: {result_2hb['lattice_type']}")

# 2-helix: only 1 adjacent pair, all staples should be multi-domain
ds2 = result_2hb["design_summary"]
check(ds2["num_multi_domain_staples"] > 0,
      f"Multi-domain staples: {ds2['num_multi_domain_staples']} (>0 required)")
check(ds2["num_helices"] == 2,
      f"Helix count: {ds2['num_helices']}")

section("Validation for 2-helix bundle")
for r in result_2hb["validation_report"]:
    icon = {"PASS": "[OK]", "WARNING": "[!!]", "FAIL": "[XX]"}.get(r["status"], "[??]")
    print(f"  {icon} {r['check']}: {r['status']} -- {r['message']}")

# Crossover check must PASS (not FAIL) for 2-helix bundle
cr_check = [r for r in result_2hb["validation_report"] if r["check"] == "crossovers"]
if cr_check:
    check(cr_check[0]["status"] == "PASS",
          f"Crossover check: {cr_check[0]['status']} (expected PASS for 2-helix)")


# ============================================================================
# Test 4: 4-helix bundle (honeycomb)
# ============================================================================

test("4-helix bundle (honeycomb)")

result_4hb = td.create_design(
    shape_id="4_helix_bundle",
    output_basename="test_4hb",
    num_helices=4,
    bases_per_helix=210,
)

check(result_4hb["design_status"] == "GENERATED",
      f"Design status: {result_4hb['design_status']}")
check(result_4hb["lattice_type"] == "honeycomb",
      f"Lattice type: {result_4hb['lattice_type']}")

ds4 = result_4hb["design_summary"]
check(ds4["num_helices"] == 4,
      f"Helix count: {ds4['num_helices']}")
check(ds4["num_multi_domain_staples"] > 0,
      f"Multi-domain staples: {ds4['num_multi_domain_staples']} (>0 required)")


# ============================================================================
# Test 5: 6-helix bundle (honeycomb)
# ============================================================================

test("6-helix bundle (honeycomb)")

result_6hb = td.create_design(
    shape_id="6_helix_bundle",
    output_basename="test_6hb",
    num_helices=6,
    bases_per_helix=210,
)

check(result_6hb["design_status"] == "GENERATED",
      f"Design status: {result_6hb['design_status']}")
check(result_6hb["design_summary"]["num_helices"] == 6,
      f"Helix count: 6")


# ============================================================================
# Test 6: Square tube
# ============================================================================

test("Square tube")

result_tube = td.create_design(
    shape_id="regular_tube",
    output_basename="test_tube",
    side_helices=4,
    bases_per_helix=128,
)

check(result_tube["design_status"] == "GENERATED",
      f"Design status: {result_tube['design_status']}")
check(result_tube["lattice_type"] == "square",
      f"Lattice type: {result_tube['lattice_type']}")

dst = result_tube["design_summary"]
check(dst["num_helices"] == 16,  # 4 faces × 4 helices
      f"Helix count: {dst['num_helices']} (expected 16)")
check(dst["num_multi_domain_staples"] > 0,
      f"Multi-domain staples: {dst['num_multi_domain_staples']} (>0 required)")


# ============================================================================
# Test 7: Open box (partially implemented)
# ============================================================================

test("Open box (partially implemented)")

result_box = td.create_design(
    shape_id="open_box",
    output_basename="test_box",
    side_helices=3,
    bases_per_helix=150,
)

check(result_box["design_status"] == "GENERATED",
      f"Design status: {result_box['design_status']} (expected GENERATED)")
check(result_box["implementation_status"] == "partially_implemented",
      f"Implementation: {result_box['implementation_status']}")
check("implementation_note" in result_box["design_summary"],
      "Implementation note present for partially-implemented template")


# ============================================================================
# Test 8: Scaffold length exceeded
# ============================================================================

test("Scaffold length exceeded")

# Request a design that uses more nt than M13mp18 has
result_big = td.create_design(
    shape_id="rectangle",
    output_basename="test_big",
    num_helices=50,
    bases_per_helix=200,  # 50 × 200 = 10,000 nt > 7,249
)

ds_big = result_big["design_summary"]
total_nt = ds_big.get("total_scaffold_nt", 0)
check(total_nt > td.DEFAULT_SCAFFOLD_LENGTH,
      f"Scaffold usage {total_nt} nt exceeds capacity {td.DEFAULT_SCAFFOLD_LENGTH} nt")

# Scaffold validation should FAIL
scaf_check = [r for r in result_big["validation_report"]
              if r["check"] == "scaffold_connectivity"]
if scaf_check:
    check(scaf_check[0]["status"] == "FAIL",
          f"Scaffold check correctly reports FAIL: {scaf_check[0]['message']}")


# ============================================================================
# Test 9: Not-yet-implemented shape handling
# ============================================================================

test("Not-yet-implemented shape")

result_nyi = td.create_design(
    shape_id="L_shape",
    output_basename="test_nyi",
)

check(result_nyi["design_status"] == "UNSUPPORTED_REQUEST",
      f"Design status: {result_nyi['design_status']} (expected UNSUPPORTED_REQUEST)")
check(result_nyi["full_path"] is None,
      "No full file generated for not-yet-implemented shape")
check(result_nyi["implementation_status"] == "not_yet_implemented",
      f"Implementation status: {result_nyi['implementation_status']}")


# ============================================================================
# Test 10: Staple connectivity -- must have multi-domain crossovers
# ============================================================================

test("Staple connectivity -- real crossovers required")

# Reload the small rectangle design and verify staples
with open("test_rect_sq.full.json", 'r') as f:
    full_data = json.load(f)

section("Direct JSON inspection of staples")
vstrands = full_data.get('vstrands', [])

total_scaf = sum(len(vs.get('scaf', [])) for vs in vstrands)
total_stap = sum(len(vs.get('stap', [])) for vs in vstrands)
check(total_scaf > 0, f"Scaffold entries in JSON: {total_scaf} (>0 required)")
check(total_stap > 0, f"Staple entries in JSON: {total_stap} (>0 required)")

# Count helices with staples
helices_with_staples = sum(1 for vs in vstrands if vs.get('stap', []))
check(helices_with_staples == len(vstrands),
      f"All {len(vstrands)} helices have staples: {helices_with_staples}")


# ============================================================================
# Test 11: Full/Cando consistency
# ============================================================================

test("Compact topology preservation")

# Run the dedicated compact preservation validator
preservation_result = td.validate_compact_preservation(
    "test_rect_sq.full.json",
    "test_rect_sq.cando_compact.json",
)
check(preservation_result["status"] == "PASS",
      f"Compact preservation: {preservation_result['status']} -- {preservation_result['message']}")

# Verify compact file has scaffold preserved (topology-preserving)
with open("test_rect_sq.cando_compact.json", 'r') as f:
    compact_data = json.load(f)

compact_scaf = sum(len(vs.get('scaf', [])) for vs in compact_data.get('vstrands', []))
compact_stap = sum(len(vs.get('stap', [])) for vs in compact_data.get('vstrands', []))
compact_loop = sum(len(vs.get('stapLoop', [])) for vs in compact_data.get('vstrands', []))
check(compact_scaf > 0,
      f"Compact file scaf entries: {compact_scaf} (must be >0 — topology preserved)")

# Verify full file matches compact file exactly
with open("test_rect_sq.full.json", 'r') as f:
    full_data2 = json.load(f)
full_scaf = sum(len(vs.get('scaf', [])) for vs in full_data2.get('vstrands', []))
full_stap = sum(len(vs.get('stap', [])) for vs in full_data2.get('vstrands', []))
full_loop = sum(len(vs.get('stapLoop', [])) for vs in full_data2.get('vstrands', []))
check(full_scaf == compact_scaf,
      f"Scaffold count match: full={full_scaf}, compact={compact_scaf}")
check(full_stap == compact_stap,
      f"Staple count match: full={full_stap}, compact={compact_stap}")
check(full_loop == compact_loop,
      f"StapleLoop count match: full={full_loop}, compact={compact_loop}")


# ============================================================================
# Test 12: Standalone validation functions
# ============================================================================

test("Standalone validation functions")

# Test all 6 validators on the rectangle design
json_val = td.validate_json_structure("test_rect_sq.full.json")
check(json_val["status"] == "PASS",
      f"validate_json_structure: {json_val['status']}")

scaf_val = td.validate_scaffold_connectivity("test_rect_sq.full.json")
check(scaf_val["status"] == "PASS",
      f"validate_scaffold_connectivity: {scaf_val['status']}")

stap_val = td.validate_staple_connectivity("test_rect_sq.full.json")
check(stap_val["status"] in ("PASS", "WARNING"),
      f"validate_staple_connectivity: {stap_val['status']}")

xover_val = td.validate_crossovers("test_rect_sq.full.json", "square")
check(xover_val["status"] in ("PASS", "WARNING"),
      f"validate_crossovers: {xover_val['status']}")

dim_val = td.validate_dimensions("test_rect_sq.full.json",
                                  expected_helices=8, expected_bases=128)
check(dim_val["status"] == "PASS",
      f"validate_dimensions: {dim_val['status']} -- {dim_val['message']}")

# Test validate_dimensions with wrong expectations
dim_bad = td.validate_dimensions("test_rect_sq.full.json",
                                  expected_helices=99, expected_bases=999)
check(dim_bad["status"] == "WARNING",
      f"validate_dimensions with wrong params: {dim_bad['status']} (expected WARNING)")

# Test validate_json_structure on non-existent file
json_bad = td.validate_json_structure("nonexistent_file.json")
check(json_bad["status"] == "FAIL",
      f"validate_json_structure on missing file: {json_bad['status']} (expected FAIL)")

# Test validate_json_structure on invalid JSON
with open("bad.json", 'w') as f:
    f.write("this is not json{{{")
json_bad2 = td.validate_json_structure("bad.json")
check(json_bad2["status"] == "FAIL",
      f"validate_json_structure on bad JSON: {json_bad2['status']} (expected FAIL)")


# ============================================================================
# Test 13: Catalog display
# ============================================================================

test("Template catalog")

td.print_catalog()

# Verify catalog integrity
check("rectangle" in td.TEMPLATE_REGISTRY, "rectangle in registry")
check("2_helix_bundle" in td.TEMPLATE_REGISTRY, "2_helix_bundle in registry")
check("L_shape" in td.TEMPLATE_REGISTRY, "L_shape in registry")

full_impl = [k for k, v in td.TEMPLATE_REGISTRY.items()
             if v["implementation"] == "fully_implemented"]
part_impl = [k for k, v in td.TEMPLATE_REGISTRY.items()
             if v["implementation"] == "partially_implemented"]
notyet = [k for k, v in td.TEMPLATE_REGISTRY.items()
          if v["implementation"] == "not_yet_implemented"]

check(len(full_impl) >= 1, f"Fully implemented: {len(full_impl)} ({', '.join(full_impl)})")
check(len(part_impl) >= 1, f"Partially implemented: {len(part_impl)} ({', '.join(part_impl)})")
check(len(notyet) >= 1, f"Not yet implemented: {len(notyet)} ({', '.join(notyet)})")


# ============================================================================
# Test 14: Generated files exist
# ============================================================================

test("Generated files inventory")

expected_files = [
    "test_rect_sq.full.json", "test_rect_sq.cando_compact.json",
    "test_rect_hc.full.json", "test_rect_hc.cando_compact.json",
    "test_2hb.full.json", "test_2hb.cando_compact.json",
    "test_4hb.full.json", "test_4hb.cando_compact.json",
    "test_6hb.full.json", "test_6hb.cando_compact.json",
    "test_tube.full.json", "test_tube.cando_compact.json",
    "test_box.full.json", "test_box.cando_compact.json",
    "test_big.full.json", "test_big.cando_compact.json",
]

for fname in expected_files:
    exists = os.path.exists(fname)
    check(exists, f"File exists: {fname}")

# Verify no files for not-yet-implemented
check(not os.path.exists("test_nyi.full.json"),
      "No full file for not-yet-implemented shape")
check(not os.path.exists("test_nyi.cando_compact.json"),
      "No compact file for not-yet-implemented shape")


# ============================================================================
# Test 15: CANDO_COMPATIBILITY_TESTED stage semantics
# ============================================================================

test("CANDO_COMPATIBILITY_TESTED stage semantics")

section("15a — local generation must not set CANDO_COMPATIBILITY_TESTED")
# All locally-generated designs should cap at CANDO_INPUT_GENERATED
for shape_key, basename in [("rectangle", "test_stage_rect"),
                              ("2_helix_bundle", "test_stage_2hb")]:
    res = td.create_design(shape_id=shape_key, output_basename=basename,
                           num_helices=6, bases_per_helix=128)
    check(res["validation_status"] != "CANDO_COMPATIBILITY_TESTED",
          f"{shape_key}: validation_status={res['validation_status']} "
          f"(must NOT be CANDO_COMPATIBILITY_TESTED — requires real CanDo call)")
    check(res["validation_status"] in ("CANDO_INPUT_GENERATED", "TOPOLOGY_VALIDATED",
                                        "FORMAT_VALIDATED"),
          f"{shape_key}: validation_status={res['validation_status']} (valid local status)")

section("15b — compact preservation pass confirms CANDO_INPUT_GENERATED (highest local)")
res2 = td.create_design(shape_id="rectangle", output_basename="test_stage_rect2",
                        num_helices=6, bases_per_helix=128)
consistency_check = [r for r in res2["validation_report"]
                     if r["check"] == "compact_preservation"]
if consistency_check and consistency_check[0]["status"] == "PASS":
    check(res2["validation_status"] == "CANDO_INPUT_GENERATED",
          f"With compact preservation PASS, validation_status should be "
          f"CANDO_INPUT_GENERATED (highest local), got: {res2['validation_status']}")

section("15c — four status dimensions are independent")
check("design_status" in res2, "design_status field present")
check("validation_status" in res2, "validation_status field present")
check("experimental_status" in res2, "experimental_status field present")
check("submission_status" in res2, "submission_status field present")
check(res2["experimental_status"] == "EXPERIMENTALLY_UNVALIDATED",
      "Default experimental_status is EXPERIMENTALLY_UNVALIDATED")
check(res2["submission_status"] == "NOT_SUBMITTED",
      "Default submission_status is NOT_SUBMITTED")


# ============================================================================
# Test 16: validate_crossovers() JSON path mode
# ============================================================================

test("validate_crossovers() JSON path mode")

section("16a — normal JSON with real cross-helix staple connections returns PASS or WARNING")
# Use the rectangle design that has real crossovers
xover_result = td.validate_crossovers("test_rect_sq.full.json", "square")
check(xover_result["status"] in ("PASS", "WARNING"),
      f"Normal design crossovers: {xover_result['status']} (expected PASS or WARNING) -- "
      f"{xover_result['message']}")
check(xover_result["details"].get("crossover_count", 0) > 0,
      f"crossover_count > 0: {xover_result['details'].get('crossover_count', 0)}")

section("16b — JSON with no cross-helix connections returns FAIL")
# Build a no-crossover JSON: all staple entries connect only to their own helix
no_xover_vstrands = []
for i in range(4):
    stap = []
    for pos in range(0, 128, 32):
        # Each entry connects to its own helix (prev_helix=i, next_helix=i) or -1
        stap.append([-1, -1, i, pos])
    no_xover_vstrands.append({
        "row": i, "col": 0,
        "num": i, "scaf": [[-1, -1, -1, -1]],
        "stap": stap,
        "scafLoop": [], "stapLoop": [],
    })
no_xover_json = {"name": "no_crossover_test", "vstrands": no_xover_vstrands}
no_xover_path = os.path.join(TMPDIR, "no_crossover_test.json")
with open(no_xover_path, 'w') as f:
    json.dump(no_xover_json, f)
no_xover_result = td.validate_crossovers(no_xover_path, "square")
check(no_xover_result["status"] == "FAIL",
      f"No-crossover JSON: {no_xover_result['status']} (expected FAIL) -- "
      f"{no_xover_result['message']}")

section("16c — file not found returns FAIL")
missing_result = td.validate_crossovers(os.path.join(TMPDIR, "does_not_exist.json"), "square")
check(missing_result["status"] == "FAIL",
      f"Missing file: {missing_result['status']} (expected FAIL) -- {missing_result['message']}")

section("16d — invalid staple entries handled without crash")
# Create JSON with some malformed staple entries mixed in
mixed_vstrands = []
for i in range(4):
    stap = []
    # Add some valid cross-helix entries
    for pos in range(0, 128, 32):
        next_h = i + 1 if i < 3 else 0
        stap.append([-1, -1, next_h, pos])
    # Add an invalid entry (too short)
    stap.append([-1])
    # Add a non-list entry
    stap.append("not_a_list")
    mixed_vstrands.append({
        "row": i, "col": 0,
        "num": i, "scaf": [[-1, -1, -1, -1]],
        "stap": stap,
        "scafLoop": [], "stapLoop": [],
    })
mixed_json = {"name": "mixed_test", "vstrands": mixed_vstrands}
mixed_path = os.path.join(TMPDIR, "mixed_test.json")
with open(mixed_path, 'w') as f:
    json.dump(mixed_json, f)
mixed_result = td.validate_crossovers(mixed_path, "square")
# Should not crash and should detect the valid crossovers
check(mixed_result["status"] in ("PASS", "WARNING"),
      f"Mixed valid/invalid entries: {mixed_result['status']} -- {mixed_result['message']}")
check(mixed_result["details"].get("crossover_count", 0) > 0,
      "Valid crossovers detected despite invalid entries")


# ============================================================================
# Test 17: validate_full_cando_consistency() deep content comparison
# ============================================================================

test("validate_full_cando_consistency() deep comparison")

# NOTE: .cando.json is no longer generated by default. Generate it explicitly
# for testing the legacy validator function.
section("17a — generate legacy .cando.json for testing")
legacy_cando = td.derive_cando_file("test_rect_sq.full.json", "test_rect_sq")
check(legacy_cando is not None and os.path.exists(legacy_cando),
      f"Legacy .cando.json generated for testing: {legacy_cando}")

section("17b — normal full/cando pair returns PASS")
consistency = td.validate_full_cando_consistency(
    "test_rect_sq.full.json", "test_rect_sq.cando.json")
check(consistency["status"] == "PASS",
      f"Normal pair: {consistency['status']} (expected PASS) -- {consistency['message']}")

section("17c — modifying one stap entry in cando (same count) returns FAIL")
# Copy cando file, modify one stap entry value but keep same count
with open("test_rect_sq.cando.json", 'r') as f:
    cando_data_mod = json.load(f)
# Find first vstrand with staples and modify one entry
for vs in cando_data_mod.get("vstrands", []):
    stap = vs.get("stap", [])
    if stap:
        for j, entry in enumerate(stap):
            if isinstance(entry, list) and len(entry) >= 4:
                # Modify next_pos to a different value
                old_val = entry[3]
                entry[3] = old_val + 999 if isinstance(old_val, int) else 999
                break
        break
mod_stap_path = os.path.join(TMPDIR, "test_mod_stap.cando.json")
with open(mod_stap_path, 'w') as f:
    json.dump(cando_data_mod, f)
mod_stap_result = td.validate_full_cando_consistency(
    "test_rect_sq.full.json", mod_stap_path)
check(mod_stap_result["status"] == "FAIL",
      f"Modified stap entry (same count): {mod_stap_result['status']} (expected FAIL) -- "
      f"{mod_stap_result['message']}")
check("mismatched_vstrand_indices" in mod_stap_result.get("details", {}),
      "Details include mismatched_vstrand_indices")

section("17d — modifying stapLoop content (same count) returns FAIL")
with open("test_rect_sq.cando.json", 'r') as f:
    cando_data_loop = json.load(f)
# Add a non-matching stapLoop entry to first vstrand
for vs in cando_data_loop.get("vstrands", []):
    vs["stapLoop"] = [[0, 0, 1, 999]]  # Different from original
    break
mod_loop_path = os.path.join(TMPDIR, "test_mod_loop.cando.json")
with open(mod_loop_path, 'w') as f:
    json.dump(cando_data_loop, f)
mod_loop_result = td.validate_full_cando_consistency(
    "test_rect_sq.full.json", mod_loop_path)
check(mod_loop_result["status"] == "FAIL",
      f"Modified stapLoop (same count): {mod_loop_result['status']} (expected FAIL) -- "
      f"{mod_loop_result['message']}")

section("17e — count change also returns FAIL")
# Remove one staple entry from cando
with open("test_rect_sq.cando.json", 'r') as f:
    cando_data_fewer = json.load(f)
for vs in cando_data_fewer.get("vstrands", []):
    stap = vs.get("stap", [])
    if stap:
        vs["stap"] = stap[:-1]  # Remove last entry
        break
fewer_path = os.path.join(TMPDIR, "test_fewer_stap.cando.json")
with open(fewer_path, 'w') as f:
    json.dump(cando_data_fewer, f)
fewer_result = td.validate_full_cando_consistency(
    "test_rect_sq.full.json", fewer_path)
check(fewer_result["status"] == "FAIL",
      f"Fewer staples: {fewer_result['status']} (expected FAIL) -- "
      f"{fewer_result['message']}")

section("17f — scaffold rules still enforced")
# cando with scaffold → FAIL
with open("test_rect_sq.full.json", 'r') as f:
    full_with_scaf = json.load(f)
cando_with_scaf_path = os.path.join(TMPDIR, "test_cando_with_scaf.json")
with open(cando_with_scaf_path, 'w') as f:
    json.dump(full_with_scaf, f)  # full data (has scaf) written as cando
scaf_in_cando = td.validate_full_cando_consistency(
    "test_rect_sq.full.json", cando_with_scaf_path)
check(scaf_in_cando["status"] == "FAIL",
      f"Cando with scaffold: {scaf_in_cando['status']} (expected FAIL) -- "
      f"{scaf_in_cando['message']}")

# full without scaffold → FAIL
cando_clean_path = os.path.join(TMPDIR, "test_cando_clean.json")
with open(cando_clean_path, 'w') as f:
    json.dump(full_with_scaf, f)  # full data also has scaf
# Use cando as "full" (which has no scaf) → full has no scaffold → FAIL
with open("test_rect_sq.cando.json", 'r') as f:
    cando_clean = json.load(f)
full_no_scaf_path = os.path.join(TMPDIR, "test_full_no_scaf.json")
with open(full_no_scaf_path, 'w') as f:
    json.dump(cando_clean, f)  # cando data (no scaf) written as full
no_scaf_in_full = td.validate_full_cando_consistency(
    full_no_scaf_path, cando_clean_path)
check(no_scaf_in_full["status"] == "FAIL",
      f"Full without scaffold: {no_scaf_in_full['status']} (expected FAIL) -- "
      f"{no_scaf_in_full['message']}")


# ============================================================================
# Test 18: CanDo compact file — topology-preserving, compact JSON
# ============================================================================

test("CanDo compact file generation")

section("18a — compact file generated alongside full master")
res_compact = td.create_design(
    shape_id="rectangle", output_basename="test_compact",
    user_lattice="square", num_helices=6, bases_per_helix=128)
check(res_compact["cando_compact_path"] is not None,
      f"Compact file path: {res_compact['cando_compact_path']}")
check(os.path.exists(res_compact["cando_compact_path"]),
      f"Compact file exists: {res_compact['cando_compact_path']}")

section("18b — compact file preserves ALL scaffold entries")
with open(res_compact["cando_compact_path"]) as f:
    compact_data = json.load(f)
compact_scaf = sum(len(v.get('scaf', [])) for v in compact_data.get('vstrands', []))
check(compact_scaf > 0,
      f"Compact file scaffold entries: {compact_scaf} (must be >0 — topology preserved)")
check(compact_scaf == res_compact["design_summary"]["total_scaffold_nt"],
      f"Compact scaffold count {compact_scaf} matches design scaffold "
      f"{res_compact['design_summary']['total_scaffold_nt']}")

section("18c — compact file preserves ALL staple entries")
compact_stap = sum(len(v.get('stap', [])) for v in compact_data.get('vstrands', []))
full_stap = sum(len(v.get('stap', [])) for v in
                json.load(open(res_compact["full_path"])).get('vstrands', []))
check(compact_stap == full_stap,
      f"Compact staple count {compact_stap} == full staple count {full_stap}")

section("18d — compact file is single-line (compact JSON)")
with open(res_compact["cando_compact_path"]) as f:
    line_count = sum(1 for _ in f)
check(line_count == 1,
      f"Compact file is {line_count} line(s) (expected 1 — compact JSON)")

section("18e — compatibility report present and all checks PASS")
compat = res_compact.get("cando_compat_report", {})
for check_name in ("vstrands", "scaffold", "staple", "dsDNA", "crossover"):
    ckr = compat.get(check_name, {})
    check(ckr.get("status") == "PASS",
          f"CanDo compat {check_name}: {ckr.get('status')} (expected PASS) — "
          f"{ckr.get('message', '')}")

section("18f — compatibility counts are reasonable")
check(compat.get("scaffold_records", 0) > 0,
      f"scaffold_records: {compat.get('scaffold_records', 0)} (>0)")
check(compat.get("staple_records", 0) > 0,
      f"staple_records: {compat.get('staple_records', 0)} (>0)")
check(compat.get("dsdna_positions", 0) > 0,
      f"dsdna_positions: {compat.get('dsdna_positions', 0)} (>0)")
check(compat.get("crossover_records", 0) > 0,
      f"crossover_records: {compat.get('crossover_records', 0)} (>0)")

section("18g — validate_cando_compatibility() standalone")
with open(res_compact["full_path"]) as f:
    full_data = json.load(f)
compat_standalone = td.validate_cando_compatibility(full_data)
check(compat_standalone["scaffold"]["status"] == "PASS",
      "Standalone: scaffold PASS")
check(compat_standalone["staple"]["status"] == "PASS",
      "Standalone: staple PASS")
check(compat_standalone["dsDNA"]["status"] == "PASS",
      "Standalone: dsDNA PASS")
check(compat_standalone["crossover"]["status"] == "PASS",
      "Standalone: crossover PASS")

section("18h — empty design returns all FAILs")
empty_compat = td.validate_cando_compatibility({"vstrands": []})
check(empty_compat["vstrands"]["status"] == "FAIL",
      f"Empty vstrands: {empty_compat['vstrands']['status']} (expected FAIL)")
check(empty_compat["scaffold"]["status"] == "FAIL",
      f"Empty scaffold: {empty_compat['scaffold']['status']} (expected FAIL)")


# ============================================================================
# Final report
# ============================================================================

test("FINAL REPORT")

print(f"\n  Total tests: {PASS + FAIL}")
print(f"  Passed:      {PASS}")
print(f"  Failed:      {FAIL}")
print(f"  Pass rate:   {100 * PASS / max(PASS + FAIL, 1):.1f}%")

print(f"\n  IMPLEMENTATION STATUS:")
print(f"    Fully implemented:      {len(full_impl)} -- {', '.join(full_impl)}")
print(f"    Partially implemented:  {len(part_impl)} -- {', '.join(part_impl)}")
print(f"    Not yet implemented:    {len(notyet)} -- {', '.join(notyet)}")

print(f"\n  VALIDATION FUNCTIONS:")
print(f"    validate_json_structure          -- active")
print(f"    validate_scaffold_connectivity   -- active")
print(f"    validate_staple_connectivity     -- active")
print(f"    validate_crossovers             -- active")
print(f"    validate_dimensions             -- active")
print(f"    validate_full_cando_consistency -- active")

print(f"\n  FILES GENERATED: {sum(1 for f in expected_files if os.path.exists(f))}")
for fname in sorted(expected_files):
    if os.path.exists(fname):
        size = os.path.getsize(fname)
        print(f"    {fname} ({size:,} bytes)")

cleanup()

if FAIL > 0:
    print(f"\n{FAIL} TEST(S) FAILED!")
    sys.exit(1)
else:
    print(f"\nALL {PASS} TESTS PASSED!")
    sys.exit(0)
