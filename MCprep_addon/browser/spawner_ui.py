
def draw_library(layout, context, library):
    workspace = context.workspace
    wm = context.window_manager
    wm_props = wm.mcprep_props
    ws_props = workspace.mcprep_props
    lib = "library_assets"
    index = "library_index"
    try:
        if library.activate_id:
            activate_id = library.activate_id
        if library.drop_id:
            drop_id = library.drop_id
    except: # Use poselib if error
        activate_id = "poselib.apply_pose_asset"
        drop_id = "poselib.blend_pose_asset"
        lib = "pose_assets"
        wm_props = wm
        ws_props = workspace
        index = "active_pose_asset_index"

    activate_op_props, drag_op_props = layout.template_asset_view(
        lib,
        workspace,
        "asset_library_ref",
        wm_props,
        lib,
        ws_props,
        index,
        filter_id_types={"filter_object"},
        # display_options={'NO_FILTER','NO_LIBRARY'},
        activate_operator=activate_id,
        drag_operator=drop_id
    )
    if library:
        layout.label("A")
    else:
        layout.separator()
        layout.operator('mcprep.load_library')
      