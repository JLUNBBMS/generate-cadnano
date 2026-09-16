"""caDNAno 2 lattice coordinates and crossover phase tables.

Tables: Douglas Lab cadnano2, model/parts/{square,honeycomb}part.py.
Coordinates below are cadnano (row, col), NOT scadnano grid_position.
caDNAno Low/High mean the lower/higher site of a crossover pair.
At a Low site the domain lies to the LEFT (its high endpoint); at a High
site the domain lies to the RIGHT (its low endpoint). See prexoveritem.py.
The high argument here means domain high endpoint, hence the inversion.
"""

TABLES = {
    "square": {
        "period": 32,
        "scaf": ([[4, 26, 15], [18, 28, 7], [10, 20, 31], [2, 12, 23]],
                 [[5, 27, 16], [19, 29, 8], [11, 21, 0], [3, 13, 24]]),
        "stap": ([[31], [23], [15], [7]], [[0], [24], [16], [8]]),
    },
    "honeycomb": {
        "period": 21,
        "scaf": ([[1, 11], [8, 18], [4, 15]], [[2, 12], [9, 19], [5, 16]]),
        "stap": ([[6], [13], [20]], [[7], [14], [0]]),
    },
}


def neighbors(lattice, coord):
    r, c = coord
    even = (r + c) % 2 == 0
    if lattice == "square":
        return ([(r, c + 1), (r + 1, c), (r, c - 1), (r - 1, c)] if even else
                [(r, c - 1), (r - 1, c), (r, c + 1), (r + 1, c)])
    if lattice == "honeycomb":
        return ([(r, c + 1), (r - 1, c), (r, c - 1)] if even else
                [(r, c - 1), (r + 1, c), (r, c + 1)])
    raise ValueError("Unsupported lattice: " + str(lattice))


def phases(lattice, source, target, strand, high):
    direction = neighbors(lattice, source).index(target)
    return TABLES[lattice][strand][int(not high)][direction]


def legal(lattice, source, target, strand, offset, high):
    return (target in neighbors(lattice, source) and
            offset % TABLES[lattice]["period"] in
            phases(lattice, source, target, strand, high))
