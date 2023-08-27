
# Author: Lovro Bosnar
# Date: 27.08.2023.

# Blender: 3.6.1.


import bpy
import mathutils
import bmesh
import numpy as np

# Interpolate [a,b] using factor t.
def lerp(t, a, b):
    return (1.0 - t) * a + t * b

def create_collection_if_not_exists(collection_name):
    if collection_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(new_collection) #Creates a new collection

def add_object_to_collection(base_object, collection_name="collection"):
    create_collection_if_not_exists(collection_name)
    bpy.data.collections[collection_name].objects.link(base_object)

def copy_obj(obj, collection_name):
    obj_cpy = obj.copy()
    obj_cpy.data = obj.data.copy()
    obj_cpy.animation_data_clear()
    if collection_name == None:
        bpy.context.collection.objects.link(obj_cpy)
    else:
        add_object_to_collection(obj_cpy, collection_name)
    return obj_cpy

def animate_curve_growth(curve, frame_start, frame_end, growth_factor_start, growth_factor_end):
    # Set starting.
    curve.data.bevel_factor_end = growth_factor_start
    curve.data.bevel_factor_start = growth_factor_start
    curve.data.keyframe_insert(data_path="bevel_factor_start", frame=frame_start)
    curve.data.keyframe_insert(data_path="bevel_factor_end", frame=frame_start)
    # Set end.
    curve.data.bevel_factor_end = growth_factor_end
    curve.data.keyframe_insert(data_path="bevel_factor_end", frame=frame_end)

def animate_curve_thickness(curve, frame_start, frame_end, thickness_min, thickness_max, start_thickness=0.0):
    curve.data.bevel_depth = start_thickness
    curve.data.keyframe_insert(data_path="bevel_depth", frame=frame_start)
    curve.data.bevel_depth = lerp(mathutils.noise.random(), thickness_min, thickness_max)
    curve.data.keyframe_insert(data_path="bevel_depth", frame=frame_end)

# https://behreajj.medium.com/scripting-curves-in-blender-with-python-c487097efd13
def set_animation_fcurve(base_object, option='BOUNCE'):
    fcurves = base_object.data.animation_data.action.fcurves
    for fcurve in fcurves:
        for kf in fcurve.keyframe_points:
            # Options: ['CONSTANT', 'LINEAR', 'BEZIER', 'SINE',
            # 'QUAD', 'CUBIC', 'QUART', 'QUINT', 'EXPO', 'CIRC',
            # 'BACK', 'BOUNCE', 'ELASTIC']
            kf.interpolation = option
            # Options: ['AUTO', 'EASE_IN', 'EASE_OUT', 'EASE_IN_OUT']
            kf.easing = 'EASE_OUT'

def create_material(mat_id, mat_type, color=mathutils.Color((1.0, 0.5, 0.1)), emission_intensity=1, glossy_roughness=0.1):

    mat = bpy.data.materials.get(mat_id)

    if mat is None:
        mat = bpy.data.materials.new(name=mat_id)

    mat.use_nodes = True

    if mat.node_tree:
        mat.node_tree.links.clear()
        mat.node_tree.nodes.clear()

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    output = nodes.new(type='ShaderNodeOutputMaterial')

    if mat_type == "diffuse":
        shader = nodes.new(type='ShaderNodeBsdfDiffuse')
        nodes["Diffuse BSDF"].inputs[0].default_value = color[:] + (1.0,)

    elif mat_type == "emission":
        shader = nodes.new(type='ShaderNodeEmission')
        nodes["Emission"].inputs[0].default_value = color[:] + (1.0,)
        nodes["Emission"].inputs[1].default_value = emission_intensity

    elif mat_type == "glossy":
        shader = nodes.new(type='ShaderNodeBsdfGlossy')
        nodes["Glossy BSDF"].inputs[0].default_value = color[:] + (1.0,)
        nodes["Glossy BSDF"].inputs[1].default_value = glossy_roughness

    links.new(shader.outputs[0], output.inputs[0])

    return mat

# Based on: https://blog.federicopepe.com/en/2020/05/create-random-palettes-of-colors-that-will-go-well-together/
def generate_5_random_colors_that_fit():
    hue = int(mathutils.noise.random() * 360.0) # Random between [0,360]
    hue_op = int(mathutils.noise.random() * 180.0) # Random between [0,180]
    hues = [
        hue,
        hue - hue_op,
        hue + hue_op,
        hue - 2 * hue_op,
        hue + 2 * hue_op]
    rand_cols = []
    for i in range (5):
        col = mathutils.Color()
        col.hsv = (hues[i]/360.0, mathutils.noise.random(), mathutils.noise.random())
        rand_cols.append(col)
    return rand_cols

def grow_from_thicker_to_thinner(curve, n_instances, n_frames):

    growth_delta = 1.0 / n_instances
    curr_start_growth = 0.0
    curr_end_growth = 1.0
    curr_thickness = 0.1
    thickness_delta = 0.3

    rand_5_colors = generate_5_random_colors_that_fit()

    for instance_i in range(n_instances):

        curve_cpy = copy_obj(curve, "curve_cpy_thicker_to_thinner_collection")

        # Animate growth.
        animate_curve_growth(curve_cpy, frame_start=0, frame_end=n_frames, growth_factor_start=curr_start_growth, growth_factor_end=curr_end_growth)
        set_animation_fcurve(curve_cpy, option="CUBIC")
        curr_end_growth -= growth_delta

        # Animate thickening.
        curve_cpy.data.bevel_depth = curr_thickness
        curve_cpy.data.keyframe_insert(data_path="bevel_depth", frame=0)
        curr_thickness += thickness_delta

        # Add material.     
        mat = create_material(curve_cpy.name+"_mat", "diffuse", color=rand_5_colors[instance_i % 2]   , emission_intensity=1, glossy_roughness=0.1)
        curve_cpy.data.materials.append(mat)

def grow_from_thinner_to_thicker(curve, n_instances, n_frames):

    curr_frame = 0
    delta_frame = n_frames / n_instances
    growth_delta = 1.0 / n_instances
    curr_start_growth = 0.0
    curr_thickness = 0.1
    thickness_delta = 0.3

    rand_5_colors = generate_5_random_colors_that_fit()

    for instance_i in range(n_instances):

        curve_cpy = copy_obj(curve, "curve_cpy_thinner_to_thicker_collection")

        # Animate growth.
        animate_curve_growth(curve_cpy, frame_start=curr_frame, frame_end=curr_frame+delta_frame, growth_factor_start=curr_start_growth, growth_factor_end=curr_start_growth+growth_delta)
        set_animation_fcurve(curve_cpy, option="LINEAR")
        curr_start_growth += growth_delta
        curr_frame += delta_frame

        # Animate thickening.
        curve_cpy.data.bevel_depth = curr_thickness
        curve_cpy.data.keyframe_insert(data_path="bevel_depth", frame=0)
        curr_thickness += thickness_delta

        # Add material.     
        mat = create_material(curve_cpy.name+"_mat", "diffuse", color=rand_5_colors[instance_i % 2]   , emission_intensity=1, glossy_roughness=0.1)
        curve_cpy.data.materials.append(mat)


def main():

    # Parameters.
    n_instances = 10
    n_frames = 300

    for curve in bpy.data.collections["start_thicker_to_thinner_collection"].all_objects:
        grow_from_thicker_to_thinner(curve, n_instances, n_frames)

    for curve in bpy.data.collections["start_thinner_to_thicker_collection"].all_objects:
        grow_from_thinner_to_thicker(curve, n_instances, n_frames)

        

#
# Script entry point.
#
if __name__ == "__main__":
    main()