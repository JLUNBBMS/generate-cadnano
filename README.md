# generate-cadnano
A cadnano-to-CanDo skill for DNA nanostructure design validation and export. It checks scaffold/staple topology, loops, skips, base pairing, and deduplicated crossovers, then generates topology-preserving compact JSON. Users provide helix layout, routing, and scaffold/staple parameters.
# cadnano CanDo Skill

A skill for validating cadnano DNA nanostructure designs, preserving topology, exporting compact JSON representations, and preparing structures for CanDo analysis.

## Overview

This skill connects a cadnano design workflow with CanDo-compatible structural analysis.

Its main purpose is to:

1. Read and inspect cadnano design JSON files.
2. Validate scaffold and staple strand topology.
3. Count occupied scaffold and staple bases.
4. Identify paired dsDNA positions.
5. Count deduplicated cross-helix connections.
6. Compare full and compact JSON representations.
7. Confirm that a compact export preserves the original topology.
8. Prepare a validated compact JSON file for downstream CanDo import or analysis.

The skill is intended for DNA-origami design validation and format conversion. It is not a replacement for cadnano, CanDo, molecular dynamics software, or experimental validation.

## Current validation status

The current smoke test has verified a 4-helix structure with the following results:

- 4 virtual helices
- 256 occupied scaffold bases
- 256 occupied staple bases
- 256 paired dsDNA positions
- 3 deduplicated scaffold cross-helix connections
- 6 deduplicated staple cross-helix connections
- 9 total deduplicated cross-helix connections
- Full and compact JSON files matched for:
  - `num`
  - `row`
  - `col`
  - `scaf`
  - `stap`
  - `loop`
  - `skip`
  - `stap_colors`

The compact file was verified as topology-preserving relative to the full file for this test case.

## Relationship with cadnano

cadnano is used as the design-side tool.

A typical workflow is:

1. Design a DNA nanostructure in cadnano.
2. Export the design as JSON.
3. Provide the JSON file to this skill.
4. Validate the virtual helices and strand arrays.
5. Count occupied bases and connections.
6. Detect invalid or inconsistent topology.
7. Export a compact topology-preserving JSON file.
8. Use the validated output as input for CanDo or another compatible analysis workflow.

The skill does not replace cadnano's graphical design interface. It operates on the exported design data.

## Relationship with CanDo

CanDo is used for structural analysis and mechanical simulation of DNA nanostructures.

This skill prepares and validates the design data before CanDo analysis. Its role is to reduce import ambiguity and catch topology problems before the file is submitted to CanDo.

The workflow is:

cadnano design
    ↓
cadnano JSON export
    ↓
topology validation
    ↓
full/compact consistency check
    ↓
compact JSON export
    ↓
CanDo import or analysis

The skill does not itself guarantee that every structure can be solved by CanDo. Successful topology validation means that the input representation is internally consistent; it does not guarantee numerical convergence, physical validity, or successful mechanical simulation.

## Input data

The user should provide:

- A cadnano-exported JSON file.
- The intended structure type.
- The number of virtual helices, if known.
- The intended scaffold routing.
- The intended staple routing.
- Any special loop or skip information.
- Whether the user wants a full export, compact export, or both.
- Whether CanDo compatibility checking is required.

A typical cadnano JSON file may contain:

- `vstrands`
- virtual-helix identifiers
- `num`
- `row`
- `col`
- `scaf`
- `stap`
- `loop`
- `skip`
- `stap_colors`

The exact schema depends on the cadnano version and export configuration.

## Parameters required for generating a structure

For a new structure, the user should provide as many of the following parameters as possible:

### 1. Global structure parameters

- Structure name.
- Number of virtual helices.
- Helix arrangement.
- Helix lattice type, if applicable.
- Overall dimensions.
- Desired shape.
- Design orientation.
- Whether the structure is linear, closed, planar, tubular, or multi-layered.

### 2. Virtual-helix layout

For each virtual helix:

- Helix ID or `num`.
- Grid row.
- Grid column.
- Relative position.
- Orientation.
- Neighboring helices.
- Intended crossover locations.

### 3. Scaffold parameters

- Scaffold length.
- Scaffold starting helix.
- Scaffold starting base.
- Scaffold routing direction.
- Scaffold crossover positions.
- Whether the scaffold is circular or linear.
- End treatment.
- Any required breaks or nick positions.

### 4. Staple parameters

- Number of staple strands.
- Staple routing.
- Staple crossover positions.
- Staple lengths.
- Staple color information, if needed.
- Whether staples should be generated automatically.
- Whether staples should contain intentional breaks or nicks.

### 5. Base-level parameters

- Occupied base intervals.
- Empty positions.
- Loop lengths.
- Skip positions.
- Strand connection arrays.
- Any insertion or deletion information supported by the input schema.

### 6. Output parameters

- Full JSON only.
- Compact JSON only.
- Both full and compact JSON.
- Topology comparison report.
- CanDo preparation report.
- Human-readable summary.
- Machine-readable validation report.

## Supported structure scope

### Verified

The following capability has been verified by the current smoke test:

- Multi-helix cadnano JSON data.
- Scaffold and staple arrays.
- Occupied-base counting.
- Paired dsDNA position counting.
- Scaffold cross-helix connections.
- Staple cross-helix connections.
- Deduplication of bidirectional connection records.
- Full versus compact topology comparison.
- Preservation of `num`, `row`, `col`, `scaf`, `stap`, `loop`, `skip`, and `stap_colors`.

### Potentially supported, subject to testing

The following may be supported if represented correctly by the cadnano schema and implemented by the current version of the skill:

- Linear multi-helix bundles.
- Planar DNA-origami arrangements.
- Rectangular helix bundles.
- Tubular or multilayer arrangements.
- Structures with multiple staple crossovers.
- Structures containing loops and skips.
- Structures with different scaffold and staple routing patterns.
- Larger structures with more than four virtual helices.

Each new topology should be validated with a dedicated test case before being described as fully supported.

### Not currently guaranteed

The skill does not currently guarantee successful construction or CanDo analysis for:

- Arbitrary three-dimensional curved shapes.
- Smooth continuous 3D surfaces.
- Spheres, toroids, knots, or highly curved shells.
- Structures requiring unsupported lattice types.
- Structures using cadnano features not represented in the parser.
- Designs with malformed or incomplete strand arrays.
- Designs with inconsistent reverse and forward connections.
- Structures requiring insertions or deletions if they are not explicitly supported.
- Designs that are topologically valid but physically impossible.
- Structures that CanDo cannot numerically solve.
- Experimental assembly, folding, or stability.

A structure can pass JSON topology validation and still fail CanDo because of geometry, boundary conditions, unsupported features, or numerical convergence problems.

## Validation rules

The validator should distinguish between:

- Empty array slots such as `[-1, -1, -1, -1]`.
- Occupied scaffold bases.
- Occupied staple bases.
- Paired dsDNA positions.
- Directional connection records.
- Deduplicated physical cross-helix connections.

The same physical connection must not be counted twice merely because it is represented from both directions.

For a valid full/compact comparison, the following fields should match:

- Virtual-helix count.
- `num`.
- `row`.
- `col`.
- `scaf`.
- `stap`.
- `loop`.
- `skip`.
- `stap_colors`, if present.

## Example validation result

```text
FINAL RECOUNT — cando_smoke_test_4hb

vstrands:                         4
scaffold occupied bases:          256
staple occupied bases:            256
paired dsDNA positions:           256
scaffold cross-helix connections: 3
staple cross-helix connections:   6
total cross-helix connections:    9

Full and compact topology:        PASS
