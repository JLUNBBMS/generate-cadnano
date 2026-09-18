"""Checks actual exported occupancy, cavity and face connectivity against intent."""
from geometry import inside
from lattice import neighbors


def validate_shape(data,meta):
    errors=[]
    lattice=meta['lattice_type']
    wall=[tuple(p) for p in meta['wall_coordinates_row_col']]
    helices={(v['row'],v['col']):v for v in data['vstrands']}
    empty=[-1]*4
    occupied={p:{i for i,r in enumerate(v['scaf']) if r!=empty} for p,v in helices.items()}
    tube=meta['cross_section']!='bundle'
    length=meta['bases_per_helix'];cap=meta['cap_length_bp'];end=meta['end_style']
    if tube:
        if len(set(wall))!=len(wall) or any(b not in neighbors(lattice,a) for a,b in zip(wall,wall[1:]+wall[:1])):
            errors.append('Tube wall is not a simple closed neighbor cycle')
        interior={(r,c) for r in range(min(p[0] for p in wall),max(p[0] for p in wall)+1)
                  for c in range(min(p[1] for p in wall),max(p[1] for p in wall)+1)
                  if inside((r,c),wall,lattice)}
        wanted=set(wall)|(interior if end!='open' else set())
        if set(helices)!=wanted:errors.append('Exported cross-section differs from wall/cap volume')
        # Leave phase margin at outer ends. The complete lumen must remain empty
        # in every interior helix column, not merely at the axial midpoint.
        lumen=range(cap if end!='open' else 32,length-cap if end=='two_caps' else length-32)
        for p in interior:
            if any(i in occupied.get(p,set()) for i in lumen):errors.append('Interior lumen obstructed')
            for sample in ([cap//2] if end=='one_cap' else [cap//2,length-cap//2] if end=='two_caps' else []):
                if sample not in occupied.get(p,set()):errors.append('Cap has missing interior occupancy')
        mid=(lumen.start+lumen.stop)//2
        if any(mid not in occupied.get(p,set()) for p in wall):errors.append('Wall missing at cavity cross-section')
    by_id={v['num']:v for v in data['vstrands']}
    for a,b,lo,hi in meta['required_staple_contacts']:
        recs=by_id.get(a,{}).get('stap',[])
        if not any(any(r[side]==b and lo<=r[side+1]<hi for side in (0,2)) for r in recs[lo:hi]):
            errors.append(f'Missing staple reinforcement between {a} and {b} in {lo}..{hi}')
    return {'status':'FAIL' if errors else 'PASS','errors':errors,
            'wall_cycle_checked':tube,'cap_volume_checked':end!='open',
            'interpretation':'Ideal parallel-helix lattice geometry; no relaxation or experimental inference'}
