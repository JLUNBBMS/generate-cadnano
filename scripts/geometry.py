"""Deterministic lattice cross-sections and bounded routing search for V3."""
import math
from lattice import neighbors

NEW_SHAPES = ('parametric_tube', 'square_tube', 'rectangular_tube',
              'polygonal_tube', 'near_circular_tube', 'capped_square_tube',
              'capped_rectangular_tube', 'closed_rectangular_box', 'n_helix_bundle')


def integer(value, name, lo=1, hi=128):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f'{name} must be an integer in {lo}..{hi}')
    return value


def xy(coord, lattice):
    r, c = coord
    return (float(c), float(r)) if lattice == 'square' else (
        c * math.sqrt(3) / 2, 1.5 * r + 0.5 * ((r+c) % 2))


def cycle_order(edges):
    if not edges:return None
    adjacent = {}
    for a,b in edges:
        adjacent.setdefault(a, []).append(b)
        adjacent.setdefault(b, []).append(a)
    if any(len(v) != 2 for v in adjacent.values()):
        return None
    start = min(adjacent)
    order, prev, cur = [], None, start
    while cur not in order:
        order.append(cur)
        nxt = sorted(x for x in adjacent[cur] if x != prev)[0]
        prev, cur = cur, nxt
    return order if cur == start and len(order) == len(adjacent) else None


def edges_of(path):
    return frozenset(tuple(sorted((a,b))) for a,b in zip(path, path[1:]+path[:1]))


def area(path, lattice):
    pts = [xy(p,lattice) for p in path]
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(pts,pts[1:]+pts[:1]))) / 2


def roundness(path, lattice):
    pts = [xy(p,lattice) for p in path]
    center = tuple(sum(p[i] for p in pts)/len(pts) for i in (0,1))
    radii = [math.dist(p,center) for p in pts]
    mean = sum(radii)/len(radii)
    return (max(radii)-min(radii))/mean


def faces_around(path, lattice):
    faces = set()
    if lattice == 'square':
        for r,c in path:
            for dr,dc in ((0,0),(-1,0),(0,-1),(-1,-1)):
                a,b=r+dr,c+dc
                faces.add(edges_of([(a,b),(a,b+1),(a+1,b+1),(a+1,b)]))
    else:
        for r,c in path:
            for dc in (-2,-1,0):
                a,b=r,c+dc
                if (a+b)%2 != 0:
                    continue
                hexagon=[(a,b),(a,b+1),(a+1,b+1),(a+1,b),(a+1,b-1),(a,b-1)]
                faces.add(edges_of(hexagon))
                faces.add(edges_of([(x-1,y+1) for x,y in hexagon]))
    return faces


def circular_cycle(n, lattice):
    """Beam search over unions of elementary faces, exact perimeter count.

    Keep a single simple boundary (no pinches/holes); optimize physical radial
    spread, then enclosed area. Bounded search, never claim global optimality.
    """
    integer(n,'num_helices',6 if lattice=='honeycomb' else 8,128)
    if n%2:
        raise ValueError('A closed square/honeycomb neighbor cycle requires an even helix count')
    start = ([(0,0),(0,1),(1,1),(1,0)] if lattice=='square' else
             [(0,0),(0,1),(1,1),(1,0),(1,-1),(0,-1)])
    states={len(start): [edges_of(start)]}
    for size in range(len(start), n+1, 2):
        candidates=states.get(size,[])
        if lattice=='square':
            candidates += [edges_of(rectangle_cycle(w,size//2-w))
                           for w in range(2,size//2-1)]
        elif (size-6)%12==0:
            candidates.append(edges_of(hexagonal_cycle(size)))
        # Filling a concave notch can add area without changing perimeter.
        # Without these neutral moves even a 2x2 square is unreachable.
        pool=set(candidates)
        for _ in range(4):
            ranked=sorted(pool,key=lambda e:(roundness(cycle_order(e),lattice),
                          -area(cycle_order(e),lattice),sorted(e)))[:24]
            additions=set()
            for boundary in ranked:
                old_area=area(cycle_order(boundary),lattice)
                for face in faces_around(cycle_order(boundary),lattice):
                    merged=boundary.symmetric_difference(face)
                    if len(merged)!=size:continue
                    ordered=cycle_order(merged)
                    if ordered and area(ordered,lattice)>old_area:
                        additions.add(merged)
            if additions.issubset(pool):break
            pool.update(additions)
        ranked=sorted(pool,key=lambda e:(roundness(cycle_order(e),lattice),
                      -area(cycle_order(e),lattice),sorted(e)))[:24]
        if size==n:
            if not ranked:break
            return cycle_order(ranked[0])
        for boundary in ranked:
            path=cycle_order(boundary)
            for face in faces_around(path,lattice):
                merged=boundary.symmetric_difference(face)
                length=len(merged)
                if not size < length <= n:continue
                ordered=cycle_order(merged)
                if ordered and all(b in neighbors(lattice,a) for a,b in zip(ordered,ordered[1:]+ordered[:1])):
                    states.setdefault(length,[]).append(merged)
    raise ValueError(f'No simple {n}-helix {lattice} cycle found within bounded face search')


def hexagonal_cycle(n):
    if n<6 or (n-6)%12:
        raise ValueError('Symmetric honeycomb hexagonal shells require 6,18,30,42,... wall helices; use near_circular for other counts')
    boundary=edges_of([(0,0),(0,1),(1,1),(1,0),(1,-1),(0,-1)])
    for _ in range((n-6)//12):
        old=boundary
        for face in sorted(faces_around(cycle_order(old),'honeycomb'),key=lambda e:sorted(e)):
            merged=old.symmetric_difference(face)
            ordered=cycle_order(merged)
            if len(face&old) in (1,2) and ordered and area(ordered,'honeycomb')>area(cycle_order(old),'honeycomb'):
                boundary=boundary.symmetric_difference(face)
        if cycle_order(boundary) is None:raise ValueError('Hexagonal shell construction failed')
    ordered=cycle_order(boundary)
    if len(ordered)!=n:raise ValueError('Hexagonal shell count differs from request')
    return ordered


def rectangle_cycle(w,h):
    return ([(0,c) for c in range(w)] + [(r,w) for r in range(h)] +
            [(h,c) for c in range(w,0,-1)] + [(r,0) for r in range(h,0,-1)])


def inside(point, polygon, lattice):
    x,y=xy(point,lattice)
    pts=[xy(p,lattice) for p in polygon]
    flag=False
    for (a,b),(c,d) in zip(pts,pts[1:]+pts[:1]):
        if (b>y)!=(d>y) and x < (c-a)*(y-b)/(d-b)+a:
            flag=not flag
    return flag and point not in polygon


def hamiltonian(nodes, adjacent, limit=250000):
    """Bounded directed segment path, with a necessary bipartite count check."""
    if abs(sum((-1)**sum(a[:2]) for a in nodes))>1:
        raise ValueError('Scaffold route impossible for this segment parity balance; change cross-section dimensions')
    steps=0
    def visit(path,remaining):
        nonlocal steps
        steps+=1
        if steps>limit:return None
        if not remaining:return path
        options=sorted((b for b in adjacent[path[-1]] if b in remaining),
                       key=lambda b:(sum(x in remaining for x in adjacent[b]),b))
        for b in options:
            rest=remaining-{b}
            # Every remaining vertex except the eventual final one needs a successor.
            if sum(not any(x in rest for x in adjacent[t]) for t in rest)>1:
                continue
            found=visit(path+[b],rest)
            if found:return found
    for start in nodes:
        if sum(start[:2])%2:continue
        result=visit([start],set(nodes)-{start})
        if result:return result
        if steps>limit:break
    raise ValueError('No single-scaffold route found within search budget; change dimensions')


def section(shape,lattice,num_helices=None,side_helices=None,width_helices=None,
            height_helices=None,cross_section=None,polygon_sides=None,end_style=None):
    capped=shape.startswith('capped_') or shape=='closed_rectangular_box'
    end=end_style or ('two_caps' if capped else 'open')
    if end not in ('open','one_cap','two_caps'):
        raise ValueError('end_style must be open, one_cap, or two_caps')
    if capped and end=='open':raise ValueError('Capped/closed templates require a cap')
    if shape=='closed_rectangular_box' and end!='two_caps':
        raise ValueError('closed_rectangular_box requires two_caps')
    subtype={'square_tube':'square','rectangular_tube':'rectangle',
             'capped_square_tube':'square','capped_rectangular_tube':'rectangle',
             'closed_rectangular_box':'rectangle','near_circular_tube':'near_circular',
             'polygonal_tube':'polygon','n_helix_bundle':'bundle'}.get(shape)
    if subtype and cross_section and cross_section!=subtype:
        raise ValueError('cross_section conflicts with shape name')
    subtype=subtype or cross_section or 'near_circular'
    if subtype not in ('square','rectangle','near_circular','polygon','bundle'):
        raise ValueError('Unsupported cross_section')
    if subtype=='bundle' and (shape!='n_helix_bundle' or end!='open'):
        raise ValueError('bundle requires n_helix_bundle with end_style=open')
    if polygon_sides is not None and subtype!='polygon':
        raise ValueError('polygon_sides applies only to polygon cross-section')
    if subtype in ('near_circular','polygon','bundle') and any(x is not None for x in (side_helices,width_helices,height_helices)):
        raise ValueError('This cross-section uses num_helices, not rectangular side counts')
    if subtype in ('square','rectangle'):
        if lattice!='square':raise ValueError('Exact rectangular cross-sections require square lattice')
        if side_helices is not None:
            integer(side_helices,'side_helices',2,32)
            if width_helices is not None or height_helices is not None:
                raise ValueError('Use side_helices OR width_helices/height_helices')
            width_helices=height_helices=side_helices
        if subtype=='square' and width_helices is None and height_helices is None and num_helices is not None:
            integer(num_helices,'num_helices',8,128)
            if num_helices%4:raise ValueError('Square perimeter helix count must be divisible by 4')
            width_helices=height_helices=num_helices//4
        w=integer(3 if width_helices is None else width_helices,'width_helices',2,32)
        h=integer((w if subtype=='square' else 4) if height_helices is None else height_helices,'height_helices',2,32)
        if subtype=='square' and w!=h:raise ValueError('square_tube requires equal width and height')
        boundary=rectangle_cycle(w,h)
        if num_helices is not None and num_helices!=len(boundary):
            raise ValueError('num_helices conflicts with 2*(width_helices+height_helices)')
    elif subtype=='bundle':
        n=integer(12 if num_helices is None else num_helices,'num_helices',4,128)
        # Compact row-filled square lattice; HC requires an explicitly discovered
        # neighbor path, so no serpentine adjacency assumption is made.
        for width in sorted(range(2,min(n,16)+1),key=lambda w:(abs(w-math.sqrt(n)),w)):
            sites=[(i//width,i%width) for i in range(n)]
            nodes=[(r,c,'wall') for r,c in sites]
            adj={a:[b for b in nodes if b[:2] in neighbors(lattice,a[:2])] for a in nodes}
            try:
                boundary=[a[:2] for a in hamiltonian(nodes,adj,limit=10000)]
                if sum(boundary[0])%2:continue
                break
            except ValueError:continue
        else:raise ValueError('No compact bundle path found for this helix count and lattice')
    else:
        default_n=18 if subtype=='polygon' and lattice=='honeycomb' else 24
        n=integer(default_n if num_helices is None else num_helices,'num_helices',6,128)
        if subtype=='polygon':
            sides=polygon_sides or (4 if lattice=='square' else 6)
            integer(sides,'polygon_sides',3,12)
            if lattice=='square' and sides==4:
                if n%4:raise ValueError('Regular square polygon needs num_helices divisible by 4')
                boundary=rectangle_cycle(n//4,n//4)
            elif lattice=='honeycomb' and sides==6:
                boundary=hexagonal_cycle(n)
            else:
                raise ValueError('V3 polygon supports square/4 or honeycomb/6; other polygon angles need a different routing model')
        else:
            boundary=circular_cycle(n,lattice)
            if roundness(boundary,lattice)>0.5:
                raise ValueError('Best searched cycle exceeds 50% radial spread; use another helix count')
    # Keep physical parity intact after translation.
    dr,dc=2-min(r for r,c in boundary),2-min(c for r,c in boundary)
    if (dr+dc)%2:dc+=1
    boundary=[(r+dr,c+dc) for r,c in boundary]
    if subtype!='bundle' and boundary[-1] not in neighbors(lattice,boundary[0]):
        raise ValueError('Cross-section is not a closed lattice cycle')
    interior=[] if subtype=='bundle' else [
        (r,c) for r in range(min(r for r,c in boundary),max(r for r,c in boundary)+1)
        for c in range(min(c for r,c in boundary),max(c for r,c in boundary)+1)
        if inside((r,c),boundary,lattice)]
    if end!='open' and not interior:raise ValueError('Cross-section has no interior lattice sites for a cap')
    if len(boundary)+len(interior)*(end!='open')>196:
        raise ValueError('Capped cross-section exceeds 196 occupied helix columns')
    return boundary,interior,subtype,end
