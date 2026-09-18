# V3 geometry and routing

Use with README parameters. The representation stays within cadnano's parallel-helix square/honeycomb model. See the original [cadnano publication](https://pmc.ncbi.nlm.nih.gov/articles/PMC2731887/) and [scadnano](https://github.com/UC-Davis-molecular-computing/scadnano) for the underlying representation, not as validation of this new generator.

## Cross-sections

Square rectangles are explicit simple lattice cycles. Near-circular sections use a bounded beam search over elementary face unions, including perimeter-neutral concavity fills. The beam ranks physical radial spread then area; exact wall helix count is required. The 0.5 radial-spread limit is a coarse engineering acceptance threshold. Never describe the output as a perfect cylinder or globally optimal circle.

Honeycomb physical unit coordinates are x=col*sqrt(3)/2 and y=1.5*row+0.5*((row+col)%2). Multiply by the nominal center spacing 2.5 nm. A honeycomb regular hexagonal shell is grown by complete neighbor-face layers, giving 6+12k boundary helices. Straight triangles and arbitrary polygons are not supported by this implementation.

Bundles search compact row-filled patches for a neighbor Hamiltonian path. The count is exact but the arrangement can differ from a manually chosen literature bundle.

## Fixed caps

Wall helix segments occupy the axial envelope. Interior helix columns are occupied only in the low cap interval and, for two_caps, the high cap interval. The central interior volume remains empty. These are thick parallel-helix blocks, not hinged plates. The biological membrane remains porous on the inter-helix scale.

Scaffold search operates on occupied segments, not only helix columns. Edges require actual lattice neighbors and compatible low/high end regions. A bounded directed Hamiltonian search visits each segment once. Coordinate parity determines direction. Exact crossover residues then inset segment ends. A parity imbalance greater than one is a necessary impossibility test for this path representation; it is not a universal impossibility theorem for DNA origami.

Repeated cap segments map back to the same physical helix, retaining disjoint intervals. Physical IDs are compacted independently within even/odd coordinate parity so native cadnano preserves them on import/export.

All overlapping lattice-neighbor segment contacts receive full staple crossovers. A constrained scheduler reserves a site for each contact before adding extra sites. Staples are subsequently nicked using the V2 20–60 nt total / 8 nt domain constraints. No feasible schedule means failure; the gate is never bypassed.

## Verification layers

1. Exact exported IDs, coordinates and interval unions match the generation plan.
2. Every link is reciprocal; scaffold is one oligo; staples are linear and length-bounded; every crossover obeys native lattice phase rules.
3. Actual JSON occupancy fills cap interior columns, leaves the entire axial lumen empty, and retains wall occupancy at its center. All planned adjacent contacts have staple links.
4. Independent cadnano2 import, native crossover lookup and native routing roundtrip must be tested for releases.

These checks establish combinatorial topology and ideal-lattice shape. They do not establish absence of knots/links during folding, equilibrium shape, mechanical strength, molecular impermeability, or experimental yield. Native Path View and preview_geometry.py serve different purposes: the latter plots actual JSON occupancy in ideal 3D coordinates but does not simulate relaxation.
