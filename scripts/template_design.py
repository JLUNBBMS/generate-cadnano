#!/usr/bin/env python3
"""V3: lattice-aware plates, bundles, parameterized tubes and fixed-cap containers."""

import argparse
import json
import math
from pathlib import Path
import tempfile

import scadnano as sc

from lattice import TABLES, legal, neighbors
from validation import validate, preservation, read_data

VERSION = "3.0.0"
DEFAULT_SCAFFOLD_LENGTH = 7249
SUPPORTED = ("rectangle", "square", "long_strip", "planar_plate",
             "2_helix_bundle", "4_helix_bundle", "6_helix_bundle", "regular_tube")
LEGACY_SUPPORTED = SUPPORTED
from geometry import NEW_SHAPES
SUPPORTED = SUPPORTED + NEW_SHAPES
UNSUPPORTED = ("open_box", "simple_triangle", "simple_trapezoid", "simple_hexagon",
               "L_shape", "T_shape", "cross_shape", "rectangular_frame",
               "plate_with_rectangular_hole", "static_closed_box", "simple_U_shape",
               "simple_channel", "simple_assembly", "polygon_approximation_of_disk",
               "polygon_approximation_of_ring", "piecewise_linear_arc")
TEMPLATE_REGISTRY = {
    name: {"implementation": "implemented" if name in SUPPORTED else "not_yet_implemented",
           "default_lattice": "honeycomb" if "helix_bundle" in name else "square"}
    for name in SUPPORTED + UNSUPPORTED
}


def resolve_lattice(shape_id, user_lattice=None):
    if shape_id not in SUPPORTED:
        raise ValueError(f"Unsupported shape: {shape_id}")
    lattice = user_lattice or TEMPLATE_REGISTRY[shape_id]["default_lattice"]
    if lattice not in TABLES:
        raise ValueError("lattice must be square or honeycomb")
    if shape_id == "regular_tube" and lattice != "square":
        raise ValueError("regular_tube supports only square lattice; choose explicitly")
    return lattice, ("user selection" if user_lattice else "template default")


def positive_int(value, name, minimum=1, maximum=100000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


def layout(shape, lattice, num_helices, side_helices):
    if "helix_bundle" in shape:
        fixed = int(shape.split("_")[0])
        if num_helices is not None and num_helices != fixed:
            raise ValueError(f"{shape} requires exactly {fixed} helices")
        if side_helices is not None:
            raise ValueError("side_helices applies only to regular_tube")
        if fixed == 2:
            coords = [(0, 0), (0, 1)]
        elif fixed == 4:
            coords = [(0, 0), (0, 1), (1, 1), (1, 0)]
        elif lattice == "honeycomb":
            coords = [(0, 0), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
        else:
            coords = [(0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0)]
    elif shape == "regular_tube":
        if num_helices is not None:
            raise ValueError("regular_tube uses side_helices, not num_helices")
        s = positive_int(4 if side_helices is None else side_helices, "side_helices", 1, 16)
        coords = ([(0, x) for x in range(s)] + [(x, s) for x in range(s)] +
                  [(s, s - x) for x in range(s)] + [(s - x, 0) for x in range(s)])
    else:
        if side_helices is not None:
            raise ValueError("side_helices applies only to regular_tube")
        default_n = {"rectangle": 8, "square": 16, "long_strip": 4, "planar_plate": 24}[shape]
        n = positive_int(default_n if num_helices is None else num_helices, "num_helices", 2, 64)
        coords = [(0, x) for x in range(n)]
    # Even translation keeps coordinate parity and avoids negative JSON coords.
    coords = [(r + 2, c + 2) for r, c in coords]
    for a, b in zip(coords, coords[1:]):
        if b not in neighbors(lattice, a):
            raise ValueError("template route is not a lattice-neighbor path")
    return coords


def to_domains(path):
    domains = []
    start = 0
    for end in range(1, len(path) + 1):
        if end == len(path) or path[end][0] != path[start][0]:
            section = path[start:end]
            h = section[0][0]
            forward = h % 2 != 0  # staples run opposite scaffold
            indices = [i for _, i in section]
            domains.append(sc.Domain(helix=h, forward=forward,
                                     start=min(indices), end=max(indices) + 1))
            start = end
    return domains


def segment_staple(path):
    """Dynamic programming: 20..60 nt oligos, every binding domain >=8 nt.

    Cuts are along a helix only; a crossover is never removed by a nick.
    Cost prefers lengths close to 32 nt. No successful partition means reject.
    """
    n = len(path)
    costs = [math.inf] * (n + 1)
    previous = [None] * (n + 1)
    costs[0] = 0
    for end in range(20, n + 1):
        if end < n and path[end - 1][0] != path[end][0]:
            continue
        for start in range(max(0, end - 60), end - 19):
            if costs[start] == math.inf:
                continue
            run = 1
            good = True
            for j in range(start + 1, end):
                if path[j][0] != path[j - 1][0]:
                    if run < 8:
                        good = False
                        break
                    run = 0
                run += 1
            if not good or run < 8:
                continue
            cost = costs[start] + (end - start - 32) ** 2 + 1
            if cost < costs[end]:
                costs[end] = cost
                previous[end] = start
    if previous[n] is None:
        raise ValueError(f"No legal staple nicking solution for {n}-nt path "
                         f"({path[0]} to {path[-1]}); change length or helix count")
    segments = []
    end = n
    while end:
        start = previous[end]
        segments.append(path[start:end])
        end = start
    return list(reversed(segments))


def build_staples(coords, intervals, lattice, required_pairs=None):
    # This internal directed graph is converted to scadnano Domains/Strands.
    # Only scadnano's exporter writes cadnano routing arrays.
    successor = {}
    for h, (lo, hi) in enumerate(intervals):
        indices = list(range(lo, hi))
        if h % 2 == 0:
            indices.reverse()
        for pos, i in enumerate(indices):
            successor[h, i] = (h, indices[pos + 1]) if pos + 1 < len(indices) else None
    endpoint_sites = set()
    pairs = [(h, h + 1) for h in range(len(coords) - 1)]
    if len(coords) > 2 and coords[-1] in neighbors(lattice, coords[0]):
        pairs.append((len(coords) - 1, 0))
    if required_pairs is not None:
        pairs = required_pairs
    planned = None
    if required_pairs is not None:
        from routing_v3 import schedule_contacts
        planned = schedule_contacts(coords, intervals, lattice, pairs)
    for a, b in pairs:
        lo = max(intervals[a][0], intervals[b][0])
        hi = min(intervals[a][1], intervals[b][1])
        cuts = []
        for k in range(lo + 10, hi - 9):
            if planned is not None and k not in planned[(a,b)]:
                continue
            if not (legal(lattice, coords[a], coords[b], "stap", k - 1, True) and
                    legal(lattice, coords[a], coords[b], "stap", k, False)):
                continue
            spacing = (4 if lattice == "honeycomb" else 2) * TABLES[lattice]["period"]
            if cuts and k - cuts[-1] < spacing:
                continue
            if planned is None and any(h == t and abs(k - previous) < 16
                   for h in (a, b) for t, previous in endpoint_sites):
                continue
            cuts.append(k)
            endpoint_sites.update(((a, k), (b, k)))
            # Exchange the successors at a full crossover (sites k-1 and k).
            a_end = (a, k if a % 2 == 0 else k - 1)
            b_end = (b, k if b % 2 == 0 else k - 1)
            successor[a_end], successor[b_end] = successor[b_end], successor[a_end]
        if not cuts:
            raise ValueError(f"No legal staple crossover for helices {a},{b}; increase length")
    incoming = {v for v in successor.values() if v is not None}
    unseen = set(successor)
    starts = sorted(set(successor) - incoming)
    paths = []
    for start in starts:
        path = []
        cur = start
        while cur is not None:
            if cur not in unseen:
                raise ValueError("Internal staple path merged unexpectedly")
            unseen.remove(cur)
            path.append(cur)
            cur = successor[cur]
        paths.append(path)
    while unseen:
        start = min(unseen)
        path = []
        cur = start
        while cur in unseen:
            unseen.remove(cur)
            path.append(cur)
            cur = successor[cur]
        if cur != start:
            raise ValueError("Internal staple cycle did not close")
        # Open at the midpoint of the longest uninterrupted helix run.
        options = []
        n = len(path)
        for j in range(n):
            if path[j - 1][0] != path[j][0]:
                run = 1
                while run < n and path[(j + run) % n][0] == path[j][0]:
                    run += 1
                options.append((run, (j + run // 2) % n))
        if not options:
            raise ValueError("Unexpected cycle without crossover")
        _, cut = max(options)
        paths.append(path[cut:] + path[:cut])
    strands = []
    palette = (0xCC6633, 0x339966, 0x9933CC, 0xCC9933, 0x3366CC, 0xCC3366)
    for path in paths:
        for segment in segment_staple(path):
            color = palette[len(strands) % len(palette)]
            strands.append(sc.Strand(domains=to_domains(segment),
                                     color=sc.Color(hex_string=f"#{color:06x}")))
    return strands


def build(shape, lattice, num_helices=None, bases_per_helix=None, side_helices=None):
    coords = layout(shape, lattice, num_helices, side_helices)
    n = len(coords)
    # square is a physical aspect ratio, not equal helix count and base count.
    transverse_nm = (n - 1) * (2.5 if lattice == "square" else math.sqrt(3) * 1.25) + 2.5
    default_bases = max(96, round(transverse_nm / 0.34)) if shape == "square" else 210 if lattice == "honeycomb" else 128
    length = positive_int(default_bases if bases_per_helix is None else bases_per_helix,
                          "bases_per_helix", 96, 4096)
    ratio = length * 0.34 / transverse_nm
    if shape == "square" and not 0.85 <= ratio <= 1.15:
        raise ValueError("square requires axial/transverse size ratio 0.85..1.15; use more helices or rectangle")
    if shape == "long_strip" and ratio < 3:
        raise ValueError("long_strip requires axial/transverse size ratio >=3; increase length")
    if shape == "planar_plate" and ratio > 1:
        raise ValueError("planar_plate requires transverse width >= axial length; use rectangle or more helices")
    intervals = [[0, length] for _ in coords]
    for h in range(n - 1):
        high = h % 2 == 0
        candidates = [i for i in range(length) if
                      legal(lattice, coords[h], coords[h + 1], "scaf", i, high)]
        idx = max(candidates) if high else min(candidates)
        if high:
            intervals[h][1] = intervals[h + 1][1] = idx + 1
        else:
            intervals[h][0] = intervals[h + 1][0] = idx
    scaffold = sc.Strand(domains=[sc.Domain(helix=h, forward=h % 2 == 0, start=lo, end=hi)
                                 for h, (lo, hi) in enumerate(intervals)], is_scaffold=True)
    staples = build_staples(coords, intervals, lattice)
    period = TABLES[lattice]["period"]
    storage_length = math.ceil(length / period) * period
    other_period = 21 if lattice == "square" else 32
    if storage_length % other_period == 0:
        storage_length += period  # avoid cadnano's ambiguous 672-bp lattice inference
    design = sc.Design(helices=[sc.Helix(max_offset=storage_length, grid_position=(c, r)) for r, c in coords],
                       grid=sc.Grid.square if lattice == "square" else sc.Grid.honeycomb,
                       strands=[scaffold] + staples)
    metadata = {
        "shape_id": shape, "num_helices": n, "bases_per_helix": length,
        "lattice_type": lattice, "coordinates_row_col": coords,
        "occupied_intervals": intervals,
        "requested_axial_envelope_nm": round(length * 0.34, 3),
        "approximate_transverse_envelope_nm": round(transverse_nm, 3) if shape in SUPPORTED[:4] else None,
        "total_scaffold_nt": sum(hi - lo for lo, hi in intervals),
        "num_staples": len(staples),
        "boundary_note": "Lattice-valid scaffold crossovers produce stepped ends, not a mathematically exact outline.",
        "max_boundary_inset_bp": max(max(lo, length - hi) for lo, hi in intervals),
        "actual_axial_span_nm": round((max(hi for _, hi in intervals) - min(lo for lo, _ in intervals)) * 0.34, 3),
        "storage_length_bp": storage_length,
    }
    return design, metadata


def create_design(shape_id="rectangle", output_basename="design", user_lattice=None,
                  num_helices=None, bases_per_helix=None, side_helices=None,
                  scaffold_length=DEFAULT_SCAFFOLD_LENGTH, width_helices=None,
                  height_helices=None, cross_section=None, polygon_sides=None,
                  end_style=None, cap_length=None, **unknown):
    result = {"version": VERSION, "design_status": "GENERATION_FAILED", "validation_status": "NOT_RUN",
              "experimental_status": "EXPERIMENTALLY_UNVALIDATED", "submission_status": "NOT_SUBMITTED",
              "sequence_status": "not_assigned", "full_path": None, "cando_compact_path": None}
    created = []
    try:
        if shape_id not in SUPPORTED:
            result["design_status"] = "UNSUPPORTED_REQUEST"
            raise ValueError(f"No verified template for {shape_id}")
        if unknown:
            raise ValueError("Unknown parameters: " + ", ".join(sorted(unknown)))
        positive_int(scaffold_length, "scaffold_length")
        lattice, reason = resolve_lattice(shape_id, user_lattice)
        result.update(lattice_type=lattice, lattice_reason=reason)
        base = Path(output_basename)
        targets = [Path(str(base) + suffix) for suffix in
                   (".full.json", ".cando_compact.json", ".report.json")]
        if any(p.exists() for p in targets):
            raise ValueError("Output already exists; use a new output basename")
        if shape_id in NEW_SHAPES:
            from routing_v3 import build_v3
            design, metadata, expected = build_v3(
                shape_id, lattice, num_helices, bases_per_helix, side_helices,
                width_helices, height_helices, cross_section, polygon_sides,
                end_style, cap_length, scaffold_length)
        else:
            if any(x is not None for x in (width_helices,height_helices,cross_section,
                                           polygon_sides,end_style,cap_length)):
                raise ValueError('V3 geometry parameters require a V3 template')
            design, metadata = build(shape_id, lattice, num_helices, bases_per_helix, side_helices)
            expected = {h: (coord, interval) for h, (coord, interval) in
                        enumerate(zip(metadata["coordinates_row_col"], metadata["occupied_intervals"]))}
        targets[0].parent.mkdir(parents=True, exist_ok=True)
        # No final files until exported data passes the full validator.
        with tempfile.TemporaryDirectory(prefix="cadnano_v2_", dir=targets[0].parent) as temp:
            full = Path(temp) / "master.json"
            design.write_cadnano_v2_file(directory=temp, filename="master.json")
            data = read_data(full)
            data["name"] = base.name  # remove transient path; routing unchanged
            full.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            audit = validate(full, lattice, scaffold_length, expected)
            if shape_id in NEW_SHAPES:
                from shape_validation import validate_shape
                shape_audit = validate_shape(data, metadata)
                result['geometry_validation'] = shape_audit
                if shape_audit['status'] != 'PASS':
                    audit['errors'].extend(shape_audit['errors'])
                    audit['status'] = 'FAIL'
            result.update(validation_report=audit, design_summary=metadata)
            if audit["status"] != "PASS":
                raise ValueError("Export validation failed: " + "; ".join(audit["errors"][:8]))
            compact = Path(temp) / "compact.json"
            compact.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
            check = preservation(full, compact)
            if check["status"] != "PASS":
                raise ValueError("Compact preservation failed")
            result.update(design_status="GENERATED", validation_status="CANDO_INPUT_GENERATED",
                          full_path=str(targets[0]), cando_compact_path=str(targets[1]),
                          report_path=str(targets[2]), compact_preservation=check,
                          scaffold_length=scaffold_length)
            report = Path(temp) / "report.json"
            report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            for source, target in zip((full, compact, report), targets):
                # Exclusive creation avoids overwriting another run's output.
                with target.open("xb") as handle:
                    created.append(target)
                    handle.write(source.read_bytes())
        return result
    except (ValueError, OSError, sc.IllegalDesignError) as exc:
        for path in created:
            path.unlink()
        result["error"] = str(exc)
        result["design_status"] = "UNSUPPORTED_REQUEST" if shape_id not in SUPPORTED else "GENERATION_FAILED"
        result["validation_status"] = "NOT_RUN"
        result["full_path"] = result["cando_compact_path"] = None
        return result


def validate_crossovers(design_or_path, lattice_type="square"):
    return validate(design_or_path, lattice_type)


def validate_compact_preservation(full_path, compact_path):
    return preservation(full_path, compact_path)


def print_catalog():
    for name, info in TEMPLATE_REGISTRY.items():
        print(f"{name}: {info['implementation']} ({info['default_lattice']})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shape", nargs="?", default="rectangle")
    parser.add_argument("-o", "--output", default="design")
    parser.add_argument("-l", "--lattice", choices=sorted(TABLES))
    parser.add_argument("--num-helices", type=int)
    parser.add_argument("--bases-per-helix", type=int)
    parser.add_argument("--side-helices", type=int)
    parser.add_argument("--width-helices", type=int)
    parser.add_argument("--height-helices", type=int)
    parser.add_argument("--cross-section", choices=('square','rectangle','near_circular','polygon'))
    parser.add_argument("--polygon-sides", type=int)
    parser.add_argument("--end-style", choices=('open','one_cap','two_caps'))
    parser.add_argument("--cap-length", type=int)
    parser.add_argument("--scaffold-length", type=int, default=7249)
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--validate", metavar="CADNANO_JSON")
    args = parser.parse_args()
    if args.catalog:
        print_catalog()
        return 0
    if args.validate:
        if args.lattice is None:
            parser.error("--validate requires an explicit --lattice")
        result = validate(args.validate, args.lattice, args.scaffold_length)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "PASS" else 1
    result = create_design(args.shape, args.output, args.lattice,
                           args.num_helices, args.bases_per_helix,
                           args.side_helices, args.scaffold_length,
                           args.width_helices,args.height_helices,args.cross_section,
                           args.polygon_sides,args.end_style,args.cap_length)
    print(json.dumps(result, indent=2))
    return 0 if result["design_status"] == "GENERATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
