import os

EXAMPLE_DESCRIPTIVE_NAME = 'Simple carputils Example'
EXAMPLE_AUTHOR = 'Andrew Crozier <andrew.crozier@medunigraz.at>, Axel Loewe <axel.loewe@kit.edu>'
EXAMPLE_DIR = os.path.dirname(__file__)

from datetime import date

# import required carputils modules
from carputils import settings
from carputils import tools
from carputils import mesh
from carputils import testing
from carputils.carpio import txt
import numpy as np

# define parameters exposed to the user on the commandline
def parser():
    parser = tools.standard_parser()
    parser.add_argument('--tend',
                        type=float, default=20.,
                        help='Duration of simulation (ms). Run for longer to also see repolarization.')
    return parser

def jobID(args):
    """
    Generate name of top level output directory.
    """
    today = date.today()
    return '{}_simple_{}_{}_np{}'.format(today.isoformat(), args.tend,
                                         args.flv, args.np)

@tools.carpexample(parser, jobID)
def run(args, job):

    #
    BASE_DIR = os.path.dirname(__file__)
    meshname = os.path.join(BASE_DIR, 'meshes', 'mesh2', 'ellipsoid')

    _, etags, _ = txt.read(meshname + '.elem')
    etags = np.unique(etags)

    IntraTags = etags[etags != 0].tolist()
    ExtraTags = etags.tolist().copy()

    # (0,0,-20000)
    stim = ['-stim[0].elec.p0[0]',      -10000,
            '-stim[0].elec.p1[0]',      10000,
            '-stim[0].elec.p0[1]',      -10000,
            '-stim[0].elec.p1[1]',      10000,
            '-stim[0].elec.p0[2]',      5000,
            '-stim[0].elec.p1[2]',      5000]
    
    cmd = tools.carp_cmd(tools.simfile_path(os.path.join(EXAMPLE_DIR, 'simple.par')))

    # Instead of generating a mesh, you could also load one using the 'meshname' openCARP
    # command. This requires .elem and .pts files that can be generated for VTK files using
    # meshtool 
    
    # Get basic command line, including solver options from external .par file
    #cmd = tools.carp_cmd(tools.carp_path(os.path.join(EXAMPLE_DIR, 'simple.par')))
    #cmd = tools.carp_cmd(tools.simfile_path(os.path.join(EXAMPLE_DIR, 'simple.par')))
    
    # Attach electrophysiology physics (monodomain) to mesh region with tag 1
    
    cmd += ['-simID',    job.ID,
            '-meshname', meshname,
            '-tend',     args.tend]

    cmd += tools.gen_physics_opts(ExtraTags=ExtraTags, IntraTags=IntraTags)

    cmd += stim

    # Set monodomain conductivities
    cmd += ['-num_gregions',			1,
    		'-gregion[0].name', 		"myocardium",
    		'-gregion[0].num_IDs', 	1,  		# one tag will be given in the next line
    		'-gregion[0].ID', 		"0",		# use these settings for the mesh region with tag 0
    		# mondomain conductivites will be calculated as half of the harmonic mean of intracellular
    		# and extracellular conductivities
    		'-gregion[0].g_el', 		0.625,	# extracellular conductivity in longitudinal direction
    		'-gregion[0].g_et', 		0.236,	# extracellular conductivity in transverse direction
    		'-gregion[0].g_en', 		0.236,	# extracellular conductivity in sheet direction
    		'-gregion[0].g_il', 		0.174,	# intracellular conductivity in longitudinal direction
    		'-gregion[0].g_it', 		0.019,	# intracellular conductivity in transverse direction
    		'-gregion[0].g_in', 		0.019,	# intracellular conductivity in sheet direction
    		'-gregion[0].g_mult',		0.5		# scale all conducitivites by a factor (to reduce conduction velocity)    		
    		]

    # Define the ionic model to use
    cmd += ['num_imp_regions',          1,
            'imp_region[0].im',         'Courtemanche',
            'imp_region[0].num_IDs',    1,
            'imp_region[0].ID[1]',      1     # use this setting for the mesh region with tag 1    
    ]


    # compute local activation times in postprocessing
    cmd += ['-num_LATs',           1,
           '-lats[0].ID',         'activation',
           '-lats[0].all',        0,	# only detect first activation
           '-lats[0].measurand',  0,	# determine LAT from transmembrane voltage
           '-lats[0].mode',       0,	# take maximum slope to detemine LAT
           '-lats[0].threshold', -10,	# -10mV threshold
           ]

	# Define the geometry of the first stimulus (index 0) at end of the block
    # (upper bound of x coordinate), units in um
    #stim = mesh.block_bc_opencarp(meshname, 'stim', 0, 'x', True)
    

    if args.visualize:
        cmd += ['-gridout_i', 3]	# output both surface & volumetric mesh for visualization

    # Run simulation
    job.carp(cmd)

    # Do visualization
    if args.visualize and not settings.platform.BATCH:

        # Prepare file paths
        meshname = os.path.join(job.ID, os.path.basename(meshname)+'_i')
        # display trensmembrane voltage
        data = os.path.join(job.ID, 'vm.igb.gz')
        # Alternatively, you could visualize the activation times instead
        #data = os.path.join(job.ID, 'init_acts_activation-thresh.dat')
        
        # load predefined visualization settings
        view = tools.simfile_path(os.path.join(BASE_DIR, 'simple.mshz'))

        # Call meshalyzer
        job.meshalyzer(meshname, data, view)

if __name__ == '__main__':
    run()
