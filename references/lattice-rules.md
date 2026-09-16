# Lattice rules used by V2

The coordinate convention is cadnano `(row, col)`. scadnano exports
`grid_position=(col, row)`. Both square and honeycomb use the parity of
`row + col`; scaffold travels forward on even-numbered helices, backwards on
odd-numbered helices. Staple polarity is opposite.

The actual `(row, col)` neighbor graph is authoritative. Consecutive helix
numbers do not establish spatial adjacency. The crossover period is 32 bases
for square and 21 for honeycomb; direction-specific residues within the
period differ for scaffold and staple.

## Low and High are NOT interchangeable

cadnano's `*Low` table gives the lower site of a crossover pair: the attached
domain lies to the **left**, ending at its high coordinate. `*High` gives the
higher site: the domain lies to the **right**, beginning at its low coordinate.
Therefore a forward strand's outgoing 3′ crossover uses `Low`; a reverse
strand's outgoing 3′ crossover uses `High`. The opposite applies to incoming
5′ connections. `lattice.phases(..., high=...)` takes a domain-end flag and
explicitly inverts it for table selection.

For example, square horizontal neighbors `(2,2)` and `(2,3)` use direction 0.
Staple Low is offset 31 modulo 32; High is offset 0 modulo 32. A full crossover
uses sites 31 and 32, not 0 and 31 in the same period. Honeycomb direction 0
uses staple sites 6 and 7 modulo 21.

Full staple crossovers are spaced at least 64 bp (square) or 84 bp (honeycomb)
on each pair in this template implementation; different pairs sharing a helix
have cuts separated by at least 16 bp. These are conservative routing choices
for feasible nicking, not universal DNA requirements. Sites themselves always
follow the cadnano phase tables. Staples are partitioned into 20–60 nt oligos,
each uninterrupted binding domain at least 8 nt.

## Authoritative implementation references

- [cadnano2 square lattice](https://github.com/douglaslab/cadnano2/blob/main/cadnano2/model/parts/squarepart.py)
- [cadnano2 honeycomb lattice](https://github.com/douglaslab/cadnano2/blob/main/cadnano2/model/parts/honeycombpart.py)
- [cadnano2 crossover-site view semantics](https://github.com/douglaslab/cadnano2/blob/main/cadnano2/views/pathview/prexoveritem.py)
- [cadnano2 legacy decoder](https://github.com/douglaslab/cadnano2/blob/main/cadnano2/model/io/legacydecoder.py)

The numeric tables and coordinate rules in `scripts/lattice.py` are drawn
from these implementations. `scripts/check_cadnano.py` checks against the
installed cadnano2 implementation independently and compares native-exported
routing to the input. Passing does not prove thermodynamic stability or the
success of downstream 3D simulation.
