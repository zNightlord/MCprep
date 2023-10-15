def _install_path():
    import bpy
    import os
    return os.path.join(bpy.utils.script_path_user(), 'mcprep_addon')


__path__ = [_install_path()]