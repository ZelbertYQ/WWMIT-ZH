import bpy

from bpy.props import BoolProperty, StringProperty, PointerProperty, IntProperty, FloatProperty, CollectionProperty

from .. import bl_info
from .. import __name__ as package_name
from .. import addon_updater_ops

from .exceptions import clear_error

class WWMI_Settings(bpy.types.PropertyGroup):

    def on_update_clear_error(self, property_name):
        if self.last_error_setting_name == property_name:
            clear_error(self)

    wwmi_tools_version: bpy.props.StringProperty(
        name = "WWMI Tools Version",
        default = '.'.join(map(str, bl_info["version"]))
    ) # type: ignore

    required_wwmi_version: bpy.props.StringProperty(
        name = "Required WWMI Version",
        default = '.'.join(map(str, bl_info["wwmi_version"]))
    ) # type: ignore

    vertex_ids_cache: bpy.props.StringProperty(
        name = "Loop Data Cache",
        default = ""
    ) # type: ignore
    
    vertex_ids_cached_collection: PointerProperty(
        name="Loop Data Cached Components",
        type=bpy.types.Collection,
    ) # type: ignore

    tool_mode: bpy.props.EnumProperty(
        name="模式",
        description="Defines list of available actions",
        items=[
            ('EXTRACT_FRAME_DATA', 'Step1: 提取游戏模型', 'Extract components of all WWMI-compatible objects from the selected frame dump directory'),
            ('IMPORT_OBJECT', 'Step2: 导入游戏模型', 'Import .ib ad .vb files from selected directory'),
            ('EXPORT_MOD', 'Step3: 导出模组文件', 'Export selected collection as WWMI mod'),
            ('TOOLS_MODE', 'Other: 工具箱', 'Bunch of useful object actions'),
        ],
        update=lambda self, context: clear_error(self),
        default=0,
    ) # type: ignore

    ########################################
    # Extract Frame Data
    ########################################

    frame_dump_folder: StringProperty(
        name="帧分析文件夹",
        description="Frame dump files directory",
        default='',
        subtype="DIR_PATH",
        update=lambda self, context: self.on_update_clear_error('frame_dump_folder'),
    ) # type: ignore

    skip_small_textures: BoolProperty(
        name="纹理过滤：跳过小文件",
        description="Skip texture smaller than specified size",
        default=True,
    ) # type: ignore

    skip_small_textures_size: IntProperty(
        name="最小值 (KB)",
        description="Minimal texture size in KB. Default is 25KB",
        default=25,
    ) # type: ignore

    skip_jpg_textures: BoolProperty(
        name="纹理过滤：跳过.jpg格式文件",
        description="Skip texture with .jpg extension. These textures are mostly gradients and other masks",
        default=True,
    ) # type: ignore

    skip_same_slot_hash_textures: BoolProperty(
        name="纹理过滤：跳过全插槽文件",
        description="Skip texture if its hash is found in same slot of all components. May filter out useful textures!",
        default=False,
    ) # type: ignore

    extract_output_folder: StringProperty(
        name="提取文件存放夹",
        description="Extracted WWMI objects export directory",
        default='',
        subtype="DIR_PATH",
    ) # type: ignore

    ########################################
    # Object Import
    ########################################

    object_source_folder: StringProperty(
        name="游戏模型文件夹",
        description="Directory with components and textures of WWMI object",
        default='',
        subtype="DIR_PATH",
        update=lambda self, context: self.on_update_clear_error('object_source_folder'),
    ) # type: ignore

    import_skeleton_type: bpy.props.EnumProperty(
        name="骨骼分权模式",
        description="Controls the way of Vertex Groups handling",
        items=[
            ('MERGED', '全合并', 'Imported mesh will have unified list of Vertex Groups, allowing to weight any vertex of any component to any bone. Mod Upsides: easy to weight, custom skeleton scale support, advanced weighting support (i.e. long hair to cape). Mod Downsides: model will be updated with 1 frame delay, mod will pause while there are more than one of same modded object on screen. Suggested usage: new modders, character or echo mods with complex weights.'),
            ('COMPONENT', '分部件', 'Imported mesh will have its Vertex Groups split into per component lists, restricting weighting of any vertex only to its parent component. Mod Upsides: no 1-frame delay for model updates, minor performance gain. Mod downsides: hard to weight, very limited weighting options, no custom skeleton scale support. Suggested usage: weapon mods and simple retextures.'),
        ],
        default=0,
    ) # type: ignore

    mirror_mesh: BoolProperty(
        name="镜像模型",
        description="Automatically mirror mesh to match actual in-game left-right. Transformation applies to the data itself and does not affect Scale X of Transform section in Object Properties.",
        default=False,
    ) # type: ignore

    ########################################
    # Mod Export
    ########################################
        
    component_collection: PointerProperty(
        name="导出集合",
        description="Collection with WWMI object's components named like `Component 0` or `Component_1 RedHat` or `Dat Gas cOmPoNENT- 3 OMG` (lookup RegEx: r'.*component[_ -]*(\d+).*')",
        type=bpy.types.Collection,
        update=lambda self, context: self.on_update_clear_error('component_collection'),
        # default=False
    ) # type: ignore

    mod_output_folder: StringProperty(
        name="模组导出文件夹",
        description="Mod export directory to place mod.ini and Meshes&Textures folders into",
        default='',
        subtype="DIR_PATH",
        update=lambda self, context: self.on_update_clear_error('mod_output_folder'),
    ) # type: ignore
    
    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply all modifiers to temporary copy of the merged object",
        default=False,
    ) # type: ignore

    mod_name: StringProperty(
        name="模组名称",
        description="Name of mod to be displayed in user notifications and mod managers",
        default='Ori - Char',
    ) # type: ignore

    mod_author: StringProperty(
        name="作者名称",
        description="Name of mod author to be displayed in user notifications and mod managers",
        default='ZelbertYQ',
    ) # type: ignore

    mod_desc: StringProperty(
        name="模组描述",
        description="Short mod description to be displayed in user notifications and mod managers",
        default='Model From Official/Public',
    ) # type: ignore

    mod_link: StringProperty(
        name="发布链接",
        description="Link to mod web page to be displayed in user notifications and mod managers",
        default='https://afdian.com/a/Zelbert \nhttps://www.caimogu.cc/user/1634144.html \nhttps://www.patreon.com/c/ZelbertYQ',
    ) # type: ignore

    mod_logo: StringProperty(
        name="模组图标",
        description="Texture with 512x512 size and .dds extension (BC7 SRGB) to be displayed in user notifications and mod managers, will be placed to /Textures/Logo.dds",
        default='',
        subtype="FILE_PATH",
    ) # type: ignore

    mod_readme: StringProperty(
        name="说明文档",
        description="说明文档注释测试230",
        default='说明文字230',
    )  # type: ignore   

    mod_skeleton_type: bpy.props.EnumProperty(
        name="骨骼分权模式",
        description="Select the same skeleton type that was used for import! Defines logic of exported mod.ini.",
        items=[
            ('MERGED', '全合并', 'Mesh with this skeleton should have unified list of Vertex Groups'),
            ('COMPONENT', '分部件', 'Mesh with this skeleton should have its Vertex Groups split into per-component lists.'),
        ],
        default=0,
    ) # type: ignore

    partial_export: BoolProperty(
        name="部分导出",
        description="For advanced usage only. Allows to export only selected buffers. Speeds up export when you're sure that there were no changes to certain data since previous export. Disables INI generation and assets copying",
        default=False,
    ) # type: ignore

    export_index: BoolProperty(
        name="索引缓冲区",
        description="Contains data that associates vertices with faces",
        default=True,
    ) # type: ignore

    export_positions: BoolProperty(
        name="位置缓冲区",
        description="Contains coordinates of each vertex",
        default=True,
    ) # type: ignore

    export_blends: BoolProperty(
        name="混合缓冲区",
        description="Contains VG ids and weights of each vertex",
        default=True,
    ) # type: ignore

    export_vectors: BoolProperty(
        name="矢量缓冲区",
        description="Contains normals and tangents",
        default=True,
    ) # type: ignore

    export_colors: BoolProperty(
        name="颜色缓冲区",
        description="Contains vertex color attribute named COLOR",
        default=True,
    ) # type: ignore

    export_texcoords: BoolProperty(
        name="纹理坐标缓冲区",
        description="Contains UVs and vertex color attribute named COLOR1",
        default=True,
    ) # type: ignore

    export_shapekeys: BoolProperty(
        name="形态键缓冲区",
        description="Contains shape keys data",
        default=True,
    ) # type: ignore
    
    ignore_hidden_objects: BoolProperty(
        name="不导出被隐藏的部件",
        description="If enabled, hidden objects inside Components collection won't be exported",
        default=False,
    ) # type: ignore
    
    ignore_muted_shape_keys: BoolProperty(
        name="不导出被禁用的形态键",
        description="If enabled, muted (unchecked) shape keys won't be exported",
        default=True,
    ) # type: ignore

    apply_all_modifiers: BoolProperty(
        name="应用全部修改器",
        description="Automatically apply all existing modifiers to temporary copies of each object",
        default=False,
    ) # type: ignore

    copy_textures: BoolProperty(
        name="复制贴图",
        description="Copy texture files to export folder",
        default=True,
    ) # type: ignore

    write_ini: BoolProperty(
        name="编写配置文件",
        description="Write new .ini to export folder",
        default=True,
    ) # type: ignore

    comment_ini: BoolProperty(
        name="注释配置文件",
        description="Add comments to INI code, useful if you want to get better idea how it works",
        default=False,
    ) # type: ignore

    skeleton_scale: FloatProperty(
        name="骨架尺寸",
        description="Scales model in-game (default is 1.0). Not supported for Per-Component Skeleton",
        default=1.0,
    ) # type: ignore

    unrestricted_custom_shape_keys: BoolProperty(
        name="额外形态键支持",
        description="Allows to use Custom Shape Keys for components that don't have them by default. Generates extra mod.ini logic",
        default=False,
    ) # type: ignore

    remove_temp_object: BoolProperty(
        name="删除临时副本",
        description="Remove temporary object built from merged components after export. May be useful to uncheck for debug purposes",
        default=True,
    ) # type: ignore

    make_readme: BoolProperty(
        name="生成说明文档",
        description="请勾选自定义配置文件",
        default=True,
    ) # type: ignore

    export_on_reload: BoolProperty(
        name="重载时导出",
        description="Trigger mod export on addon reload. Useful for export debugging.",
        default=False,
    ) # type: ignore

    use_custom_template: BoolProperty(
        name="使用自定义模板",
        description="Use configured jinja2 template to build fully custom mod.ini.",
        default=False,
        update=lambda self, context: self.on_update_clear_error('use_custom_template'),
    ) # type: ignore

    custom_template_live_update: BoolProperty(
        name="Template Live Updates",
        description="Controls state of live ini generation thread.",
        default=False,
    ) # type: ignore

    custom_template_source: bpy.props.EnumProperty(
        name="存储类型",
        description="Select custom template storage type.",
        items=[
            ('INTERNAL', '内置编辑器', 'Use Blender scripting tab file as custom template.'),
            ('EXTERNAL', '外部文件', 'Use specified file as custom template.'),
        ],
        default=0,
        update=lambda self, context: self.on_update_clear_error('use_custom_template'),
    ) # type: ignore

    custom_template_path: StringProperty(
        name="自定义模板文件",
        description="Path to mod.ini template file.\nTo create new file, copy template text from built-in editor to new text file.",
        default='',
        subtype="FILE_PATH",
        update=lambda self, context: self.on_update_clear_error('custom_template_path'),
    ) # type: ignore

    last_error_setting_name: StringProperty(
        name="Last Error Setting Name",
        description="Name of setting property which was cause of last error.",
        default='component_collection',
    ) # type: ignore

    last_error_text: StringProperty(
        name="Last Error Text",
        description="Text of last error.",
        default='Collection must be filled!',
    ) # type: ignore


class Preferences(bpy.types.AddonPreferences):
    """Preferences updater"""
    bl_idname = package_name
    # Addon updater preferences.

    auto_check_update: BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=True) # type: ignore

    updater_interval_months: IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0) # type: ignore

    updater_interval_days: IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=1,
        min=0,
        max=31) # type: ignore

    updater_interval_hours: IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23) # type: ignore

    updater_interval_minutes: IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59) # type: ignore

    def draw(self, context):
        layout = self.layout
        print(addon_updater_ops.get_user_preferences(context))
        # Works best if a column, or even just self.layout.
        mainrow = layout.row()
        col = mainrow.column()
        # Updater draw function, could also pass in col as third arg.
        addon_updater_ops.update_settings_ui(self, context)

        # Alternate draw function, which is more condensed and can be
        # placed within an existing draw function. Only contains:
        #   1) check for update/update now buttons
        #   2) toggle for auto-check (interval will be equal to what is set above)
        # addon_updater_ops.update_settings_ui_condensed(self, context, col)

        # Adding another column to help show the above condensed ui as one column
        # col = mainrow.column()
        # col.scale_y = 2
        # ops = col.operator("wm.url_open","Open webpage ")
        # ops.url=addon_updater_ops.updater.website
