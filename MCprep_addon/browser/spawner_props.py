MCPREP_ASSET_LIBRARY = 'mcprep_asset_library'

class MCPREL_Workspace_Props(PropertyGroup):  
    library_index: bpy.props.IntProperty()

class MCPREP_WM_Props(PropertyGroup):
  library_assets: bpy.props.CollectionProperty(
    type=bpy.types.AssetHandle,
    description="Current Set of Assets In Asset Browser"
  )
class MCPREP_SCN_Props(PropertyGroup):
    spawner_tabs: EnumProperty(
      name="Spawner Tabs",
      items=[
        ('BLOCKS',"Blocks","Blocks and Meshswaps"),
        ('MOBS',"Mobs","Entity rigs"),
        ('ITEMS',"Items","Items"),
        ('EFFECTS',"Effects","Effects"),
        ('MATERIALS',"Materials","Materials")
        ],
      default='BLOCKS',
      update=update_spawner)
    
    def update_spawner(self, context):
        prefs = context.preferences
        asset_lib = prefs.filepaths.asset_libraries.get(MCPREP_ASSET_LIBRARY)
        library = hb_utils.get_active_library(context)
        if library:
            asset_lib.path = library.library_path
    
            for workspace in bpy.data.workspaces:
                workspace.asset_library_ref = "home_builder_library"
            
            if bpy.ops.asset.library_refresh.poll():
                bpy.ops.asset.library_refresh()
                
def register():
  bpy.types.WorkSpace.mcprep_props = PointerProperty(
    type=MCPREL_Workspace_Props
  )
  bpy.types.WindowManager.mcprep_props = PointerProperty(
    type=MCPREP_WM_Props,
  )
  bpy.types.Scene.scn_props = PointerProperty(
    type=MCPREP_SCN_Props
  )

def unregister():
  del bpy.types.WorkSpace.mcprep_props
  del bpy.types.WindowManager.mcprep_props
  del bpy.types.Scene.scn_props
  