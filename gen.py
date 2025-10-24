import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

import bpy 
from utils import (clear_all_blocks, 
                   clear_lights, 
                   cleanup_orphaned_data, 
                   generate_random_field, 
                   spawn_lights, new_world, 
                   cleanup_render_images)
from block import spawn_ground, spawn_loaders, spawn_lg, spawn_cg
from capture import spawn_robot, capture
import argparse
import json 
import random 

import time 
start_time = time.time()
parser = argparse.ArgumentParser()
parser.add_argument('--gpu', type=int, default=0, help='GPU id to use')
parser.add_argument('--n_capture', type=int, default=5, help='Number of captures per scene (robot locations)')
parser.add_argument('--n_scene', type=int, default=10, help='Number of scenes to generate')
parser.add_argument('--cycles-device', required=False, help='Place holder for cycles device')
argv = []
if "--" in sys.argv:
    argv = sys.argv[sys.argv.index("--") + 1:]  # get all args after "--"
else:
    argv = sys.argv[1:]
args = parser.parse_args(argv)
staticg_objects = [
    'LongLeg.001',
    'LongLeg.002',
    'LongLeg.003',
    'LongLeg.004',
    'CenterLeg.001',
    'CenterLeg.002',
    'LowerCenterGoal',
    'Loader.001',
    'Loader.002',
    'Loader.003',
    'Loader.004',
    'GroundGoalBlue.001',
    'GroundGoalBlue.002',
    'GroundGoalBlue.003',
    'GroundGoalBlue.004',
    'GroundGoalBlue.005',
    'GroundGoalRed.001',
    'GroundGoalRed.002',
    'GroundGoalRed.003',
    'GroundGoalRed.004',
    'GroundGoalRed.005',
    'LongSupportBar.002',
    'LongSupportBar.001'
    
] + ['Wall.{:03d}'.format(i) for i in range(1, 45)] # objects to avoid collisions with when spawning
def new_scene():
    """
    Generate a new random scene and return metadata for saving
    """
    clear_all_blocks()
    cleanup_orphaned_data()
    field_config = generate_random_field()
    # spawn blocks on field
    gb, gbc = spawn_ground(field_config['ground']['red_percentage'], field_config['ground']['total_blocks'], staticg_objects, 50)
    lb, lbc = spawn_loaders(field_config['loaders']['red_percentage'], field_config['loaders']['total_blocks'])
    lg, lgc = spawn_lg(field_config['long']['red_percentage'], field_config['long']['total_blocks'])
    cg, cgc = spawn_cg(field_config['center']['red_percentage'], field_config['center']['total_blocks'])

    # metadata 
    all_blocks = gb + lb + lg + cg
    all_classes = gbc + lbc + lgc + cgc
    assert len(all_blocks) == len(all_classes)
    block_positions = []
    for idx, obj in enumerate(all_blocks):
        block_positions.append({
            "location": tuple(obj.location),
            "rotation": tuple(obj.rotation_euler),
            "colour": "red" if "RedBlock" in obj.name else "blue",
            "class": all_classes[idx]
        })
    meta_data  = {
        "blocks": block_positions,
        "field_config": field_config,
        "total_blocks": len(all_blocks)
    }
    return meta_data, all_blocks

# init stuff 
# set camera clip start and end
for cam in [obj for obj in bpy.data.objects if obj.type == 'CAMERA']:
    cam.data.clip_start = 0.01
    cam.data.clip_end = 1000 
# render settings
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128
scene.render.image_settings.file_format = 'JPEG'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.cycles.denoising_use_gpu = True
scene.render.use_persistent_data = True
scene.cycles.adaptive_threshold = 0.03

# main generation loop
output_dir = os.path.join(os.getcwd(), 'renders', f'gpu_{args.gpu}')
all_hdris_path = [os.path.join("hdris_world", fname) for fname in os.listdir("hdris_world") if os.path.isfile(os.path.join("hdris_world", fname))]
for scene_idx in range(args.n_scene):
    cleanup_render_images()
    # create new scene 
    print(f"Generating scene {scene_idx}")
    meta_data, all_blocks = new_scene()
    # save scene metadata
    os.makedirs(os.path.join(output_dir, f"scene_{scene_idx:04d}"), exist_ok=True)
    with open(os.path.join(output_dir, f"scene_{scene_idx:04d}", "field_metadata.json"), 'w') as f:
        json.dump(meta_data, f, indent=4)
        
    # capture
    for capture_idx in range(args.n_capture):
        print(f"  Capturing {capture_idx}")
        # spawn lights and get new world
        clear_lights()
        spawn_lights()
        new_world(random.choice(all_hdris_path))
        robot_meta = spawn_robot(staticg_objects + [obj.name for obj in all_blocks], 50)
        # capture_dir = f"output/scene_{scene_idx:04d}/capture_{capture_idx:02d}"
        capture_dir = os.path.join(output_dir, f"scene_{scene_idx:04d}", f"capture_{capture_idx:02d}")
        scene = bpy.context.scene
        cameras_meta = capture(scene, capture_dir, 'jpg')
        capture_meta = {
            "robot": robot_meta,
            "cameras": cameras_meta
        }
        with open(f"{capture_dir}/capture_meta.json", 'w') as f:
            json.dump(capture_meta, f, indent=4)

end_time = time.time()
print(f"Total time taken: {end_time - start_time} seconds")
print("Generation complete!")
