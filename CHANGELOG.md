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
