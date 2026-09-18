"""Scaffold through wall/cap segments; scadnano remains the only JSON exporter."""
import math
import scadnano as sc
from geometry import section, integer, hamiltonian, roundness, xy
from lattice import neighbors, legal, TABLES


def schedule_contacts(coords,intervals,lattice,pairs):
    candidates={}
    for a,b in pairs:
        lo=max(intervals[a][0],intervals[b][0]);hi=min(intervals[a][1],intervals[b][1])
        candidates[a,b]=[k for k in range(lo+10,hi-9) if
            legal(lattice,coords[a],coords[b],'stap',k-1,True) and
            legal(lattice,coords[a],coords[b],'stap',k,False)]
    chosen={};steps=0
    def compatible(pair,k):
        return all(not(set(pair)&set(other)) or abs(k-v)>=16 for other,v in chosen.items())
    def search(todo):
        nonlocal steps
        steps+=1
        if steps>50000:return False
        if not todo:return True
        viable={p:[k for k in candidates[p] if compatible(p,k)] for p in todo}
        p=min(todo,key=lambda p:len(viable[p]))
        for k in viable[p]:
            chosen[p]=k
            if search([x for x in todo if x!=p]):return True
            del chosen[p]
        return False
    if not search(list(pairs)):
        raise ValueError('No full-crossover schedule covering all required contacts; increase axial/cap length')
    planned={p:[k] for p,k in chosen.items()}
    spacing=(4 if lattice=='honeycomb' else 2)*TABLES[lattice]['period']
    for p in pairs:
        for k in candidates[p]:
            if any(abs(k-v)<spacing for v in planned[p]):continue
            if any(set(p)&set(other) and abs(k-v)<16 for other,vals in planned.items() for v in vals):continue
            planned[p].append(k)
        planned[p].sort()
    return planned


def build_v3(shape,lattice,num_helices,length,side,width,height,cross_section,
             polygon_sides,end_style,cap_length,scaffold_length):
    from template_design import build_staples
    boundary,interior,subtype,end = section(shape,lattice,num_helices,side,width,height,
                                          cross_section,polygon_sides,end_style)
    length=integer((384 if end!='open' else 210 if lattice=='honeycomb' else 192)
                   if length is None else length,'bases_per_helix',96,4096)
    if end=='open' and cap_length is not None:
        raise ValueError('cap_length requires end_style one_cap or two_caps')
    cap=integer(128 if cap_length is None else cap_length,'cap_length',96,1024)
    if end!='open' and length < (cap if end=='one_cap' else 2*cap)+96:
        raise ValueError('Axial length must leave at least 96 bp of lumen beyond the caps')
    nodes=[(r,c,'wall') for r,c in boundary]
    if end!='open':
        nodes += [(r,c,k) for k in ('low','high')[:1 if end=='one_cap' else 2] for r,c in interior]
    bounds={a:([0,cap] if a[2]=='low' else [length-cap,length] if a[2]=='high' else [0,length]) for a in nodes}
    if sum(hi-lo for lo,hi in bounds.values())>scaffold_length+len(nodes)*32:
        raise ValueError('Requested occupied volume exceeds scaffold budget even with boundary insets')
    if end=='open':
        route=nodes
        if sum(route[0][:2])%2:
            if subtype=='bundle':
                # Search explicitly for an even start (IDs and exporter parity).
                adj={a:[b for b in nodes if b[:2] in neighbors(lattice,a[:2])] for a in nodes}
                route=hamiltonian(sorted(nodes,key=lambda a:sum(a[:2])%2),adj)
            else:route=route[1:]+route[:1]
    else:
        adj={a:[] for a in nodes}
        for a in nodes:
            for b in nodes:
                if b[:2] not in neighbors(lattice,a[:2]):continue
                high=sum(a[:2])%2==0
                if a[2]==b[2] or {a[2],b[2]}=={'wall','high' if high else 'low'}:
                    adj[a].append(b)
        route=hamiltonian(sorted(nodes,key=lambda a:(sum(a[:2])%2,a)),adj)
    # Virtual segment IDs alternate parity. An odd starting helix is represented
    # with one dummy offset in this internal numbering, never as an empty helix.
    if sum(route[0][:2])%2:
        raise ValueError('No even-start scaffold route found; change helix count or dimensions')
    coords=[a[:2] for a in route]
    intervals=[bounds[a][:] for a in route]
    for j,(a,b) in enumerate(zip(route,route[1:])):
        high=j%2==0
        lo=max(bounds[a][0],bounds[b][0]);hi=min(bounds[a][1],bounds[b][1])
        candidates=[i for i in range(lo,hi) if legal(lattice,a[:2],b[:2],'scaf',i,high)]
        if not candidates:raise ValueError('No scaffold crossover in segment overlap')
        idx=max(candidates) if high else min(candidates)
        if high:intervals[j][1]=intervals[j+1][1]=idx+1
        else:intervals[j][0]=intervals[j+1][0]=idx
    if any(hi-lo<64 for lo,hi in intervals):raise ValueError('Segment too short after lattice boundary adjustment')
    usage=sum(hi-lo for lo,hi in intervals)
    if usage>scaffold_length:raise ValueError(f'Scaffold needs {usage} nt, budget is {scaffold_length}')
    # Reinforce every actual neighbor contact, including the tube seam and caps.
    pairs=[(a,b) for a in range(len(route)) for b in range(a+1,len(route))
           if coords[b] in neighbors(lattice,coords[a]) and
           min(intervals[a][1],intervals[b][1])-max(intervals[a][0],intervals[b][0])>=64]
    # Try deterministic contact orders because greedy crossover scheduling can
    # leave short domains. The same strict length gate applies on every attempt.
    errors=[]
    for attempt in range(min(12,len(pairs))):
        ordered=pairs[attempt:]+pairs[:attempt]
        try:
            staples=build_staples(coords,intervals,lattice,ordered)
            break
        except ValueError as exc:errors.append(str(exc))
    else:raise ValueError('No legal staple schedule: '+errors[-1])
    physical={}
    segment_to_helix={}
    next_id=[0,1]
    for j,coord in enumerate(coords):
        if coord not in physical:
            parity=sum(coord)%2
            physical[coord]=next_id[parity]
            next_id[parity]+=2
        segment_to_helix[j]=physical[coord]
    for strand in staples:
        for domain in strand.domains:domain.helix=segment_to_helix[domain.helix]
    scaffold=sc.Strand(domains=[sc.Domain(helix=segment_to_helix[j],forward=j%2==0,start=lo,end=hi)
                               for j,(lo,hi) in enumerate(intervals)],is_scaffold=True)
    period=TABLES[lattice]['period']
    storage=math.ceil(length/period)*period
    if storage%(21 if lattice=='square' else 32)==0:storage+=period
    design=sc.Design(helices={h:sc.Helix(max_offset=storage,grid_position=(c,r)) for (r,c),h in physical.items()},
                     grid=sc.Grid.square if lattice=='square' else sc.Grid.honeycomb,strands=[scaffold]+staples)
    expected={h:(coord,[]) for coord,h in physical.items()}
    for j,span in enumerate(intervals):expected[segment_to_helix[j]][1].append(span)
    for _,spans in expected.values():spans.sort()
    points=[xy(c,lattice) for c in boundary]
    metadata={'shape_id':shape,'cross_section':subtype,'end_style':end,'lattice_type':lattice,
              'num_helices':len(physical),'wall_num_helices':len(boundary),
              'cap_interior_helix_columns':len(interior) if end!='open' else 0,
              'bases_per_helix':length,'cap_length_bp':cap if end!='open' else 0,
              'nominal_cap_thickness_nm':round(cap*.34,3) if end!='open' else 0,
              'nominal_lumen_length_bp':length-(cap if end=='one_cap' else 2*cap if end=='two_caps' else 0),
              'total_scaffold_nt':usage,'num_staples':len(staples),'storage_length_bp':storage,
              'wall_coordinates_row_col':boundary,'interior_coordinates_row_col':interior,
              'coordinates_row_col':list(physical),'helix_ids':list(physical.values()),
              'occupied_intervals':{str(h):spans for h,(_,spans) in expected.items()},
              'segment_route':[{'helix':segment_to_helix[j],'region':a[2],'interval':intervals[j]} for j,a in enumerate(route)],
              'required_staple_contacts':[[segment_to_helix[a],segment_to_helix[b],
                  max(intervals[a][0],intervals[b][0]),min(intervals[a][1],intervals[b][1])] for a,b in pairs],
              'nominal_envelope_nm':{'x':round((max(x for x,y in points)-min(x for x,y in points))*2.5+2.5,3),
                                     'y':round((max(y for x,y in points)-min(y for x,y in points))*2.5+2.5,3),'z':round(length*.34,3)},
              'radial_spread_fraction':round(roundness(boundary,lattice),4) if subtype!='bundle' else None,
              'boundary_note':'Ends are lattice-stepped; fixed caps are filled parallel-helix blocks, not hinged sheets or a watertight membrane.',
              'search_note':'Deterministic bounded search; near-circular means low radial spread among explored candidates, not a global optimum.'}
    return design,metadata,expected
