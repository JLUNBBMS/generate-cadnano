# Changelog

## 2.0.0 — 2026-09-15

### Fixed

- Replaced index-difference adjacency checks with actual square/honeycomb coordinates.
- Rebuilt scaffold routing around legal direction-specific crossover sites.
- Rebuilt staples using legal full crossovers and bounded-length nicking; added tube/ring seam connections.
- Validate both 5′ and 3′ references, strand direction, actual occupied bases,
  connected oligos, helix parity, complete pairing, and crossover endpoint type.
- Count each physical crossover once and preserve every field in compact JSON.
- Validate the exported cadnano JSON before publishing output files.
- Reject incompatible lattices, unknown parameters and mismatched bundle counts.
- Enforce separate physical envelope constraints for square, strip and wide plate.
- Avoid ambiguous array lengths divisible by both lattice periods.
- Protect existing output files and return nonzero CLI exit codes on failure.

### Changed / migration

- Single unified `validation_report` object with status/errors/counts replaces
  the V1 list of permissive checks. V1 validation helpers are replaced by
  `validation.validate()` and `--validate`; `validate_crossovers()` now invokes
  that full gate. `create_design()` returns structured failures.
- Staple length is 20–60 nt per complete oligo, with at least 8 nt per binding
  domain. V1's domain-length claim was unsuitable for direction-specific routing.
- 16 incomplete/unimplemented templates explicitly refuse generation.
- Nonzero insertions/deletions and custom routing are explicitly unsupported;
  their data is never discarded to make a design pass.
- Removed legacy scaffold-stripped `.cando.json` exporter and stale instructions.
- README describes occupied intervals, stepped ends, default shapes and actual limitations.

### Added

- Portable positive/negative regression suite and optional independent cadnano2
  native import, crossover-table and roundtrip test.
- Reproducible dependency pin, Git ignore rules and release validation evidence.

This release establishes local format/routing/lattice correctness for tested
templates. It makes no claims about CanDo acceptance or experimental folding.
# 3.0.0 — 2026-09-17

- Preserve all eight V2 template routes and add nine V3 entry points.
- Add exact-count lattice-cycle search, rectangular controls, symmetric honeycomb hexagonal shells and compact variable-count bundles.
- Add fixed-cap containers using interior parallel-helix blocks with a central cavity and a single scaffold routed through all occupied segments.
- Schedule staple contacts globally; validate disjoint cap intervals, actual cap occupancy, lumen clearance and contact reinforcement.
- Compact physical helix IDs by parity for native cadnano roundtrip compatibility.
- Add geometry previews, V3 negative tests and independent native integration evidence.
- Bound search explicitly. Not every integer, lattice, cap thickness or polygon is feasible. Polygon mode supports square/4 and honeycomb/6; no arbitrary triangle or hinged lids.
- New-template reports distinguish wall count from total helix columns. Their occupied_intervals field maps helix IDs to interval lists; legacy template reports retain V2 format.
