# VEXU Synthetic

Use this repository to generate synthetic data to train occupancy networks. All scripts are designed to run on a cluster (use Turing). Run this locally if you want to set your laptop on fire.

Clone the repo first of course
```bash
git clone https://github.com/Autonomous-VEXU/vexu_synthetic.git
cd vexu_synthetic
```

## Set up Python virtual environment
```bash
uv sync # sync dependencies. (install if don't have uv https://docs.astral.sh/uv/getting-started/installation/)
source .venv/bin/activate # activate virtual environment
```

## Download HDRIS and blend file
```bash
uv run get_hdris_blend.py # download hdris and .blend file from MQP drive
tar -xf hdris_world.tar # extract 
```
## Set up Blender
Download blender and extract. **Only do this first time!!!!!!**
```bash
wget https://mirrors.iu13.net/blender/release/Blender4.5/blender-4.5.3-linux-x64.tar.xz
tar -xvf blender-4.5.3-linux-x64.tar.xz
```
Before doing any generation, load all necessary modules from the cluster. Do this every time you log in.
```bash
source ./load_module.sh
``` 
## Run generation

### From terminal (reccommended for testing only)
Before running from terminal, make sure you are on a GPU node. Use `sinteractive` and request L40S GPU, minimum 32 cores, 64GB memory. More infor here https://docs.turing.wpi.edu/getting-started/. Then run
```bash
# running from vexu_synthetic directory, cd .. if needed
./blender-4.5.3-linux-x64/blender -b v1.0.1.blend --quiet --python gen.py -- --gpu 0 --n_capture 5 --n_scene 5 --cycles-device OPTIX
```
Here `--n_capture` is the number of captures to get per scene, and `--n_scene` is the number of scenes to generate. Adjust these numbers as needed. The above command will generate 5 scenes with 5 captures (image from all cameras) each, for a total of 25 images. The `--gpu` flag specifies gpu index (useful for sending jobs). Each scene means randomly spawning blocks. After each capture, lighting, background, robot pose will change while the blocks stay the same.

By default resolution is set to 1280 x 720.

### From slurm job (reccommended for large generation)
Submit a job
```bash
sbatch gen.sh
``` 
See `gen.sh` for more details. By default script generate 1000 scenes with 5 captures each. Adjust as needed. You can generate on multiple GPUs by submitting multiple jobs with different `--gpu` index. Simply `sbatch gen.sh` multiple times but change the `--gpu` flag.

## Hardware + time considerations
Note that each capture (with 1920x1200 resolution) is ~1.2MB. So 1000 scenes with 5 captures each is ~6GB. Make sure you have enough space in your home directory. A single capture takes ~ 13-15s. So 1000 scenes with 5 captures each will take ~ 18 hours on a single L40S GPU. You can speed this up by submitting multiple jobs with different `--gpu` index.

## UPDATE
### 24/10/2025
- Updated to use v1.0.1.blend. Fix camera pose bug. 
- Updated resolution to 1280 x 720. Neural network doen't need 1920 x 1200. Too much memory wasted.
- Fix robot position bug. Should now not collide with blocks.