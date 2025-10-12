import bpy 
import random
import math 
import mathutils
import gc 
from colorsys import rgb_to_hsv, hsv_to_rgb

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

def get_obb(obj):
    """
    Return center, axes (unit vectors), and half-sizes of a Blender object as OBB.
    """
    bb_world = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    
    # compute center
    center = sum(bb_world, mathutils.Vector()) / 8.0
    scale = obj.matrix_world.to_scale()
    rot = obj.matrix_world.to_3x3()
    axes = [
        (rot @ mathutils.Vector((1,0,0))).normalized(),
        (rot @ mathutils.Vector((0,1,0))).normalized(),
        (rot @ mathutils.Vector((0,0,1))).normalized()
    ]

    # half-sizes along each local axis
    local_bb = [mathutils.Vector(c) for c in obj.bound_box]
    half_sizes = [
        (max(v[i] for v in local_bb) - min(v[i] for v in local_bb)) / 2.0
        for i in range(3)
    ]

    return center, axes, half_sizes

def check_overlap(obj_a, obj_b):
    """
    Check if two objects overlap using full 3D SAT (OBB).
    """
    C1, A1, H1 = get_obb(obj_a)
    C2, A2, H2 = get_obb(obj_b)

    R = [[A1[i].dot(A2[j]) for j in range(3)] for i in range(3)]
    absR = [[abs(R[i][j]) + 1e-8 for j in range(3)] for i in range(3)]  # epsilon
    t_vec = C2 - C1
    t = [t_vec.dot(A1[i]) for i in range(3)]
    for i in range(3):
        ra = H1[i]
        rb = H2[0]*absR[i][0] + H2[1]*absR[i][1] + H2[2]*absR[i][2]
        if abs(t[i]) > ra + rb:
            return False

    for i in range(3):
        ra = H1[0]*absR[0][i] + H1[1]*absR[1][i] + H1[2]*absR[2][i]
        rb = H2[i]
        proj = t[0]*R[0][i] + t[1]*R[1][i] + t[2]*R[2][i]
        if abs(proj) > ra + rb:
            return False

    for i in range(3):
        for j in range(3):
            ra = H1[(i+1)%3]*absR[(i+2)%3][j] + H1[(i+2)%3]*absR[(i+1)%3][j]
            rb = H2[(j+1)%3]*absR[i][(j+2)%3] + H2[(j+2)%3]*absR[i][(j+1)%3]
            val = abs(t[(i+2)%3]*R[(i+1)%3][j] - t[(i+1)%3]*R[(i+2)%3][j])
            if val > ra + rb:
                return False

    return True

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
    gp = red_percentages[8:]
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
            "total_blocks": [ground_counts]
        },
        "actual_red": actual_red,
        "total": total_blocks
    }
    
def spawn_lights(n_lights=6, radius=3.4, height=1.5, energy_range=(10,100), colour_jitter=0.5):    
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

def new_world(path):
    world = bpy.context.scene.world
    node_tree = world.node_tree
    nodes = node_tree.nodes 
    env_node = nodes.get("Environment Texture")
    img = bpy.data.images.load(path, check_existing=True)
    #replace hdri
    env_node.image = img
    # random rotationz
    mapping_node = nodes.get("Mapping")
    if mapping_node:
        mapping_node.inputs['Rotation'].default_value[0] = random.uniform(0, 2*math.pi)  # X tilt
        mapping_node.inputs['Rotation'].default_value[1] = random.uniform(0, 2*math.pi)  # Y tilt
        mapping_node.inputs['Rotation'].default_value[2] = random.uniform(0, 2*math.pi)  # Z rotation
    # random noise texture
    noise_node = nodes.get("Noise Texture")
    if noise_node:
        noise_node.inputs['Scale'].default_value = random.uniform(2, 8)
        noise_node.inputs['Detail'].default_value = random.uniform(2, 6)
        noise_node.inputs['Roughness'].default_value = random.uniform(0.4, 0.8)
        noise_node.inputs['W'].default_value = random.random() * 10
     # random colour ramp
    color_ramp = nodes.get("ColorRamp")
    if color_ramp:
        for elem in color_ramp.color_ramp.elements:
            r, g, b = elem.color[:3]
            h, s, v = rgb_to_hsv(r, g, b)
            h += random.uniform(-0.03, 0.03)
            s += random.uniform(-0.05, 0.05)
            v += random.uniform(-0.05, 0.05)
            elem.color = (*hsv_to_rgb(h, s, v), 1)

    # ramdom hsv
    hsv_node = nodes.get("Hue Saturation Value")
    if hsv_node:
        hsv_node.inputs['Hue'].default_value = 1 + random.uniform(-0.03, 0.03)
        hsv_node.inputs['Saturation'].default_value = 1 + random.uniform(-0.1, 0.1)
        hsv_node.inputs['Value'].default_value = 1 + random.uniform(-0.05, 0.05)