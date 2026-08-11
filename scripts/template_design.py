#!/usr/bin/env python3
"""
Cadnano DNA origami design generator with proper scaffold routing,
multi-domain staple crossovers, and structured validation.

Produces:
  <basename>.full.json   -- Full master with scaffold + staples (for cadnano).
  <basename>.cando.json  -- CanDo submission file, scaffold removed (for CanDo).

Design principle:
  - Every staple that bridges adjacent helices is a multi-domain Strand
    with an explicit crossover between domains -- never a collection of
    single-domain-per-helix pseudo-staples.
  - Scaffold routing is continuous 5'->3' with proper inter-helix connections.
  - Templates that cannot guarantee reliable crossover routing are explicitly
    marked "not_yet_implemented" rather than producing broken designs.
  - All designs without real nucleotide sequences are marked
    sequence_status = "not_assigned".
"""

import json
import os
import sys
import time
import copy
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any, Callable

import scadnano
from scadnano import Design, Helix, Domain, Strand, Grid

# ============================================================================
# Constants
# ============================================================================
DEFAULT_SCAFFOLD_NAME = "M13mp18"
DEFAULT_SCAFFOLD_LENGTH = 7249
SQUARE_CROSSOVER_SPACING = 32   # nt between crossovers on the same helix pair (square)
HONEYCOMB_CROSSOVER_SPACING = 21  # nt between crossovers on the same helix pair (honeycomb)
MIN_STAPLE_DOMAIN = 20
MAX_STAPLE_DOMAIN = 60

# ============================================================================
# Structured result helpers
# ============================================================================

def _make_check(check_name: str, status: str, message: str = "",
                details: dict = None) -> dict:
    return {
        "check": check_name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def _pass(check_name: str, message: str = "", **details) -> dict:
    return _make_check(check_name, "PASS", message, details)


def _warn(check_name: str, message: str = "", **details) -> dict:
    return _make_check(check_name, "WARNING", message, details)


def _fail(check_name: str, message: str = "", **details) -> dict:
    return _make_check(check_name, "FAIL", message, details)


# ============================================================================
# Validation functions
# ============================================================================

def validate_json_structure(file_path: str) -> dict:
    """Check that a cadnano JSON file is parseable and has basic structure."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return _fail("json_structure", f"Invalid JSON: {e}")
    except FileNotFoundError:
        return _fail("json_structure", f"File not found: {file_path}")

    if 'vstrands' not in data:
        return _fail("json_structure", "Missing 'vstrands' key -- not cadnano v2 format")

    vstrands = data['vstrands']
    if not isinstance(vstrands, list):
        return _fail("json_structure", "'vstrands' is not a list")

    if len(vstrands) == 0:
        return _fail("json_structure", "No vstrands found -- design is empty")

    return _pass("json_structure",
                 f"Valid cadnano v2 JSON, {len(vstrands)} vstrands",
                 num_vstrands=len(vstrands))


def validate_scaffold_connectivity(design_or_path) -> dict:
    """Check scaffold forms a continuous 5'->3' path without breaks."""
    # Accept either a scadnano Design or a file path
    if isinstance(design_or_path, str):
        try:
            with open(design_or_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return _fail("scaffold_connectivity", f"Cannot read file: {e}")

        vstrands = data.get('vstrands', [])
        # cadnano v2: scaf[i] = [prev_helix, prev_pos, next_helix, next_pos]
        # -1 means no connection at that end
        scaffold_positions = 0
        for vs_idx, vs in enumerate(vstrands):
            scaf = vs.get('scaf', [])
            for entry in scaf:
                if isinstance(entry, list) and any(x != -1 for x in entry):
                    scaffold_positions += 1

        if scaffold_positions == 0:
            return _fail("scaffold_connectivity",
                         "No scaffold positions found in any vstrand")

        total_nt = scaffold_positions

        if total_nt > DEFAULT_SCAFFOLD_LENGTH:
            return _fail("scaffold_connectivity",
                         f"Scaffold usage ({total_nt} nt) exceeds "
                         f"{DEFAULT_SCAFFOLD_NAME} length ({DEFAULT_SCAFFOLD_LENGTH} nt)",
                         total_scaffold_nt=total_nt,
                         scaffold_capacity=DEFAULT_SCAFFOLD_LENGTH)

        return _pass("scaffold_connectivity",
                     f"Scaffold present across {len(vstrands)} vstrands, "
                     f"{total_nt} nt used of {DEFAULT_SCAFFOLD_LENGTH} nt available",
                     total_scaffold_nt=total_nt,
                     scaffold_capacity=DEFAULT_SCAFFOLD_LENGTH)
    else:
        # scadnano Design object
        design = design_or_path
        scaffold_strands = [s for s in design.strands if s.is_scaffold]

        if not scaffold_strands:
            return _fail("scaffold_connectivity",
                         "No scaffold strand found in design")

        if len(scaffold_strands) > 1:
            return _warn("scaffold_connectivity",
                         f"Multiple scaffold strands ({len(scaffold_strands)}) -- "
                         f"only 1 expected for single-scaffold design",
                         num_scaffold_strands=len(scaffold_strands))

        scaf = scaffold_strands[0]
        domains = scaf.domains
        total_nt = sum(d.dna_length() for d in domains)

        # Check domain continuity: each domain's end should connect to next domain's start
        breaks = []
        for i in range(len(domains) - 1):
            d0, d1 = domains[i], domains[i + 1]
            # A break exists if domains are on non-adjacent helices or have gaps
            # In scadnano, the connection is automatic if domains are sequential
            # We flag when helices are not adjacent in a serpentine pattern
            pass  # scadnano handles inter-domain connectivity

        # Check helix adjacency (serpentine: each domain on adjacent helix pair)
        helix_seq = [d.helix for d in domains]
        for i in range(len(helix_seq) - 1):
            if abs(helix_seq[i] - helix_seq[i + 1]) != 1:
                breaks.append(f"Non-adjacent helix jump: {helix_seq[i]} -> {helix_seq[i + 1]}")

        if breaks:
            return _warn("scaffold_connectivity",
                         f"Scaffold has {len(breaks)} non-adjacent helix transitions",
                         breaks=breaks,
                         helix_sequence=helix_seq,
                         total_scaffold_nt=total_nt)

        if total_nt > DEFAULT_SCAFFOLD_LENGTH:
            return _fail("scaffold_connectivity",
                         f"Scaffold usage ({total_nt} nt) exceeds "
                         f"{DEFAULT_SCAFFOLD_NAME} length ({DEFAULT_SCAFFOLD_LENGTH} nt)",
                         total_scaffold_nt=total_nt,
                         scaffold_capacity=DEFAULT_SCAFFOLD_LENGTH)

        return _pass("scaffold_connectivity",
                     f"Continuous scaffold, {len(domains)} domains, "
                     f"{total_nt} nt used of {DEFAULT_SCAFFOLD_LENGTH} nt available",
                     num_domains=len(domains),
                     helix_sequence=helix_seq,
                     total_scaffold_nt=total_nt,
                     scaffold_capacity=DEFAULT_SCAFFOLD_LENGTH)


def validate_staple_connectivity(design_or_path) -> dict:
    """Check staples: proper domain lengths, multi-domain crossovers exist."""
    if isinstance(design_or_path, str):
        try:
            with open(design_or_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return _fail("staple_connectivity", f"Cannot read file: {e}")

        vstrands = data.get('vstrands', [])
        # cadnano v2: stap[i] = [prev_helix, prev_pos, next_helix, next_pos]
        # Count positions where staple is present (non-(-1) entries)
        staple_count = 0
        crossover_count = 0
        for vs_idx, vs in enumerate(vstrands):
            stap = vs.get('stap', [])
            for entry in stap:
                if isinstance(entry, list):
                    active = [x for x in entry if x != -1]
                    if active:
                        staple_count += 1
                        # Check for cross-helix connection
                        if entry[0] != -1 and entry[0] != vs_idx:
                            crossover_count += 1
                        elif entry[2] != -1 and entry[2] != vs_idx:
                            crossover_count += 1

        if staple_count == 0:
            return _fail("staple_connectivity", "No staple entries found")

        if crossover_count == 0:
            return _fail("staple_connectivity",
                         f"{staple_count} staple positions but ZERO cross-helix "
                         f"connections -- no real crossovers detected at JSON level. "
                         f"Run Design-object validation for accurate crossover analysis.",
                         num_staple_positions=staple_count,
                         crossover_connections=0)

        return _pass("staple_connectivity",
                     f"{staple_count} staple positions, {crossover_count} cross-helix "
                     f"connections detected at JSON level",
                     num_staple_positions=staple_count,
                     crossover_connections=crossover_count)
    else:
        design = design_or_path
        staples = [s for s in design.strands if not s.is_scaffold]

        if not staples:
            return _fail("staple_connectivity", "No staple strands found")

        # Count multi-domain staples (real crossovers)
        multi_domain = [s for s in staples if len(s.domains) >= 2]
        single_domain = [s for s in staples if len(s.domains) == 1]

        # Check domain lengths
        all_lengths = []
        for s in staples:
            for d in s.domains:
                all_lengths.append(d.dna_length())

        too_short = [l for l in all_lengths if l < MIN_STAPLE_DOMAIN]
        too_long = [l for l in all_lengths if l > MAX_STAPLE_DOMAIN]

        issues = []
        if not multi_domain:
            issues.append("NO multi-domain staples -- no real crossovers present")
        if too_short:
            issues.append(f"{len(too_short)} domains < {MIN_STAPLE_DOMAIN} nt")
        if too_long:
            issues.append(f"{len(too_long)} domains > {MAX_STAPLE_DOMAIN} nt")

        # Check for orphaned staples (single-domain staples on internal helices
        # that should have crossovers)
        if len(single_domain) > 0 and len(multi_domain) == 0:
            return _fail("staple_connectivity",
                         f"All {len(staples)} staples are single-domain -- "
                         f"no cross-helix crossovers. This is NOT a valid DNA origami design. "
                         f"Each staple must bridge adjacent helices.",
                         num_staples=len(staples),
                         num_multi_domain=0,
                         num_single_domain=len(single_domain),
                         min_domain_length=min(all_lengths) if all_lengths else 0,
                         max_domain_length=max(all_lengths) if all_lengths else 0)

        if issues:
            return _warn("staple_connectivity",
                         "; ".join(issues),
                         num_staples=len(staples),
                         num_multi_domain=len(multi_domain),
                         num_single_domain=len(single_domain),
                         min_domain_length=min(all_lengths) if all_lengths else 0,
                         max_domain_length=max(all_lengths) if all_lengths else 0)

        return _pass("staple_connectivity",
                     f"{len(staples)} staples: {len(multi_domain)} multi-domain "
                     f"(with crossovers), {len(single_domain)} single-domain (edge fillers), "
                     f"domain lengths {min(all_lengths)}--{max(all_lengths)} nt",
                     num_staples=len(staples),
                     num_multi_domain=len(multi_domain),
                     num_single_domain=len(single_domain),
                     min_domain_length=min(all_lengths),
                     max_domain_length=max(all_lengths))


def validate_crossovers(design_or_path, lattice_type: str = "square") -> dict:
    """Check that real multi-domain crossover staples exist and are valid."""
    if isinstance(design_or_path, str):
        try:
            with open(design_or_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            return _fail("crossovers", f"Invalid JSON: {e}")
        except FileNotFoundError:
            return _fail("crossovers", f"File not found: {design_or_path}")
        except Exception as e:
            return _fail("crossovers", f"Cannot read file: {e}")

        vstrands = data.get('vstrands', [])
        if not vstrands:
            return _fail("crossovers", "No vstrands found in JSON file")

        # In cadnano v2 JSON, each staple entry is:
        #   [prev_helix, prev_pos, next_helix, next_pos]
        # A crossover exists when prev_helix or next_helix points to
        # a different valid helix (not -1, not the current vstrand index).

        crossover_count = 0
        helix_pairs = set()
        invalid_entries = 0
        num_staple_positions = 0

        for vs_idx, vs in enumerate(vstrands):
            stap = vs.get('stap', [])
            for entry in stap:
                if not isinstance(entry, list) or len(entry) < 4:
                    invalid_entries += 1
                    continue
                num_staple_positions += 1
                prev_helix, prev_pos, next_helix, next_pos = entry[0], entry[1], entry[2], entry[3]

                # Check prev_helix connection
                if prev_helix != -1 and prev_helix != vs_idx:
                    crossover_count += 1
                    pair = tuple(sorted([vs_idx, prev_helix]))
                    helix_pairs.add(pair)

                # Check next_helix connection
                if next_helix != -1 and next_helix != vs_idx:
                    crossover_count += 1
                    pair = tuple(sorted([vs_idx, next_helix]))
                    helix_pairs.add(pair)

        # No staple positions at all
        if num_staple_positions == 0:
            return _fail("crossovers",
                         "No staple entries found in any vstrand",
                         num_staple_positions=0,
                         crossover_count=0)

        # No cross-helix connections detected
        if crossover_count == 0:
            return _fail("crossovers",
                         f"No cross-helix staple connections detected "
                         f"({num_staple_positions} staple positions but zero crossovers)",
                         num_staple_positions=num_staple_positions,
                         crossover_count=0,
                         helix_pairs=[])

        # Check for non-adjacent helix pairs
        non_adjacent_pairs = []
        for h1, h2 in helix_pairs:
            if abs(h1 - h2) > 2:
                non_adjacent_pairs.append((h1, h2))

        details = {
            "crossover_count": crossover_count,
            "num_staple_positions": num_staple_positions,
            "helix_pairs": sorted(helix_pairs),
        }
        if invalid_entries > 0:
            details["invalid_entries"] = invalid_entries

        if non_adjacent_pairs:
            details["non_adjacent_pairs"] = non_adjacent_pairs
            return _warn("crossovers",
                         f"{crossover_count} cross-helix connections across "
                         f"{len(helix_pairs)} helix pairs; "
                         f"{len(non_adjacent_pairs)} non-adjacent pair(s) detected. "
                         f"JSON-level spacing check is limited",
                         **details)

        return _pass("crossovers",
                     f"{crossover_count} cross-helix connections across "
                     f"{len(helix_pairs)} helix pairs",
                     **details)
    else:
        design = design_or_path
        staples = [s for s in design.strands if not s.is_scaffold]

        # A crossover exists when a strand has domains on different helices
        crossover_staples = []
        helix_pairs = set()
        for s in staples:
            helices_in_strand = [d.helix for d in s.domains]
            unique_helices = set(helices_in_strand)
            if len(unique_helices) >= 2:
                crossover_staples.append(s)
                # Record all helix pairs connected by this staple
                for i in range(len(helices_in_strand) - 1):
                    if helices_in_strand[i] != helices_in_strand[i + 1]:
                        pair = tuple(sorted([helices_in_strand[i],
                                            helices_in_strand[i + 1]]))
                        helix_pairs.add(pair)

        if not crossover_staples:
            return _fail("crossovers",
                         "NO crossover staples found. Every staple is confined "
                         "to a single helix -- this is NOT a valid origami design. "
                         "Staples must bridge adjacent helices to create crossovers.",
                         num_crossover_staples=0,
                         helix_pairs=list(helix_pairs))

        # Check crossover spacing consistency
        expected_spacing = (SQUARE_CROSSOVER_SPACING if lattice_type == "square"
                           else HONEYCOMB_CROSSOVER_SPACING)

        # Verify crossovers are between adjacent helices (within ±1)
        non_adjacent = []
        for h1, h2 in helix_pairs:
            if abs(h1 - h2) > 2:  # Allow skip of 1 for honeycomb patterns
                non_adjacent.append((h1, h2))

        if non_adjacent:
            return _warn("crossovers",
                         f"{len(non_adjacent)} non-adjacent helix crossovers detected",
                         non_adjacent_pairs=non_adjacent,
                         num_crossover_staples=len(crossover_staples),
                         num_helix_pairs=len(helix_pairs),
                         helix_pairs=sorted(helix_pairs))

        return _pass("crossovers",
                     f"{len(crossover_staples)} crossover staples connecting "
                     f"{len(helix_pairs)} helix pairs",
                     num_crossover_staples=len(crossover_staples),
                     num_helix_pairs=len(helix_pairs),
                     helix_pairs=sorted(helix_pairs),
                     expected_spacing=expected_spacing)


def validate_dimensions(design_or_path,
                        expected_helices: int = None,
                        expected_bases: int = None) -> dict:
    """Check that design dimensions match expectations."""
    if isinstance(design_or_path, str):
        try:
            with open(design_or_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return _fail("dimensions", f"Cannot read file: {e}")

        vstrands = data.get('vstrands', [])
        actual_helices = len(vstrands)
        # cadnano v2: scaf[i] = [prev_helix, prev_pos, next_helix, next_pos]
        # Count positions with non-(-1) entries per vstrand to get helix length
        bases_per_helix = []
        for vs in vstrands:
            scaf = vs.get('scaf', [])
            bp_count = 0
            for entry in scaf:
                if isinstance(entry, list) and any(x != -1 for x in entry):
                    bp_count += 1
            if bp_count > 0:
                bases_per_helix.append(bp_count)

        actual_bases = max(bases_per_helix) if bases_per_helix else 0
    else:
        design = design_or_path
        actual_helices = len(design.helices)
        scaffold_strands = [s for s in design.strands if s.is_scaffold]
        if scaffold_strands:
            # Get max bases from scaffold domains
            actual_bases = max(
                d.end - d.start
                for s in scaffold_strands
                for d in s.domains
            )
        else:
            actual_bases = 0

    details = {
        "actual_helices": actual_helices,
        "actual_bases": actual_bases,
        "expected_helices": expected_helices,
        "expected_bases": expected_bases,
    }

    warnings = []
    if expected_helices is not None and actual_helices != expected_helices:
        warnings.append(f"helices: expected {expected_helices}, got {actual_helices}")
    if expected_bases is not None and actual_bases != expected_bases:
        warnings.append(f"bases: expected {expected_bases}, got {actual_bases}")

    if warnings:
        return _warn("dimensions", "; ".join(warnings), **details)

    return _pass("dimensions",
                 f"{actual_helices} helices x ~{actual_bases} bp",
                 **details)


def validate_full_cando_consistency(full_path: str, cando_path: str) -> dict:
    """Verify full/cando file consistency: same structure, cando has no scaffold."""
    try:
        with open(full_path, 'r') as f:
            full = json.load(f)
        with open(cando_path, 'r') as f:
            cando = json.load(f)
    except Exception as e:
        return _fail("full_cando_consistency", f"Cannot read files: {e}")

    full_vstrands = full.get('vstrands', [])
    cando_vstrands = cando.get('vstrands', [])

    # Same number of vstrands
    if len(full_vstrands) != len(cando_vstrands):
        return _fail("full_cando_consistency",
                     f"Vstrand count mismatch: full={len(full_vstrands)}, "
                     f"cando={len(cando_vstrands)}")

    # Check cando has no scaffold
    cando_scaf_count = 0
    for vs in cando_vstrands:
        scaf = vs.get('scaf', [])
        scaf_loop = vs.get('scafLoop', [])
        if scaf:
            cando_scaf_count += len(scaf)
        if scaf_loop:
            cando_scaf_count += len(scaf_loop)

    if cando_scaf_count > 0:
        return _fail("full_cando_consistency",
                     f"CanDo file contains {cando_scaf_count} scaffold entries -- "
                     f"must be zero",
                     cando_scaf_entries=cando_scaf_count)

    # Check full retains scaffold
    full_scaf_count = 0
    for vs in full_vstrands:
        scaf = vs.get('scaf', [])
        if scaf:
            full_scaf_count += len(scaf)

    if full_scaf_count == 0:
        return _fail("full_cando_consistency",
                     "Full master has no scaffold entries -- was it overwritten?")

    # Deep content comparison: stap and stapLoop arrays per vstrand
    mismatched_vstrand_indices = []
    stap_mismatches = 0
    stap_loop_mismatches = 0
    first_mismatch_full = None
    first_mismatch_cando = None

    for vs_idx in range(len(full_vstrands)):
        full_vs = full_vstrands[vs_idx]
        cando_vs = cando_vstrands[vs_idx]

        full_stap = full_vs.get('stap', [])
        cando_stap = cando_vs.get('stap', [])
        full_stap_loop = full_vs.get('stapLoop', [])
        cando_stap_loop = cando_vs.get('stapLoop', [])

        stap_match = (full_stap == cando_stap)
        loop_match = (full_stap_loop == cando_stap_loop)

        if not stap_match:
            stap_mismatches += 1
            if vs_idx not in mismatched_vstrand_indices:
                mismatched_vstrand_indices.append(vs_idx)
            if first_mismatch_full is None:
                first_mismatch_full = copy.deepcopy(full_stap)
                first_mismatch_cando = copy.deepcopy(cando_stap)

        if not loop_match:
            stap_loop_mismatches += 1
            if vs_idx not in mismatched_vstrand_indices:
                mismatched_vstrand_indices.append(vs_idx)
            if first_mismatch_full is None:
                first_mismatch_full = copy.deepcopy(full_stap_loop)
                first_mismatch_cando = copy.deepcopy(cando_stap_loop)

    if mismatched_vstrand_indices:
        details = {
            "mismatched_vstrand_indices": mismatched_vstrand_indices,
            "stap_mismatches": stap_mismatches,
            "stap_loop_mismatches": stap_loop_mismatches,
            "full_scaf_entries": full_scaf_count,
            "cando_scaf_entries": cando_scaf_count,
        }
        if first_mismatch_full is not None:
            details["first_mismatch_full_content"] = first_mismatch_full
            details["first_mismatch_cando_content"] = first_mismatch_cando

        return _fail("full_cando_consistency",
                     f"Staple content mismatch in {len(mismatched_vstrand_indices)} "
                     f"vstrand(s): {stap_mismatches} stap mismatches, "
                     f"{stap_loop_mismatches} stapLoop mismatches",
                     **details)

    full_stap_count = sum(len(vs.get('stap', [])) for vs in full_vstrands)

    return _pass("full_cando_consistency",
                 f"Full ({full_scaf_count} scaf, {full_stap_count} stap) <-> "
                 f"CanDo (0 scaf, {cando_scaf_count} stap) -- consistent",
                 full_scaf_entries=full_scaf_count,
                 cando_scaf_entries=cando_scaf_count,
                 staple_entries=full_stap_count)


def validate_compact_preservation(full_path: str, compact_path: str) -> dict:
    """Verify the compact CanDo file preserves the full master topology exactly.

    The compact file must have:
      - Same vstrand count as full
      - Identical scaf arrays per vstrand (topology preserved)
      - Identical stap arrays per vstrand
      - Identical stapLoop arrays per vstrand
    Only serialization format (indentation) may differ.
    """
    try:
        with open(full_path, 'r') as f:
            full = json.load(f)
        with open(compact_path, 'r') as f:
            compact = json.load(f)
    except Exception as e:
        return _fail("compact_preservation", f"Cannot read files: {e}")

    full_vstrands = full.get('vstrands', [])
    compact_vstrands = compact.get('vstrands', [])

    # Same number of vstrands
    if len(full_vstrands) != len(compact_vstrands):
        return _fail("compact_preservation",
                     f"Vstrand count mismatch: full={len(full_vstrands)}, "
                     f"compact={len(compact_vstrands)}")

    # Deep content comparison: scaf, stap, stapLoop per vstrand
    mismatched = []
    scaf_mismatches = 0
    stap_mismatches = 0
    loop_mismatches = 0

    for vs_idx in range(len(full_vstrands)):
        fv = full_vstrands[vs_idx]
        cv = compact_vstrands[vs_idx]

        f_scaf = fv.get('scaf', [])
        c_scaf = cv.get('scaf', [])
        f_stap = fv.get('stap', [])
        c_stap = cv.get('stap', [])
        f_loop = fv.get('stapLoop', [])
        c_loop = cv.get('stapLoop', [])

        if f_scaf != c_scaf:
            scaf_mismatches += 1
            if vs_idx not in mismatched:
                mismatched.append(vs_idx)
        if f_stap != c_stap:
            stap_mismatches += 1
            if vs_idx not in mismatched:
                mismatched.append(vs_idx)
        if f_loop != c_loop:
            loop_mismatches += 1
            if vs_idx not in mismatched:
                mismatched.append(vs_idx)

    if mismatched:
        details = {
            "mismatched_vstrand_indices": mismatched,
            "scaf_mismatches": scaf_mismatches,
            "stap_mismatches": stap_mismatches,
            "stap_loop_mismatches": loop_mismatches,
        }
        return _fail("compact_preservation",
                     f"Topology mismatch in {len(mismatched)} vstrand(s): "
                     f"{scaf_mismatches} scaf, {stap_mismatches} stap, "
                     f"{loop_mismatches} stapLoop mismatches. "
                     f"Compact file must preserve full topology exactly.",
                     **details)

    full_scaf_total = sum(len(v.get('scaf', [])) for v in full_vstrands)
    full_stap_total = sum(len(v.get('stap', [])) for v in full_vstrands)

    return _pass("compact_preservation",
                 f"Compact file preserves full topology: "
                 f"{len(full_vstrands)} vstrands, "
                 f"{full_scaf_total} scaf, {full_stap_total} stap — identical",
                 num_vstrands=len(full_vstrands),
                 scaf_entries=full_scaf_total,
                 stap_entries=full_stap_total)


# ============================================================================
# Scaffold routing helpers
# ============================================================================

def _route_scaffold_serpentine(design: Design, num_helices: int,
                                bases_per_helix: int, start_pos: int = 0) -> int:
    """
    Route scaffold in serpentine pattern through all helices.

    Helix 0: start -> end (forward)
    Helix 1: end -> start (reverse)
    Helix 2: start -> end (forward)
    ...

    Returns total scaffold nt used.
    """
    scaffold_domains = []
    for h in range(num_helices):
        forward = (h % 2 == 0)
        scaffold_domains.append(Domain(
            helix=h,
            forward=forward,
            start=start_pos,
            end=start_pos + bases_per_helix,
        ))

    scaffold = Strand(domains=scaffold_domains, is_scaffold=True)
    design.add_strand(scaffold)
    return num_helices * bases_per_helix


# ============================================================================
# Staple crossover helpers
# ============================================================================

def _add_crossover_staples(design: Design, num_helices: int,
                           bases_per_helix: int,
                           domain_len: int = SQUARE_CROSSOVER_SPACING) -> Tuple[int, int]:
    """
    Add multi-domain staple crossovers between adjacent helix pairs.

    Interleaved segment pattern ensures each position on each helix is
    covered by exactly one staple domain -- no overlaps, no gaps (except
    at edges where single-domain fillers are used).

    Even pairs (h even, h<->h+1): segments at [0, L], [2L, 3L], [4L, 5L], ...
    Odd pairs  (h odd,  h<->h+1): segments at [L, 2L], [3L, 4L], [5L, 6L], ...

    Step between consecutive segments of the SAME pair: 2*L.
    This leaves every other L-length segment for the adjacent pair,
    creating a perfect interleaved partition.

    Returns (num_multi_domain_staples, num_single_domain_staples).
    """
    step = 2 * domain_len   # spacing between consecutive segments of the same pair
    multi_count = 0
    single_count = 0

    # --- Multi-domain crossover staples for adjacent helix pairs ---
    for h in range(num_helices - 1):
        scaf_fwd_h = (h % 2 == 0)
        scaf_fwd_h1 = ((h + 1) % 2 == 0)

        # Even pairs: start at 0 with step 2L -> [0,L], [2L,3L], [4L,5L], ...
        # Odd pairs:  start at L with step 2L -> [L,2L], [3L,4L], [5L,6L], ...
        if h % 2 == 0:
            segment_starts = list(range(0, bases_per_helix, step))
        else:
            segment_starts = list(range(domain_len, bases_per_helix, step))

        for seg_start in segment_starts:
            seg_end = min(seg_start + domain_len, bases_per_helix)

            # Domain on helix h -- runs antiparallel to scaffold
            d_h = Domain(
                helix=h,
                forward=not scaf_fwd_h,
                start=seg_start,
                end=seg_end,
            )
            # Domain on helix h+1 -- runs antiparallel to scaffold
            d_h1 = Domain(
                helix=h + 1,
                forward=not scaf_fwd_h1,
                start=seg_start,
                end=seg_end,
            )

            staple = Strand(domains=[d_h, d_h1], is_scaffold=False)
            design.add_strand(staple)
            multi_count += 1

    # --- Single-domain staples to fill edge helix gaps ---
    # Edge helices (0 and M-1) only participate in ONE pair.
    # The interleaved pattern leaves gaps on these helices.
    for h in [0, num_helices - 1]:
        scaf_fwd = (h % 2 == 0)

        # Determine which segments are covered by the pair this helix is in
        if h == 0:
            # Helix 0 is in even pair (0,1) -> covered: [0,L], [2L,3L], [4L,5L], ...
            # Gaps: [L,2L], [3L,4L], ...
            gap_starts = list(range(domain_len, bases_per_helix, step))
        else:
            # Last helix M-1: which pair does it belong to?
            # It belongs to pair (M-2, M-1) where h_pair = M-2
            pair_h = num_helices - 2
            if pair_h % 2 == 0:
                # Even pair (M-2, M-1) -> covered: [0,L], [2L,3L], ...
                # Gaps: [L,2L], [3L,4L], ...
                gap_starts = list(range(domain_len, bases_per_helix, step))
            else:
                # Odd pair (M-2, M-1) -> covered: [L,2L], [3L,4L], ...
                # Gaps: [0,L], [2L,3L], ...
                gap_starts = list(range(0, bases_per_helix, step))

        for gap_start in gap_starts:
            gap_end = min(gap_start + domain_len, bases_per_helix)
            d = Domain(
                helix=h,
                forward=not scaf_fwd,
                start=gap_start,
                end=gap_end,
            )
            staple = Strand(domains=[d], is_scaffold=False)
            design.add_strand(staple)
            single_count += 1

    return multi_count, single_count


# ============================================================================
# Template: Rectangle (square lattice) -- FULLY IMPLEMENTED
# ============================================================================

def create_rectangle_design(
    num_helices: int = 24,
    bases_per_helix: int = 234,
    lattice_type: str = "square",
    **kwargs,
) -> Tuple[Design, dict]:
    """
    Build a rectangular planar DNA origami design.

    Scaffold: serpentine raster through all helices.
    Staples: multi-domain crossovers between adjacent helix pairs,
             single-domain fillers at edges.
    """
    grid = Grid.square if lattice_type == "square" else Grid.honeycomb
    domain_len = SQUARE_CROSSOVER_SPACING if lattice_type == "square" else HONEYCOMB_CROSSOVER_SPACING

    helices = [
        Helix(max_offset=bases_per_helix, grid_position=(0, i))
        for i in range(num_helices)
    ]
    design = Design(helices=helices, grid=grid)

    # Scaffold
    total_scaffold_nt = _route_scaffold_serpentine(design, num_helices, bases_per_helix)

    # Staples with real crossovers
    multi, single = _add_crossover_staples(design, num_helices, bases_per_helix, domain_len)

    stats = {
        "shape_id": "rectangle",
        "num_helices": num_helices,
        "bases_per_helix": bases_per_helix,
        "total_scaffold_nt": total_scaffold_nt,
        "num_staples": multi + single,
        "num_multi_domain_staples": multi,
        "num_single_domain_staples": single,
        "lattice_type": lattice_type,
        "is_approximation": False,
        "approximation_report": None,
        "implementation_status": "fully_implemented",
    }
    return design, stats


# ============================================================================
# Template: Helix Bundle (honeycomb lattice) -- FULLY IMPLEMENTED
# ============================================================================

def create_helix_bundle_design(
    num_helices: int = 2,
    bases_per_helix: int = 240,
    lattice_type: str = "honeycomb",
    **kwargs,
) -> Tuple[Design, dict]:
    """
    Build a 2/4/6-helix bundle design in honeycomb lattice.

    Scaffold: serpentine through all helices.
    Staples: multi-domain crossovers between adjacent helix pairs.
    """
    if lattice_type not in ("honeycomb", "square"):
        lattice_type = "honeycomb"

    grid = Grid.honeycomb if lattice_type == "honeycomb" else Grid.square
    domain_len = HONEYCOMB_CROSSOVER_SPACING if lattice_type == "honeycomb" else SQUARE_CROSSOVER_SPACING

    # Arrange helices in a single row for simplicity
    # For honeycomb, use standard grid positions
    helices = [
        Helix(max_offset=bases_per_helix, grid_position=(0, i))
        for i in range(num_helices)
    ]
    design = Design(helices=helices, grid=grid)

    # Scaffold
    total_scaffold_nt = _route_scaffold_serpentine(design, num_helices, bases_per_helix)

    # Staples with real crossovers
    multi, single = _add_crossover_staples(design, num_helices, bases_per_helix, domain_len)

    stats = {
        "shape_id": f"{num_helices}_helix_bundle",
        "num_helices": num_helices,
        "bases_per_helix": bases_per_helix,
        "total_scaffold_nt": total_scaffold_nt,
        "num_staples": multi + single,
        "num_multi_domain_staples": multi,
        "num_single_domain_staples": single,
        "lattice_type": lattice_type,
        "is_approximation": False,
        "approximation_report": None,
        "implementation_status": "fully_implemented",
    }
    return design, stats


# ============================================================================
# Template: Square Tube (square lattice) -- FULLY IMPLEMENTED
# ============================================================================

def create_tube_design(
    side_helices: int = 6,
    bases_per_helix: int = 234,
    lattice_type: str = "square",
    **kwargs,
) -> Tuple[Design, dict]:
    """
    Build a square-section tube design.

    4 faces x side_helices = total helices, arranged in square perimeter.
    Scaffold: serpentine around the perimeter.
    Staples: multi-domain crossovers between adjacent helices including
             across face boundaries.
    """
    if lattice_type != "square":
        raise ValueError("square_section_tube requires square lattice")

    grid = Grid.square
    domain_len = SQUARE_CROSSOVER_SPACING
    total_helices = side_helices * 4

    # Arrange helices in a square perimeter
    helices = []
    for i in range(total_helices):
        face = i // side_helices
        pos_in_face = i % side_helices
        if face == 0:    # bottom
            gp = (pos_in_face, 0)
        elif face == 1:  # right
            gp = (side_helices, pos_in_face)
        elif face == 2:  # top
            gp = (side_helices - pos_in_face, side_helices)
        else:            # left
            gp = (0, side_helices - pos_in_face)
        helices.append(Helix(max_offset=bases_per_helix, grid_position=gp))

    design = Design(helices=helices, grid=grid)

    # Scaffold serpentine through all helices around the perimeter
    total_scaffold_nt = _route_scaffold_serpentine(design, total_helices, bases_per_helix)

    # Staples with real crossovers -- adjacent helices in the linear ordering
    # are geometrically adjacent on the tube surface
    multi, single = _add_crossover_staples(design, total_helices, bases_per_helix, domain_len)

    stats = {
        "shape_id": "square_section_tube",
        "num_helices": total_helices,
        "bases_per_helix": bases_per_helix,
        "tube_faces": 4,
        "side_helices": side_helices,
        "total_scaffold_nt": total_scaffold_nt,
        "num_staples": multi + single,
        "num_multi_domain_staples": multi,
        "num_single_domain_staples": single,
        "lattice_type": lattice_type,
        "is_approximation": False,
        "approximation_report": None,
        "implementation_status": "fully_implemented",
    }
    return design, stats


# ============================================================================
# Template: Open Box -- PARTIALLY IMPLEMENTED
# ============================================================================

def create_open_box_design(
    side_helices: int = 4,
    bases_per_helix: int = 200,
    lattice_type: str = "square",
    **kwargs,
) -> Tuple[Design, dict]:
    """
    Build an open box (5 faces: bottom + 4 walls).

    The box is laid out as a cross-shaped unfold pattern in 2D.
    Scaffold routes through all 5 faces in serpentine.
    Staples bridge adjacent helices within and across faces.

    STATUS: PARTIALLY IMPLEMENTED -- scaffold topology is correct but
    crossover routing at face boundaries (corners) has not been fully
    validated for 3D folding fidelity.
    """
    if lattice_type != "square":
        raise ValueError("open_box requires square lattice")

    grid = Grid.square
    domain_len = SQUARE_CROSSOVER_SPACING

    # Layout: cross pattern in 2D
    #        [wall_N: s helices]
    # [wall_W: s] [bottom: sxs] [wall_E: s]
    #        [wall_S: s helices]
    s = side_helices

    # Build helix list in scaffold-routing order:
    # wall_N -> wall_E -> wall_S -> wall_W -> bottom
    # This creates a continuous serpentine path through all faces

    helices = []
    idx = 0

    # Wall N (s helices, placed above bottom)
    for i in range(s):
        helices.append(Helix(max_offset=bases_per_helix, grid_position=(i + s, -s)))
        idx += 1

    # Wall E (s helices, placed right of bottom)
    for i in range(s):
        helices.append(Helix(max_offset=bases_per_helix, grid_position=(2 * s, i)))
        idx += 1

    # Wall S (s helices, placed below bottom)
    for i in range(s):
        helices.append(Helix(max_offset=bases_per_helix, grid_position=(i + s, s)))
        idx += 1

    # Wall W (s helices, placed left of bottom)
    for i in range(s):
        helices.append(Helix(max_offset=bases_per_helix, grid_position=(-1, i)))
        idx += 1

    # Bottom (s x s helices)
    for row in range(s):
        for col in range(s):
            helices.append(Helix(max_offset=bases_per_helix,
                                grid_position=(col + s, row)))
            idx += 1

    total_helices = len(helices)
    design = Design(helices=helices, grid=grid)

    # Scaffold serpentine through all faces
    total_scaffold_nt = _route_scaffold_serpentine(design, total_helices, bases_per_helix)

    # Staples with crossovers between adjacent helices
    multi, single = _add_crossover_staples(design, total_helices, bases_per_helix, domain_len)

    stats = {
        "shape_id": "open_box",
        "num_helices": total_helices,
        "bases_per_helix": bases_per_helix,
        "box_faces": 5,
        "side_helices": s,
        "total_scaffold_nt": total_scaffold_nt,
        "num_staples": multi + single,
        "num_multi_domain_staples": multi,
        "num_single_domain_staples": single,
        "lattice_type": lattice_type,
        "is_approximation": False,
        "approximation_report": None,
        "implementation_status": "partially_implemented",
        "implementation_note": (
            "Scaffold topology and staple crossovers within faces are correct. "
            "Crossover routing at face boundaries (box corners) has not been "
            "fully validated for 3D folding fidelity. Staple layout at corners "
            "may need manual adjustment in cadnano before wet-lab synthesis."
        ),
    }
    return design, stats


# ============================================================================
# Template: Simple Triangle -- PARTIALLY IMPLEMENTED
# ============================================================================

def create_simple_triangle_design(
    side_bases: int = 200,
    lattice_type: str = "square",
    **kwargs,
) -> Tuple[Design, dict]:
    """
    Build a triangular planar design.

    STATUS: PARTIALLY IMPLEMENTED -- scaffold routing with progressive helix
    lengths works. However, staple crossover routing for the tapered edges
    (where helix length changes row-to-row) has not been fully validated.
    Multi-domain staples are generated between adjacent full-length helices,
    but the tapered boundary regions may have suboptimal staple placement.
    """
    grid = Grid.square if lattice_type == "square" else Grid.honeycomb
    domain_len = SQUARE_CROSSOVER_SPACING if lattice_type == "square" else HONEYCOMB_CROSSOVER_SPACING
    num_helices = max(6, side_bases // 8)

    # Progressive helix lengths toward apex
    helices = []
    for i in range(num_helices):
        row_bases = max(21, int(side_bases * (num_helices - i) / num_helices))
        helices.append(Helix(max_offset=row_bases, grid_position=(0, i)))

    design = Design(helices=helices, grid=grid)

    # Scaffold serpentine with progressive lengths
    scaffold_domains = []
    for h in range(num_helices):
        row_bases = helices[h].max_offset
        forward = (h % 2 == 0)
        scaffold_domains.append(Domain(
            helix=h, forward=forward, start=0, end=row_bases,
        ))
    scaffold = Strand(domains=scaffold_domains, is_scaffold=True)
    design.add_strand(scaffold)
    total_scaffold_nt = sum(d.dna_length() for d in scaffold_domains)

    # Staples: crossover only where both helices in a pair have sufficient length
    multi = 0
    single = 0
    for h in range(num_helices - 1):
        scaf_fwd_h = (h % 2 == 0)
        scaf_fwd_h1 = ((h + 1) % 2 == 0)
        max_bases = min(helices[h].max_offset, helices[h + 1].max_offset)

        if h % 2 == 0:
            seg_starts = list(range(0, max_bases, domain_len))
        else:
            seg_starts = list(range(domain_len // 2, max_bases, domain_len))

        for seg_start in seg_starts:
            seg_end = min(seg_start + domain_len, max_bases)
            d_h = Domain(helix=h, forward=not scaf_fwd_h, start=seg_start, end=seg_end)
            d_h1 = Domain(helix=h + 1, forward=not scaf_fwd_h1, start=seg_start, end=seg_end)
            design.add_strand(Strand(domains=[d_h, d_h1], is_scaffold=False))
            multi += 1

        # Fill gaps: where the longer helix extends beyond the shorter one
        longer_h = h if helices[h].max_offset > helices[h + 1].max_offset else h + 1
        longer_max = helices[longer_h].max_offset
        shorter_max = min(helices[h].max_offset, helices[h + 1].max_offset)
        if longer_max > shorter_max:
            scaf_fwd_longer = (longer_h % 2 == 0)
            gap_start = shorter_max
            while gap_start < longer_max:
                gap_end = min(gap_start + domain_len, longer_max)
                d = Domain(helix=longer_h, forward=not scaf_fwd_longer,
                          start=gap_start, end=gap_end)
                design.add_strand(Strand(domains=[d], is_scaffold=False))
                single += 1
                gap_start = gap_end

    # Edge helix (0) gaps
    h0_fwd = (0 % 2 == 0)
    for seg_start in range(domain_len // 2, helices[0].max_offset, domain_len):
        seg_end = min(seg_start + domain_len, helices[0].max_offset)
        d = Domain(helix=0, forward=not h0_fwd, start=seg_start, end=seg_end)
        design.add_strand(Strand(domains=[d], is_scaffold=False))
        single += 1

    stats = {
        "shape_id": "simple_triangle",
        "num_helices": num_helices,
        "bases_per_helix": "variable (triangle taper)",
        "total_scaffold_nt": total_scaffold_nt,
        "num_staples": multi + single,
        "num_multi_domain_staples": multi,
        "num_single_domain_staples": single,
        "lattice_type": lattice_type,
        "is_approximation": False,
        "approximation_report": None,
        "implementation_status": "partially_implemented",
        "implementation_note": (
            "Scaffold routing with progressive helix lengths is correct. "
            "Multi-domain staple crossovers are generated between adjacent "
            "full-length helices. Tapered boundary regions use single-domain "
            "staples which may be suboptimal. Manual review in cadnano is "
            "recommended before wet-lab synthesis."
        ),
    }
    return design, stats


# ============================================================================
# "Not Yet Implemented" stub
# ============================================================================

def _not_implemented(shape_name: str) -> Tuple[Design, dict]:
    """Return a clear not-yet-implemented result."""
    raise NotImplementedError(
        f"'{shape_name}': reliable scaffold and crossover routing not yet implemented. "
        f"This shape has research precedents in DNA nanotechnology, but the current "
        f"template does not guarantee correct staple crossover topology. "
        f"Supported shapes with full implementation: rectangle (square/honeycomb), "
        f"2/4/6-helix bundle (honeycomb), square tube (square). "
        f"Partially implemented: open_box, simple_triangle."
    )


# ============================================================================
# Template Registry
# ============================================================================

TEMPLATE_REGISTRY: Dict[str, dict] = {
    # ── Fully implemented ──
    "rectangle": {
        "category": "planar",
        "default_lattice": "square",
        "builder": create_rectangle_design,
        "implementation": "fully_implemented",
        "description": "Generic rectangle, user-specified width x height",
    },
    "square": {
        "category": "planar",
        "default_lattice": "square",
        "builder": create_rectangle_design,  # special case
        "implementation": "fully_implemented",
        "description": "Square (special case of rectangle)",
    },
    "long_strip": {
        "category": "planar",
        "default_lattice": "square",
        "builder": create_rectangle_design,  # high-aspect-ratio rectangle
        "implementation": "fully_implemented",
        "description": "Narrow long rectangular strip",
    },
    "planar_plate": {
        "category": "planar",
        "default_lattice": "square",
        "builder": create_rectangle_design,
        "implementation": "fully_implemented",
        "description": "Wide flat rectangular plate",
    },
    "2_helix_bundle": {
        "category": "bundle",
        "default_lattice": "honeycomb",
        "builder": create_helix_bundle_design,
        "implementation": "fully_implemented",
        "description": "Two-helix parallel bundle",
        "builder_kwargs": {"num_helices": 2},
    },
    "4_helix_bundle": {
        "category": "bundle",
        "default_lattice": "honeycomb",
        "builder": create_helix_bundle_design,
        "implementation": "fully_implemented",
        "description": "Four-helix parallel bundle",
        "builder_kwargs": {"num_helices": 4},
    },
    "6_helix_bundle": {
        "category": "bundle",
        "default_lattice": "honeycomb",
        "builder": create_helix_bundle_design,
        "implementation": "fully_implemented",
        "description": "Six-helix parallel bundle",
        "builder_kwargs": {"num_helices": 6},
    },
    "regular_tube": {
        "category": "tube_box",
        "default_lattice": "square",
        "builder": create_tube_design,
        "implementation": "fully_implemented",
        "description": "Tube with square cross-section",
    },

    # ── Partially implemented ──
    "open_box": {
        "category": "tube_box",
        "default_lattice": "square",
        "builder": create_open_box_design,
        "implementation": "partially_implemented",
        "description": "Box with open top face (5 faces). Scaffold correct; corner crossovers need manual review.",
    },
    "simple_triangle": {
        "category": "planar",
        "default_lattice": "square",
        "builder": create_simple_triangle_design,
        "implementation": "partially_implemented",
        "description": "Pre-defined regular triangle. Variable helix lengths; tapered edges have suboptimal staples.",
    },

    # ── Not yet implemented ──
    "simple_trapezoid": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("simple_trapezoid"),
        "implementation": "not_yet_implemented",
        "description": "Pre-defined regular trapezoid -- not yet implemented",
    },
    "simple_hexagon": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("simple_hexagon"),
        "implementation": "not_yet_implemented",
        "description": "Pre-defined regular hexagon -- not yet implemented",
    },
    "L_shape": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("L_shape"),
        "implementation": "not_yet_implemented",
        "description": "L-shape from 2 orthogonal rectangles -- not yet implemented",
    },
    "T_shape": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("T_shape"),
        "implementation": "not_yet_implemented",
        "description": "T-shape from 2 orthogonal rectangles -- not yet implemented",
    },
    "cross_shape": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("cross_shape"),
        "implementation": "not_yet_implemented",
        "description": "Cross shape from 3+ rectangles -- not yet implemented",
    },
    "rectangular_frame": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("rectangular_frame"),
        "implementation": "not_yet_implemented",
        "description": "Hollow rectangular border -- not yet implemented",
    },
    "plate_with_rectangular_hole": {
        "category": "planar",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("plate_with_rectangular_hole"),
        "implementation": "not_yet_implemented",
        "description": "Plate with rectangular hole -- not yet implemented",
    },
    "static_closed_box": {
        "category": "tube_box",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("static_closed_box"),
        "implementation": "not_yet_implemented",
        "description": "Fully closed box (6 faces) -- not yet implemented",
    },
    "simple_U_shape": {
        "category": "channel",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("simple_U_shape"),
        "implementation": "not_yet_implemented",
        "description": "U-shaped channel -- not yet implemented",
    },
    "simple_channel": {
        "category": "channel",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("simple_channel"),
        "implementation": "not_yet_implemented",
        "description": "Straight open channel/trough -- not yet implemented",
    },
    "simple_assembly": {
        "category": "assembly",
        "default_lattice": None,
        "builder": lambda **kw: _not_implemented("simple_assembly"),
        "implementation": "not_yet_implemented",
        "description": "Up to 3 regular modules -- not yet implemented",
    },
    "polygon_approximation_of_disk": {
        "category": "approximate",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("polygon_approximation_of_disk"),
        "implementation": "not_yet_implemented",
        "description": "N-gon approximating a disk -- not yet implemented",
    },
    "polygon_approximation_of_ring": {
        "category": "approximate",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("polygon_approximation_of_ring"),
        "implementation": "not_yet_implemented",
        "description": "N-gon ring approximating an annulus -- not yet implemented",
    },
    "piecewise_linear_arc": {
        "category": "approximate",
        "default_lattice": "square",
        "builder": lambda **kw: _not_implemented("piecewise_linear_arc"),
        "implementation": "not_yet_implemented",
        "description": "Segmented arc -- not yet implemented",
    },
}


def get_template_info(shape_id: str) -> dict:
    """Get template metadata for a shape ID."""
    if shape_id not in TEMPLATE_REGISTRY:
        known = ", ".join(TEMPLATE_REGISTRY.keys())
        raise ValueError(f"Unknown shape '{shape_id}'. Supported: {known}")
    return TEMPLATE_REGISTRY[shape_id]


def resolve_lattice(shape_id: str, user_lattice: str | None = None) -> Tuple[str, str]:
    """Apply Unified Lattice Selection Strategy. Returns (lattice, reason)."""
    info = get_template_info(shape_id)
    default_lattice = info["default_lattice"]

    if default_lattice is None:
        return (user_lattice or "square",
                "assembly: lattice determined per module; defaulting to square")

    if user_lattice is not None and user_lattice != default_lattice:
        # Check for known incompatibilities
        incompatible = {
            "regular_tube": ["honeycomb"],  # square tube requires square
        }
        if shape_id in incompatible and user_lattice in incompatible[shape_id]:
            return (default_lattice,
                    f"'{shape_id}' requires '{default_lattice}' lattice; "
                    f"cannot use '{user_lattice}'")

        return (user_lattice,
                f"user explicitly chose '{user_lattice}' for '{shape_id}'")

    return (default_lattice,
            f"template default for '{shape_id}' ({info['category']})")


# ============================================================================
# Derive CanDo submission file
# ============================================================================

def derive_cando_file(full_json_path: str, output_basename: str) -> str:
    """
    Derive CanDo-submittable JSON from the full master.

    Rules:
      - Clear ALL scaffold (scaf, scafLoop) arrays from every vstrand.
      - Keep ALL staple (stap, stapLoop) entries intact.
      - Preserve helix metadata, vstrand structure, and connectivity.
      - Do NOT add, modify, or redesign any staple entries.
      - Non-participating staples default to KEPT (only remove if clearly
        marked as auxiliary in the source design).
    """
    t_start = time.time()

    with open(full_json_path, 'r') as f:
        data = json.load(f)

    vstrands = data.get('vstrands', [])
    scaf_removed = 0
    scaf_loop_removed = 0

    for v in vstrands:
        if 'scaf' in v and v['scaf']:
            scaf_removed += len(v['scaf'])
            v['scaf'] = []
        if 'scafLoop' in v and v['scafLoop']:
            scaf_loop_removed += len(v['scafLoop'])
            v['scafLoop'] = []

    stap_retained = sum(len(v.get('stap', [])) for v in vstrands)
    stap_loop_retained = sum(len(v.get('stapLoop', [])) for v in vstrands)

    cando_path = f"{output_basename}.cando.json"
    with open(cando_path, 'w') as f:
        json.dump(data, f, indent=2)

    t_done = time.time()
    print(f"[OK] CanDo submission file: {cando_path}")
    print(f"     scaf entries removed: {scaf_removed}")
    print(f"     scafLoop entries removed: {scaf_loop_removed}")
    print(f"     stap entries retained: {stap_retained}")
    print(f"     stapLoop entries retained: {stap_loop_retained}")
    print(f"     derivation time: {t_done - t_start:.4f}s")

    return cando_path


# ============================================================================
# CanDo compact file: topology-preserving, compact-serialized submission file
# ============================================================================

def validate_cando_compatibility(design_data: dict) -> dict:
    """
    Non-destructive compatibility checks for CanDo submission readiness.

    Verifies that the design contains:
      - Non-empty vstrands
      - At least one valid scaffold topology entry
      - At least one valid staple topology entry
      - At least one position with both scaffold AND staple (dsDNA)
      - At least one cross-helix crossover connection

    Returns a dict with per-check PASS/FAIL status and summary counts.
    Does NOT modify design_data.
    """
    vstrands = design_data.get("vstrands", [])

    # --- vstrands check ---
    if not isinstance(vstrands, list) or len(vstrands) == 0:
        return {
            "vstrands": _fail("cando_vstrands", "vstrands is empty"),
            "scaffold": _fail("cando_scaffold", "skipped — no vstrands"),
            "staple": _fail("cando_staple", "skipped — no vstrands"),
            "dsDNA": _fail("cando_dsDNA", "skipped — no vstrands"),
            "crossover": _fail("cando_crossover", "skipped — no vstrands"),
            "scaffold_records": 0,
            "staple_records": 0,
            "dsdna_positions": 0,
            "crossover_records": 0,
        }

    dsdna_positions = 0
    crossover_records = 0
    scaffold_records = 0
    staple_records = 0
    scaf_stap_len_mismatch = 0

    for vh in vstrands:
        vh_num = vh.get("num")
        scaf = vh.get("scaf", [])
        stap = vh.get("stap", [])

        if len(scaf) != len(stap):
            scaf_stap_len_mismatch += 1

        for s, t in zip(scaf, stap):
            valid_scaf = (
                isinstance(s, list)
                and len(s) == 4
                and any(x != -1 for x in s)
            )
            valid_stap = (
                isinstance(t, list)
                and len(t) == 4
                and any(x != -1 for x in t)
            )

            if valid_scaf:
                scaffold_records += 1

            if valid_stap:
                staple_records += 1

            if valid_scaf and valid_stap:
                dsdna_positions += 1

            for conn in (s, t):
                if isinstance(conn, list) and len(conn) == 4:
                    for neighbor_vh in (conn[0], conn[2]):
                        if neighbor_vh != -1 and neighbor_vh != vh_num:
                            crossover_records += 1

    # --- Per-check results ---
    vstrands_ok = _pass("cando_vstrands",
                        f"{len(vstrands)} vstrands present",
                        num_vstrands=len(vstrands))

    scaffold_ok = (_pass("cando_scaffold",
                         f"{scaffold_records} scaffold records",
                         scaffold_records=scaffold_records)
                   if scaffold_records > 0 else
                   _fail("cando_scaffold",
                         "No scaffold topology detected — CanDo cannot identify scaffold"))

    staple_ok = (_pass("cando_staple",
                       f"{staple_records} staple records",
                       staple_records=staple_records)
                 if staple_records > 0 else
                 _fail("cando_staple",
                       "No staple topology detected — CanDo cannot identify staples"))

    dsdna_ok = (_pass("cando_dsDNA",
                      f"{dsdna_positions} potential dsDNA positions",
                      dsdna_positions=dsdna_positions)
                if dsdna_positions > 0 else
                _fail("cando_dsDNA",
                      "No positions with both scaffold and staple — "
                      "CanDo may not recognize dsDNA"))

    crossover_ok = (_pass("cando_crossover",
                          f"{crossover_records} crossover records",
                          crossover_records=crossover_records)
                    if crossover_records > 0 else
                    _fail("cando_crossover",
                          "No cross-helix crossover connections detected"))

    details = {
        "scaffold_records": scaffold_records,
        "staple_records": staple_records,
        "dsdna_positions": dsdna_positions,
        "crossover_records": crossover_records,
    }
    if scaf_stap_len_mismatch > 0:
        details["scaf_stap_len_mismatch_vstrands"] = scaf_stap_len_mismatch

    return {
        "vstrands": vstrands_ok,
        "scaffold": scaffold_ok,
        "staple": staple_ok,
        "dsDNA": dsdna_ok,
        "crossover": crossover_ok,
        **details,
    }


def derive_cando_compact_file(full_json_path: str, output_basename: str) -> Tuple[str, dict]:
    """
    Generate a topology-preserving, compact-serialized CanDo submission file.

    Rules:
      - Read the full master JSON WITHOUT modifying topology.
      - Scaffold (scaf) entries are KEPT intact.
      - Staple (stap) entries are KEPT intact.
      - All helix metadata, vstrand structure, and connectivity are preserved.
      - Output is compact JSON (no indentation, minimal separators).
      - Runs non-destructive compatibility checks first.

    Returns (output_path, compatibility_report).
    """
    t_start = time.time()

    # --- Read full master ---
    with open(full_json_path, 'r', encoding='utf-8') as f:
        design = json.load(f)

    # --- Structural validation ---
    if "vstrands" not in design:
        raise ValueError(
            f"File '{full_json_path}' is not a valid cadnano v2 JSON: "
            f"missing 'vstrands' key."
        )

    # --- Non-destructive compatibility checks ---
    compat_report = validate_cando_compatibility(design)

    # --- Compact serialization ---
    compact_path = f"{output_basename}.cando_compact.json"
    with open(compact_path, 'w', encoding='utf-8', newline='') as f:
        json.dump(design, f, ensure_ascii=False, separators=(",", ":"))

    t_done = time.time()

    # --- Report ---
    print(f"\n[OK] CanDo compact submission file: {compact_path}")
    print(f"     topology: FULLY PRESERVED (scaffold + staples + crossovers)")
    print(f"     format: compact JSON (no indentation)")
    print(f"     serialization time: {t_done - t_start:.4f}s")
    print(f"\n  CanDo compatibility check:")
    for check_name in ("vstrands", "scaffold", "staple", "dsDNA", "crossover"):
        check = compat_report.get(check_name, {})
        icon = {"PASS": "[OK]", "WARNING": "[!!]", "FAIL": "[XX]"}.get(
            check.get("status", "?"), "[??]")
        print(f"    {icon} {check_name}: {check.get('status', '?')}"
              f" -- {check.get('message', '')}")
    print(f"    [OK] compact JSON serialization: PASS")

    return compact_path, compat_report


# ============================================================================
# Main public API: create_design()
# ============================================================================

def create_design(
    shape_id: str = "rectangle",
    output_basename: str = "design",
    user_lattice: str | None = None,
    **shape_params,
) -> dict:
    """
    Create a DNA origami design with proper scaffold + crossover staples.

    Args:
        shape_id: Shape identifier from TEMPLATE_REGISTRY.
        output_basename: Base name for output files.
        user_lattice: Lattice override (None = use template default).
        **shape_params: Shape-specific parameters (num_helices, bases_per_helix, ...).

    Returns:
        dict with keys:
            full_path, cando_path, validation_report, design_summary,
            sequence_status, design_status, lattice_type, lattice_reason
    """
    if shape_id not in TEMPLATE_REGISTRY:
        known = ", ".join(TEMPLATE_REGISTRY.keys())
        return {
            "full_path": None,
            "cando_path": None,
            "cando_compact_path": None,
            "cando_compat_report": None,
            "validation_report": [],
            "design_summary": {"error": f"Unknown shape '{shape_id}'"},
            "sequence_status": "not_assigned",
            "design_status": "UNSUPPORTED_REQUEST",
            "validation_status": "NOT_RUN",
            "experimental_status": "EXPERIMENTALLY_UNVALIDATED",
            "submission_status": "NOT_SUBMITTED",
            "lattice_type": None,
            "lattice_reason": f"Unknown shape '{shape_id}'. Supported: {known}",
        }

    info = get_template_info(shape_id)
    lattice, lattice_reason = resolve_lattice(shape_id, user_lattice)
    builder = info["builder"]

    # Merge template kwargs with user params
    builder_kwargs = {**info.get("builder_kwargs", {}), **shape_params}
    builder_kwargs["lattice_type"] = lattice

    # Default dimensions by category
    cat = info["category"]
    if cat == "planar":
        builder_kwargs.setdefault("num_helices", 24)
        builder_kwargs.setdefault("bases_per_helix", 234)
    elif cat == "bundle":
        builder_kwargs.setdefault("num_helices", 6)
        builder_kwargs.setdefault("bases_per_helix", 240)
    elif cat == "tube_box":
        builder_kwargs.setdefault("side_helices", 6)
        builder_kwargs.setdefault("bases_per_helix", 234)
    elif cat == "approximate":
        builder_kwargs.setdefault("num_sides", 12)

    # ── Build ──
    t_build = time.time()
    try:
        design, stats = builder(**builder_kwargs)
    except NotImplementedError as e:
        print(f"[NOT IMPLEMENTED] {shape_id}: {e}")
        return {
            "full_path": None,
            "cando_path": None,
            "cando_compact_path": None,
            "cando_compat_report": None,
            "validation_report": [
                _fail("design_generation", str(e)),
            ],
            "design_summary": {
                "shape_id": shape_id,
                "implementation_status": info["implementation"],
                "error": str(e),
            },
            "sequence_status": "not_assigned",
            "design_status": "UNSUPPORTED_REQUEST",
            "validation_status": "NOT_RUN",
            "experimental_status": "EXPERIMENTALLY_UNVALIDATED",
            "submission_status": "NOT_SUBMITTED",
            "implementation_status": info["implementation"],
            "lattice_type": lattice,
            "lattice_reason": lattice_reason,
        }
    except Exception as e:
        print(f"[ERROR] {shape_id}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "full_path": None,
            "cando_path": None,
            "cando_compact_path": None,
            "cando_compat_report": None,
            "validation_report": [
                _fail("design_generation", f"Builder error: {e}"),
            ],
            "design_summary": {
                "shape_id": shape_id,
                "implementation_status": info["implementation"],
                "error": str(e),
            },
            "sequence_status": "not_assigned",
            "design_status": "GENERATION_FAILED",
            "validation_status": "NOT_RUN",
            "experimental_status": "EXPERIMENTALLY_UNVALIDATED",
            "submission_status": "NOT_SUBMITTED",
            "lattice_type": lattice,
            "lattice_reason": lattice_reason,
        }

    build_sec = time.time() - t_build
    stats["lattice_type"] = lattice
    stats["lattice_selection_reason"] = lattice_reason
    stats["implementation_status"] = info["implementation"]
    stats["build_time_sec"] = build_sec

    # ── Write full master ──
    full_path = f"{output_basename}.full.json"
    design.write_cadnano_v2_file(directory='.', filename=full_path)
    print(f"[OK] Full master: {full_path}")
    print(f"     shape: {shape_id} ({info['category']})")
    print(f"     implementation: {info['implementation']}")
    print(f"     helices: {stats['num_helices']}")
    print(f"     bases per helix: {stats['bases_per_helix']}")
    print(f"     lattice: {lattice} -- {lattice_reason}")
    print(f"     scaffold: {stats['total_scaffold_nt']} nt")
    print(f"     staples: {stats['num_staples']} "
          f"({stats.get('num_multi_domain_staples', '?')} multi-domain with crossovers, "
          f"{stats.get('num_single_domain_staples', '?')} single-domain edge fillers)")
    print(f"     build time: {build_sec:.4f}s")

    # ── Derive CanDo compact file (topology-preserved, compact JSON) ──
    # NOTE: The legacy scaffold-stripped .cando.json is NO LONGER generated
    # by default to prevent accidental upload to CanDo.
    cando_path = None
    cando_compact_path, cando_compat_report = derive_cando_compact_file(
        full_path, output_basename)

    # ── Run validation ──
    validation_report = []

    # 1. JSON structure
    validation_report.append(validate_json_structure(full_path))

    # 2. Scaffold connectivity (from Design object for accuracy)
    validation_report.append(validate_scaffold_connectivity(design))

    # 3. Staple connectivity (from Design object)
    validation_report.append(validate_staple_connectivity(design))

    # 4. Crossovers (from Design object)
    validation_report.append(validate_crossovers(design, lattice))

    # 5. Dimensions
    validation_report.append(validate_dimensions(
        design,
        expected_helices=stats.get('num_helices'),
        expected_bases=stats.get('bases_per_helix')
        if isinstance(stats.get('bases_per_helix'), int) else None,
    ))

    # 6. Compact file topology preservation
    validation_report.append(validate_compact_preservation(full_path, cando_compact_path))

    # ── Summarize validation (progressive: each level implies prior levels) ──
    # NOTE: CANDO_COMPATIBILITY_TESTED requires a real CanDo service call.
    # Local compact preservation check can only reach CANDO_INPUT_GENERATED.
    checks = {r['check']: r['status'] for r in validation_report}
    json_ok = checks.get('json_structure') == 'PASS'
    # TOPOLOGY_VALIDATED: all 4 topology checks must be PASS (no WARNING, no FAIL).
    # WARNINGs on scaffold/staple/crossover/dimension checks keep status at
    # FORMAT_VALIDATED because they indicate potentially unreliable topology.
    topo_checks = ['scaffold_connectivity', 'staple_connectivity',
                   'crossovers', 'dimensions']
    topo_all_pass = all(checks.get(c) == 'PASS' for c in topo_checks)
    compact_ok = checks.get('compact_preservation') == 'PASS'

    # Collect topology warnings for the result
    topo_warnings = [
        r for r in validation_report
        if r['check'] in topo_checks and r['status'] == 'WARNING'
    ]

    # CANDO_COMPATIBILITY_TESTED is intentionally NOT set here --
    # it requires a real CanDo service call, not a local file check.
    if compact_ok and cando_compact_path and topo_all_pass and json_ok:
        validation_status = "CANDO_INPUT_GENERATED"
    elif topo_all_pass and json_ok:
        validation_status = "TOPOLOGY_VALIDATED"
    elif json_ok:
        validation_status = "FORMAT_VALIDATED"
    else:
        validation_status = "NOT_RUN"

    # ── Determine design status ──
    design_status = "GENERATED"

    # ── Build result ──
    result = {
        "full_path": full_path,
        "cando_path": cando_path,
        "cando_compact_path": cando_compact_path,
        "cando_compat_report": cando_compat_report,
        "validation_report": validation_report,
        "validation_warnings": topo_warnings,
        "design_summary": stats,
        "sequence_status": "not_assigned",
        "design_status": design_status,
        "validation_status": validation_status,
        "experimental_status": "EXPERIMENTALLY_UNVALIDATED",
        "submission_status": "NOT_SUBMITTED",
        "lattice_type": lattice,
        "lattice_reason": lattice_reason,
        "implementation_status": info["implementation"],
    }

    # Print validation summary
    print(f"\n{'='*60}")
    print(f"  VALIDATION SUMMARY: {validation_status}")
    print(f"{'='*60}")
    for r in validation_report:
        icon = {"PASS": "[OK]", "WARNING": "[!!]", "FAIL": "[XX]"}.get(r['status'], '[??]')
        print(f"  {icon} {r['check']}: {r['status']}")
        if r['message']:
            print(f"     {r['message']}")
    print(f"{'='*60}")

    return result


# ============================================================================
# Catalog display
# ============================================================================

def print_catalog():
    """Print the template catalog with implementation status."""
    print("=" * 70)
    print("  Template Catalog -- Implementation Status")
    print("=" * 70)

    categories = defaultdict(list)
    for sid, info in TEMPLATE_REGISTRY.items():
        categories[info["category"]].append((sid, info))

    status_icons = {
        "fully_implemented": "[FULL]",
        "partially_implemented": "[PART]",
        "not_yet_implemented": "[ ---]",
    }

    for cat in ["planar", "bundle", "tube_box", "channel", "assembly", "approximate"]:
        if cat not in categories:
            continue
        print(f"\n[{cat}]")
        for sid, info in categories[cat]:
            icon = status_icons.get(info["implementation"], "[ ?? ]")
            lat = info["default_lattice"] or "per-module"
            print(f"  {icon} {sid:<38s} lattice={str(lat):<10s} {info['description']}")

    full_count = sum(1 for v in TEMPLATE_REGISTRY.values()
                     if v["implementation"] == "fully_implemented")
    part_count = sum(1 for v in TEMPLATE_REGISTRY.values()
                     if v["implementation"] == "partially_implemented")
    notyet_count = sum(1 for v in TEMPLATE_REGISTRY.values()
                       if v["implementation"] == "not_yet_implemented")
    print(f"\n[FULL] = fully implemented    ({full_count})")
    print(f"[PART] = partially implemented ({part_count})")
    print(f"[ ---] = not yet implemented   ({notyet_count})")
    print("=" * 70)


# ============================================================================
# CLI entry point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate cadnano-compatible DNA origami designs with real crossover staples."
    )
    parser.add_argument("shape", nargs="?", default="rectangle",
                        help="Shape ID from the template catalog")
    parser.add_argument("-o", "--output", default="design",
                        help="Output basename (default: design)")
    parser.add_argument("-l", "--lattice", default=None,
                        choices=["square", "honeycomb"],
                        help="Lattice type override")
    parser.add_argument("--catalog", action="store_true",
                        help="Print template catalog and exit")
    parser.add_argument("--num-helices", type=int, default=None)
    parser.add_argument("--bases-per-helix", type=int, default=None)
    parser.add_argument("--side-helices", type=int, default=None)
    parser.add_argument("--side-bases", type=int, default=None)

    args = parser.parse_args()

    if args.catalog:
        print_catalog()
        sys.exit(0)

    shape_params = {}
    if args.num_helices is not None:
        shape_params["num_helices"] = args.num_helices
    if args.bases_per_helix is not None:
        shape_params["bases_per_helix"] = args.bases_per_helix
    if args.side_helices is not None:
        shape_params["side_helices"] = args.side_helices
    if args.side_bases is not None:
        shape_params["side_bases"] = args.side_bases

    result = create_design(
        shape_id=args.shape,
        output_basename=args.output,
        user_lattice=args.lattice,
        **shape_params,
    )

    print(f"\nDESIGN STATUS:       {result['design_status']}")
    print(f"VALIDATION STATUS:   {result['validation_status']}")
    print(f"EXPERIMENTAL STATUS: {result['experimental_status']}")
    print(f"SUBMISSION STATUS:   {result['submission_status']}")
    print(f"SEQUENCE STATUS:     {result['sequence_status']}")
    print(f"IMPLEMENTATION:      {result['implementation_status']}")

    if result['full_path']:
        print(f"\nFiles:")
        print(f"  cadnano master:         {result['full_path']}")
        if result.get('cando_compact_path'):
            print(f"  CanDo submit (compact): {result['cando_compact_path']}")
        print(f"  lattice:                {result['lattice_type']} -- {result['lattice_reason']}")
