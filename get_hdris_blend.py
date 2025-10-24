import gdown 
hdris_link = "https://drive.google.com/file/d/1yP7sUQb-qmHP1y1JbbmuTsdWp_n0iH-A/view?usp=sharing"
blend_link = "https://drive.google.com/file/d/1tFyBY9qBCDMls_pddZJJmiPoL66UuQeD/view?usp=drive_link"
gdown.download(hdris_link, "hdris_world.tar", quiet=False, fuzzy=True)
gdown.download(blend_link, "v1.0.1.blend", quiet=False, fuzzy=True)