#!/bin/bash

# Blender Setup Script for HPC Cluster
# This script loads all necessary modules and sets up the environment
# to run Blender in headless mode on the cluster

echo "Setting up Blender environment..."

# Load required modules
echo "Loading modules..."
module load libxrender
module load libxfixes
module load libxi
module load libxkbcommon
module load mesa
module load gcc/15.1.0

echo "Modules loaded successfully."

# Set up library paths
echo "Setting up library paths..."

# Add libXrender library path
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-x86_64/libxrender-0.9.12-uolsbnwrlcqwodd55lbc6si6cu3rx2pe/lib:$LD_LIBRARY_PATH"

# Add libXfixes library path
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-ubuntu20.04-x86_64/gcc-13.2.0/libxfixes-5.0.3-x776t2yf6u5cpzzfhrmuparlsq262u6f/lib:$LD_LIBRARY_PATH"

# Add libXi library path
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-ubuntu20.04-x86_64/gcc-13.2.0/libxi-1.7.10-yliyie6bpifieikysurgqkg6drloc5as/lib:$LD_LIBRARY_PATH"

# Add libxkbcommon library path
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-ubuntu20.04-x86_64/gcc-13.2.0/libxkbcommon-1.7.0-uchgu4dmtvnz35dqv6cfudl2i36cn2hs/lib:$LD_LIBRARY_PATH"

# Add Mesa (OpenGL) library path
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-x86_64/mesa-25.0.5-rclmohiaitjskxy2qh4gqxqi2wt5hv75/lib:$LD_LIBRARY_PATH"

# Add GCC library path for newer libstdc++
export LD_LIBRARY_PATH="/cm/shared/spack/opt/spack/linux-ubuntu20.04-x86_64/gcc-13.2.0/gcc-15.1.0-hgqgy4pz47kszzww4vzvxsxbriahfcor/lib64:$LD_LIBRARY_PATH"

echo "Library paths configured."

# Navigate to Blender directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_DIR="$SCRIPT_DIR/blender-4.5.3-linux-x64"
cd "$BLENDER_DIR"

echo "Environment setup complete!"
echo "You can now run Blender with: ./blender --background [options]"
echo "Current directory: $(pwd)"
echo ""
echo "Example commands:"
echo "  ./blender --background --version"
echo "  ./blender --background --help"
echo "  ./blender --background your_file.blend --render-frame 1"
echo ""

# Test if Blender works
echo "Testing Blender..."
if ./blender --background --version > /dev/null 2>&1; then
    echo "✅ Blender is working correctly!"
    echo ""
    echo "🔧 USAGE: To use this environment, run 'source ./setup_blender.sh' instead of './setup_blender.sh'"
    echo "   This will keep the environment and directory changes in your current shell."
else
    echo "❌ Blender setup failed. Please check the error messages above."
    return 1
fi
