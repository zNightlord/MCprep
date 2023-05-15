import bpy
# useful functions for generate material textures... 
from MCprep_addon.materials import generate
from MCprep_addon import util

def execute(context, mat, options):
    passes = options.passes
    # Do stuffs
    # Print material and passes dictionary
    print(mat, passes) 