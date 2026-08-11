# CanDo Submission Guide

Detailed field-to-form mapping for the `cando_submission` object, lattice selection rules, status fields, submission modes, file relationship rules, and validation guidance.

---

## 1. Unified Lattice Selection Strategy

### Lattice Rules

#### Planar regular structures
**Default: `square`**

Applies to: `rectangle`, `square`, `long_strip`, `planar_plate`, `rectangular_frame`, `plate_with_rectangular_hole`, `simple_triangle`, `simple_trapezoid`, `simple_hexagon`, `L_shape`, `T_shape`, `cross_shape`.

Only use `honeycomb` if the user explicitly chooses it.

#### Regular 3D structures
**Lattice determined by the specific template:**

| Shape | Default Lattice | Notes |
|-------|----------------|-------|
| `2_helix_bundle`, `4_helix_bundle`, `6_helix_bundle` | `honeycomb` | Standard helix-bundle convention |
| `regular_tube` (square-section) | `square` | Requires `square`; `honeycomb` is incompatible |
| `regular_tube` (hexagonal-section) | `honeycomb` | Template-determined |
| `open_box`, `static_closed_box` | `square` | Box structures use square lattice |
| `simple_U_shape`, `simple_channel` | `square` | Channel structures use square lattice |

#### User explicitly specifies a lattice
- **Honor the user's choice** when the template supports it.
- If the user's chosen lattice is **incompatible** with the template:
  1. Clearly state the incompatibility.
  2. Do **NOT** silently swap to the template default.
  3. Ask whether the user accepts the template's default lattice.
- `simple_assembly`: lattice determined **per module** by each module's own template.

#### Lattice report format
Every output must include:

```yaml
lattice_type: "square" | "honeycomb"
lattice_selection_reason: <one-sentence plain-language explanation>
```

**Examples of valid reasons:**
- `"template default for 'rectangle' (planar)"`
- `"user explicitly chose 'honeycomb' for 'rectangle'"`
- `"'regular_tube' requires 'square' lattice; cannot use 'honeycomb'"`
- `"template default for '4_helix_bundle' (bundle)"`

---

## 2. Default CanDo Model Parameters

These parameters are used by the skill when building a CanDo submission. They represent **the current skill's default model choices**, not universal constants.

### dna_geometry

```yaml
dna_geometry:
  axial_rise_per_base_pair_nm: 0.34
  helix_diameter_nm: 2.25
  crossover_spacing_bp: 10.5
```

### dna_mechanical_properties

```yaml
dna_mechanical_properties:
  axial_stiffness_pN: 1100
  bending_stiffness_pN_nm2: 230
  torsional_stiffness_pN_nm2: 460
  nick_stiffness_factor: 0.01
```

### Important caveats

- These are **standard B-DNA literature values**, not absolute requirements for every design.
- **They do NOT guarantee experimental success.** Real folding depends on buffer conditions, annealing protocol, staple purity, and other factors beyond these parameters.
- **General users should NOT modify these** unless they have a specific reason.
- If a user **explicitly requests a change**, apply it AND record the modification reason:

```yaml
parameter_modifications:
  - parameter: <name>
    original_value: <skill default>
    user_value: <user-requested value>
    reason: <user's stated reason>
```

---

## 3. Submission Modes

### Mode Summary

| Mode | Description |
|------|-------------|
| `export_only` | Generate files and parameters only. Do NOT claim submission occurred. |
| `semi_automatic` | Prepare files; user must manually log in, submit, or retrieve results. |
| `automatic_if_environment_allows` | Full auto-submit **only if** all prerequisites are met. |

### Mode Rules

#### `export_only`
- Default mode.
- Output files and the `cando_submission` parameter package.
- Provide manual submission instructions.
- **Never** claim the design has been submitted to CanDo.
- Use when: CanDo unreachable, no automation, no login, or environment unknown.

#### `semi_automatic`
- Skill prepares and may assist with form-filling.
- User handles: login, CAPTCHA, final submission confirmation, result retrieval.
- Skill states: "CanDo results are asynchronous — real-time completion is not guaranteed."
- User brings result link/file back to the conversation; skill helps parse and explain.

#### `automatic_if_environment_allows`
- Requires **ALL** of:
  - Real network access to CanDo's server
  - Valid, logged-in user session (not fabricated)
  - Browser/form automation capability
  - Task tracking for async results
  - Result file download/retrieval capability
- If **any** prerequisite is missing → fall back to `semi_automatic` or `export_only`.
- If uncertainties exist about any capability → fall back to `semi_automatic`.

### Hard Boundaries

- Do **NOT** fabricate login state.
- Do **NOT** fabricate submission success, task IDs, or computation results.
- Do **NOT** bypass registration, CAPTCHA, access controls, or network restrictions.
- **CanDo is an asynchronous service.** Submission accepted ≠ computation complete.
- **CanDo computation complete ≠ experiment successful.**

---

## 4. Status Fields

Four independent status dimensions track the lifecycle of a design.

### design_status

Refers to the `design.full.json` master file generation outcome.

| Value | Meaning |
|-------|---------|
| `DRAFT` | User is still describing requirements; no generation attempted. |
| `GENERATED` | Master file produced by the template without errors. |
| `UNSUPPORTED_REQUEST` | Shape is outside V1 scope; no generation attempted. Out-of-Scope Handling Protocol applied. |
| `GENERATION_FAILED` | Template execution errored; no valid master file exists. |

### validation_status

Refers to the sequence of validation checks run against the generated files.

| Value | Meaning |
|-------|---------|
| `NOT_RUN` | No validation checks have been executed. |
| `FORMAT_VALIDATED` | JSON structure check passed (parseable, cadnano v2 schema). Topology checks may have WARNINGs or FAILs — status stays here until all 4 topology checks are clean. |
| `TOPOLOGY_VALIDATED` | All 4 topology checks (scaffold, staple, crossover, dimension) return PASS with zero WARNINGs. Any WARNING keeps status at `FORMAT_VALIDATED` — warnings indicate potentially unreliable topology. |
| `CANDO_INPUT_GENERATED` | `design.cando_compact.json` derived + compact topology preservation check passed. **Highest level reachable without a real CanDo service call.** |
| `CANDO_COMPATIBILITY_TESTED` | Real CanDo program or external CanDo service confirmed compatibility. **Cannot be set from local file checks alone.** |

Validation is sequential: each level implies all prior levels passed. The local toolchain tops out at `CANDO_INPUT_GENERATED`. `CANDO_COMPATIBILITY_TESTED` requires an actual CanDo service interaction beyond the scope of local file generation and validation.

### experimental_status

Refers to real-world experimental evidence.

| Value | Meaning |
|-------|---------|
| `EXPERIMENTALLY_UNVALIDATED` | No experimental data exists. **Default for all generated designs.** |
| `EXPERIMENTALLY_VALIDATED` | User has provided experimental confirmation (folding, AFM, TEM, etc.). |

**Rules:**
- Default: `EXPERIMENTALLY_UNVALIDATED`.
- Do **NOT** use `EXPERIMENTALLY_VALIDATED` without real experimental data provided by the user.
- CanDo 3D prediction results **do not** constitute experimental validation.
- CanDo results received ≠ `EXPERIMENTALLY_VALIDATED`.

### submission_status

Refers to the CanDo submission lifecycle.

| Value | Meaning |
|-------|---------|
| `NOT_SUBMITTED` | Files exported; no CanDo submission attempted. **Default.** |
| `SUBMISSION_PREPARED` | `cando_submission` package built; all required fields present; ready for upload. |
| `SUBMITTED` | `design.cando_compact.json` uploaded to CanDo; submission confirmation received. |
| `QUEUED` | CanDo has accepted the job and placed it in the processing queue. |
| `RUNNING` | CanDo computation is actively in progress. |
| `COMPLETED` | CanDo returned 3D prediction results (link or file). |
| `FAILED` | CanDo job failed (server error, invalid input, timeout, etc.). |
| `UNKNOWN` | Submission status cannot be determined (e.g., lost tracking, expired session). |

**Rules:**
- Default: `NOT_SUBMITTED` — this skill generates files; it does not submit by default.
- Never claim `SUBMITTED` or beyond without a real upload confirmation from CanDo.
- Never claim `COMPLETED` without real CanDo 3D prediction output.
- `SUBMISSION_PREPARED` can be set when the `cando_submission` package is fully built with no missing required fields.

---

## 5. cando_submission Parameter Object

### Full Structure

```yaml
cando_submission:
  name: ""               # REQUIRED: from user
  affiliation: ""        # REQUIRED: from user
  email: ""              # REQUIRED: from user
  lattice: ""            # REQUIRED: must match actual design lattice
  model_resolution: "coarse"
  include_movie: "no"
  atomic_model_option: "no"
  submission_mode: "export_only"
```

### Field Requirements

| Field | Source | Rules |
|-------|--------|-------|
| `name` | **User must provide** | Never fabricate. Leave empty if unknown; list in `missing_fields`. |
| `affiliation` | **User must provide** | Never fabricate. Leave empty if unknown; list in `missing_fields`. |
| `email` | **User must provide** | Never fabricate. Leave empty if unknown; list in `missing_fields`. |
| `lattice` | **Must match design** | Use the resolved lattice from the Unified Lattice Selection Strategy. Must be consistent with the actual `design.full.json` grid. |
| `model_resolution` | Default: `"coarse"` | Only change to `"fine"` if user explicitly requests high precision. |
| `include_movie` | Default: `"no"` | Only change to `"yes"` if user explicitly requests trajectory movie. |
| `atomic_model_option` | Default: `"no"` | Only change if user explicitly requests atomic model generation. |
| `submission_mode` | **Environment-determined** | Must reflect current environment capabilities. See Section 3. |

### Missing Fields

When `name`, `affiliation`, or `email` are not provided:

```yaml
missing_fields:
  - name
  - affiliation
  - email
```

Prompt the user for each missing field before any submission attempt. Do **NOT** proceed with submission while fields are missing.

---

## 6. Full / CanDo File Relationship

### Master-Derived Model

```
design.full.json          <-- ONE AND ONLY MASTER (design authority)
       |
       | derive (topology-preserving, compact JSON)
       v
design.cando_compact.json <-- TOPOLOGY-PRESERVING SUBMISSION ARTIFACT (never a design source)
```

> **Legacy note:** The old scaffold-stripped `.cando.json` is NO LONGER generated by default. It was removed to prevent accidental upload of a file missing scaffold topology, which would cause "no dsDNA" errors in CanDo.

### Rules

1. **`design.full.json` is the sole master.** It contains:
   - Scaffold strands (full routing, 5'→3' connectivity)
   - Staple strands (all structural staples with crossovers)
   - Helix definitions (positions, grid, max_bases)
   - Complete topology (inter-helix connections, loops)

2. **`design.cando_compact.json` can ONLY be derived from the master.** It must never be generated independently or from a different source.

3. **Derivation is a topology-preserving operation:**
   - Keep ALL `scaf` arrays from every `vstrands` entry (required for CanDo dsDNA centerline inference).
   - Keep ALL `scafLoop` arrays from every `vstrands` entry.
   - Keep ALL `stap` and `stapLoop` entries intact.
   - Preserve all helix metadata, vstrand structure, and connectivity.
   - Do **NOT** add, modify, or redesign any entries.
   - Output as **compact JSON**: no indentation, no extra whitespace, `separators=(",", ":")`.

4. **What to keep vs. remove:**
   - **Keep:** ALL scaffold strands, structural staples, helix definitions, crossover connectivity (full topology).
   - **Strip scaffold data will cause CanDo to fail dsDNA recognition.**
   - **If uncertain:** whether a strand is structural or auxiliary → **default to KEEPING it.**

5. **Post-derivation topology preservation check is mandatory:**
   - Verify `design.cando_compact.json` and `design.full.json` have identical `vstrands` count.
   - Verify `scaf` arrays are identical between the two files (topology preserved).
   - Verify `stap` arrays are identical between the two files.
   - Verify `stapLoop` arrays are identical between the two files.

6. **All design modifications** (shape, dimensions, sequences, strand edits) **MUST go back to `design.full.json`**. After modifying the master, re-derive `design.cando_compact.json`. Never edit `design.cando_compact.json` directly and then try to reconstruct the master.

> "The full version is the master; the compact version is a topology-preserving submission artifact. All design modifications must be based on the full version."

> Pitfall: "The compact CanDo file preserves all scaffold and staple topology. Never upload a scaffold-stripped file to CanDo — it will fail dsDNA recognition. CanDo needs scaffold topology to infer dsDNA geometry."

---

## 7. Basic Validation (V1)

The skill runs six structured validation checks. Each returns `{check, status: PASS|WARNING|FAIL, message, details}`.

### Checks

| # | Check | What It Verifies |
|---|-------|-----------------|
| 1 | **JSON structure** | File is parseable JSON; contains `vstrands` key; cadnano v2 format. |
| 2 | **Scaffold connectivity** | Scaffold forms a continuous path; total nt usage ≤ scaffold length (default 7249 nt). |
| 3 | **Staple connectivity** | Staples present; domain lengths in 20–60 nt range; no orphan domains. |
| 4 | **Crossover legality** | Crossovers between adjacent helices only; spacing respects lattice geometry (32 nt square / 21 nt honeycomb). |
| 5 | **Dimensions** | Helix count and bases-per-helix match user request within tolerance; no empty helices. |
| 6 | **Compact preservation** | Same vstrand count; identical scaf, stap, and stapLoop arrays between full and compact files. |

### Validation Truths

```
File generation succeeded ≠ Topology is correct.
Topology check passed      ≠ CanDo will accept the file.
CanDo accepted the file    ≠ 3D prediction is physically valid.
CanDo returned results     ≠ Experiment will succeed.
```

- A file that parses but has broken scaffold routing is **not** a valid design.
- A file that passes all 6 checks is **ready for CanDo submission**, but success is not guaranteed.
- Only real experimental data can move `experimental_status` to `EXPERIMENTALLY_VALIDATED`.

---

## 8. Field Mapping (CanDo Submission Form)

### user_info

| Field | CanDo Form Label | Required | Default | Notes |
|-------|-----------------|----------|---------|-------|
| `name` | Name | Yes | — | Never fabricate; leave empty if unknown |
| `affiliation` | Affiliation / Institution | Yes | — | Never fabricate; leave empty if unknown |
| `email` | Email | Yes | — | Never fabricate; leave empty if unknown |

### dna_geometry

| Field | CanDo Form Label | Default | Unit |
|-------|-----------------|---------|------|
| `axial_rise_per_base_pair_nm` | Axial rise per base pair | 0.34 | nm |
| `helix_diameter_nm` | Helix diameter | 2.25 | nm |
| `crossover_spacing_bp` | Crossover spacing | 10.5 | bp |

See Section 2 for caveats about these defaults.

### dna_mechanical_properties

| Field | CanDo Form Label | Default | Unit |
|-------|-----------------|---------|------|
| `axial_stiffness_pN` | Axial stiffness | 1100 | pN |
| `bending_stiffness_pN_nm2` | Bending stiffness | 230 | pN·nm² |
| `torsional_stiffness_pN_nm2` | Torsional stiffness | 460 | pN·nm² |
| `nick_stiffness_factor` | Nick stiffness factor | 0.01 | (dimensionless) |

See Section 2 for caveats about these defaults.

### model_resolution

| Value | Description |
|-------|-------------|
| `"coarse"` | Coarse-grained model (faster, default) |
| `"fine"` | Fine-grained model (slower, higher accuracy) |

Default: `"coarse"` unless user explicitly asks for high precision.

### cadnano_file

Points to the CanDo submission JSON file. Always `"design.cando_compact.json"` (the topology-preserving compact file). See Section 6 for derivation rules.

### lattice_type

| Value | Description |
|-------|-------------|
| `"honeycomb"` | Honeycomb lattice (3-connection-per-helix) |
| `"square"` | Square lattice (4-connection-per-helix) |

**Selection follows the Unified Lattice Selection Strategy (Section 1).** Do NOT use a single global default for all shapes.

### include_movie

| Value | Description |
|-------|-------------|
| `"yes"` | Generate a trajectory movie |
| `"no"` | No movie (default) |

Default: `"no"` unless user explicitly requests a movie.

### atomic_model_option

| Value | Description |
|-------|-------------|
| `"atomic_model_only"` | Generate atomic model only |
| `"atomic_model_with_298K_movie"` | Generate atomic model with 298K thermal movie |
| `"no"` | No atomic model (default) |

Default: `"no"` unless user explicitly requests atomic model generation.

---

## 9. Submission Mode Decision Tree

```
Can the environment reach CanDo's server?
├── NO  → export_only
└── YES → Is browser/form automation available?
    ├── NO  → semi_automatic
    └── YES → Does a valid logged-in session exist?
        ├── NO  → semi_automatic (user must log in first)
        └── YES → Are all required user_info fields present?
            ├── NO  → Ask user for missing fields; stay in semi_automatic
            └── YES → Can the environment poll for async results?
                ├── NO  → semi_automatic
                └── YES → automatic_if_environment_allows
```

At any branch where a capability is uncertain → fall back to the safer mode (rightward branches first, then upward).

---

## 10. CanDo Operational Status Values

These are the status values used during the CanDo submission interaction (distinct from the `submission_status` lifecycle field in Section 4).

| Status | Meaning |
|--------|---------|
| `submitted` | Successfully uploaded to CanDo; awaiting async results |
| `submission_failed` | Upload attempted but failed (network error, server error, etc.) |
| `needs_more_information` | Missing required fields; prompt user |
| `login_required` | CanDo requires login; user must authenticate |
| `environment_not_supported` | Environment lacks required capabilities |
| `export_only` | Package exported; user must submit manually |
| `needs_user_login_or_manual_submission` | Combined: user needs to log in AND manually submit |

---

## 11. Result Retrieval Notes

- CanDo computation is **asynchronous**. Jobs may take minutes to hours.
- Results are typically delivered via email link or a status page URL.
- If the environment cannot poll for results or read email → switch to `semi_automatic`.
- In `semi_automatic` mode: tell user to bring the result link/file back; skill will help parse, explain, and visualize.
- Never claim results are complete without real CanDo output.
