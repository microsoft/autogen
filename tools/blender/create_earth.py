# Blender script: create_earth.py
# Usage (Windows):
# "F:\\Blender 5.1\\blender.exe" --background --python create_earth.py

import bpy
import os

# --- User-editable settings ---
TEXTURE_PATH = r"C:\\path\\to\\earth_color.jpg"   # change or leave empty to use procedural color
EXPORT_GLB = r"%s\\exports\\earth.glb" % os.path.dirname(__file__)

# --- Helper: clear scene ---
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

# --- Create planet ---
def create_planet(radius=1.0, segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=(0,0,0))
    planet = bpy.context.active_object
    planet.name = "Planet"
    bpy.ops.object.shade_smooth()

    # material
    mat = bpy.data.materials.new(name="Earth_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    texcoord = nodes.new(type='ShaderNodeTexCoord')
    image_node = nodes.new(type='ShaderNodeTexImage')
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')

    links.new(texcoord.outputs['UV'], image_node.inputs['Vector'])
    links.new(image_node.outputs['Color'], principled.inputs['Base Color'])
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    # load texture if present
    if TEXTURE_PATH and os.path.exists(TEXTURE_PATH):
        try:
            img = bpy.data.images.load(TEXTURE_PATH)
            image_node.image = img
            print('Loaded texture:', TEXTURE_PATH)
        except Exception as e:
            print('Failed to load texture:', e)
            principled.inputs['Base Color'].default_value = (0.15,0.4,0.7,1)
    else:
        # fallback simple color
        principled.inputs['Base Color'].default_value = (0.15,0.4,0.7,1)

    planet.data.materials.append(mat)
    return planet

# --- Create atmosphere as a slightly larger transparent sphere ---
def create_atmosphere(radius=1.02, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius, location=(0,0,0))
    atm = bpy.context.active_object
    atm.name = 'Atmosphere'
    bpy.ops.object.shade_smooth()

    atm_mat = bpy.data.materials.new(name='Atmosphere_Mat')
    atm_mat.use_nodes = True
    atm_mat.blend_method = 'BLEND'
    nodes = atm_mat.node_tree.nodes
    links = atm_mat.node_tree.links
    nodes.clear()

    principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    output = nodes.new(type='ShaderNodeOutputMaterial')
    principled.inputs['Base Color'].default_value = (0.4,0.6,1.0,1)
    principled.inputs['Alpha'].default_value = 0.06
    # Emission input omitted for compatibility with this Blender version
    principled.inputs['Roughness'].default_value = 1.0

    links.new(principled.outputs['BSDF'], output.inputs['Surface'])

    atm.data.materials.append(atm_mat)

    # invert normals so transparency looks correct from outside (optional)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()
    bpy.ops.object.mode_set(mode='OBJECT')
    return atm

# --- Export GLB ---
def export_glb(filepath):
    dirp = os.path.dirname(filepath)
    if not os.path.exists(dirp):
        os.makedirs(dirp, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=filepath, export_format='GLB', export_materials='EXPORT')
    print('Exported GLB to', filepath)


if __name__ == '__main__':
    clear_scene()
    planet = create_planet(radius=1.0)
    atm = create_atmosphere(radius=1.02)

    # optional: add a simple sun light and camera
    bpy.ops.object.light_add(type='SUN', location=(5,5,5))
    bpy.ops.object.camera_add(location=(0,-4,1.2), rotation=(1.2,0,0))

    # export
    export_path = os.path.abspath(EXPORT_GLB)
    export_glb(export_path)

    print('Done.\nRun Blender with:')
    print('"F:\\Blender 5.1\\blender.exe" --background --python', os.path.basename(__file__))
