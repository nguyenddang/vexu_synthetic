import bpy 
import random 
import math 
from block import check_overlap
def spawn_robot(static_objects, retry_limit: 50):
    """Spawn robot (camera base) at random location
    
    Args:
        static_objects (list): list of objects to avoid collisions with
        retry_limit (int): number of attempts to find a valid spawn location
    """
    z = -0.102071 # hard coding here. not the best practice
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
    cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
    robot = bpy.data.objects['Robot']
    # use a single "camera" to render, move it around. 
    # this increase loading time significantly 
    render_camera = cameras[0]
    scene.camera = render_camera
    original_transforms = [(cam.location.copy(), cam.rotation_euler.copy()) for cam in cameras]
    
    camera_transforms = []
    for i, cam in enumerate(cameras):
        render_camera.location = cam.location
        render_camera.rotation_euler = cam.rotation_euler
        cam_world_matrix = robot.matrix_world @ cam.matrix_local
        camera_transforms.append({
            'name': cam.name,
            'location': tuple(cam_world_matrix.to_translation()),
            'rotation': tuple(cam_world_matrix.to_euler())
        })
        save_dir = f"{output_dir}/{cam.name}.{compression_type}"
        scene.render.filepath = save_dir
        bpy.ops.render.render(write_still=True)
    
    # restore original camera transforms
    for cam, (loc, rot) in zip(cameras, original_transforms):
        cam.location = loc
        cam.rotation_euler = rot
    
    return camera_transforms