
def draw_library(self,layout,context, library):
    if library:
        workspace = context.workspace
        wm = context.window_manager        
        activate_id = "home_builder.todo"
        drop_id = "home_builder.todo"
        if library.activate_id != "":
            activate_id = library.activate_id
        if library.drop_id != "":
            drop_id = library.drop_id

        activate_op_props, drag_op_props = layout.template_asset_view(
            "home_builder_library",
            workspace,
            "asset_library_ref",
            wm.home_builder,
            "home_builder_library_assets",
            workspace.home_builder,
            "home_builder_library_index",
            # filter_id_types={"filter_object"},
            display_options={'NO_LIBRARY'},
            # display_options={'NO_FILTER','NO_LIBRARY'},
            activate_operator=activate_id,
            drag_operator=drop_id,            
        )
    else:
        layout.separator()
        layout.operator('home_builder.load_library')
      