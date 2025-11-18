import bpy 
import random
import math 
import mathutils
import gc 

def cleanup_render_images():
    """Remove render result images that accumulate in memory"""
    for img in list(bpy.data.images):
        if img.name in ['Render Result', 'Viewer Node']:
            bpy.data.images.remove(img)
            
def cleanup_orphaned_data():
    """More thorough cleanup of orphaned data blocks"""
    # multiple passes to catch dependencies
    for _ in range(3):
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for mat in list(bpy.data.materials):
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        for img in list(bpy.data.images):
            if img.users == 0 and img.name not in ['Render Result', 'Viewer Node']:
                bpy.data.images.remove(img)
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    
    # Force garbage collection
    gc.collect()
    
def world_aabb(obj): 
    """
    Convert local bounding box of obj to world axis-aligned bounding box 
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    bpy.context.view_layer.update()  # ensure transforms are fresh
    bb = [eval_obj.matrix_world @ mathutils.Vector(c) for c in eval_obj.bound_box]
    xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

def get_aabb(obj):
    """Return min and max world coordinates of an axis-aligned object."""
    bb_world = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    xs = [v.x for v in bb_world]
    ys = [v.y for v in bb_world]
    zs = [v.z for v in bb_world]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))

def check_overlap(obj_a, obj_b):
    (ax_min, ax_max), (ay_min, ay_max), (az_min, az_max) = get_aabb(obj_a)
    (bx_min, bx_max), (by_min, by_max), (bz_min, bz_max) = get_aabb(obj_b)
    return (
        ax_min <= bx_max and ax_max >= bx_min and
        ay_min <= by_max and ay_max >= by_min and
        az_min <= bz_max and az_max >= bz_min
    )

def local_aabb(obj):
    bb_local = [mathutils.Vector(corner) for corner in obj.bound_box]
    xs = [v.x for v in bb_local]; ys = [v.y for v in bb_local]; zs = [v.z for v in bb_local]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

def clear_all_blocks():
    """
    Delete all spawned blocks and remove their mesh datablocks.
    """
    to_delete = [
        obj for obj in bpy.data.objects
        if (obj.name.startswith("BlueBlock") or obj.name.startswith("RedBlock"))
        and obj.name not in ['BlueBlock', 'RedBlock']
    ]
    for obj in to_delete:
        # store the mesh before deleting the object
        mesh = getattr(obj, "data", None)
        # remove the object from the scene and Blender data
        bpy.data.objects.remove(obj, do_unlink=True)
        # if the mesh has no other users, remove it too
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)

def clear_lights():
    """
    Delete all lights
    """
    lights = bpy.data.collections['Lights']
    for obj in list(lights.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
        
def generate_random_field(n_blocks=(68, 74)):
    """
    Generate a randomized field stats
    
    Args:
        n_blocks (tuple): min, max number of total blocks to spawn
    """
    
    total_blocks = random.randint(*n_blocks)
    target_red_blocks = total_blocks // 2  # Target ~50% red blocks
    loaders_counts = [random.randint(0, 6) for _ in range(4)]
    long_counts = [random.randint(0, 15) for _ in range(2)]
    center_counts = [random.randint(0, 7) for _ in range(2)]
    goal_counts = sum(loaders_counts) + sum(long_counts) + sum(center_counts)
    ground_counts = total_blocks - goal_counts    
    all_c = loaders_counts + long_counts + center_counts + [ground_counts]
    
    # allocation 
    red_allocations = []
    remaining_red = target_red_blocks
    for i, c in enumerate(all_c):
        if c == 0:
            red_allocations.append(0)
        elif i == len(all_c) - 1: # last one, take all remaining
            red_allocations.append(min(remaining_red, c))
        else:
            red_count = random.randint(0, min(remaining_red, c))
            red_allocations.append(red_count)
            remaining_red -= red_count
            
    red_percentages = [r / c if c > 0 else 0 for r, c in zip(red_allocations, all_c)]
    lp = red_percentages[:4]
    lgp = red_percentages[4:6]
    cgp = red_percentages[6:8]
    gp = red_percentages[8]
    actual_red = sum(red_allocations)
    return {
        "loaders": {
            "red_percentage": lp,
            "total_blocks": loaders_counts
        },
        "long": {
            "red_percentage": lgp,
            "total_blocks": long_counts
        },
        "center": {
            "red_percentage": cgp,
            "total_blocks": center_counts
        },
        "ground": {
            "red_percentage": gp,
            "total_blocks": ground_counts
        },
        "actual_red": actual_red,
        "total": total_blocks
    }
    
def spawn_lights(n_lights=6, radius=1.7, height=8, energy_range=(50,200), colour_jitter=0.8):
    """
    Spawn random light rig in dome formation above the field
    """
    for i in range(n_lights):
        # math stuff: dome calculation
        theta = random.uniform(0, 2 * math.pi)
        phi = random.uniform(0, math.pi/2)
        r = random.uniform(0.3, 1.0) * radius
        x = r * math.cos(theta) * math.sin(phi)
        y = r * math.sin(theta) * math.sin(phi)
        z = height * math.cos(phi)
        # init
        light_type = random.choice(['POINT', 'AREA'])
        light_data = bpy.data.lights.new(f"Light_{i}", type=light_type)
        light_obj = bpy.data.objects.new(f"Light_{i}", light_data)
        #link to collection
        bpy.data.collections["Lights"].objects.link(light_obj)
        # create
        light_obj.location = (x, y, z)
        light_data.energy = random.uniform(*energy_range)
        hue_shift = random.uniform(-colour_jitter, colour_jitter)
        light_data.color = (
            1.0 - abs(hue_shift) * random.random(),
            1.0 - abs(hue_shift) * random.random(),
            1.0
            )
        light_data.use_temperature = True
        light_data.temperature = random.uniform(3000, 7000)
        
        if light_type == "AREA":
            light_data.shape = random.choice(['SQUARE', 'RECTANGLE', 'DISK', 'ELLIPSE'])
            light_data.size = random.uniform(0.5, 2.0)
            if light_data.shape == 'RECTANGLE':
                light_data.size_y = random.uniform(0.5, 2.0)
            direction = (x, y, z)  # vector from light to origin
            light_obj.rotation_mode = 'XYZ'
            light_obj.rotation_euler = (
                math.atan2(direction[1], direction[2] + 1e-6) + random.uniform(-0.1, 0.1),
                -math.atan2(direction[0], direction[2] + 1e-6) + random.uniform(-0.1, 0.1),
                random.uniform(-math.pi, math.pi)
            )

def new_world(path, new_hdri=True):
    """
    Set up the world HDRI.
    
    Args:
        path (str): Path to HDRI image.
        new_hdri (bool): If True, load a new HDRI; if False, just rotate existing one.
    """
    world = bpy.context.scene.world
    node_tree = world.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    # Try to get existing nodes
    env = nodes.get("Environment Texture")
    mapping = nodes.get("Mapping")
    
    if new_hdri or env is None:
        # Clear and recreate nodes
        nodes.clear()
        tex_coord = nodes.new(type='ShaderNodeTexCoord')
        mapping = nodes.new(type='ShaderNodeMapping')
        env = nodes.new(type='ShaderNodeTexEnvironment')
        background = nodes.new(type='ShaderNodeBackground')
        output = nodes.new(type='ShaderNodeOutputWorld')

        env.name = "Environment Texture"
        mapping.name = "Mapping"

        # Load HDRI
        env.image = bpy.data.images.load(path, check_existing=True)

        # Link nodes
        links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], env.inputs['Vector'])
        links.new(env.outputs['Color'], background.inputs['Color'])
        links.new(background.outputs['Background'], output.inputs['Surface'])

    # Always rotate mapping node randomly
    mapping.inputs['Rotation'].default_value = (
        random.uniform(0, 2 * math.pi),  # X rotation
        random.uniform(0, 2 * math.pi),  # Y rotation
        random.uniform(0, 2 * math.pi)   # Z rotation
    )

    if new_hdri:
        print(f"[World] Loaded new HDRI: {path} with random rotation (XYZ)")
    else:
        print(f"[World] Rotated existing HDRI randomly (XYZ)")