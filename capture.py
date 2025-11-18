import bpy 
import random 
import math 
from block import check_overlap
import numpy as np
def spawn_robot(static_objects, retry_limit: 50):
    """Spawn robot (camera base) at random location
    
    Args:
        static_objects (list): list of objects to avoid collisions with
        retry_limit (int): number of attempts to find a valid spawn location
    """
    z = -0.07856 # hard coding here. not the best practice
    static_objects = [obj for obj in static_objects if obj != 'Robot']
    yr = (bpy.data.objects['Wall.025'].location.y,bpy.data.objects['Wall.026'].location.y)
    xr = (bpy.data.objects['Wall.029'].location.x,bpy.data.objects['Wall.024'].location.x)
    robot = bpy.data.objects['Robot']
    old_location = robot.location.copy()
    old_rotation = robot.rotation_euler.copy()
    static_objects = [obj for obj in bpy.data.objects if obj.name in static_objects]
    success = False 
    attempts = 0
    while not success and attempts < retry_limit:
        attempts += 1
        location = (random.uniform(xr[0], xr[1]), random.uniform(yr[0], yr[1]), z)
        robot.location = location
        robot.rotation_euler[2] = random.uniform(0, 2 * math.pi)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        bpy.context.view_layer.update()
        if any(check_overlap(robot, obj) for obj in static_objects):
            continue
        else:
            success = True
    if not success:
        # respawn at original location
        robot.location = old_location
        robot.rotation_euler = old_rotation
        print(f"Warning: Failed to spawn robot without collisions after {retry_limit} attempts. Respawning at original location.")
    bpy.context.view_layer.objects.active = robot
    robot.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    robot.select_set(False)
    bpy.context.view_layer.update()
    return {
        'location': tuple(robot.location),
        'rotation': tuple(robot.rotation_euler)
    }
    
def capture(scene, output_dir, compression_type):
    """
    Render all cameras in the scene (Front, Back, Left, Right)
    Args:
        scene: bpy.types.Scene
        output_dir: directory to save the rendered images
        compression_type: image compression type (e.g., 'png', 'jpg')
    """
    obj_hide = ['RedBlock', 'BlueBlock', 'Robot']
    for obj_name in obj_hide:
        obj = bpy.data.objects[obj_name]
        obj.hide_render = True
        obj.hide_viewport = True
    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
    # use a single "camera" to render, move it around. 
    # this increase loading time significantly 
    render_camera = cameras[0]
    scene.camera = render_camera
    original_transforms = [(cam.location.copy(), cam.rotation_euler.copy()) for cam in cameras]
    
    camera_transforms = []
    for i, cam in enumerate(cameras):
        render_camera.location = cam.location
        render_camera.rotation_euler = cam.rotation_euler
        cam_world_matrix = cam.matrix_world.normalized().inverted()
        vf = [np.array(vf_i).tolist() for vf_i in cam.data.view_frame(scene=scene)]
        camera_transforms.append({
            'name': cam.name,
            'extrinsic_matrix': np.array(cam_world_matrix).tolist(),
            'view_frame': vf
        })
        save_dir = f"{output_dir}/{cam.name}.{compression_type}"
        scene.render.filepath = save_dir
        bpy.ops.render.render(write_still=True)
    
    # restore original camera transforms
    for cam, (loc, rot) in zip(cameras, original_transforms):
        cam.location = loc
        cam.rotation_euler = rot
    
    # unhide objects
    for obj_name in obj_hide:
        obj = bpy.data.objects[obj_name]
        obj.hide_render = False
        obj.hide_viewport = False
    
    return camera_transforms