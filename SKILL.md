---
name: generate-cadnano
description: "Generate lattice-aware cadnano v2 JSON for fixed DNA origami plate, helix-bundle and square-tube templates; validate exported routing and prepare topology-preserving compact files for manual CanDo submission. Reject unsupported shapes and invalid routing."
metadata:
  version: "2.0.0"
---

# Generate Cadnano V2

Use `README.md` for supported templates, dimensions, examples and limitations.
This skill generates a locally validated design, not a simulated 3D structure.

## Workflow

1. Identify the requested shape and dimensions. The only implemented templates
   are `rectangle`, `square`, `long_strip`, `planar_plate`, `2_helix_bundle`,
   `4_helix_bundle`, `6_helix_bundle`, and square-section `regular_tube`.
   Unsupported shapes must be identified explicitly. Do not adapt the Python
   template ad hoc, invent custom routing, or substitute shapes without consent.
2. Collect only missing choices: template, helix count or tube side count,
   axial length, optional lattice, and scaffold capacity. Offer the README
   defaults when the user has no dimensions. Explain that bp specifies an axial
   envelope; transverse width depends on lattice and helix count. Convert nm
   to axial bp using approximately 0.34 nm/bp and disclose rounding.
3. Read `references/lattice-rules.md` before interpreting crossover geometry.
   Run `python scripts/check_deps.py`. Install dependencies from
   `requirements.txt` if required and authorized in the current workflow.
4. Run `scripts/template_design.py` with the chosen template and output basename,
   or use `create_design()`. Every routing export must use this implementation
   and scadnano. Unknown parameters, incompatible lattices and shape/count
   contradictions must remain errors; never silently change them.
5. Require exit code zero, `design_status=GENERATED`, and a passing
   `validation_report` before presenting JSON as a validated design.
   Failure means report the specific reason and adjust parameters with the user;
   do not bypass the gate or write routing arrays by hand.
6. Inspect the report's actual coordinates, occupied intervals, end insets,
   scaffold usage, staple lengths and crossover counts. Explain material
   differences from requested dimensions. Templates have lattice-constrained
   stepped ends. In particular, a honeycomb four-helix bundle has an open
   neighbor chain; it is not a closed four-helix ring.
7. Deliver `.full.json`, `.cando_compact.json`, `.report.json`. Full is the
   editable master; compact preserves every parsed JSON field. Regenerate and
   revalidate compact after edits to the master. Existing output names are
   protected; use a new basename.
8. If cadnano2 is available, run `scripts/check_cadnano.py` in its environment
   for native import, geometry and roundtrip verification. State separately
   whether native loading or native rendering was actually tested.

## Existing-file validation

Run `python scripts/template_design.py --validate INPUT.json --lattice LATTICE`.
An explicit lattice is required. `validation.validate()` is the same gate used
for generation. V2 intentionally rejects nonzero loop/skip and nonempty legacy
loop fields. Preserve the input and report the unsupported feature.

## Status and evidence

- `GENERATED`: both design files and report were created after validation.
- `UNSUPPORTED_REQUEST`: no implemented template; no design files generated.
- `GENERATION_FAILED`: parameters, construction or checks failed; no successful
  export. Never promote this result to a validated status.
- `CANDO_INPUT_GENERATED`: local structural validation and compact preservation
  passed. It does not mean the CanDo website accepted or simulated the file.
- Sequence: `not_assigned`; a 7249-nt budget does not assign M13mp18 sequence.
- Submission: `NOT_SUBMITTED`; the generator never submits to CanDo.
- Experiment: `EXPERIMENTALLY_UNVALIDATED`; neither JSON validation nor a CanDo
  prediction supplies experimental evidence.

## CanDo handoff

Use `references/cando-submission-guide.md` if the user asks about submission.
The normal handoff is for the user to upload compact JSON and select the
reported lattice. Keep all scaffold, staples, loops/skips and metadata in
compact; never use a scaffold-stripped file. Do not fabricate submission,
results, sequence assignment, experimental success or private account details.

## Development and validation

If asked to modify this skill, use meaningful positive and corrupted-input
regression tests in `scripts/test_design.py`. Test generated JSON, not only
in-memory scadnano objects. Repeat the independent cadnano2 integration check
after changing geometry. Keep the README and supported catalog consistent;
do not call unimplemented shapes supported.
