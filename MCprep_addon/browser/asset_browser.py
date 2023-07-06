import bpy
import os
from bpy_extras import view3d_utils
from bpy.app.handlers import persistent
from bpy.types import (
        Operator,
        Panel,
        PropertyGroup,
        UIList,
        AddonPreferences,
        )
from bpy.props import (
        IntProperty,
        PointerProperty,
        CollectionProperty,
        )
                
bl_info = {
    "name": "Test Asset Library",
    "author": "Andrew Peel",
    "version": (0, 0, 1),
    "blender": (3, 0, 0),
    "location": "3D Viewport Sidebar",
    "description": "Test Asset Library",
    "warning": "",
    "wiki_url": "",
    "category": "Asset Library",
}

@persistent
def load_library(dummy):
    """
    Load Asset Libraries
    """
    LIBRARY_NAME = "test_library"
    LIBRARY_PATH = os.path.join(os.path.dirname(__file__),'assets')

    prefs = bpy.context.preferences
    asset_lib = prefs.filepaths.asset_libraries.get(LIBRARY_NAME)
    if not asset_lib:
        bpy.ops.preferences.asset_library_add()
        asset_lib = prefs.filepaths.asset_libraries[-1]
        asset_lib.name = LIBRARY_NAME
    asset_lib.path = str(LIBRARY_PATH)

    for workspace in bpy.data.workspaces:
        workspace.asset_library_ref = LIBRARY_NAME

def get_selection_point(context, region, event):
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

        depsgraph = context.evaluated_depsgraph_get()
        for dup in depsgraph.object_instances:
            if dup.is_instance:  # Real dupli instance
                obj = dup.instance_object
                yield (obj, dup.matrix_world.copy())
            else:  # Usual object
                obj = dup.object
                yield (obj, obj.matrix_world.copy())

    def obj_ray_cast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

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

    # cast rays and find the closest object
    best_length_squared = -1.0
    best_obj = None

    for obj, matrix in visible_objects_and_duplis():
        if obj.type == 'MESH':
            hit, normal, face_index = obj_ray_cast(obj, matrix)
            if hit is not None:
                hit_world = matrix @ hit
                scene.cursor.location = hit_world
                length_squared = (hit_world - ray_origin).length_squared
                if best_obj is None or length_squared < best_length_squared:
                    best_length_squared = length_squared
                    best_obj = obj

    # now we have the object under the mouse cursor,
    # we could do lots of stuff but for the example just select.
    if best_obj is not None:
        # for selection etc. we need the original object,
        # evaluated objects are not in viewlayer
        best_original = best_obj.original
        best_original.select_set(True)
        context.view_layer.objects.active = best_original


class test_library_OT_place_object(bpy.types.Operator):
    bl_idname = "object.test_asset_library_place_object"
    bl_label = "Place Object"
    bl_decription = "Test operator to define custom placement functionality"
    bl_options = {'UNDO'}
    obj = None

    def execute(self, context):
        # TRIED TO GET 3D REGION DATA, BUT RETURNS WRONG VIEW MATRIX
        # for area in context.screen.areas:
        #     if area.type == 'VIEW_3D':
        #         for region in area.regions:
        #             if region.data:
        #                 self.region_data = region.data
        self.get_object(context.region_data)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def get_object(self,context):
        object_file_path = os.path.join(os.path.dirname(__file__),'assets','library.blend')
        with bpy.data.libraries.load(object_file_path) as (data_from, data_to):
                data_to.objects = data_from.objects        
        for obj in data_to.objects:
            self.obj = obj        
            context.view_layer.active_layer_collection.collection.objects.link(obj)
            
    @staticmethod
    def get_main_region(context):
        for region in context.area.regions:
            if region.type == 'WINDOW':
                return region
        return None

    def modal(self, context, event):
        context.view_layer.update()


        region = self.get_main_region(context)
        if not region:
            return {'RUNNING_MODAL'}
            
        selected_point, selected_obj, selected_normal = get_selection_point(context,region,event)
        self.obj.location = selected_point

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            return {'FINISHED'}
            
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return {'CANCELLED'}

        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

class TEST_LIBRARY_PT_library(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Test Library"
    bl_category = "Test Library"

    def draw(self, context):
        layout = self.layout
        workspace = context.workspace
        wm = context.window_manager    
        layout.prop(workspace,'asset_library_ref')     

        activate_op_props, drag_op_props = layout.template_asset_view(
            "test_library",
            workspace,
            "asset_library_ref",
            wm.test_library,
            "library_assets",
            workspace.test_library,
            "library_index",
            filter_id_types={"filter_object"},
            display_options={'NO_FILTER','NO_LIBRARY'},
            # activate_operator="object.test_asset_library_place_object",
            drag_operator="object.test_asset_library_place_object('INVOKE_DEFAULT')",
        )

class Test_Library_Workspace_Props(PropertyGroup):  
    library_index: IntProperty()

    @classmethod
    def register(cls):
        bpy.types.WorkSpace.test_library = PointerProperty(
            name="Home Builder Props",
            description="Home Builder Props",
            type=cls,
        )
        
    @classmethod
    def unregister(cls):
        del bpy.types.WorkSpace.test_library    

class Test_Library_Window_Manager_Props(PropertyGroup):
    library_assets: CollectionProperty(type=bpy.types.AssetHandle)
        
    @classmethod
    def register(cls):
        bpy.types.WindowManager.test_library = PointerProperty(
            name="Home Builder Props",
            description="Home Builder Props",
            type=cls,
        )
        
    @classmethod
    def unregister(cls):
        del bpy.types.WindowManager.test_library    

def register():
    bpy.utils.register_class(Test_Library_Window_Manager_Props)
    bpy.utils.register_class(Test_Library_Workspace_Props)
    bpy.utils.register_class(TEST_LIBRARY_PT_library)
    bpy.utils.register_class(test_library_OT_place_object)
    bpy.app.handlers.load_post.append(load_library)

def unregister():
    bpy.utils.unregister_class(Test_Library_Window_Manager_Props)
    bpy.utils.unregister_class(Test_Library_Workspace_Props)
    bpy.utils.unregister_class(TEST_LIBRARY_PT_library)
    bpy.utils.unregister_class(test_library_OT_place_object)    
    bpy.app.handlers.load_post.remove(load_library)

if __name__ == '__main__':
    print('register')
    load_library(None)
    register()