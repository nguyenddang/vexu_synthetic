import bpy 
import random
import math 
import mathutils
from utils import check_overlap, world_aabb, local_aabb

def spawn_block(colour, location, random_rotate=True, extra45=False):
    """
    Spawn block of a single colour at specified location.
    Optional random rotate + 45 degree z axis rotation
    
    Args:
        colour: 'BlueBlock' or 'RedBlock'
        location: (x, y, z) coordinates.
    """
    src = bpy.data.objects[colour]
    block_collection = bpy.data.collections["Block"]
    #spawn
    new_obj = src.copy()
    new_obj.data = src.data.copy() # copy data. avoid linked mesh data for better overlap checking
    new_obj.location = location
    block_collection.objects.link(new_obj) # add block to collection. for sanity sake
    #rotation
    if random_rotate:
        new_obj.rotation_euler = tuple(
            random.uniform(-0.1, 2 * math.pi) for _ in range(3)
        )
        # apply rotation
        bpy.context.view_layer.objects.active = new_obj
        new_obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        new_obj.select_set(False)
        if extra45:
            new_obj.rotation_euler.z += math.radians(45) # extra 45 degree rotation for center tubes
    bpy.context.view_layer.update()
    return new_obj

def spawn_ground(red_percentage: float, total_block: int, static_objects: list[str], retry_limit: int):
    """
    Spawn blocks on ground and lift them slightly above floor
    
    Args:
        red_percentage (float): percentage of red blocks [0, 1]
        total_block (int): total red + blue blocks to spawn on ground 
        static_objects (list[str]): names of object to not overlap with when spawning
        retry_limit: if overlap, how many times to retry
    """
    n_red = int(red_percentage * total_block)
    spawned_objects = []  
    all_objects = [obj for obj in bpy.data.objects if obj.name in static_objects]

    floor_obj = bpy.data.objects['Floor.015']
    floor_top_z = floor_obj.location.z + floor_obj.dimensions.z / 2

    yr = (bpy.data.objects['Wall.025'].location.y, bpy.data.objects['Wall.026'].location.y)
    xr = (bpy.data.objects['Wall.029'].location.x, bpy.data.objects['Wall.024'].location.x)

    for i in range(total_block):
        colour = "RedBlock" if i < n_red else "BlueBlock"
        success = False
        attempts = 0

        while not success and attempts < retry_limit: 
            attempts += 1
            location = (
                random.uniform(*xr),
                random.uniform(*yr),
                floor_top_z  # start at floor top
            )
            dummy_obj = spawn_block(colour, location, random_rotate=True)
            lift = dummy_obj.dimensions.z / 2
            dummy_obj.location.z += lift
            bpy.context.view_layer.update()

            if any(check_overlap(dummy_obj, obj) for obj in all_objects):
                mesh = getattr(dummy_obj, "data", None)
                bpy.data.objects.remove(dummy_obj, do_unlink=True)
                if mesh is not None and mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            else:
                spawned_objects.append(dummy_obj)
                all_objects.append(dummy_obj)
                success = True
        bpy.context.view_layer.update()
        if not success:
            print(f"Could not place {colour} after {retry_limit} attempts!")

    return spawned_objects, ['Ground'] * len(spawned_objects)

def spawn_loaders(red_percentage: list[float], total_blocks: list[int]):
    assert len(red_percentage) == len(total_blocks) == 4, "Only have 4 loaders"
    assert max(total_blocks) <= 6, "Loaders can only hold max 6 blocks"

    def world_z_min(obj):
        return min((obj.matrix_world @ v.co).z for v in obj.data.vertices)

    all_spawned = []
    classes = []
    epsilon = 0.03
    x_eps = 0.0095
    y_eps = 0.0105

    # loader XY positions
    xys = [
        (obj.location.x,
         obj.location.y + epsilon if obj.location.y < 0 else obj.location.y - epsilon)
        for obj in bpy.data.objects if obj.name.startswith('Loader.')
    ]

    # floor top (world Z)
    floor_obj = bpy.data.objects['Floor.015']
    floor_top_z = max((floor_obj.matrix_world @ v.co).z for v in floor_obj.data.vertices)

    z = bpy.data.objects['RedBlock'].location.z

    for idx, (rp, tb) in enumerate(zip(red_percentage, total_blocks)):
        block_spawned = []

        # Spawn stack
        for i in range(tb):
            colour = "RedBlock" if random.random() < rp else "BlueBlock"
            location = (
                xys[idx][0] + random.uniform(-1, 1) * x_eps,
                xys[idx][1] + random.uniform(-1, 1) * y_eps,
                z
            )
            dummy_obj = spawn_block(colour, location)

            if i != 0:
                prev_top = block_spawned[-1].dimensions.z / 2 + block_spawned[-1].location.z
                curr_height = dummy_obj.dimensions.z / 2
                dummy_obj.location.z = prev_top + curr_height

            block_spawned.append(dummy_obj)
        if block_spawned:
            bottom = block_spawned[0]
            bottom_min_z = world_z_min(bottom)

            if bottom_min_z < floor_top_z:
                lift = floor_top_z - bottom_min_z
                for obj in block_spawned:
                    obj.location.z += lift

        # bookkeeping
        classes.extend([f'Loader_{idx}'] * len(block_spawned))
        all_spawned.extend(block_spawned)

    return all_spawned, classes

def spawn_lg(red_percentage: list[float], total_blocks: list[int]):
    """
    Spawn blocks in long goals
    
    Args:
        red_percentage (float): percentage of red blocks [0, 1]
        total_block (int): total red + blue blocks to spawn on ground 
    """
    assert len(red_percentage) == len(total_blocks) == 2, "Only have 2 long goals"
    assert max(total_blocks) <= 15, "Long goals can only hold 15 blocks"
    epsilon_z = 0.035
    epsilon_x = 0.001
    all_spawned = []
    classes = []
    bounds = [world_aabb(obj) for obj in bpy.data.objects if obj.name.startswith('LongGoal.')]
    xs = [obj.location.x + epsilon_x if obj.location.x < 0 else obj.location.x - epsilon_x for obj in bpy.data.objects if obj.name.startswith('LongGoal.')]
    z = bpy.data.objects['LongGoal.001'].location.z + epsilon_z
    for idx, (rp, tb) in enumerate(zip(red_percentage, total_blocks)):
        min_y, max_y = bounds[idx][0][1], bounds[idx][1][1]
        tube_spawned = []

        # Spawn evenly first
        for i in range(tb):
            colour = "RedBlock" if random.random() < rp else "BlueBlock"
            # evenly spaced from min_y to max_y including edges
            y_pos = min_y + i * (max_y - min_y) / (tb - 1) if tb > 1 else (min_y + max_y) / 2
            location = (xs[idx], y_pos, z)
            dummy_obj = spawn_block(colour, location)
            tube_spawned.append(dummy_obj)
        for i, obj in enumerate(tube_spawned):
            # Space in front (toward max_y)
            if i < tb - 1:
                front_space = (tube_spawned[i + 1].location.y - tube_spawned[i + 1].dimensions.y / 2
                            - (obj.location.y + obj.dimensions.y / 2))
            else:
                front_space = 0

            # compute space behind (toward lower y)
            if i > 0:
                back_space = (obj.location.y - obj.dimensions.y / 2
                            - (tube_spawned[i - 1].location.y + tube_spawned[i - 1].dimensions.y / 2))
            else:
                back_space = 0

            
            if i == 0:
                move_dist = front_space * random.uniform(0, 1)
            elif i == len(tube_spawned) - 1:
                move_dist = -back_space * random.uniform(0, 1)
            else:
                direction = random.choice([-1, 1])
                if direction == 1:
                    move_dist = front_space * random.uniform(0, 1)
                elif direction == -1:
                    move_dist = -back_space * random.uniform(0, 1)

            obj.location.y += move_dist
        classes.extend([f'LongGoal_{idx}'] * len(tube_spawned))
        all_spawned.extend(tube_spawned)
    bpy.context.view_layer.update()
    return all_spawned, classes 

def spawn_cg(red_percentage: list[float], total_blocks: list[int]):
    """
    Spawn blocks in center goal
    
    Args:
        red_percentage (float): percentage of red blocks [0, 1]
        total_block (int): total red + blue blocks to spawn on ground     
    """
    assert len(red_percentage) == len(total_blocks) == 2, 'Only 2 center goals'
    assert max(total_blocks) <= 7, 'Center goals can hold max 7 blocks'
    upper_epsilon = 0.027
    lower_epsilon = -0.002    
    all_spawned = []
    classes = []
    cgs = [obj for obj in bpy.data.objects if obj.name.endswith('CenterGoal')]
    for idx, (rp, tb) in enumerate(zip(red_percentage, total_blocks)):
        tube = cgs[idx]
        bounds = local_aabb(tube)
        y_min, y_max = bounds[0][1], bounds[1][1]
        z = cgs[idx].location.z + upper_epsilon if tube.name.startswith('Upper') else cgs[idx].location.z + lower_epsilon
        block_spawned = []
        x_rand = 0 if tube.name == "UpperCenterGoal" else random.uniform(-0.0062, 0.0053)
        for i in range(tb):
            colour = "RedBlock" if random.random() < rp else "BlueBlock"
            y_local = y_min + i * (y_max - y_min) / (tb - 1) if tb > 1 else (y_min + y_max)/2
            local_vec = mathutils.Vector((x_rand, y_local, 0))
            world_vec = tube.matrix_world @ local_vec
            world_loc = (world_vec.x, world_vec.y, z)
            dummy_obj = spawn_block(colour, world_loc, random_rotate=True, extra45=True)
            block_spawned.append(dummy_obj)

        local_positions = [tube.matrix_world.inverted() @ obj.location for obj in block_spawned]

        for i, obj in enumerate(block_spawned):
            local_pos = local_positions[i]
            local_dim_y = obj.dimensions.y / tube.matrix_world.to_scale().y  
            if i < tb - 1:
                next_local = local_positions[i + 1]
                front_space = next_local.y - local_dim_y/2 - (local_pos.y + local_dim_y/2)
            else:
                front_space = 0
            if i > 0:
                prev_local = local_positions[i - 1]
                back_space = (local_pos.y - local_dim_y/2) - (prev_local.y + local_dim_y/2)
            else:
                back_space = 0
            direction = random.choice([-1, 1])
            if direction == 1:
                move_dist = front_space * random.uniform(0, 1)
            else:
                move_dist = -back_space * random.uniform(0, 1)

            local_pos.y += move_dist
            obj.location = tube.matrix_world @ local_pos
            local_positions[i] = local_pos

        classes.extend([f'CenterGoal_{idx}'] * len(block_spawned))
        all_spawned.extend(block_spawned)
    for obj in all_spawned:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.select_set(False)
    return all_spawned, classes


            