"""Render ideal lattice occupancy from actual JSON (not a CanDo prediction).

Optional dependency: matplotlib. Usage: preview_geometry.py FILE.full.json OUT.png
"""
import argparse
import json
from pathlib import Path
from geometry import xy


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input');p.add_argument('output')
    args=p.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from matplotlib.patches import Circle
    source=Path(args.input)
    report=Path(str(source).removesuffix('.full.json')+'.report.json')
    meta=json.loads(report.read_text())['design_summary']
    data=json.loads(source.read_text())
    lattice=meta['lattice_type'];length=meta['bases_per_helix']
    cap=meta.get('cap_length_bp',0)
    end_slice=cap//2 if cap else 32
    fig=plt.figure(figsize=(13,5),layout='constrained')
    ax=fig.add_subplot(131,projection='3d')
    axes=[fig.add_subplot(132),fig.add_subplot(133)]
    for v in data['vstrands']:
        x,y=xy((v['row'],v['col']),lattice);x*=2.5;y*=2.5
        occ=[i for i,r in enumerate(v['scaf']) if r!=[-1]*4]
        runs=[]
        for i in occ:
            if not runs or i!=runs[-1][1]:runs.append([i,i+1])
            else:runs[-1][1]+=1
        for lo,hi in runs:
            color='#187d98' if hi-lo>length/2 else '#dc823b'
            ax.plot([x,x],[y,y],[lo*.34,hi*.34],color=color,linewidth=5,alpha=.65)
        for plane,z in zip(axes,[end_slice,length//2]):
            if z in occ:plane.add_patch(Circle((x,y),1.0,color='#187d98',alpha=.9))
            else:plane.plot(x,y,'+',color='#cccccc',markersize=4)
    ax.set_xlabel('x (nm)');ax.set_ylabel('y (nm)');ax.set_zlabel('z (nm)')
    ax.set_title('Actual occupied segments\nIdeal lattice, unrelaxed')
    ax.view_init(elev=20,azim=-55)
    ax.xaxis.set_major_locator(MaxNLocator(3))
    ax.yaxis.set_major_locator(MaxNLocator(3))
    ax.set_box_aspect((1,1,2))
    for plane,z in zip(axes,[end_slice,length//2]):
        plane.autoscale_view();plane.set_aspect('equal');plane.margins(.15)
        plane.set_xlabel('x (nm)');plane.set_ylabel('y (nm)')
        plane.set_title(f'Cross-section at {z} bp')
    fig.suptitle(meta['shape_id']+' | '+meta.get('end_style','open')+' | cadnano JSON geometry')
    fig.savefig(args.output,dpi=180,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':main()
