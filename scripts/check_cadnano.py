#!/usr/bin/env python3
"""Optional independent integration test using cadnano2's native model.

Run in a separate environment with cadnano2 and PyQt6 installed.
Does not import the generator's lattice tables or validator.
"""

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--lattice", required=True, choices=("square", "honeycomb"))
    parser.add_argument("--output")
    args = parser.parse_args()
    import cadnano2.util as util
    util.qtFrameworkList = ["PyQt"]
    from PyQt6.QtWidgets import QApplication
    qapp = QApplication.instance() or QApplication([])
    import cadnano2.cadnano as cn
    from PyQt6.QtCore import QObject, pyqtSignal

    class Signals(QObject):
        created = pyqtSignal(object)

    signals = Signals()
    app = cn.app()
    app.documentWasCreatedSignal = signals.created
    # cadnano2's headless prefs omit these GUI defaults. Only fill that shell;
    # the native decoder, model, encoder and crossover tables are unmodified.
    for key, value in {"honeycombRows": 30, "honeycombCols": 32,
                       "honeycombSteps": 2, "squareSteps": 2}.items():
        setattr(app.prefs, key, value)
    from cadnano2.model.document import Document
    from cadnano2.model.enum import LatticeType, StrandType
    from cadnano2.model.io.legacydecoder import import_legacy_dict
    from cadnano2.model.io.legacyencoder import legacy_dict_from_doc
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    lattice = LatticeType.Square if args.lattice == "square" else LatticeType.Honeycomb
    doc = Document()
    import_legacy_dict(doc, data, lattice)
    if len(doc.parts()) != 1:
        raise AssertionError("Expected exactly one cadnano part")
    part = doc.parts()[0]
    native_helices = list(part.getVirtualHelices())
    if len(native_helices) != len(data["vstrands"]):
        raise AssertionError("Helix count changed on import")
    errors = []
    crossovers = {"scaf": 0, "stap": 0}
    for vh in native_helices:
        adjacent = part.getVirtualHelixNeighbors(vh)
        for kind, strand_type, strand_set in (("scaf", StrandType.Scaffold, vh.scaffoldStrandSet()),
                                             ("stap", StrandType.Staple, vh.stapleStrandSet())):
            for strand in strand_set:
                target = strand.connection3p()
                if target is None:
                    continue
                other = target.virtualHelix()
                index = strand.idx3Prime()
                crossovers[kind] += 1
                if other not in adjacent:
                    errors.append(f"{kind} {vh.number()}:{index}: not a native lattice neighbor")
                    continue
                direction = adjacent.index(other)
                # A domain to the left uses cadnano Low; domain to right High.
                is_left = index == strand.highIdx()
                allowed = (part.getPreXoversLow if is_left else part.getPreXoversHigh)(strand_type, direction)
                if index not in allowed or index != target.idx5Prime():
                    errors.append(f"{kind} {vh.number()}:{index}: native phase mismatch")
    encoded = legacy_dict_from_doc(doc, "roundtrip.json", [(v["row"], v["col"]) for v in data["vstrands"]])
    back = {vh["num"]: vh for vh in encoded["vstrands"]}
    for vh in data["vstrands"]:
        for field in ("num", "row", "col", "scaf", "stap", "loop", "skip"):
            if vh[field] != back[vh["num"]][field]:
                errors.append(f"native roundtrip changed helix {vh['num']} {field}")
    oligos = list(part.oligos())
    result = {"status": "FAIL" if errors else "PASS", "errors": errors,
              "virtual_helices": len(native_helices), "crossovers": crossovers,
              "scaffold_oligos": sum(not x.isStaple() for x in oligos),
              "staple_oligos": sum(x.isStaple() for x in oligos),
              "scaffold_lengths": sorted(x.length() for x in oligos if not x.isStaple()),
              "staple_lengths": sorted(x.length() for x in oligos if x.isStaple()),
              "native_routing_roundtrip": not any("roundtrip" in e for e in errors)}
    text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
