from bpy_extras import view3d_utils
import mathutils
from mathutils import Vector
import math, random


# 3D viewpprt
def get_selection_point(context, region, event, ray_max=10000.0, objects=None, floor=None, exclude_objects=[],ignore_opening_meshes=False):
    """Run this function on left mouse, execute the ray cast"""
    # get the context arguments
    scene = context.scene
    rv3d = region.data
    coord = event.mouse_x - region.x, event.mouse_y - region.y   

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    ray_target = ray_origin + view_vector

    def visible_objects_and_duplis():
        """Loop over (object, matrix) pairs (mesh only)"""

        for obj in context.visible_objects:
            if ignore_opening_meshes:
                if 'IS_OPENING_MESH' in obj:
                    continue
            if objects:
                if obj in objects and obj not in exclude_objects:
                    yield (obj, obj.matrix_world.copy())

            else:
                if obj not in exclude_objects:
                    if floor is not None and obj == floor:
                        yield (obj, obj.matrix_world.copy())

                    if obj.type in {'MESH','CURVE'} and obj.hide_select == False:
                        yield (obj, obj.matrix_world.copy())

    def obj_ray_cast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

        try:
            # get the ray relative to the object
            matrix_inv = matrix.inverted()
            ray_origin_obj = matrix_inv @ ray_origin
            ray_target_obj = matrix_inv @ ray_target
            ray_direction_obj = ray_target_obj - ray_origin_obj

            # cast the ray
            success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)
            if success:
                return location, normal, face_index
            else:
                return None, None, None
        except:
            print("ERROR IN obj_ray_cast", obj)
            return None, None, None

    best_length_squared = ray_max * ray_max
    best_obj = None
    best_hit = (0,0,0)
    best_norm = Vector((0, 0, 0))

    for obj, matrix in visible_objects_and_duplis():
        if obj.type in {'MESH','CURVE'}:
            if obj.data:

                hit, normal, face_index = obj_ray_cast(obj, matrix)
                if hit is not None:
                    hit_world = matrix @ hit
                    length_squared = (hit_world - ray_origin).length_squared
                    if length_squared < best_length_squared:
                        best_hit = hit_world
                        best_length_squared = length_squared
                        best_obj = obj
                        best_norm = normal

    return best_hit, best_obj, best_norm    

def floor_raycast(context: Context, mx, my):
    '''
    This casts a ray into the 3D view and returns information based on what is under the mouse

    ARGS
    context (bpy.context) = current blender context
    mx (float) = 2D mouse x location
    my (float) = 2D mouse y location

    RETURNS tuple
    has_hit (boolean) - determines if an object is under the mouse
    snapped_location (tuple) - x,y,z location of location under mouse
    snapped_normal (tuple) - normal direction
    snapped_rotation (tuple) - rotation
    face_index (int) - face index under mouse
    object (bpy.types.Object) - Blender Object under mouse
    martix (float multi-dimensional array of 4 * 4 items in [-inf, inf]) - matrix of placement under mouse
    '''
    r = context.region
    rv3d = context.region_data
    coord = mx, my

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(r, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(r, rv3d, coord)
    # ray_target = ray_origin + (view_vector * 1000000000)
    ray_target = ray_origin + view_vector

    snapped_location = mathutils.geometry.intersect_line_plane(ray_origin, ray_target, (0, 0, 0), (0, 0, 1),
                                                               False)
    if snapped_location != None:
        has_hit = True
        snapped_normal = Vector((0, 0, 1))
        face_index = None
        object = None
        matrix = None
        snapped_rotation = snapped_normal.to_track_quat('Z', 'Y').to_euler()
        offset_rotation_amount = 0
        randomize_rotation_amount = 0
        randomize_rotation = False
        if randomize_rotation:
            randoffset = offset_rotation_amount + math.pi + (
                    random.random() - 0.5) * randomize_rotation_amount
        else:
            randoffset = offset_rotation_amount + math.pi
        snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, object, matrix

def create_box_coord(width, height, depth):
    """
    This function takes inputs and returns vertex and face arrays.
    No actual mesh data creation is done here.
    """
    
    verts = [(+1.0, +1.0, -1.0),
             (+1.0, -1.0, -1.0),
             (-1.0, -1.0, -1.0),
             (-1.0, +1.0, -1.0),
             (+1.0, +1.0, +1.0),
             (+1.0, -1.0, +1.0),
             (-1.0, -1.0, +1.0),
             (-1.0, +1.0, +1.0),
             ]
    
    faces = [(0, 1, 2, 3),
             (4, 7, 6, 5),
             (0, 4, 5, 1),
             (1, 5, 6, 2),
             (2, 6, 7, 3),
             (4, 0, 3, 7),
             ]
    
    # apply size
    for i, v in enumerate(verts):
        verts[i] = v[0] * width, v[1] * depth, v[2] * height
    
    return verts, faces

# Create cube

def get_3d_view_region(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.data:
                    return region

# Events 
def event_rotate_state(event):
  """This event cycle through the rotate state
    rotate = 0 # UP
    rotate = 1 # DOWN
    rotate = 2 # NORTH
    rotate = 3 # EAST
    rotate = 4 # SOUTH
    rotate = 5 # WEST
  """
  if event.type == 'R':
    return True
  else:
    return False

def event_is_place_asset(event):
    """"""
    if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
        return True
    elif event.type == 'NUMPAD_ENTER' and event.value == 'PRESS':
        return True
    elif event.type == 'RET' and event.value == 'PRESS':
        return True
    else:
        return False
        
def event_is_cancel_command(event):
    """"""
    if event.type in {'RIGHTMOUSE', 'ESC'}:
        return True
    else:
        return False
        
def event_is_pass_through(event):
    """Passthrough """
    if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
        return True
    else:
        return False
        
# Placement
def position_block_placement():
  print("TODO")

def position_wall_placement():
  """Placement for objects like vine, ladder, painting, itemframe, banner"""
  
  
# ETC
def snapping(obj, location, snap_mode = 'CENTER'):
  if snap_mode == "CENTER":
    offset = 0
    obj.location = [round(x + offset) - offset for x in location]
    obj.location.z -= 0.5
  elif self.snapping == "OFFSET":
    offset = 0.5
    obj.location = [round(x + offset) - offset for x in location]
    obj.location.z -= 0.5
  else:
    obj.location = location

def get_active_library(context):
    scn_props = context.scene.mcprep_props
    wm = context.window_manager        
    wm_props = wm.mcprep_props

    if scn_props.library_tabs == 'PRODUCTS':
        return get_library(wm_props,'PRODUCTS')

    if scn_props.library_tabs == 'ROOMS':
        if scn_props.room_tabs == 'DOORS_WINDOWS':
            return get_library(wm_props,'DOORS_WINDOWS')   

    if scn_props.library_tabs == 'BUILD':
        if scn_props.build_tabs == 'STARTERS':
            return get_library(wm_props,'STARTERS')    

        if scn_props.build_tabs == 'INSERTS':
            return get_library(wm_props,'INSERTS')  

        if scn_props.build_tabs == 'PARTS':
            return get_library(wm_props,'PARTS') 

        if scn_props.build_tabs == 'LIBRARY':
            return get_library(wm_props,'BUILD_LIBRARY') 

    if scn_props.library_tabs == 'DECORATIONS':
        return get_library(wm_props,'DECORATIONS') 

    if scn_props.library_tabs == 'MATERIALS':
        return get_library(wm_props,'MATERIALS')       

def get_material(library_path,material_name):
    if material_name in bpy.data.materials:
        return bpy.data.materials[material_name]

    if os.path.exists(library_path):

        with bpy.data.libraries.load(library_path) as (data_from, data_to):
            for mat in data_from.materials:
                if mat == material_name:
                    data_to.materials = [mat]
                    break    
        
        for mat in data_to.materials:
            return mat