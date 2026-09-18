"""V3 geometry and failure regression tests; run alongside test_design.py."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from template_design import create_design
from geometry import NEW_SHAPES, roundness, hexagonal_cycle
from shape_validation import validate_shape
from validation import validate


class V3Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.n=0

    def generate(self,shape,**params):
        self.n+=1
        result=create_design(shape,str(Path(self.temp.name)/str(self.n)),**params)
        self.assertEqual(result['design_status'],'GENERATED',result.get('error'))
        self.assertEqual(result['geometry_validation']['status'],'PASS')
        data=json.loads(Path(result['full_path']).read_text())
        return result,data

    def test_new_defaults(self):
        for shape in NEW_SHAPES:
            with self.subTest(shape=shape):self.generate(shape)

    def test_multiple_tube_counts_and_lattices(self):
        for lattice,counts in [('square',(8,12,16,24,32)),('honeycomb',(6,18,24,32))]:
            for count in counts:
                with self.subTest(lattice=lattice,n=count):
                    r,d=self.generate('near_circular_tube',user_lattice=lattice,num_helices=count)
                    self.assertEqual(len(d['vstrands']),count)
                    self.assertLessEqual(roundness(r['design_summary']['wall_coordinates_row_col'],lattice),.5)

    def test_bundle_counts(self):
        for lattice in ('square','honeycomb'):
            for n in (8,12,16,24):
                with self.subTest(lattice=lattice,n=n):
                    _,d=self.generate('n_helix_bundle',user_lattice=lattice,num_helices=n)
                    self.assertEqual(len(d['vstrands']),n)

    def test_fixed_caps_and_lumen(self):
        for shape in ('capped_square_tube','capped_rectangular_tube'):
            for end in ('one_cap','two_caps'):
                r,d=self.generate(shape,end_style=end)
                meta=r['design_summary'];cap=meta['cap_length_bp'];length=meta['bases_per_helix']
                interior=set(map(tuple,meta['interior_coordinates_row_col']))
                self.assertTrue(interior)
                for v in d['vstrands']:
                    if (v['row'],v['col']) not in interior:continue
                    occupied={i for i,x in enumerate(v['scaf']) if x!=[-1]*4}
                    self.assertIn(cap//2,occupied)
                    self.assertNotIn(length//2,occupied)
                    self.assertEqual(length-cap//2 in occupied,end=='two_caps')

    def test_parametric_and_dimension_controls(self):
        r,_=self.generate('parametric_tube',cross_section='rectangle',width_helices=3,height_helices=4,end_style='two_caps')
        self.assertEqual(r['design_summary']['wall_num_helices'],14)
        self.assertEqual(r['design_summary']['num_helices'],20)
        self.generate('square_tube',num_helices=20)
        self.generate('near_circular_tube',num_helices=12,end_style='two_caps')

    def test_polygon_hexagonal_shells(self):
        for n in (6,18,30):
            r,_=self.generate('polygonal_tube',user_lattice='honeycomb',polygon_sides=6,num_helices=n)
            self.assertEqual(r['design_summary']['wall_num_helices'],n)
            self.assertEqual(len(hexagonal_cycle(n)),n)

    def test_invalid_requests_produce_no_files(self):
        cases=[('near_circular_tube',dict(num_helices=15)),
               ('near_circular_tube',dict(user_lattice='honeycomb',num_helices=8)),
               ('square_tube',dict(width_helices=3,height_helices=4)),
               ('square_tube',dict(num_helices=14)),
               ('rectangular_tube',dict(user_lattice='honeycomb')),
               ('rectangular_tube',dict(num_helices=24,width_helices=3,height_helices=4)),
               ('polygonal_tube',dict(polygon_sides=3)),
               ('closed_rectangular_box',dict(end_style='one_cap')),
               ('capped_square_tube',dict(end_style='open')),
               ('capped_square_tube',dict(side_helices=4)),
               ('closed_rectangular_box',dict(bases_per_helix=128)),
               ('closed_rectangular_box',dict(scaffold_length=100)),
               ('n_helix_bundle',dict(end_style='two_caps')),
               ('near_circular_tube',dict(width_helices=3)),
               ('square_tube',dict(cap_length=128)),
               ('parametric_tube',dict(num_helices=True)),
               ('rectangle',dict(end_style='open'))]
        for j,(shape,params) in enumerate(cases):
            base=Path(self.temp.name)/str(j)
            with self.subTest(shape=shape,params=params):
                r=create_design(shape,str(base),**params)
                self.assertEqual(r['design_status'],'GENERATION_FAILED')
                self.assertEqual(list(base.parent.glob(base.name+'.*')),[])

    def test_geometric_corruption_detected(self):
        r,d=self.generate('closed_rectangular_box');m=r['design_summary']
        interior=set(map(tuple,m['interior_coordinates_row_col']))
        broken=copy.deepcopy(d)
        v=next(v for v in broken['vstrands'] if (v['row'],v['col']) in interior)
        v['scaf'][m['cap_length_bp']//2]=[-1]*4
        self.assertEqual(validate_shape(broken,m)['status'],'FAIL')
        # Obstruction is detected even before a topology check is consulted.
        v['scaf'][m['bases_per_helix']//2]=[v['num'],0,-1,-1]
        self.assertIn('Interior lumen obstructed',validate_shape(broken,m)['errors'])
        moved=copy.deepcopy(d);moved['vstrands'][0]['col']+=100
        self.assertEqual(validate_shape(moved,m)['status'],'FAIL')

    def test_disjoint_cap_intervals_validate_exactly(self):
        r,d=self.generate('closed_rectangular_box');m=r['design_summary']
        expected={h:(p,m['occupied_intervals'][str(h)]) for h,p in zip(m['helix_ids'],m['coordinates_row_col'])}
        self.assertTrue(any(len(spans)==2 for p,spans in expected.values()))
        self.assertEqual(validate(d,'square',expected=expected)['status'],'PASS')
        h=next(h for h,(_,spans) in expected.items() if len(spans)==2)
        expected[h][1][0][1]-=1
        self.assertEqual(validate(d,'square',expected=expected)['status'],'FAIL')


if __name__=='__main__':unittest.main(verbosity=2)
