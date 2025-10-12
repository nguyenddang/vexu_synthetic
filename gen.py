import bpy 
from utils import clear_all_blocks, clear_lights, cleanup_orphaned_data, generate_random_field, spawn_lights
from block import spawn_ground, spawn_loaders, spawn_lg, spawn_cg
from capture import spawn_robot, capture

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
    
] + ['Wall.{:03d}'.format(i) for i in range(1, 45)]
def new_scene():
    """
    Generate a new random scene and return metadata for saving
    """
    clear_all_blocks()
    clear_lights()
    cleanup_orphaned_data()
    spawn_lights()
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
    return meta_data
