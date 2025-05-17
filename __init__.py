#!/usr/bin/env python3
import sys

from . import auto_load
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'libs'))


bl_info = {
    "name": "WWMI Tools 中文版",
    "version": (1, 2, 1),
    "wwmi_version": (0, 7, 7),
    "blender": (2, 93, 0),
    "author": "SpectrumQT, LeoTorreZ, SinsOfSeven, SilentNightSound, DarkStarSword, ZelbertYQ(Translater_Zh-hans)",
    "location": "View3D > Sidebar > Tool Tab",
    "description": "Wuthering Waves modding toolkit",
    "category": "中文版",
    "tracker_url": "https://github.com/ZelbertYQ/WWMIT-ZH",
}
auto_load.init()

import bpy
from .addon import settings

# 真121版本，更新成功
def trigger_mod_export():
    if bpy.context.scene.wwmi_tools_settings.export_on_reload:
        print('Triggered export on addon reload...')
        bpy.ops.wwmi_tools.export_mod()
    

def register():
    auto_load.register()

    bpy.types.Scene.wwmi_tools_settings = bpy.props.PointerProperty(type=settings.WWMI_Settings)
    
    # prefs = bpy.context.preferences.addons[__package__].preferences
    bpy.app.timers.register(trigger_mod_export, first_interval=0.1)

def unregister():
    auto_load.unregister()

    del bpy.types.Scene.wwmi_tools_settings

    if bpy.app.timers.is_registered(trigger_mod_export):
        bpy.app.timers.unregister(trigger_mod_export)
