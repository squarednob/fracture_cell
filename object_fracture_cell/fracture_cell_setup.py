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

# <pep8 compliant>

# Script copyright (C) Blender Foundation 2012

import bpy
import bmesh


def _redraw_yasiamevil():
    _redraw_yasiamevil.opr(**_redraw_yasiamevil.arg)
_redraw_yasiamevil.opr = bpy.ops.wm.redraw_timer
_redraw_yasiamevil.arg = dict(type='DRAW_WIN_SWAP', iterations=1)

def _limit_source(points, source_limit):
    if source_limit != 0 and source_limit < len(points):
        import random
        random.shuffle(points)
        points[source_limit:] = []
        return points
    else:
        return points

def _points_from_object(obj, verts,
                        source_vert_own,
                        source_vert_child,
                        source_particle_own,
                        source_particle_child,
                        source_pencil,
                        source_random):
    
    '''
    _source_all = {
        'PARTICLE_OWN', 'PARTICLE_CHILD',
        'PENCIL',
        'VERT_OWN', 'VERT_CHILD',
        }
    
    print(source - _source_all)
    print(source)
    assert(len(source | _source_all) == len(_source_all))
    assert(len(source))
    '''
    
    points = []
    
    def edge_center(mesh, edge):
        v1, v2 = edge.vertices
        return (mesh.vertices[v1].co + mesh.vertices[v2].co) / 2.0

    def poly_center(mesh, poly):
        from mathutils import Vector
        co = Vector()
        tot = 0
        for i in poly.loop_indices:
            co += mesh.vertices[mesh.loops[i].vertex_index].co
            tot += 1
        return co / tot

    def points_from_verts(obj):
        """Takes points from _any_ object with geometry"""
        if obj.type == 'MESH':
            mesh = obj.data
            matrix = obj.matrix_world.copy()    
            p = [(matrix @ v.co, 'VERTS') for v in mesh.vertices]
            
            return p
        else:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            ob_eval = obj.evaluated_get(depsgraph)
            try:
                mesh = ob_eval.to_mesh()
            except:
                mesh = None

            if mesh is not None:               
                matrix = obj.matrix_world.copy()
                p =  [(matrix @ v.co, 'VERTS') for v in mesh.vertices]
                
                ob_eval.to_mesh_clear()
                return p

    def points_from_particles(obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        
        #points.extend([p.location.copy()
        #               for psys in obj_eval.particle_systems
        #               for p in psys.particles])                
        p = [(particle.location.copy(), 'PARTICLE')
               for psys in obj_eval.particle_systems
               for particle in psys.particles]
        return p
    
    def points_from_random(obj, verts):
        xa = [v[0] for v in verts]
        ya = [v[1] for v in verts]
        za = [v[2] for v in verts]
        xmin, xmax = min(xa), max(xa)
        ymin, ymax = min(ya), max(ya)
        zmin, zmax = min(za), max(za)

        from random import uniform
        from mathutils import Vector
        
        p = []
        for i in range(source_random):
            new_pos = Vector( (uniform(xmin, xmax), uniform(ymin, ymax), uniform(zmin, zmax)) )
            p.append((new_pos, 'RANDOM'))
  
        return p  
    
     # geom own
    if source_vert_own > 0:
        new_points = points_from_verts(obj)
        new_points = _limit_source(new_points, source_vert_own)
        points.extend(new_points)
    
    # geom random
    if source_random > 0:
        new_points = points_from_random(obj, verts)
        points.extend(new_points)


    # geom children
    if source_vert_child > 0:
        for obj_child in obj.children:
            new_points  = points_from_verts(obj_child, verts)
            new_points = _limit_source(new_points, source_vert_child)
            points.extend(new_points)
    
    # geom particles
    if source_particle_own > 0:
        new_points = points_from_particles(obj)
        new_points = _limit_source(new_points, source_particle_own)
        points.extend(new_points)

    if source_particle_child > 0:
        for obj_child in obj.children:
            new_points = points_from_particles(obj_child)
            new_points = _limit_source(new_points, source_particle_child)
            points.extend(new_points)

    # grease pencil
    def get_points(stroke):
        return [point.co.copy() for point in stroke.points]

    def get_splines(gp):
        gpl = gp.layers.active
        if gpl:
            fr = gpl.active_frame
            if not fr:
                current = bpy.context.scene.frame_current
                gpl.frames.new(current)
                gpl.active_frame = current
                fr = gpl.active_frame
            
            return [get_points(stroke) for stroke in fr.strokes]
        
        else:
            return []

    if source_pencil > 0:   
        gp = bpy.context.scene.grease_pencil
        
        if gp:
            line_points = [(p, 'PENCIL') for spline in get_splines(gp)
                             for p in spline]
            line_points = _limit_source(line_points, source_pencil)

        # Make New point between the line point and the closest point.
        if not points:
            points.extend(line_points)
            
        else:
            for lp in line_points:
                # Make vector between the line point and its closest point.
                points.sort(key=lambda p: (p[0] - lp[0]).length_squared)
                closest_point = points[0]           
                normal = lp[0].xyz - closest_point[0].xyz
                           
                new_point = (lp[0], lp[1])
                new_point[0].xyz +=  normal / 2
               
                points.append(new_point)
    
    #print("Found %d points" % len(points))
    return points


def cell_fracture_objects(context, obj,
                          # Source From
                          source_vert_own=100,
                          source_vert_child=0,
                          source_particle_own=0,
                          source_particle_child=0,
                          source_pencil=0,
                          source_random=0,
                          source_limit=0,
                          source_noise=0.0,
                          clean=True,
                          # operator options
                          use_smooth_faces=False,
                          use_data_match=False,
                          use_debug_points=False,
                          margin=0.0,
                          material_index=0,
                          use_debug_redraw=False,
                          cell_scale=(1.0, 1.0, 1.0),
                          ):

    from . import fracture_cell_calc
    collection = context.collection
    view_layer = context.view_layer
    
    mesh = obj.data
    matrix = obj.matrix_world.copy()
    verts = [matrix @ v.co for v in mesh.vertices]
    
    # -------------------------------------------------------------------------
    # GET POINTS
    points = _points_from_object(obj, verts,
                                source_vert_own,
                                source_vert_child,
                                source_particle_own,
                                source_particle_child,
                                source_pencil,
                                source_random
                                )
    
    '''
    if not points:
        # print using fallback
        #points = _points_from_object(obj, {'VERT_OWN'})
        _points_from_object(obj, source_vert_own, 0,0,0,0)
    '''

    if not points:
        assert points, "No points found"
        #print("no points found")
        #return []
        #return 

    
    '''
    # apply optional clamp
    if source_limit != 0 and source_limit < len(points):
        import random
        random.shuffle(points)
        points[source_limit:] = []
    '''

    
    # saddly we cant be sure there are no doubles
    from mathutils import Vector
    to_tuple = Vector.to_tuple
    
    # To remove doubles, round the values.    
    #points = list({to_tuple(p, 4): p for p in points}.values())
    points = [(Vector(to_tuple(p[0], 4)),p[1]) for p in points]
    del to_tuple
    del Vector

    if source_noise > 0.0:
        from random import random
        # boundbox approx of overall scale
        from mathutils import Vector
        matrix = obj.matrix_world.copy()
        bb_world = [matrix @ Vector(v) for v in obj.bound_box]
        scalar = source_noise * ((bb_world[0] - bb_world[6]).length / 2.0)

        from mathutils.noise import random_unit_vector

        points[:] = [(p[0] + (random_unit_vector() * (scalar * random())), p[1]) for p in points]

    if use_debug_points:
        bm = bmesh.new()
        for p in points:
            bm.verts.new(p[0])
        mesh_tmp = bpy.data.meshes.new(name="DebugPoints")
        bm.to_mesh(mesh_tmp)
        bm.free()
        obj_tmp = bpy.data.objects.new(name=mesh_tmp.name, object_data=mesh_tmp)
        collection.objects.link(obj_tmp)
        del obj_tmp, mesh_tmp

    '''
    mesh = obj.data
    matrix = obj.matrix_world.copy()
    verts = [matrix @ v.co for v in mesh.vertices]
    '''

    cells = fracture_cell_calc.points_as_bmesh_cells(verts,
                                                     points,
                                                     cell_scale,
                                                     margin_cell=margin)

    # some hacks here :S
    cell_name = obj.name + "_cell"

    objects = []
    for center_point, cell_points in cells:
        # ---------------------------------------------------------------------
        # BMESH

        # create the convex hulls
        bm = bmesh.new()
        
        #この段階でセルの各点にランダム性を加えるより、前の点計算の段階でやったほうがいいのでは？　bm.verts.new(co)以外は。
        # WORKAROUND FOR CONVEX HULL BUG/LIMIT
        # XXX small noise
        import random
        def R():
            return (random.random() - 0.5) * 0.001
        # XXX small noise

        for i, co in enumerate(cell_points):

            # XXX small noise
            co.x += R()
            co.y += R()
            co.z += R()
            # XXX small noise

            bm_vert = bm.verts.new(co)

        import mathutils
        #　この重複削除の距離は、調節したいな。ただし、これより前の計算段階でできそうだが。
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)
        try:
            # Making cell meshes as convex full here!
            bmesh.ops.convex_hull(bm, input=bm.verts)
        except RuntimeError:
            import traceback
            traceback.print_exc()

        if clean:
            bm.normal_update()
            try:
                bmesh.ops.dissolve_limit(bm, verts=bm.verts, angle_limit=0.001)
            except RuntimeError:
                import traceback
                traceback.print_exc()
        # smooth faces will remain only inner faces, after appling boolean modifier.
        if use_smooth_faces:
            for bm_face in bm.faces:
                bm_face.smooth = True

        if material_index != 0:
            for bm_face in bm.faces:
                bm_face.material_index = material_index


        # ---------------------------------------------------------------------
        # MESH
        mesh_dst = bpy.data.meshes.new(name=cell_name)

        bm.to_mesh(mesh_dst)
        bm.free()
        del bm

        if use_data_match:
            # match materials and data layers so boolean displays them
            # currently only materials + data layers, could do others...
            mesh_src = obj.data
            for mat in mesh_src.materials:
                mesh_dst.materials.append(mat)
            #for lay_attr in ("vertex_colors", "uv_textures"):
            for lay_attr in ("vertex_colors", "uv_layers"):
                lay_src = getattr(mesh_src, lay_attr)
                lay_dst = getattr(mesh_dst, lay_attr)
                for key in lay_src.keys():
                    lay_dst.new(name=key)

        # ---------------------------------------------------------------------
        # OBJECT

        obj_cell = bpy.data.objects.new(name=cell_name, object_data=mesh_dst)
        collection.objects.link(obj_cell)
        # scene.objects.active = obj_cell
        obj_cell.location = center_point

        objects.append(obj_cell)

        # support for object materials
        if use_data_match:
            for i in range(len(mesh_dst.materials)):
                slot_src = obj.material_slots[i]
                slot_dst = obj_cell.material_slots[i]

                slot_dst.link = slot_src.link
                slot_dst.material = slot_src.material

        if use_debug_redraw:
            view_layer.update()
            _redraw_yasiamevil()

    view_layer.update()

    # move this elsewhere...
    # Blender 2.8: BGE integration was disabled, --
    # -- because BGE was deleted in Blender 2.8. 
    '''
    for obj_cell in objects:
        game = obj_cell.game
        game.physics_type = 'RIGID_BODY'
        game.use_collision_bounds = True
        game.collision_bounds_type = 'CONVEX_HULL'
    '''
    return objects


def cell_fracture_boolean(context, obj, objects,
                          use_debug_bool=False,
                          clean=True,
                          use_island_split=False,
                          use_interior_hide=False,
                          use_debug_redraw=False,
                          level=0,
                          remove_doubles=True
                          ):

    objects_boolean = []
    collection = context.collection
    scene = context.scene
    view_layer = context.view_layer
    #depsgraph = context.evaluated_depsgraph_get()

    if use_interior_hide and level == 0:
        # only set for level 0
        obj.data.polygons.foreach_set("hide", [False] * len(obj.data.polygons))  
    
    
    for obj_cell in objects:
        mod = obj_cell.modifiers.new(name="Boolean", type='BOOLEAN')
        mod.object = obj
        mod.operation = 'INTERSECT'
        
        

        if not use_debug_bool:
            if use_interior_hide:
                obj_cell.data.polygons.foreach_set("hide", [True] * len(obj_cell.data.polygons))
            
            # mesh_old should be made before appling boolean modifier.
            mesh_old = obj_cell.data
                       
            bpy.context.view_layer.objects.active = obj_cell
            bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Boolean")
            
            
            # depsgraph sould be gotten after applign boolean modifier, for new_mesh.
            depsgraph = context.evaluated_depsgraph_get()
            obj_cell_eval = obj_cell.evaluated_get(depsgraph)
            
            mesh_new = bpy.data.meshes.new_from_object(obj_cell_eval,)            
            obj_cell.data = mesh_new
            
            '''
            check_hide = [11] * len(obj_cell.data.polygons)
            obj_cell.data.polygons.foreach_get("hide", check_hide)
            print(check_hide) 
            '''
            
            # remove if not valid
            if not mesh_old.users:
                bpy.data.meshes.remove(mesh_old)
            if not mesh_new.vertices:
                collection.objects.unlink(obj_cell)
                if not obj_cell.users:
                    bpy.data.objects.remove(obj_cell)
                    obj_cell = None
                    if not mesh_new.users:
                        bpy.data.meshes.remove(mesh_new)
                        mesh_new = None

            # avoid unneeded bmesh re-conversion
            if mesh_new is not None:
                bm = None

                if clean:
                    if bm is None:  # ok this will always be true for now...
                        bm = bmesh.new()
                        bm.from_mesh(mesh_new)
                    bm.normal_update()
                    try:
                        bmesh.ops.dissolve_limit(bm, verts=bm.verts, edges=bm.edges, angle_limit=0.001)
                    except RuntimeError:
                        import traceback
                        traceback.print_exc()

                if remove_doubles:
                    if bm is None:
                        bm = bmesh.new()
                        bm.from_mesh(mesh_new)
                    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.005)

                if bm is not None:
                    bm.to_mesh(mesh_new)
                    bm.free()

            del mesh_new
            del mesh_old

        if obj_cell is not None:
            objects_boolean.append(obj_cell)

            if use_debug_redraw:
                _redraw_yasiamevil()
    
    if (not use_debug_bool) and use_island_split:
        # this is ugly and Im not proud of this - campbell
        for ob in view_layer.objects:
            ob.select_set(False)
        for obj_cell in objects_boolean:
            obj_cell.select_set(True)
        
        # If new separated meshes are made, selected objects is increased.
        bpy.ops.mesh.separate(type='LOOSE')
        objects_boolean[:] = [obj_cell for obj_cell in scene.objects if obj_cell.select_get()]
     
    context.view_layer.update()
    
    return objects_boolean


def cell_fracture_interior_handle(objects,
                                  use_interior_vgroup=False,
                                  use_sharp_edges=False,
                                  use_sharp_edges_apply=False,
                                  ):
    """Run after doing _all_ booleans"""

    assert(use_interior_vgroup or use_sharp_edges or use_sharp_edges_apply)

    for obj_cell in objects:
        mesh = obj_cell.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        if use_interior_vgroup:
            for bm_vert in bm.verts:
                bm_vert.tag = True
            for bm_face in bm.faces:
                if not bm_face.hide:
                    for bm_vert in bm_face.verts:
                        bm_vert.tag = False

            # now add all vgroups
            defvert_lay = bm.verts.layers.deform.verify()
            for bm_vert in bm.verts:
                if bm_vert.tag:
                    bm_vert[defvert_lay][0] = 1.0

            # add a vgroup
            obj_cell.vertex_groups.new(name="Interior")

        if use_sharp_edges:
            bpy.context.space_data.overlay.show_edge_sharp = True
            #mesh.show_edge_sharp = True
            for bm_edge in bm.edges:
                if len({bm_face.hide for bm_face in bm_edge.link_faces}) == 2:
                    bm_edge.smooth = False

            if use_sharp_edges_apply:
                edges = [edge for edge in bm.edges if edge.smooth is False]
                if edges:
                    bm.normal_update()
                    bmesh.ops.split_edges(bm, edges=edges)

        for bm_face in bm.faces:
            bm_face.hide = False

        bm.to_mesh(mesh)
        bm.free()

def cell_fracture_post_process(objects,
                                  use_collection=False,
                                  new_collection=False,
                                  collection_name="Fracture",
                                  use_mass=False,
                                  mass=1.0,
                                  mass_mode='VOLUME', mass_name='mass',
                                  ):
    """Run after Interiro handle"""
    #--------------
    # Collection Options   
    if use_collection:
        colle = None            
        if not new_collection:
            colle = bpy.data.collections.get(collection_name)

        if colle is None:
            colle = bpy.data.collections.new(collection_name)
        
        # THe collection should be children of master collection to show in outliner.
        child_names = [m.name for m in bpy.context.scene.collection.children]
        if colle.name not in child_names:
            bpy.context.scene.collection.children.link(colle)
            
        # Cell objects are only link to the collection.
        bpy.ops.collection.objects_remove_all() # For all selected object.
        for colle_obj in objects:           
            colle.objects.link(colle_obj)

    #--------------
    # Mass Options     
    if use_mass:
        # Blender 2.8:  Mass for BGE was no more available.--
        # -- Instead, Mass values is used for custom properies on cell objects.
        if mass_mode == 'UNIFORM':
            for obj_cell in objects:
                #obj_cell.game.mass = mass
                obj_cell[mass_name] = mass
        elif mass_mode == 'VOLUME':
            from mathutils import Vector
            def _get_volume(obj_cell):
                def _getObjectBBMinMax():
                    min_co = Vector((1000000.0, 1000000.0, 1000000.0))
                    max_co = -min_co
                    matrix = obj_cell.matrix_world
                    for i in range(0, 8):
                        bb_vec = obj_cell.matrix_world @ Vector(obj_cell.bound_box[i])
                        min_co[0] = min(bb_vec[0], min_co[0])
                        min_co[1] = min(bb_vec[1], min_co[1])
                        min_co[2] = min(bb_vec[2], min_co[2])
                        max_co[0] = max(bb_vec[0], max_co[0])
                        max_co[1] = max(bb_vec[1], max_co[1])
                        max_co[2] = max(bb_vec[2], max_co[2])
                    return (min_co, max_co)

                def _getObjectVolume():
                    min_co, max_co = _getObjectBBMinMax()
                    x = max_co[0] - min_co[0]
                    y = max_co[1] - min_co[1]
                    z = max_co[2] - min_co[2]
                    volume = x * y * z
                    return volume

                return _getObjectVolume()


            obj_volume_ls = [_get_volume(obj_cell) for obj_cell in objects]
            obj_volume_tot = sum(obj_volume_ls)
            if obj_volume_tot > 0.0:
                mass_fac = mass / obj_volume_tot
                for i, obj_cell in enumerate(objects):
                    #obj_cell.game.mass = obj_volume_ls[i] * mass_fac
                    obj_cell[mass_name] = obj_volume_ls[i] * mass_fac
        else:
            assert(0)    