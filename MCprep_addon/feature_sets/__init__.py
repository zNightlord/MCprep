def _install_path():
    import bpy
    import os
    return [os.path.join(bpy.utils.script_path_user(), 'mcprep_addon'), os.path.dirname(os.path.abspath(__file__))]


__path__ = _install_path()
