mcprep_info = {
    "name": "MCprep UI tweaks",
    "description": "Experimental UI changes for MCPrep, adding enum tabs, cleaning up the UI",
    "link": "https://gist.github.com/zNightlord/85f364da25dcee3169fd789a4979a0ef",
}

from . import replace_mcprep_ui
classes = (
  replace_mcprep_ui,
)


def register():
  from bpy.utils import register_class

  for cls in classes:
    register_class(cls)


def unregister():
  from bpy.utils import unregister_class

  for cls in classes:
    unregister_class(cls)