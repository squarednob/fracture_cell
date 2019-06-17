# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Cell Fracture",
    "author": "ideasman42, phymec, Sergey Sharybin", "Nobuyuki Hirakata"
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Transform tab",
    "description": "Fractured Object, Bomb, Projectile, Recorder",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Object/CellFracture",
    "category": "Object"}


if "bpy" in locals():
    import importlib
    importlib.reload(fracture_cell_setup)

else:
    from . import fracture_cell_setup

import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        IntProperty,
        FloatProperty,
        FloatVectorProperty,
        EnumProperty,
        BoolVectorProperty,
        )

from bpy.types import (
        Operator,
        Panel,
        )


def main_object(context, obj, level, **kw):
    import random

    # pull out some args
    kw_copy = kw.copy()
    use_recenter = kw_copy.pop("use_recenter")
    use_remove_original = kw_copy.pop("use_remove_original")
    recursion = kw_copy.pop("recursion")
    recursion_source_limit = kw_copy.pop("recursion_source_limit")
    recursion_clamp = kw_copy.pop("recursion_clamp")
    recursion_chance = kw_copy.pop("recursion_chance")
    recursion_chance_select = kw_copy.pop("recursion_chance_select")
    use_island_split = kw_copy.pop("use_island_split")
    use_debug_bool = kw_copy.pop("use_debug_bool")
    use_interior_vgroup = kw_copy.pop("use_interior_vgroup")
    use_sharp_edges = kw_copy.pop("use_sharp_edges")
    use_sharp_edges_apply = kw_copy.pop("use_sharp_edges_apply")

    collection = context.collection
    scene = context.scene

    if level != 0:
        kw_copy["source_limit"] = recursion_source_limit

    from . import fracture_cell_setup

    # not essential but selection is visual distraction.
    obj.select_set(False)

    if kw_copy["use_debug_redraw"]:
        obj_display_type_prev = obj.display_type
        obj.display_type = 'WIRE'

    objects = fracture_cell_setup.cell_fracture_objects(context, obj, **kw_copy)
    assert objects, "Can't make any fracture object."
    objects = fracture_cell_setup.cell_fracture_boolean(context, obj, objects,
                                                        use_island_split=use_island_split,
                                                        use_interior_hide=(use_interior_vgroup or use_sharp_edges),
                                                        use_debug_bool=use_debug_bool,
                                                        use_debug_redraw=kw_copy["use_debug_redraw"],
                                                        level=level,
                                                        )

    # must apply after boolean.
    if use_recenter:
        bpy.ops.object.origin_set({"selected_editable_objects": objects},
                                  type='ORIGIN_GEOMETRY', center='MEDIAN')
                                  
    #--------------
    # Recursion.
    if level == 0:
        for level_sub in range(1, recursion + 1):

            objects_recurse_input = [(i, o) for i, o in enumerate(objects)]
            if recursion_chance != 1.0:
                from mathutils import Vector
                if recursion_chance_select == 'RANDOM':
                    random.shuffle(objects_recurse_input)
                elif recursion_chance_select in {'SIZE_MIN', 'SIZE_MAX'}:
                    objects_recurse_input.sort(key=lambda ob_pair:
                        (Vector(ob_pair[1].bound_box[0]) -
                         Vector(ob_pair[1].bound_box[6])).length_squared)
                    if recursion_chance_select == 'SIZE_MAX':
                        objects_recurse_input.reverse()
                elif recursion_chance_select in {'CURSOR_MIN', 'CURSOR_MAX'}:
                    c = scene.cursor.location.copy()
                    objects_recurse_input.sort(key=lambda ob_pair:
                        (ob_pair[1].location - c).length_squared)
                    if recursion_chance_select == 'CURSOR_MAX':
                        objects_recurse_input.reverse()
            
                objects_recurse_input[int(recursion_chance * len(objects_recurse_input)):] = []
                objects_recurse_input.sort()
            
            # reverse index values so we can remove from original list.
            objects_recurse_input.reverse()

            objects_recursive = []
            for i, obj_cell in objects_recurse_input:
                assert(objects[i] is obj_cell)
                # Repeat main_object() here.
                objects_recursive += main_object(context, obj_cell, level_sub, **kw)
                if use_remove_original:
                    collection.objects.unlink(obj_cell)
                    del objects[i]
                if recursion_clamp and len(objects) + len(objects_recursive) >= recursion_clamp:
                    break
            objects.extend(objects_recursive)

            if recursion_clamp and len(objects) > recursion_clamp:
                break
    
    #--------------
    # Level Options
    if level == 0:
        # import pdb; pdb.set_trace()
        if use_interior_vgroup or use_sharp_edges:
            fracture_cell_setup.cell_fracture_interior_handle(objects,
                                                              use_interior_vgroup=use_interior_vgroup,
                                                              use_sharp_edges=use_sharp_edges,
                                                              use_sharp_edges_apply=use_sharp_edges_apply,
                                                              )

    if kw_copy["use_debug_redraw"]:
        obj.display_type = obj_display_type_prev

    # testing only!
    # obj.hide = True
    return objects

            
def main(context, **kw):
    '''
    import time
    t = time.time()
    '''
    objects_context = context.selected_editable_objects    

    kw_copy = kw.copy()
    
    # collection
    use_collection = kw_copy.pop("use_collection")
    new_collection = kw_copy.pop("new_collection")
    collection_name = kw_copy.pop("collection_name")
    
    # mass
    use_mass = kw_copy.pop("use_mass")
    mass_name = kw_copy.pop("mass_name")
    mass_mode = kw_copy.pop("mass_mode")
    mass = kw_copy.pop("mass")

    objects = []
    for obj in objects_context:
        if obj.type == 'MESH':
            objects += main_object(context, obj, 0, **kw_copy)
        else:
            assert obj.type == 'MESH', "No MESH object selected."

    bpy.ops.object.select_all(action='DESELECT')
    for obj_cell in objects:
        obj_cell.select_set(True)

    fracture_cell_setup.cell_fracture_post_process(objects,
                                  use_collection=use_collection,
                                  new_collection=new_collection,
                                  collection_name=collection_name,
                                  use_mass=use_mass,
                                  mass=mass,
                                  mass_mode=mass_mode,
                                  mass_name=mass_name,
                                  )          
    
    #print("Done! %d objects in %.4f sec" % (len(objects), time.time() - t))
    print("Done!")

class FRACTURE_OT_Cell(Operator):
    bl_idname = "object.add_fracture_cell_objects"
    bl_label = "Cell fracture selected mesh objects"
    bl_options = {'PRESET'}

    # -------------------------------------------------------------------------
    # Source Options
    source_vert_own: IntProperty(
            name="Own Verts",
            description="Use own vertices",
            min=0, max=2000,
            default=100,
            )
    source_vert_child: IntProperty(
            name="Child Verts",
            description="Use child object vertices",
            min=0, max=2000,
            default=0,
            )
    source_particle_own: IntProperty(
            name="Own Particles",
            description="All particle systems of the source object",
            min=0, max=2000,
            default=0,
            )
    source_particle_child: IntProperty(
            name="Child Particles",
            description="All particle systems of the child objects",
            min=0, max=2000,
            default=0,
            )
    source_pencil: IntProperty(
            name="Annotation Pencil",
            description="Annotation Grease Pencil",
            min=0, max=2000,
            default=0,
            )
    source_random: IntProperty(
            name="Random",
            description="Random seed position",
            min=0, max=2000,
            default=0,
            )
    '''        
    source_limit: IntProperty(
            name="Source Limit",
            description="Limit the number of input points, 0 for unlimited",
            min=0, max=5000,
            default=100,
            )
    '''
    
    # -------------------------------------------------------------------------
    # Transform 
    source_noise: FloatProperty(
            name="Noise",
            description="Randomize point distribution",
            min=0.0, max=1.0,
            default=0.0,
            )
    margin: FloatProperty(
            name="Margin",
            description="Gaps for the fracture (gives more stable physics)",
            min=0.0, max=1.0,
            default=0.001,
            )
    cell_scale: FloatVectorProperty(
            name="Scale",
            description="Scale Cell Shape",
            size=3,
            min=0.0, max=1.0,
            default=(1.0, 1.0, 1.0),
            )
    use_recenter: BoolProperty(
            name="Recenter",
            description="Recalculate the center points after splitting",
            default=True,
            )
    use_island_split: BoolProperty(
            name="Split Islands",
            description="Split disconnected meshes",
            default=True,
            )

    # -------------------------------------------------------------------------
    # Recursion
    recursion: IntProperty(
            name="Recursion",
            description="Break shards recursively",
            min=0, max=2000,
            default=0,
            )
    recursion_source_limit: IntProperty(
            name="Fracture Each",
            description="Limit the number of input points, 0 for unlimited (applies to recursion only)",
            min=2, max=2000, # Oviously, dividing in more than two objects is needed, to avoid no fracture object. 
            default=8,
            )
    recursion_clamp: IntProperty(
            name="Max Fracture",
            description="Finish recursion when this number of objects is reached (prevents recursing for extended periods of time), zero disables",
            min=0, max=10000,
            default=250,
            )
    recursion_chance: FloatProperty(
            name="Recursion Chance",
            description="Likelihood of recursion",
            min=0.0, max=1.0,
            default=1.00,
            )
    recursion_chance_select: EnumProperty(
            name="Target",
            items=(('RANDOM', "Random", ""),
                   ('SIZE_MIN', "Small", "Recursively subdivide smaller objects"),
                   ('SIZE_MAX', "Big", "Recursively subdivide bigger objects"),
                   ('CURSOR_MIN', "Cursor Close", "Recursively subdivide objects closer to the cursor"),
                   ('CURSOR_MAX', "Cursor Far", "Recursively subdivide objects farther from the cursor"),
                   ),
            default='SIZE_MIN',
            )

    # -------------------------------------------------------------------------
    # Interior Meshes Options
    use_smooth_faces: BoolProperty(
            name="Smooth Faces",
            description="Smooth Faces of inner side.",
            default=False,
            )
    use_sharp_edges: BoolProperty(
            name="Sharp Edges",
            description="Set sharp edges when disabled",
            default=True,
            )
    use_sharp_edges_apply: BoolProperty(
            name="Apply Split Edge",
            description="Split sharp hard edges",
            default=True,
            )
    use_data_match: BoolProperty(
            name="Copy Original Data",
            description="Match original mesh materials and data layers",
            default=True,
            )
    material_index: IntProperty(
            name="Interior Material Slot",
            description="Material index for interior faces",
            default=0,
            )
    use_interior_vgroup: BoolProperty(
            name="Vertex Group",
            description="Create a vertex group for interior verts",
            default=False,
            )

    # -------------------------------------------------------------------------
    # Scene Options    
    use_collection: BoolProperty(
            name="Use Collection",
            description="Use collection to organize fracture objects",
            default=True,
            )
    
    new_collection: BoolProperty(
            name="New Collection",
            description="Make new collection for fracture objects",
            default=True,
            ) 
    
    collection_name: StringProperty(
            name="Name",
            description="Collection name.",
            default="Fracture",
            )


    use_remove_original: BoolProperty(
            name="Remove Original",
            description="Removes the parents used to create the shatter",
            default=True,
            )
    
    # -------------------------------------------------------------------------
    # Physics Options
    
    use_mass: BoolProperty(
        name="Mass",
        description="Append mass data on custom properties of cell objects.",
        default=False,
        )
    
    mass_name: StringProperty(
        name="Property Name",
        description="Name for custome properties.",
        default="mass",
        )

    mass_mode: EnumProperty(
            name="Mass Mode",
            items=(('VOLUME', "Volume", "Objects get part of specified mass based on their volume"),
                   ('UNIFORM', "Uniform", "All objects get the specified mass"),
                   ),
            default='VOLUME',
            )

    mass: FloatProperty(
            name="Mass Factor",
            description="Mass to give created objects",
            min=0.001, max=1000.0,
            default=1.0,
            )

    # -------------------------------------------------------------------------
    # Debug
    use_debug_points: BoolProperty(
            name="Debug Points",
            description="Create mesh data showing the points used for fracture",
            default=False,
            )

    use_debug_redraw: BoolProperty(
            name="Show Progress Realtime",
            description="Redraw as fracture is done",
            default=False,
            )

    use_debug_bool: BoolProperty(
            name="Debug Boolean",
            description="Skip applying the boolean modifier",
            default=False,
            )

    def execute(self, context):
        keywords = self.as_keywords()  # ignore=("blah",)
        main(context, **keywords)
        return {'FINISHED'}

    def invoke(self, context, event):
        #print(self.recursion_chance_select)
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=600)

    def draw(self, context):       
        layout = self.layout
        box = layout.box()
        col = box.column()
        col.label(text="Fracture From")
        rowsub = col.row()
        #rowsub.prop(self, "source")
        rowsub.prop(self, "source_vert_own")
        rowsub.prop(self, "source_particle_own")
        rowsub.prop(self, "source_random")
        rowsub = col.row()
        rowsub.prop(self, "source_vert_child")
        rowsub.prop(self, "source_particle_child")
        rowsub.prop(self, "source_pencil")
        
        box = layout.box()
        col = box.column()
        col.label(text="Transform")
        rowsub = col.row()
        rowsub.prop(self, "source_noise")
        rowsub.prop(self, "margin")
        rowsub = col.row(align=True)
        #rowsub.alignment = 'RIGHT'
        
        rowsub.prop(self, "cell_scale")
        rowsub.prop(self, "use_recenter")
        # could be own section, control how we subdiv
        rowsub.prop(self, "use_island_split")

        box = layout.box()
        col = box.column()
        col.label(text="Recursive Shatter")
        #rowsub = col.row(align=True)
        rowsub = col.row(align=True)
        rowsub.alignment = 'LEFT'
        rowsub.prop(self, "recursion")
        rowsub = col.row(align=True)
        rowsub.alignment = 'LEFT'
        if self.recursion > 0:
            rowsub.enabled = True
        else:
            rowsub.enabled = False
        rowsub.prop(self, "recursion_source_limit")
        rowsub.prop(self, "recursion_clamp")
        rowsub.prop(self, "recursion_chance")      
        rowsub.prop(self, "recursion_chance_select") #, expand=True)

        box = layout.box()
        col = box.column()
        col.label(text="Interior Meshes")
        rowsub = col.row()
        rowsub.alignment = 'LEFT'
        rowsub.prop(self, "use_data_match")       
        rowsub.prop(self, "use_sharp_edges")
        rowsub.prop(self, "use_sharp_edges_apply")
        rowsub.prop(self, "use_smooth_faces")
        rowsub.prop(self, "use_interior_vgroup") 
                
        rowsub = col.row()
        if self.use_data_match == True:
            rowsub.enabled = True
        else:
            rowsub.enabled = False
        rowsub.alignment = 'LEFT'
        # on same row for even layout but infact are not all that related       
        rowsub.prop(self, "material_index")

        box = layout.box()
        col = box.column()
        col.label(text="Custom Properties")
        rowsub = col.row(align=True)
        rowsub.prop(self, "use_mass")
        if self.use_mass:
            rowsub = col.row(align=True)
            rowsub.prop(self, "mass_name")
            rowsub = col.row(align=True)
            rowsub.prop(self, "mass_mode")
            rowsub.prop(self, "mass")
 
        box = layout.box()
        col = box.column()
        col.label(text="Scene Management")
        rowsub = col.row(align=True)
        rowsub.prop(self, "use_collection")
        if self.use_collection:
            rowsub.prop(self, "new_collection")
            rowsub.prop(self, "collection_name")
        

                
        box = layout.box()
        col = box.column()
        col.label(text="Debug")
        rowsub = col.row(align=True)
        rowsub.prop(self, "use_debug_redraw")
        rowsub.prop(self, "use_debug_points")
        rowsub.prop(self, "use_debug_bool")


# Menu settings
class FRACTURE_PT_Cell(Panel):
    bl_idname = 'FRACTURE_PT_Cell'
    bl_label = "Fracture Cell"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Transform"
    bl_context = 'objectmode'
    bl_options = {"DEFAULT_CLOSED"}
    
    def draw(self, context):
        # Show pop-upped menu when the button is hit.
        layout = self.layout
        layout.label(text="Cell Fracture:")
        layout.operator("object.add_fracture_cell_objects",
                    text="Cell Fracture")

'''
def menu_func(self, context):
    layout = self.layout
    layout.label(text="Cell Fracture:")
    layout.operator("object.add_fracture_cell_objects",
                    text="Cell Fracture")
'''

classes = (
    FRACTURE_OT_Cell,
    FRACTURE_PT_Cell,
    )

def register():

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    #bpy.types.Scene.cra = PointerProperty(type=CrackItProperties)
    
    
def unregister():

    #del bpy.types.Scene.crackit
    
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    


'''
def register():
    bpy.utils.register_class(FractureCell)
    bpy.types.VIEW3D_PT_tools_object.append(menu_func)


def unregister():
    bpy.utils.unregister_class(FractureCell)
    bpy.types.VIEW3D_PT_tools_object.remove(menu_func)


if __name__ == "__main__":
    register()

'''