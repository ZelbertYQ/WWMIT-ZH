import bpy
import itertools

from ..blender_interface.objects import *


def remove_all_vertex_groups(context, obj):
    if obj is None:
        return
    if obj.type != 'MESH':
        return
    for x in obj.vertex_groups:
        obj.vertex_groups.remove(x)


def remove_unused_vertex_groups(context, obj):
    # take from: https://blenderartists.org/t/batch-delete-vertex-groups-script/449881/23#:~:text=10%20MONTHS%20LATER-,AdenFlorian,-Jun%202021
    
    with OpenObject(context, obj) as obj:

        vgroup_used = {i: False for i, k in enumerate(obj.vertex_groups)}

        for v in obj.data.vertices:
            for g in v.groups:
                if g.weight > 0.0:
                    vgroup_used[g.group] = True
        
        for i, used in sorted(vgroup_used.items(), reverse=True):
            if not used:
                obj.vertex_groups.remove(obj.vertex_groups[i])


def fill_gaps_in_vertex_groups(context, obj):
    # Author: SilentNightSound#7430

    # Can change this to another number in order to generate missing groups up to that number
    # e.g. setting this to 130 will create 0,1,2...130 even if the active selected object only has 90
    # Otherwise, it will use the largest found group number and generate everything up to that number
    largest = 0

    with OpenObject(context, obj) as obj:

        for vg in obj.vertex_groups:
            try:
                if int(vg.name.split(".")[0])>largest:
                    largest = int(vg.name.split(".")[0])
            except ValueError:
                print(f"Vertex group {vg.name} not named as integer, skipping")

        missing = set([f"{i}" for i in range(largest+1)]) - set([x.name.split(".")[0] for x in obj.vertex_groups])

        for number in missing:
            obj.vertex_groups.new(name=f"{number}")

        bpy.ops.object.vertex_group_sort()


def merge_vertex_groups(context, obj):
    # Author: SilentNightSound#7430

    # Combines vertex groups with the same prefix into one, a fast alternative to the Vertex Weight Mix that works for multiple groups
    # You will likely want to use blender_fill_vg_gaps.txt after this to fill in any gaps caused by merging groups together
    # Runs the merge on ALL vertex groups in the selected object(s)

    with OpenObject(context, obj) as obj:

        vg_names = [vg.name.split(".")[0] for vg in obj.vertex_groups]

        if not vg_names:
            raise ValueError('No vertex groups found, make sure that selected object has vertex groups!')

        for vg_name in vg_names:

            relevant = [x.name for x in obj.vertex_groups if x.name.split(".")[0] == f"{vg_name}"]

            if relevant:

                vgroup = obj.vertex_groups.new(name=f"x{vg_name}")
                    
                for vert_id, vert in enumerate(obj.data.vertices):
                    available_groups = [v_group_elem.group for v_group_elem in vert.groups]
                    
                    combined = 0
                    for v in relevant:
                        if obj.vertex_groups[v].index in available_groups:
                            combined += obj.vertex_groups[v].weight(vert_id)

                    if combined > 0:
                        vgroup.add([vert_id], combined ,'ADD')
                        
                for vg in [x for x in obj.vertex_groups if x.name.split(".")[0] == f"{vg_name}"]:
                    obj.vertex_groups.remove(vg)

                for vg in obj.vertex_groups:
                    if vg.name[0].lower() == "x":
                        vg.name = vg.name[1:]
                            
        bpy.ops.object.vertex_group_sort()
