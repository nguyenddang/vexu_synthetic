import bpy 
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