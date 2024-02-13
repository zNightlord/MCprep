# Copyright (c) 2024 Mahid Sheikh. All Rights Reserved.
#
# This is a build script to automatically
# generate a bpy.apps.translations compatible
# dictionary from PO files.
#
# Apparently Blender's UI Translate addon has
# this feature, but it's so confusing to use that
# it makes more sense for us to create a build script 
# that automatically generates a Python file with 
# the necessary translation dictionary.

from pathlib import Path
from typing import Dict, Tuple
from libs import polib
import pprint

translation_dict: Dict[str, Dict[Tuple[str, str], str]] = {}

def main() -> None:
    print("Building Translations...")
    languages = Path("MCprep_resources/Languages") 

    if not languages.exists() or not languages.is_dir():
        print("Invalid directory for translations! Exiting...")
    
    for locale in languages.iterdir():
        if not locale.is_dir():
            continue
        file = Path(locale, "LC_MESSAGES", "mcprep.po")
        if not file.exists():
            print(file, "does not exist!")
        
        po = polib.pofile(str(file))

        locale_dict: Dict[Tuple[str, str], str] = {}
        for entry in po:
            # Let's keep the file as small
            # as possible, and not include
            # untranslated parts
            if entry.msgstr == '':
                continue
            locale_dict[("*", entry.msgid)] = entry.msgstr
        
        # This is to handle cases like English
        # where the dictionary is empty
        if len(locale_dict):
            translation_dict[str(locale.name)] = locale_dict

    with open("translations.py", 'w') as f:
        f.write("# This file is generated by BpyBuild.\n")
        f.write("# Do not modify this file directly, modify the PO files\n")
        f.write("# under MCprep_addon/MCprep_resources/Languages\n")
        f.write("MCPREP_TRANSLATIONS = ")
        pprint.pprint(translation_dict, f)


if __name__ == "__main__":
    main()
