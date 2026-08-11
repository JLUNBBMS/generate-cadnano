---
name: generate-cadnano
description: "Beginner-friendly DNA origami CAD design assistant. Generate cadnano/scadnano-compatible .json design files for basic regular structures, with CanDo submission preparation and 3D prediction workflow guidance."
metadata:
  type: tool
  domain: dna-origami
---

# Generate Cadnano

Beginner-friendly DNA origami CAD design assistant. Generates cadnano-compatible designs from natural language descriptions for a defined set of supported regular structures, exports CanDo-submittable JSON files and `cando_submission` parameter packages, and guides users through the CanDo 3D structure prediction workflow.

## What This Skill IS

A guided design tool that helps beginners and general users:

1. Describe a desired DNA origami shape in plain language
2. Select a supported V1 structure template via step-by-step questions
3. Provide dimensions and structural parameters (with presets for beginners)
4. Generate the design using `scadnano`
5. Output a complete caDNAno JSON master (`design.full.json`)
6. Derive a topology-preserving CanDo submission file (`design.cando_compact.json`) from the master
7. Build a `cando_submission` parameter package
8. Run basic format, topology, and consistency checks
9. Report design status, validation status, and experiment status clearly
10. Provide clear usage instructions and limitation notes

## What This Skill IS NOT

- An arbitrary-shape generator
- An image/SVG-to-DNA-origami converter
- A system that auto-generates all complex 3D structures
- An experimental success-rate predictor
- A folding-yield guarantor
- A tool that guarantees CanDo will accept the file

---

## Supported Shapes (V1)

### 1. Planar Regular Structures

| Shape ID | Description | Lattice Default |
|----------|-------------|-----------------|
| `rectangle` | Generic rectangle, user-specified width × height | `square` |
| `square` | Special case of rectangle (width = height) | `square` |
| `long_strip` | Narrow, long rectangular strip | `square` |
| `planar_plate` | Wide, flat rectangular plate | `square` |
| `rectangular_frame` | Hollow rectangular border | `square` |
| `plate_with_rectangular_hole` | Plate with a single rectangular hole | `square` |
| `simple_triangle` | Pre-defined regular triangle template | `square` |
| `simple_trapezoid` | Pre-defined regular trapezoid template | `square` |
| `simple_hexagon` | Pre-defined regular hexagon template | `square` |
| `L_shape` | Composed of 2 orthogonal rectangular regions | `square` |
| `T_shape` | Composed of 2 orthogonal rectangular regions | `square` |
| `cross_shape` | Composed of 3+ orthogonal rectangular regions | `square` |

**Rules for planar structures:**
- `square` must be implemented as a special case of `rectangle`
- `L_shape`, `T_shape`, `cross_shape` must be composed of multiple regular rectangular regions — never a single arbitrary polygon
- Triangle, trapezoid, and hexagon must use pre-defined regular templates — no freehand contours
- Do NOT accept arbitrary SVG, hand-drawn outlines, or bitmap images as input for direct JSON generation
- Do NOT auto-approximate complex arbitrary contours into production DNA origami
- If a shape lacks a verified deterministic routing implementation, mark it "not yet supported" — never generate from name alone

### 2. Regular 3D Structures

| Shape ID | Description | Lattice Default |
|----------|-------------|-----------------|
| `2_helix_bundle` | Two-helix parallel bundle | `honeycomb` |
| `4_helix_bundle` | Four-helix parallel bundle | `honeycomb` |
| `6_helix_bundle` | Six-helix parallel bundle | `honeycomb` |
| `regular_tube` | Tube with regular cross-section (square or hexagonal) | template-determined |
| `open_box` | Box with one or more open faces | `square` |
| `static_closed_box` | Fully closed box, no moving parts | `square` |
| `simple_U_shape` | U-shaped channel, single scaffold | `square` |
| `simple_channel` | Straight open channel / trough | `square` |

**Rules for 3D structures:**
- Only regular, static, single-scaffold structures
- `static_closed_box`: must NOT include dynamic open/close mechanisms
- Tubes, bundles, and boxes must use explicit template parameters — never invent topology on the fly
- Tube lattice is determined by the specific tube template (square-section → `square`; hexagonal-section → `honeycomb`)

### 3. Assembly Structures

| Shape ID | Description |
|----------|-------------|
| `simple_assembly` | Up to 3 regular modules with pre-defined connections |

**Rules for assemblies:**
- Max 3 modules, each from the supported shapes catalog
- Only pre-defined connection types; no arbitrary angles or interfaces
- Lattice determined per module by its template

### 4. Approximation Structures

| Shape ID | Description |
|----------|-------------|
| `polygon_approximation_of_disk` | N-gon approximating a circular disk |
| `polygon_approximation_of_ring` | N-gon ring approximating a circular annulus |
| `piecewise_linear_arc` | Straight segments approximating a curved arc |

**Approximation output requirements — the report MUST state:**
- The user's requested ideal shape
- The actual approximation shape used
- Number of polygon sides or linear segments
- Estimated dimensional error
- Potential impact of boundary discontinuity or non-smooth edges

---

## Outside V1 Scope (Not Auto-Generated)

The following shape requests have research precedents in DNA nanotechnology but are **outside the current V1 reliable automatic generation scope**. This skill will not produce final caDNAno JSON for them:

- `flower`, `nanoflower`
- `smiley`, `animal_shape`, `human_face`
- `arbitrary_logo`, `arbitrary_image_to_origami`, `arbitrary_svg_to_origami`
- `dynamic_open_close`, `strand_displacement_machine`
- `molecular_robot`, `molecular_motor`, `force_sensor`
- `complex_hinge`, `complex_mechanical_device`
- `complex_curved_surface`, `sphere`, `saddle_surface`
- `arbitrary_twisted_structure`, `strong_twist`
- `arbitrary_polyhedron`
- `multi_scaffold_design`
- `large_modular_superstructure`

### Out-of-Scope Handling Protocol

When a user requests any out-of-scope shape, you MUST:

1. **Clearly state** the request exceeds V1 automatic design scope
2. **Acknowledge** that such structures have research precedents in DNA nanotechnology, but are not in the current reliable auto-generation range
3. **Never** generate plausibly-structured but unverified JSON
4. **If possible**, decompose the request into one or more supported V1 static basic structures
5. **Ask** whether the user would like to generate those basic structures first
6. **If an approximation is feasible**, clearly label it "approximate" — never call it an exact structure

---

## Beginner-Friendly Step-by-Step Questions

Do NOT demand that users understand technical terminology upfront. Ask these questions in order, one or two at a time. Skip questions that don't apply to the user's chosen category.

### Q1 — Structure Type

Ask the user to describe their target in everyday terms. If they are unsure, offer these categories:

- Flat plate / panel
- Long strip or beam
- Tube / pipe
- Box / container
- Plate with a hole
- U-shape or channel / trough
- Simple multi-part assembly (max 3 modules)
- Other (describe in your own words)

Map their answer to a shape ID in the Supported Shapes catalog. If ambiguous, ask clarifying questions — do not guess. If out-of-scope, apply the Out-of-Scope Handling Protocol.

### Q2 — Dimensions and Units

Once the shape is identified, ask for dimensions. Not every dimension applies to every shape — ask only what's relevant:

1. Length (longest dimension)
2. Width
3. Height or thickness (for 3D structures)
4. Units: **nanometers (nm)** or **base-pairs (bp)**

Default unit convention:
- Planar structures → base-pairs
- 3D bundles, tubes, boxes → nanometers

If the user doesn't know specific dimensions, offer three presets:

| Preset | Planar (approx. bp) | 3D Bundle/Tube/Box (approx. nm) |
|--------|---------------------|---------------------------------|
| `small` | ~50 × 50 bp | ~20 × 20 × 20 nm |
| `medium` | ~100 × 100 bp | ~40 × 40 × 40 nm |
| `large` | ~200 × 200 bp | ~80 × 80 × 80 nm |

### Q3 — Allow Approximation?

If the user's ideal shape does not exactly match a supported template:

- Ask: "An exact match isn't available for that shape. Would you accept an approximate version using a supported V1 template?"
- If yes → proceed with the closest approximation shape and clearly label it APPROXIMATE
- If no → explain the limitation and offer the closest exact supported shape as an alternative

### Q4 — Use Default Scaffold?

Ask: "Use the default scaffold (M13mp18, 7249 nucleotides)?"

- Default: **yes** (M13mp18)
- If the user specifies a different scaffold, note the length and warn if the design exceeds it
- The scaffold is the long single-stranded DNA that the staples bind to — beginners don't need to change this

### Q5 — Accept Default Lattice?

If the user is unfamiliar with square vs. honeycomb lattice:
- Do NOT force them to learn the terminology
- The skill selects the appropriate lattice based on the template (see Unified Lattice Rules below)
- Explain the choice in one plain-language sentence
- Ask: "The design will use a [square/honeycomb] lattice arrangement. Is that okay?"
- If the user explicitly overrides, follow the Unified Lattice Rules

### Q6 — Need a CanDo Parameter Package?

Ask: "Would you also like a CanDo 3D structure prediction parameter package?"

- If yes → collect `name`, `affiliation`, `email` (or leave empty and list in `missing_fields`)
- Default CanDo settings unless user requests otherwise:
  - `model_resolution = "coarse"`
  - `include_movie = "no"`
  - `atomic_model_option = "no"`
- If no → skip CanDo-related steps; output only `design.full.json`

---

## Unified Lattice Rules

### Planar regular plates (rectangle, square, long_strip, planar_plate, rectangular_frame, plate_with_rectangular_hole, simple_triangle, simple_trapezoid, simple_hexagon, L_shape, T_shape, cross_shape)
- **Default: `square`**
- Only use `honeycomb` if the user explicitly chooses it

### Regular tubes, bundles, and boxes
- **Lattice is determined by the specific template:**
  - `2_helix_bundle`, `4_helix_bundle`, `6_helix_bundle` → `honeycomb`
  - Square-section tube → `square`
  - Hexagonal-section tube → `honeycomb`
  - `open_box`, `static_closed_box` → `square`
- If the template supports only one lattice → use that one
- `simple_assembly`: lattice determined per module by each module's template

### User explicitly specifies a lattice
- **Honor the user's choice when possible**
- If the chosen lattice is incompatible with the shape template:
  1. Clearly state the incompatibility
  2. Do NOT silently swap
  3. Ask whether the user accepts the template's default lattice

### Lattice report format

Every output must include:

```text
lattice_type: "square" | "honeycomb"
lattice_selection_reason: <one-sentence plain-language explanation>
```

---

## Master File Rules (HIGHEST PRIORITY)

- **`design.full.json` is the ONE AND ONLY master.** All design authority lives here
- **`design.cando_compact.json` can ONLY be derived from the master.** It is a topology-preserving submission artifact, never a design source
- **All design modifications, shape adjustments, sequence edits, and cadnano previews MUST go back to `design.full.json`**
- **`design.cando_compact.json` MUST retain all scaffold routing data** (`scaf` arrays in `vstrands` must be kept intact for CanDo dsDNA recognition)
- **Never delete valid structural staples from `design.cando_compact.json` to satisfy CanDo** — if CanDo rejects a file, the fix belongs in the submission parameters, not in removing real staples
- **CanDo infers dsDNA geometry from staple positions and cross-helix connections** — removing scaffold or structural staples breaks this inference

> "The full version is the master; the compact version is a topology-preserving submission artifact. All design modifications must be based on the full version."

> Pitfall warning: "The compact CanDo file preserves all scaffold and staple topology. Never upload a scaffold-stripped file to CanDo — it will fail dsDNA recognition. If only a staple-only file is output, the user cannot return to cadnano for complete editing."

---

## Inputs

- **structure_description**: Natural language description of the target DNA origami structure.
- **output_basename**: Base name for output files (default: `design`). Produces `design.full.json` and `design.cando_compact.json`.
- **cando_params** (optional): User-supplied overrides for CanDo submission fields.

---

## Workflow

### Step 1 — Dependency Check

Run `scripts/check_deps.py` to verify `scadnano` is installed:

```bash
python scripts/check_deps.py
```

If missing: `pip install scadnano`

### Step 2 — Category Discovery & Shape Matching

Use the Beginner-Friendly Step-by-Step Questions (Q1–Q3 above) to discover the user's target. Map the user's description to the Supported Shapes catalog:

- If it matches a supported shape → proceed to parameter collection
- If it matches an out-of-scope shape → apply the Out-of-Scope Handling Protocol
- If ambiguous → ask clarifying questions; do not guess

### Step 3 — Parameter Collection

Collect dimensions, lattice preference, scaffold choice, and CanDo preference using Q2–Q6 of the step-by-step questions. Determine:

- Shape ID from the supported catalog
- Dimensions (in bp or nm)
- Grid/lattice (using the Unified Lattice Rules)
- Scaffold choice (default: M13mp18, 7249 nt)
- Whether approximation is acceptable (for shapes that need it)
- Staple crossover strategy (follow template conventions)
- DNA polarity: scaffold runs 5'→3'; staples are antiparallel

### Step 4 — Generate Full Master Design

Write and execute a Python script using `scadnano` that:

1. Creates a `scadnano.Design` with the correct `grid` type for the chosen shape template
2. Adds helices via `design.add_helix(...)` with proper `max_bases`
3. Routes scaffold strand(s) with `scadnano.Strand(..., is_scaffold=True)` — serpentine raster by default
4. Adds staple strands with correct crossover positions and antiparallel polarity
5. Writes the full master: `design.write_cadnano_v2_file(directory='.', filename=basename + ".full.json")`

Use `scripts/template_design.py` as the canonical starting point. Adapt it for the specific shape.

**Critical rules:**
- Use `scadnano` Python API — never hand-write raw Cadnano JSON
- **Polarity**: scaffold `forward=True` on odd helices, `forward=False` on even helices (or follow grid convention); staples are opposite
- **Crossovers**: respect grid even/odd offset rules
- **Staple length**: 20–60 nt per domain, ~32 nt average
- **Scaffold**: M13mp18 = 7249 nt; ensure total usage does not exceed

Save the generation script (temporary, overwritten each run). Run it:

```bash
python scripts/generate_design.py
```

If execution fails: read traceback, fix, retry up to 2 times before reporting failure.

### Step 5 — Run Basic Validation

After generating `design.full.json`, run the following checks. The validation status advances progressively: each level implies all prior levels passed.

- **5a passes → `validation_status = FORMAT_VALIDATED`**
- **5a–5e all PASS (no WARNINGs) → `validation_status = TOPOLOGY_VALIDATED`**
- **Any WARNING on 5b–5e keeps status at `FORMAT_VALIDATED`** — warnings are reported in `validation_warnings`

#### 5a — JSON Format Check
- Verify the file is valid JSON (parseable without errors)
- Verify it conforms to cadnano v2 schema (has `vstrands` key at minimum)
- Report: **"JSON format: PASSED"** or **"JSON format: FAILED — <reason>"**

#### 5b — Scaffold Check
- Verify at least one `scaf` entry exists across `vstrands` with non-empty routing data
- Verify total scaffold nucleotide usage does not exceed the declared scaffold length (default 7249 nt)
- Report: **"Scaffold check: PASSED — <N> nt used of <M> nt available"** or **"Scaffold check: FAILED — <reason>"**

#### 5c — Staple Check
- Verify at least one `stap` entry exists across `vstrands`
- Verify staple domain lengths are in the 20–60 nt range
- Report: **"Staple check: PASSED — <N> staples, domain lengths <min>–<max> nt"** or **"Staple check: FAILED — <reason>"**

#### 5d — Crossover Check
- Verify that scaffold routing alternates between neighboring helices (serpentine pattern)
- Verify staple crossovers follow grid even/odd offset rules for the chosen lattice
- Report: **"Crossover check: PASSED"** or **"Crossover check: WARNING — <reason>"**

#### 5e — Dimension Check
- Verify helix count and bases-per-helix match the user's requested dimensions (within tolerance)
- For approximation shapes: verify the approximation report is present and dimensional error is stated
- Report: **"Dimension check: PASSED — <N> helices x ~<M> bp"** or **"Dimension check: WARNING — <discrepancy>"**

### Step 6 — Generate Topology-Preserving Compact CanDo File

Generate `design.cando_compact.json` — the **only CanDo submission file** produced in the default workflow. It preserves full topology in compact JSON format.

> **Legacy note:** The old scaffold-stripped `design.cando.json` is NO LONGER generated by default. It was removed to prevent accidental upload of a scaffold-free file to CanDo, which would cause "no dsDNA" errors. If you need the old format for a specific reason, ask explicitly.

**After successful compact file generation + topology preservation check passes → `validation_status = CANDO_INPUT_GENERATED` (highest local-only level).**

**Rules (mandatory):**
- Read the full master JSON (`design.full.json`) WITHOUT modifying topology
- Scaffold (`scaf`) entries are **KEPT intact** — NOT cleared, NOT replaced with `[-1,-1,-1,-1]`
- Staple (`stap`) entries are **KEPT intact**
- Staple loop (`stapLoop`) entries are **KEPT intact**
- All helix metadata, vstrand structure, and connectivity are **FULLY PRESERVED**
- Output is **compact JSON**: no indentation, no extra whitespace, `separators=(",", ":")`

**Pre-serialization compatibility checks (non-destructive, inspect only):**
- **vstrands**: Verify vstrands list is non-empty
- **scaffold**: Verify at least one valid scaffold topology entry exists
- **staple**: Verify at least one valid staple topology entry exists
- **dsDNA**: Verify at least one position has both scaffold AND staple (required for CanDo dsDNA recognition)
- **crossover**: Verify at least one cross-helix crossover connection exists

### Step 6b — CanDo Compatibility Report

After generating `design.cando_compact.json`, report the compatibility check results:

```
CanDo compatibility check:
- vstrands: PASS — <N> vstrands present
- scaffold: PASS — <N> scaffold records
- staple: PASS — <N> staple records
- dsDNA: PASS — <N> potential dsDNA positions
- crossover: PASS — <N> crossover records
- compact JSON serialization: PASS
```

### Step 7 — Compact Topology Preservation Check

After generating `design.cando_compact.json`, verify it preserves the full master topology exactly.

- Verify both files have the same number of `vstrands`
- Verify `scaf` arrays are identical between full and compact files (topology preserved)
- Verify `stap` arrays are identical between full and compact files
- Verify `stapLoop` arrays are identical between full and compact files
- Report: **"Compact preservation: PASSED"** or **"Compact preservation: FAILED — <reason>"**

**After passing → confirms `CANDO_INPUT_GENERATED`. `CANDO_COMPATIBILITY_TESTED` requires a real CanDo service call — not reachable from local checks alone.**

### Step 8 — Generate `cando_submission` Parameter Object

Build a structured `cando_submission` object. See `references/cando-submission-guide.md` for the full field-to-form mapping.

**Default value rules:**
1. Unspecified params use CanDo webpage defaults
2. `name`, `affiliation`, `email` — if user hasn't provided them, leave empty and list in `missing_fields`. **Never fabricate**
3. Unless user requests high precision, movie, or atomic model, default to: `model_resolution = "coarse"`, `include_movie = "no"`, `atomic_model_option = "no"`
4. `lattice_type` follows the Unified Lattice Rules above — NOT a single global default

### Step 9 — Determine Submission Mode

Check environment capabilities and apply the decision tree in `references/cando-submission-guide.md`.

- If CanDo is unreachable → `export_only`
- If reachable but no login/automation → `export_only` with manual guidance
- If reachable + automation available + logged in → `semi_automatic` or `automatic_if_environment_allows`
- Never claim login/registration is complete when it isn't

### Step 10 — CanDo Submission (if environment allows)

1. Confirm all required fields are available
2. If fields missing → ask user; list in `missing_fields`
3. If all present + network reachable + automation available + logged in → attempt auto-fill and upload of `design.cando_compact.json`
4. Report submission status clearly
5. **Always state: CanDo results are asynchronous. Real-time completion is NOT guaranteed**
6. If auto-fetch of results isn't supported → switch to semi-automatic: tell user to bring the result link/file back

**Status values:** `submitted`, `submission_failed`, `needs_more_information`, `login_required`, `environment_not_supported`, `export_only`

**Never claim CanDo computation is complete without real results. Never fabricate 3D predictions.**

---

## Design Status, Validation Status, Experiment Status, and Submission Status

Every final output must include four clearly separated status blocks. The canonical definitions are in `references/cando-submission-guide.md`; this section provides the skill-level summary.

### 1. Design Status (`design_status`)

Refers to the `design.full.json` master file generation outcome:

| Status | Meaning |
|--------|---------|
| `DRAFT` | User is still describing requirements; no generation attempted |
| `GENERATED` | Master file produced by the template without errors |
| `UNSUPPORTED_REQUEST` | Shape is outside V1 scope; Out-of-Scope Handling Protocol applied |
| `GENERATION_FAILED` | Template execution errored; no valid master file exists |

### 2. Validation Status (`validation_status`)

Progressive — each level implies all prior levels passed:

| Status | Meaning | Triggered When |
|--------|---------|----------------|
| `NOT_RUN` | No validation checks executed | Generation failed before validation could run; or JSON format check itself failed |
| `FORMAT_VALIDATED` | JSON parses and conforms to cadnano v2 schema | `validate_json_structure` passes. Topology checks may have WARNINGs or FAILs — status stays here until all 4 topology checks are clean |
| `TOPOLOGY_VALIDATED` | Scaffold, staple, crossover, and dimension checks all PASS with zero WARNINGs | All 4 topology checks return PASS (no WARNING, no FAIL). Any WARNING keeps status at `FORMAT_VALIDATED` because it may indicate unreliable topology |
| `CANDO_INPUT_GENERATED` | `design.cando_compact.json` derived + compact topology preservation check passes | All topology checks clean + compact CanDo file derived + `compact_preservation` PASS. **This is the highest level the local tool can reach on its own** |
| `CANDO_COMPATIBILITY_TESTED` | Real CanDo service or external CanDo tool confirmed compatibility | **Requires a real CanDo program/service call.** Cannot be set from local file checks alone. Not reachable by the current local-only toolchain |

### 3. Experimental Status (`experimental_status`)

Refers to real-world experimental evidence:

| Status | Meaning |
|--------|---------|
| `EXPERIMENTALLY_UNVALIDATED` | No experimental data exists. **Default for all generated designs.** |
| `EXPERIMENTALLY_VALIDATED` | User has provided experimental confirmation (folding, AFM, TEM, etc.) |

**Rules:**
- Default: `EXPERIMENTALLY_UNVALIDATED`
- CanDo 3D prediction results **do not** constitute experimental validation
- Only real experimental data from the user can change this status

### 4. Submission Status (`submission_status`)

Refers to the CanDo submission lifecycle:

| Status | Meaning |
|--------|---------|
| `NOT_SUBMITTED` | Files exported; no CanDo submission attempted |
| `SUBMISSION_PREPARED` | `cando_submission` package built; ready for submission |
| `SUBMITTED` | `design.cando_compact.json` uploaded to CanDo; confirmation received |
| `QUEUED` | CanDo has queued the job for processing |
| `RUNNING` | CanDo computation is in progress |
| `COMPLETED` | CanDo returned 3D prediction results |
| `FAILED` | CanDo job failed (server error, invalid input, etc.) |
| `UNKNOWN` | Submission status cannot be determined |

**Rules:**
- Default: `NOT_SUBMITTED` — this skill generates files; it does not submit to CanDo by default
- Never claim `SUBMITTED` or beyond without a real upload confirmation
- Never claim `COMPLETED` without real CanDo output

Report these four statuses together at the top of every final reply:

```text
DESIGN STATUS:       <DRAFT | GENERATED | UNSUPPORTED_REQUEST | GENERATION_FAILED>
VALIDATION STATUS:   <NOT_RUN | FORMAT_VALIDATED | TOPOLOGY_VALIDATED | CANDO_INPUT_GENERATED | CANDO_COMPATIBILITY_TESTED>
EXPERIMENTAL STATUS: <EXPERIMENTALLY_UNVALIDATED | EXPERIMENTALLY_VALIDATED>
SUBMISSION STATUS:   <NOT_SUBMITTED | SUBMISSION_PREPARED | SUBMITTED | QUEUED | RUNNING | COMPLETED | FAILED | UNKNOWN>
```

---

## Final Reply Requirements

Every final reply MUST clearly distinguish which of the following have been achieved. Never conflate or skip a stage — report each one honestly:

1. **File format correct** — JSON parses and conforms to cadnano v2 schema
2. **Topology check passed** — Scaffold, staples, crossovers, and dimensions are within valid ranges
3. **CanDo file generated** — `design.cando_compact.json` derived from master with full topology preserved
4. **CanDo actually submitted** — File was uploaded to CanDo (not just exported); real submission confirmation exists
5. **CanDo results returned** — Real 3D prediction results received from CanDo (not fabricated)
6. **Experiment verified** — User has reviewed CanDo results and confirmed they match expectations

Each stage is a gate: stage N cannot be claimed true unless stages 1 through N-1 are also true. A design that passes file format but fails topology must report only stage 1 as true.

---

## CanDo Compatibility Rules

- CanDo submission file MUST retain full scaffold routing data (`scaf` arrays in `vstrands` must be kept intact for dsDNA centerline inference)
- Uploading a scaffold-stripped file to CanDo will cause `no dsDNA` errors
- CanDo infers dsDNA geometry from staple positions, scaffold topology, and cross-helix connections
- When generating `design.cando_compact.json`: preserve ALL scaffold, staple, and crossover topology; use compact JSON serialization
- `design.cando_compact.json` should include all structural staples; do not remove any valid staples
- Remind user to select the correct lattice type matching the design on the CanDo submission form
- The legacy scaffold-stripped `.cando.json` is NO LONGER generated by default — request it explicitly only if needed

---

## CanDo Login & Account Boundaries

- CanDo may require registration/login for 3D submission features
- **This skill does NOT forge login state, bypass registration, or circumvent access controls**
- The skill prepares: `design.cando_compact.json`, `cando_submission`, `missing_fields`, `submission_notes`
- If the environment supports controlled browser automation AND the user is already logged in, the skill may assist with form-filling and upload
- If the environment does not support login-state inheritance or web automation, the skill degrades to "export parameter package + manual submission guidance" mode

> "If CanDo requires login or account privileges, the skill must not pretend registration or login is complete. It can only assist with submission under an existing valid login session."

---

## Network Environment Boundaries

- CanDo may be inaccessible from certain regions or networks
- This skill must NOT assume CanDo is always reachable
- When CanDo is unreachable → default to `export_only`:
  - Export `design.full.json`, `design.cando_compact.json`, `cando_submission`
  - Output `missing_fields` and `submission_notes`
  - Guide user to manually submit in a CanDo-accessible network environment
- Do NOT instruct users to bypass network restrictions
- If CanDo is reachable → semi-automatic or automatic mode may proceed

---

## Result Retrieval Modes

### A. Export Only
When: no auto network access, no web automation, no login inheritance, or CanDo unreachable.

Output: `design.full.json` + `design.cando_compact.json` + `cando_submission` + `missing_fields` + `submission_notes` + manual submission instructions.

### B. Semi-Automatic
When: skill can generate files and possibly submit, but cannot poll results or read user email.

- Skill helps prepare and possibly submit
- Clearly states: CanDo results are asynchronous
- User brings result link/file back to conversation
- Skill continues to help parse, explain, render, or convert results

### C. Full Automatic (rare)
Only when: environment supports task tracking, file download, result return, valid login, and CanDo reachable.

---

## CanDo Auto-Submission Interaction Logic

When user says "submit to CanDo" or "directly connect to CanDo":

1. Check if all required info is present: `name`, `affiliation`, `email`, `lattice_type`, `model_resolution`, `include_movie`, `atomic_model_option`
2. If missing → ask user; list in `missing_fields`
3. If complete + network reachable + web/form automation available + valid login → attempt auto-submit
4. Report status: `submitted`, `submission_failed`, `needs_more_information`, `login_required`, `environment_not_supported`, `export_only`
5. NEVER claim CanDo computation is complete without real results
6. NEVER fabricate 3D prediction output without real CanDo results

> "CanDo result retrieval is typically an asynchronous process. The skill may handle submission and tracking, but must not fabricate completed 3D predictions."

---

## Reply Templates

### Standard output (every design):

```
DESIGN STATUS:       GENERATED
VALIDATION STATUS:   <CANDO_COMPATIBILITY_TESTED | CANDO_INPUT_GENERATED | TOPOLOGY_VALIDATED | FORMAT_VALIDATED | NOT_RUN>
EXPERIMENTAL STATUS: EXPERIMENTALLY_UNVALIDATED
SUBMISSION STATUS:   NOT_SUBMITTED

- Generated `design.full.json` — for cadnano viewing/editing, contains scaffold + staples
- Generated `design.cando_compact.json` — **topology-preserving compact CanDo file** (scaffold + staples + crossovers intact, compact JSON)
- Generated `cando_submission` — CanDo form parameters, usable for manual fill or automated form-filling
- Lattice: <lattice_type> — <lattice_selection_reason>
- Use `design.full.json` in cadnano
- Use `design.cando_compact.json` on CanDo (recommended — preserves full topology for dsDNA/crossover recognition)
- When submitting to CanDo, ensure the lattice type matches the design
- To modify the structure, always use `design.full.json` as the master — derived files are artifacts only
```

### Export-only mode (append):

```
- CanDo submission parameter package is ready
- If CanDo requires login, please complete login first before submitting
- If the current network cannot reach CanDo, use this package to manually submit in a CanDo-accessible environment
- The current environment has not completed login or submission — I am not claiming CanDo computation is done
- You may manually fill the form, or continue submission in a browser-automation-capable, CanDo-accessible environment
```

### Semi-automatic / automatic mode (append):

```
- CanDo submission task prepared with your parameters
- If the current environment supports network access, web operations, CanDo reachability, and valid login, I will attempt to submit `design.cando_compact.json`
- CanDo 3D prediction is typically asynchronous — real-time completion is not guaranteed
- If results cannot be auto-fetched, bring the result link or file back and I will help parse and display
```

### Out-of-scope shape response (append):

```
- The requested shape "<user-request>" is outside V1 automatic design scope
- Such structures have research precedents in DNA nanotechnology, but are not in the current V1 reliable automatic generation range
- <If decomposable: "This can be broken down into: <list of supported V1 basic structures>">
- Would you like me to generate <supported-alternative> instead?
- <If approximation possible: "An approximate version using <method> is possible — this would be clearly labeled APPROXIMATE, not exact">
```

### Approximation structure report (append):

```
- APPROXIMATION REPORT:
  - Requested ideal shape: <user's request>
  - Actual approximation: <shape ID used>
  - Approximation method: <N-gon / N-segment piecewise linear>
  - Estimated dimensional error: <value>
  - Boundary notes: <discontinuity / non-smooth edge impact>
```

### Validation report (append after standard output):

```
- VALIDATION:
  - JSON format:          <PASSED | FAILED>
  - Scaffold check:       <PASSED | FAILED> — <N> nt used of 7249 nt available
  - Staple check:         <PASSED | WARNING | FAILED> — <N> staples, domain lengths <min>--<max> nt
  - Crossover check:      <PASSED | WARNING | FAILED>
  - Dimension check:      <PASSED | WARNING | FAILED> — <N> helices x ~<M> bp
  - Compact preservation:  <PASSED | FAILED>
  - CanDo compatibility (compact):
    - vstrands: <PASS | FAIL>
    - scaffold: <PASS | FAIL>
    - staple: <PASS | FAIL>
    - dsDNA: <PASS | FAIL>
    - crossover: <PASS | FAIL>
    - compact JSON serialization: PASS
```

### Stage-gated final reply (use when reporting results):

```
STAGES COMPLETED:
  [✓] File format correct              — FORMAT_VALIDATED
  [✓] Topology check passed            — TOPOLOGY_VALIDATED
  [✓] CanDo file generated             — CANDO_INPUT_GENERATED
  [✓] Compact topology preservation checked — local consistency check passed
  [ ] CanDo compatibility externally tested — CANDO_COMPATIBILITY_TESTED
  [ ] CanDo actually submitted         — SUBMITTED
  [ ] CanDo results returned           — COMPLETED
  [ ] Experiment verified              — EXPERIMENTALLY_VALIDATED
```

---

## Forbidden Behaviors

- Do NOT generate simplified 3D renders as primary final results
- Do NOT treat the cando version as the only design file
- Do NOT delete scaffold from the full master
- Do NOT strip scaffold data from the CanDo submission file (scaffold topology is required for dsDNA recognition)
- Do NOT break helix or staple connectivity to accommodate CanDo
- Do NOT delete valid structural staples from the compact CanDo file to satisfy CanDo
- Do NOT let users believe scaffold is no longer needed at the design level
- Do NOT fabricate "completed 3D prediction" without real CanDo results
- Do NOT ignore that CanDo returns results asynchronously
- Do NOT claim submission success without required user info
- Do NOT fabricate user name, affiliation, or email
- Do NOT pretend registration, login, or privilege bypass has been completed
- Do NOT output submission fields that don't exist on the CanDo page
- Do NOT promise the current environment can always reach CanDo
- Do NOT instruct users to bypass network restrictions, registration, or access controls
- Do NOT accept arbitrary SVG, hand-drawn outlines, or bitmap images as input for direct JSON generation
- Do NOT auto-approximate arbitrary complex contours into production DNA origami
- Do NOT generate shapes from the out-of-scope list — apply the Out-of-Scope Handling Protocol
- Do NOT call an approximation an "exact" structure
- Do NOT silently swap an incompatible lattice — report and ask
- Do NOT conflate design status, validation status, and experiment status — report each independently
- Do NOT claim CanDo results are returned without real CanDo output (link or file)
- Do NOT claim experiment is verified without explicit user confirmation

---

## Quality Constraints

- All designs must use the `scadnano` Python library — no raw JSON generation
- Supported shapes must use pre-defined templates; do not invent topology on the fly
- Crossover positions must follow the chosen grid's geometric rules
- Scaffold polarity must be continuous 5'→3'
- Staple strands must have reasonable lengths (20–60 nt per domain)
- Auto-retry on errors: max 2 attempts with corrections applied between retries
- The compact CanDo file must be a faithful preservation of the full master — same topology, compact serialization
- For approximation structures: always include the 5 required disclosures
- Always report `lattice_type` and `lattice_selection_reason`
- Always report design status, validation status, and experiment status
- Always run all 7 validation checks (JSON, scaffold, staple, crossover, dimension, compact preservation, CanDo compatibility)
- Always include the stage-gated checklist when reporting CanDo-related outcomes

---

## References

- `references/cando-submission-guide.md` — Detailed CanDo form field mapping, default values, lattice selection rules, and submission mode decision tree
- `scripts/template_design.py` — Canonical template for dual-file generation script with shape-specific builders
- `scripts/check_deps.py` — Dependency checker (scadnano only)
