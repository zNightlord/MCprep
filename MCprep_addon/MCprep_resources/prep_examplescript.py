import bpy
# useful functions for generate material textures... 
from MCprep_addon.materials import generate
from MCprep_addon import util

def execute(context, mat, passes):
      # Do stuffs
      print(mat, passes) #print material and dictionary of passes