"""Strict, read-only validation of the exported cadnano v2 representation."""

import json
from pathlib import Path

from lattice import TABLES, legal

EMPTY = [-1, -1, -1, -1]


def read_data(value):
    if isinstance(value, (str, Path)):
        return json.loads(Path(value).read_text(encoding="utf-8"))
    if isinstance(value, dict):
        return value
    return value.to_cadnano_v2_serializable()


def validate(value, lattice, scaffold_length=7249, expected=None):
    """Fail closed. Insertions/skips are rejected in V2, never silently ignored.

    expected optionally contains exact exported helix coordinates and occupied
    intervals from the generator. Checks use helix num, not array order.
    """
    errors = []
    report = {"status": "FAIL", "errors": errors, "counts": {}}
    try:
        data = read_data(value)
        if lattice not in TABLES:
            raise ValueError("lattice must be square or honeycomb")
        if type(scaffold_length) is not int or scaffold_length < 1:
            raise ValueError("scaffold_length must be a positive integer")
        if not isinstance(data, dict) or not isinstance(data.get("vstrands"), list) or not data["vstrands"]:
            raise ValueError("non-empty vstrands list required")
        helices = {}
        coords = set()
        size = None
        for vh in data["vstrands"]:
            if not isinstance(vh, dict):
                raise ValueError("vstrand must be an object")
            for key in ("num", "row", "col"):
                if type(vh.get(key)) is not int or vh[key] < 0:
                    raise ValueError(key + " must be a nonnegative integer")
            h = vh["num"]
            coord = (vh["row"], vh["col"])
            if h in helices or coord in coords:
                raise ValueError("duplicate helix num or coordinate")
            if h % 2 != sum(coord) % 2:
                raise ValueError("helix num parity disagrees with coordinate parity")
            helices[h] = vh
            coords.add(coord)
            if not isinstance(vh.get("scaf"), list) or not vh["scaf"]:
                raise ValueError("non-empty scaf array required")
            n = len(vh["scaf"])
            size = n if size is None else size
            if n != size or n % TABLES[lattice]["period"]:
                raise ValueError("array length disagrees with lattice period or other helices")
            for key in ("stap", "loop", "skip"):
                if not isinstance(vh.get(key), list) or len(vh[key]) != n:
                    raise ValueError("strand/loop/skip array lengths must match")
            if any(type(x) is not int or x != 0 for key in ("loop", "skip") for x in vh[key]):
                raise ValueError("V2 does not support insertions/skips; no validated export produced")
            for key in ("scafLoop", "stapLoop"):
                if key in vh and vh[key] != []:
                    raise ValueError("nonempty legacy loop fields unsupported")
            for key in ("scaf", "stap"):
                for record in vh[key]:
                    if (not isinstance(record, list) or len(record) != 4 or
                            any(type(x) is not int for x in record)):
                        raise ValueError("strand records must contain exactly four integers")
            if not isinstance(vh.get("stap_colors"), list):
                raise ValueError("stap_colors list required")

        for kind in ("scaf", "stap"):
            nodes = {(h, i): rec for h, vh in helices.items()
                     for i, rec in enumerate(vh[kind]) if rec != EMPTY}
            if not nodes:
                errors.append(kind + ": no occupied bases")
            crossovers = []
            for (h, i), rec in nodes.items():
                forward = (h % 2 == 0) == (kind == "scaf")
                for side in (0, 2):
                    target = tuple(rec[side:side + 2])
                    if target == (-1, -1):
                        continue
                    if target not in nodes:
                        errors.append(f"{kind} {h}:{i}: missing reference {target}")
                        continue
                    other = nodes[target]
                    if other[2 - side:4 - side] != [h, i]:
                        errors.append(f"{kind} {h}:{i}: nonreciprocal reference {target}")
                    th, ti = target
                    if h == th:
                        delta = (1 if forward else -1) * (1 if side == 2 else -1)
                        if ti != i + delta:
                            errors.append(f"{kind} {h}:{i}: local jump or wrong polarity")
                    else:
                        high = forward if side == 2 else not forward
                        source_coord = (helices[h]["row"], helices[h]["col"])
                        target_coord = (helices[th]["row"], helices[th]["col"])
                        if ti != i or not legal(lattice, source_coord, target_coord, kind, i, high):
                            errors.append(f"{kind} {h}:{i}: illegal lattice crossover to {target}")
                        if side == 2:
                            crossovers.append([h, i, th, ti])
            # Traverse each oligo along actual 5' -> 3' links; reject cycles for
            # staples, allow one circular scaffold for existing-file validation.
            unseen = set(nodes)
            paths = []
            cyclic = 0
            starts = [node for node, rec in nodes.items() if rec[:2] == [-1, -1]]
            for start in starts:
                path = []
                cur = start
                while cur in unseen:
                    unseen.remove(cur)
                    path.append(cur)
                    cur = tuple(nodes[cur][2:])
                if cur != (-1, -1):
                    errors.append(kind + ": path merges, cycles, or points outside occupied data")
                paths.append(path)
            while unseen:
                start = next(iter(unseen))
                path = []
                cur = start
                while cur in unseen:
                    unseen.remove(cur)
                    path.append(cur)
                    cur = tuple(nodes[cur][2:])
                if cur != start:
                    errors.append(kind + ": incomplete circular path")
                cyclic += 1
                paths.append(path)
            if kind == "scaf":
                if len(paths) != 1:
                    errors.append("scaffold must be exactly one connected oligo")
                if len(nodes) > scaffold_length:
                    errors.append("scaffold capacity exceeded")
            else:
                if cyclic:
                    errors.append("circular staples require nicks")
                for path in paths:
                    if not 20 <= len(path) <= 60:
                        errors.append(f"staple length {len(path)} outside 20..60 nt")
                    run = 0
                    last_h = None
                    for h, _ in path + [(None, None)]:
                        if h != last_h:
                            if last_h is not None and run < 8:
                                errors.append("staple domain shorter than 8 nt")
                            run = 0
                        last_h = h
                        run += 1
                # caDNAno permits additional color records on the same oligo.
                for h, vh in helices.items():
                    for color in vh["stap_colors"]:
                        if (not isinstance(color, list) or len(color) != 2 or
                                any(type(x) is not int for x in color) or
                                (h, color[0]) not in nodes or not 0 <= color[1] <= 0xFFFFFF):
                            errors.append("invalid staple color record")
                if not crossovers:
                    errors.append("no staple crossovers")
            report["counts"][kind] = {
                "occupied_bases": len(nodes), "oligos": len(paths),
                "circular_oligos": cyclic, "physical_crossovers": len(crossovers),
                "oligo_lengths": sorted(map(len, paths)),
            }
        for h, vh in helices.items():
            if not any(r != EMPTY for r in vh["scaf"]):
                errors.append("empty virtual helix")
            if any((a != EMPTY) != (b != EMPTY) for a, b in zip(vh["scaf"], vh["stap"])):
                errors.append("unpaired scaffold/staple positions")
        if expected is not None:
            if set(helices) != set(expected):
                errors.append("helix identifiers do not match expected design")
            for h, (coord, interval) in expected.items():
                vh = helices.get(h)
                if vh is None:
                    continue
                if (vh["row"], vh["col"]) != tuple(coord):
                    errors.append("helix coordinates do not match expected design")
                for kind in ("scaf", "stap"):
                    occupied = [i for i, r in enumerate(vh[kind]) if r != EMPTY]
                    if occupied != list(range(*interval)):
                        errors.append("occupied intervals do not match expected design")
        report["counts"]["vstrands"] = len(helices)
        report["counts"]["paired_positions"] = sum(
            a != EMPTY and b != EMPTY for vh in helices.values()
            for a, b in zip(vh["scaf"], vh["stap"]))
        report["status"] = "FAIL" if errors else "PASS"
    except (ValueError, TypeError, KeyError, IndexError, OSError, AttributeError) as exc:
        errors.append(str(exc))
    return report


def preservation(full, compact):
    try:
        same = read_data(full) == read_data(compact)
        return {"check": "compact_preservation", "status": "PASS" if same else "FAIL",
                "message": "All parsed JSON fields identical" if same else "Full/compact content differs"}
    except (OSError, ValueError) as exc:
        return {"check": "compact_preservation", "status": "FAIL", "message": str(exc)}
