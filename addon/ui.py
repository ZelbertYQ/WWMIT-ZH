import subprocess
import bpy

from bpy.props import BoolProperty, StringProperty, PointerProperty, IntProperty, FloatProperty, CollectionProperty

from .. import bl_info
from .. import addon_updater_ops

from .exceptions import clear_error, ConfigError

from ..migoto_io.blender_interface.objects import *
from ..migoto_io.blender_interface.collections import *
from ..migoto_io.blender_interface.utility import *
from ..migoto_io.blender_tools.vertex_groups import *
from ..migoto_io.blender_tools.modifiers import *

from ..blender_import.blender_import import blender_import
from ..blender_export.blender_export import blender_export
from ..blender_export.ini_maker import IniMaker
from ..extract_frame_data.extract_frame_data import extract_frame_data


def add_row_with_error_handler(layout, cfg, setting_names):
    if not cfg.last_error_setting_name or cfg.last_error_setting_name not in setting_names:
        return layout.row()
    else:
        layout.alert = True
        row = layout.row()
        error_lines = cfg.last_error_text.split('\n')
        
        if len(error_lines) == 1:
            error_row = layout.row()
            error_row.alignment = 'CENTER'
            error_row.label(text=error_lines[0], icon='ERROR')
        else:
            error_box = layout.box()
            error_box.label(text=error_lines[0], icon='ERROR')
            for line in error_lines[1:]:
                if not line.strip():
                    continue
                error_box.label(text=line, icon='BLANK1') 
        layout.alert = False
        return row


class WWMI_TOOLS_PT_SIDEBAR(bpy.types.Panel):
    """
    Wuthering Waves modding toolkit
    """

    bl_idname = "WWMI_TOOLS_PT_SIDEBAR"
    bl_label = "WWMI Tools 中文版"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "WWMI Tools"
    # bl_context = "objectmode"

    # @classmethod
    # def poll(cls, context):
    #     return (context.object is not None)

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.alignment = 'RIGHT'
        row.label(text="v"+".".join(str(i) for i in bl_info.get('version', (0, 0, 0))))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        cfg = context.scene.wwmi_tools_settings
        layout = self.layout

        layout.row().prop(cfg, 'tool_mode')

        if cfg.tool_mode == 'TOOLS_MODE':
            self.draw_menu_tools_mode(context)

        if cfg.tool_mode == 'EXPORT_MOD':
            self.draw_menu_export_mod(context)

        elif cfg.tool_mode == 'IMPORT_OBJECT':
            self.draw_menu_import_object(context)

        elif cfg.tool_mode == 'EXTRACT_FRAME_DATA':
            self.draw_menu_extract_frame_data(context)

    def draw_menu_tools_mode(self, context):
        cfg = context.scene.wwmi_tools_settings
        layout = self.layout

        layout.row().operator(WWMI_ApplyModifierForObjectWithShapeKeysOperator.bl_idname)
        layout.row().operator(WWMI_MergeVertexGroups.bl_idname)
        layout.row().operator(WWMI_FillGapsInVertexGroups.bl_idname)
        layout.row().operator(WWMI_RemoveUnusedVertexGroups.bl_idname)
        layout.row().operator(WWMI_RemoveAllVertexGroups.bl_idname)

    def draw_menu_export_mod(self, context):
        cfg = context.scene.wwmi_tools_settings
        layout = self.layout
        
        layout.row()
        
        row = add_row_with_error_handler(layout, cfg, 'component_collection')
        row.prop(cfg, 'component_collection')

        row = add_row_with_error_handler(layout, cfg, 'object_source_folder')
        row.prop(cfg, 'object_source_folder')

        row = add_row_with_error_handler(layout, cfg, 'mod_output_folder')
        row.prop(cfg, 'mod_output_folder')
        
        layout.row().prop(cfg, 'mod_skeleton_type')
                
        layout.row()

        layout.row().prop(cfg, 'mirror_mesh')
        layout.row().prop(cfg, 'ignore_hidden_objects')
        layout.row().prop(cfg, 'ignore_muted_shape_keys')

        layout.row()
        
        layout.row().prop(cfg, 'partial_export')

        if not cfg.partial_export:
            layout.row()
            
            layout.row().prop(cfg, 'apply_all_modifiers')
            layout.row().prop(cfg, 'copy_textures')

            col = layout.column(align=True)
            grid = col.grid_flow(columns=2, align=True)
            grid.alignment = 'LEFT'
            grid.prop(cfg, 'write_ini')
            if cfg.write_ini:
                grid.prop(cfg, 'comment_ini')

                if cfg.mod_skeleton_type == 'MERGED':
                    layout.row().prop(cfg, 'skeleton_scale')
                layout.row().prop(cfg, 'unrestricted_custom_shape_keys')

    def draw_menu_import_object(self, context):
        cfg = context.scene.wwmi_tools_settings
        layout = self.layout
        
        layout.row()

        row = add_row_with_error_handler(layout, cfg, 'object_source_folder')
        row.prop(cfg, 'object_source_folder')

        layout.row().prop(cfg, 'import_skeleton_type')
        layout.row().prop(cfg, 'mirror_mesh')

        layout.row()

        layout.row().operator(WWMI_Import.bl_idname)

    def draw_menu_extract_frame_data(self, context):
        cfg = context.scene.wwmi_tools_settings
        layout = self.layout
        
        layout.row()

        row = add_row_with_error_handler(layout, cfg, 'frame_dump_folder')
        row.prop(cfg, 'frame_dump_folder')

        layout.row().prop(cfg, 'extract_output_folder')

        layout.row()

        col = layout.column(align=True)
        grid = col.grid_flow(columns=2, align=True)
        grid.alignment = 'LEFT'
        grid.prop(cfg, 'skip_small_textures')
        if cfg.skip_small_textures:
            grid.prop(cfg, 'skip_small_textures_size')

        layout.row().prop(cfg, 'skip_jpg_textures')
        layout.row().prop(cfg, 'skip_same_slot_hash_textures')

        layout.row()

        layout.row().operator(WWMI_ExtractFrameData.bl_idname)


class WWMI_TOOLS_PT_SidePanelPartialExport(bpy.types.Panel):
    bl_label = "Partial Export"
    bl_parent_id = "WWMI_TOOLS_PT_SIDEBAR"
    # bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "WWMI Tools"
    bl_options = {'HIDE_HEADER'}
    bl_idname = 'wwmi_1'
    bl_order = 1

    @classmethod
    def poll(cls, context):
        cfg = context.scene.wwmi_tools_settings
        return cfg.tool_mode == 'EXPORT_MOD' and cfg.partial_export

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings
        box = layout.box()
        box.row().prop(cfg, 'export_index')
        box.row().prop(cfg, 'export_positions')
        box.row().prop(cfg, 'export_blends')
        box.row().prop(cfg, 'export_vectors')
        box.row().prop(cfg, 'export_colors')
        box.row().prop(cfg, 'export_texcoords')
        box.row().prop(cfg, 'export_shapekeys')


class WWMI_TOOLS_PT_SidePanelModInfo(bpy.types.Panel):
    bl_label = "模组信息"
    bl_parent_id = "WWMI_TOOLS_PT_SIDEBAR"
    # bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "WWMI Tools"
    bl_order = 13

    @classmethod
    def poll(cls, context):
        cfg = context.scene.wwmi_tools_settings
        return cfg.tool_mode == 'EXPORT_MOD' and not cfg.partial_export

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings
        layout.row().prop(cfg, 'mod_name')
        layout.row().prop(cfg, 'mod_author')
        layout.row().prop(cfg, 'mod_desc')
        layout.row().prop(cfg, 'mod_link')
        layout.row().prop(cfg, 'mod_logo')


class WWMI_TOOLS_PT_SidePanelIniTemplate(bpy.types.Panel):
    bl_label = "配置文件模板"
    bl_idname = "WWMI_TOOLS_PT_INI_TEMPLATE"
    bl_parent_id = "WWMI_TOOLS_PT_SIDEBAR"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "WWMI Tools"
    bl_order = 80

    @classmethod
    def poll(cls, context):
        cfg = context.scene.wwmi_tools_settings
        return cfg.tool_mode == 'EXPORT_MOD'
    
    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings
    
        row = add_row_with_error_handler(layout, cfg, ['use_custom_template', 'custom_template_source'])

        split = row.split(factor=0.5)

        col_left = split.column()
        col_left.prop(cfg, 'use_custom_template')

        col_left = split.column()
        col_left.prop(cfg, 'custom_template_source')
        
        if cfg.custom_template_source == 'INTERNAL':
            layout.row().operator(WWMI_OpenIniTemplateEditor.bl_idname)

        elif cfg.custom_template_source == 'EXTERNAL':
            row = add_row_with_error_handler(layout, cfg, 'custom_template_path')
            row.prop(cfg, 'custom_template_path')

            row = layout.row()
            split = row.split(factor=0.5)

            col_left = split.column()
            col_left.operator(WWMI_OpenIniTemplateEditor.bl_idname)
            
            col_right = split.column()
            if cfg.custom_template_live_update:
                col_right.operator(WWMI_IniTemplateEditor_ToggleLiveUpdates.bl_idname, text="Stop Ini Updates")
            else:
                col_right.operator(WWMI_IniTemplateEditor_ToggleLiveUpdates.bl_idname, text="Start Ini Updates")


class WWMI_TOOLS_PT_SidePanelExportFooter(bpy.types.Panel):
    bl_label = "Export"
    bl_parent_id = "WWMI_TOOLS_PT_SIDEBAR"
    # bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "WWMI Tools"
    bl_options = {'HIDE_HEADER'}
    bl_order = 99

    @classmethod
    def poll(cls, context):
        cfg = context.scene.wwmi_tools_settings
        return cfg.tool_mode == 'EXPORT_MOD'
    
    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings
        if cfg.custom_template_live_update:
            layout.operator(WWMI_IniTemplateEditor_ToggleLiveUpdates.bl_idname, text="Stop Ini Updates")
        else:
            layout.row().operator(WWMI_Export.bl_idname)


# @orientation_helper(axis_forward='-Z', axis_up='Y')
class WWMI_Import(bpy.types.Operator):
    """
    Import object extracted from frame dump data with WWMI
    """
    bl_idname = "wwmi_tools.import_object"
    bl_label = "一键导入"
    bl_description = "Import object extracted from frame dump data with WWMI"

    bl_options = {'UNDO'}

    def execute(self, context):
        try:
            cfg = context.scene.wwmi_tools_settings

            clear_error(cfg)

            cfg.mod_skeleton_type = cfg.import_skeleton_type
            
            blender_import(self, context, cfg)

        except ConfigError as e:
            self.report({'ERROR'}, str(e))
        
        return {'FINISHED'}


class WWMI_Export(bpy.types.Operator):
    """
    Export object as WWMI mod
    """
    bl_idname = "wwmi_tools.export_mod"
    bl_label = "导出"
    bl_description = "Export object as WWMI mod"

    def get_excluded_buffers(self, context):
        """
        Calculates list of exported buffers and processed semantics based on partial export settings
        Speeds up export of single buffer up to 5 times compared to full export
        """
        cfg = context.scene.wwmi_tools_settings

        if cfg.partial_export:
            # Loop data is used to create list of exported vertices, so there are only two options for partial export:
            # 1. Recalculate each time whenever Index / Vector / Color / TexCoord buffers is selected
            # 2. Load from cache if there is no Index / Vector / Color / TexCoord buffers selected
            exclude_buffers = []

            if not cfg.export_index:
                exclude_buffers.append('Index')
            if not cfg.export_positions:
                exclude_buffers.append('Position')
            if not cfg.export_blends:
                exclude_buffers.append('Blend')
            if not cfg.export_vectors:
                exclude_buffers.append('Vector')
            if not cfg.export_colors:
                exclude_buffers.append('Color')
            if not cfg.export_texcoords:
                exclude_buffers.append('TexCoord')
            if not cfg.export_shapekeys:
                exclude_buffers.append('ShapeKeyOffset')
                exclude_buffers.append('ShapeKeyVertexId')
                exclude_buffers.append('ShapeKeyVertexOffset')
                
            return exclude_buffers
    
        else:

            return []

    def execute(self, context):
        try:
            cfg = context.scene.wwmi_tools_settings

            clear_error(cfg)

            excluded_buffers = self.get_excluded_buffers(context)

            blender_export(self, context, cfg, excluded_buffers)
            
        except ConfigError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}


class WWMI_ExtractFrameData(bpy.types.Operator):
    """
    Extract objects from frame dump
    """
    bl_idname = "wwmi_tools.extract_frame_data"
    bl_label = "一键提取"
    bl_description = "Extract objects from frame dump"

    def execute(self, context):
        try:
            cfg = context.scene.wwmi_tools_settings

            clear_error(cfg)

            extract_frame_data(cfg)
            
        except ConfigError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}
    

class WWMI_MergeVertexGroups(bpy.types.Operator):
    bl_idname = "wwmi_tools.merge_vertex_groups"
    bl_label = "合并顶点组"
    bl_description = "Merges vertex groups with same name before dot (i.e. `7` with `7.1` and `7.3`). Sourced by SilentNightSound#7430"

    def execute(self, context):
        try:
            for obj in get_selected_objects(context):
                merge_vertex_groups(context, obj)
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}
    

class WWMI_FillGapsInVertexGroups(bpy.types.Operator):
    """
    Fills in missing vertex groups for a model so there are no gaps, and sorts to make sure everything is in order
    Works on the currently selected object
    e.g. if the selected model has groups 0 1 4 5 7 2 it adds an empty group for 3 and 6 and sorts to make it 0 1 2 3 4 5 6 7
    Very useful to make sure there are no gaps or out-of-order vertex groups
    """
    bl_idname = "wwmi_tools.fill_gaps_in_vertex_groups"
    bl_label = "顶点组排列补缺"
    bl_description = "Adds missing vertex groups and sorts the VG lists of selected objects (i.e. if object had 0,4,2 groups, it'll add missing 1,3 and sort the list to 0,1,2,3,4). Sourced by SilentNightSound#7430"

    def execute(self, context):
        try:
            for obj in get_selected_objects(context):
                fill_gaps_in_vertex_groups(context, obj)
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}
    

class WWMI_RemoveUnusedVertexGroups(bpy.types.Operator):
    """
    Remove all vertex groups from selected objects
    """
    bl_idname = "wwmi_tools.remove_unused_vertex_groups"
    bl_label = "移除未使用顶点组"
    bl_description = "Remove vertex groups with zero weights from selected objects. Sourced by Ave"

    def execute(self, context):
        try:
            for obj in get_selected_objects(context):
                remove_unused_vertex_groups(context, obj)
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}
    

class WWMI_RemoveAllVertexGroups(bpy.types.Operator):
    """
    Remove all vertex groups from selected objects
    """
    bl_idname = "wwmi_tools.remove_all_vertex_groups"
    bl_label = "移除全部顶点组"
    bl_description = "Remove all vertex groups from selected objects"

    def execute(self, context):
        try:
            for obj in get_selected_objects(context):
                remove_all_vertex_groups(context, obj)
            
        except ValueError as e:
            self.report({'ERROR'}, str(e))
            
        return {'FINISHED'}


class PropertyCollectionModifierItem(bpy.types.PropertyGroup):
    checked: BoolProperty(
        name="", 
        default=False
    ) # type: ignore
bpy.utils.register_class(PropertyCollectionModifierItem)


class WWMI_ApplyModifierForObjectWithShapeKeysOperator(bpy.types.Operator):
    bl_idname = "wwmi_tools.apply_modifier_for_object_with_shape_keys"
    bl_label = "保留形态键应用修改器"
    bl_description = "Apply selected modifiers and remove from the stack for object with shape keys (Solves 'Modifier cannot be applied to a mesh with shape keys' error when pushing 'Apply' button in 'Object modifiers'). Sourced by Przemysław Bągard"
 
    def item_list(self, context):
        return [(modifier.name, modifier.name, modifier.name) for modifier in bpy.context.object.modifiers]
    
    my_collection: CollectionProperty(
        type=PropertyCollectionModifierItem
    ) # type: ignore
    
    disable_armatures: BoolProperty(
        name="Don't include armature deformations",
        default=True,
    ) # type: ignore
 
    def execute(self, context):
        ob = bpy.context.object
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = ob
        ob.select_set(True)
        
        selectedModifiers = [o.name for o in self.my_collection if o.checked]
        
        if not selectedModifiers:
            self.report({'ERROR'}, 'No modifier selected!')
            return {'FINISHED'}
        
        success, errorInfo = apply_modifiers_for_object_with_shape_keys(context, selectedModifiers, self.disable_armatures)
        
        if not success:
            self.report({'ERROR'}, errorInfo)
        
        return {'FINISHED'}
        
    def draw(self, context):
        if context.object.data.shape_keys and context.object.data.shape_keys.animation_data:
            self.layout.separator()
            self.layout.label(text="Warning:")
            self.layout.label(text="              Object contains animation data")
            self.layout.label(text="              (like drivers, keyframes etc.)")
            self.layout.label(text="              assigned to shape keys.")
            self.layout.label(text="              Those data will be lost!")
            self.layout.separator()
        #self.layout.prop(self, "my_enum")
        box = self.layout.box()
        for prop in self.my_collection:
            box.prop(prop, "checked", text=prop["name"])
        #box.prop(self, "my_collection")
        self.layout.prop(self, "disable_armatures")
 
    def invoke(self, context, event):
        self.my_collection.clear()
        for i in range(len(bpy.context.object.modifiers)):
            item = self.my_collection.add()
            item.name = bpy.context.object.modifiers[i].name
            item.checked = False
        return context.window_manager.invoke_props_dialog(self)


class WWMI_OpenIniTemplateEditor(bpy.types.Operator):
    """
    Open current custom template in internal or external editor.
    """
    bl_idname = "wwmi_tools.open_ini_template_editor"
    bl_label = "编辑模板"
    bl_description = "Open current custom template file in internal or external editor."

    def execute(self, context):
        cfg = context.scene.wwmi_tools_settings

        if cfg.custom_template_source == 'EXTERNAL':
            template_path = resolve_path(cfg.custom_template_path)
            if not template_path.is_file():
                raise ValueError(f'Custom ini template file not found: `{template_path}`!')
            subprocess.Popen([f'{str(template_path)}'], shell=True)
            return {'FINISHED'}

        text_name = "CustomIniTemplate"

        if text_name in bpy.data.texts:
            text = bpy.data.texts[text_name]
        else:
            text = bpy.data.texts.new(text_name)
        
        if not text.as_string().strip():
            text.clear()
            text.write(IniMaker.get_default_template(context, cfg, remove_code_comments=True))
            text.cursor_set(0)

        new_window = bpy.ops.wm.window_new()
        
        new_window_context = bpy.context.window_manager.windows[-1]

        # Switch the area to TEXT_EDITOR and assign the text
        for area in new_window_context.screen.areas:
            area.type = 'TEXT_EDITOR'
            text_area = area
            for space in area.spaces:
                if space.type == 'TEXT_EDITOR':
                    space.text = text

        # Toggle Tools sidebar
        if text_area:
            for region in text_area.regions:
                if region.type == 'UI':
                    bpy.ops.wm.context_toggle(data_path="space_data.show_region_ui")
                    break
        
        return {'FINISHED'}


class WWMI_IniTemplateEditor_ToggleLiveUpdates(bpy.types.Operator):
    bl_idname = "wwmi_tools.ini_template_start_live_updates"
    bl_label = "开始更新配置文件"
    bl_description = "Once started, WWMI Tools will run export with current settings and start writing mod.ini on each template edit.\n"
    "Warning! Mod export will be blocked until live updates are stopped!"

    def execute(self, context):
        cfg = context.scene.wwmi_tools_settings
        if cfg.custom_template_live_update:
            cfg.custom_template_live_update = False
        else:
            cfg.custom_template_live_update = True
            bpy.ops.wwmi_tools.export_mod()
        return {'FINISHED'}
    
    @classmethod
    def poll(cls, context):
        cfg = context.scene.wwmi_tools_settings
        return cfg.use_custom_template


class WWMI_IniTemplateEditor_Reset(bpy.types.Operator):
    bl_idname = "wwmi_tools.ini_template_editor_reset"
    bl_label = "Reset Template"
    bl_description = "Warning! This action will reset custom template to default!"

    def execute(self, context):
        cfg = context.scene.wwmi_tools_settings
        
        text_name = "CustomIniTemplate"

        if text_name in bpy.data.texts:
            text = bpy.data.texts[text_name]
        else:
            text = bpy.data.texts.new(text_name)
        
        text.clear()
        text.write(IniMaker.get_default_template(context, cfg, remove_code_comments=True))
        text.cursor_set(0)

        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    

class WWMI_PT_text_editor_buttons(bpy.types.Panel):
    bl_label = "WWMI Tools 中文版"
    bl_space_type = "TEXT_EDITOR"
    bl_region_type = "UI"
    bl_category = "Text"

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings
        
        if cfg.custom_template_live_update:
            layout.operator(WWMI_IniTemplateEditor_ToggleLiveUpdates.bl_idname, text="Stop Ini Updates")
        else:
            layout.operator(WWMI_IniTemplateEditor_ToggleLiveUpdates.bl_idname, text="Start Ini Updates")

        layout.operator(WWMI_IniTemplateEditor_Reset.bl_idname)


class UpdaterPanel(bpy.types.Panel):
    """Update Panel"""
    bl_label = "更新设置"
    bl_idname = "WWMI_TOOLS_PT_UpdaterPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = "objectmode"
    bl_category = "WWMI Tools"
    bl_order = 99
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Call to check for update in background.
        # Note: built-in checks ensure it runs at most once, and will run in
        # the background thread, not blocking or hanging blender.
        # Internally also checks to see if auto-check enabled and if the time
        # interval has passed.
        addon_updater_ops.check_for_update_background()
        col = layout.column()
        col.scale_y = 0.7
        # Could also use your own custom drawing based on shared variables.
        if addon_updater_ops.updater.update_ready:
            layout.label(text="There's a new update available!", icon="INFO")

        # Call built-in function with draw code/checks.
        addon_updater_ops.update_notice_box_ui(self, context)
        addon_updater_ops.update_settings_ui(self, context)


class DebugPanel(bpy.types.Panel):
    """Debug Panel"""
    bl_label = "调试设置"
    bl_idname = "WWMI_TOOLS_PT_DebugPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # bl_context = "objectmode"
    bl_category = "WWMI Tools"
    bl_order = 80
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        cfg = context.scene.wwmi_tools_settings

        layout.row().prop(cfg, 'remove_temp_object')
        layout.row().prop(cfg, 'export_on_reload')
        layout.row().prop(cfg, 'make_readme')