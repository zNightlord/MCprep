import bpy
from bpy.props import StringProperty,EnumProperty,CollectionProperty,BoolProperty
from bpy.types import AssetHandle, PropertyGroup

class MCPREL_Workspace_Props(PropertyGroup):  
    library_index: bpy.props.IntProperty(name = "Library Index")

class Asset_Library(PropertyGroup):
    library_type: StringProperty(name="Library Type")
    library_path: StringProperty(name="Library Path")
    library_menu_ui: StringProperty(name="Library Settings UI")
    activate_id: StringProperty(name="Activate ID")
    drop_id: StringProperty(name="Drop ID")
    enabled: BoolProperty(name="Enabled",default=True)

class Library_Package(PropertyGroup):
    enabled: BoolProperty(name="Enabled",default=True)
    expand: BoolProperty(name="Expand",default=False)
    package_path: StringProperty(name="Package Path",subtype='DIR_PATH',update=update_library_package_path)
    asset_libraries: bpy.props.CollectionProperty(type=Asset_Library)

class MCPREP_WM_Props(PropertyGroup):
    library_assets: bpy.props.CollectionProperty(
        type=AssetHandle,
        description="Current Set of assets In Asset Browser")
  
    asset_libraries: bpy.props.(
        type=Asset_Library,
        description="Collection of all asset libraries loaded")
  
    library_packages: bpy.props.CollectionProperty(
      type=Library_Package,
      description="Collection of all external asset libraries loaded")
      
    def get_active_library(self,context):
        return spawner_util.get_active_library(context)

    def get_active_asset(self,context):
        workspace = context.workspace.mcprep_props
        return self.library_assets[workspace.library_index]

"""
This is in place at mcprep_ui
class MCPREP_SCN_Props():
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
        library =spawner_util.get_active_library(context)
        if library:
            asset_lib.path = library.library_path
    
            for workspace in bpy.data.workspaces:
                workspace.asset_library_ref = "mcprep-library"
            
            if bpy.ops.asset.library_refresh.poll():
                bpy.ops.asset.library_refresh()

"""

classes = (
  Asset_Library,
  Library_Package,
)

def register():
  for cls in classes:
    bpy.utils.register_class(cls)
  
  bpy.types.WorkSpace.mcprep_props = PointerProperty(
    type=MCPREP_Workspace_Props
  )
  bpy.types.WindowManager.mcprep_props = PointerProperty(
    type=MCPREP_WM_Props,
  )
  bpy.types.Scene.scn_props = PointerProperty(
    type=MCPREP_SCN_Props
  )

def unregister():
  for cls in reversed(classes):
    bpy.utils.unregister_class(cls)
  
  del bpy.types.WorkSpace.mcprep_props
  del bpy.types.WindowManager.mcprep_props
  del bpy.types.Scene.scn_props
  