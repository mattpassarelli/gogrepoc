#!/bin/bash
# Build script for PyInstaller (Unix/Linux/macOS)

set -e  # Exit on error

echo "==================================="
echo "PyInstaller Build Script (Unix)"
echo "==================================="

# Detect platform
PLATFORM=$(uname -s)
echo "Platform detected: $PLATFORM"

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "ERROR: PyInstaller is not installed"
    echo "Please install it with: pip install pyinstaller"
    exit 1
fi

# Check if spec file exists
if [ ! -f "gogrepoc.spec" ]; then
    echo "ERROR: gogrepoc.spec not found in current directory"
    echo "Please run this script from the backend directory"
    exit 1
fi

# Clean previous build
echo "Cleaning previous build artifacts..."
rm -rf build dist

# Run PyInstaller
echo "Running PyInstaller..."
pyinstaller gogrepoc.spec --clean

# Verify output executable exists
if [ "$PLATFORM" = "Darwin" ] || [ "$PLATFORM" = "Linux" ]; then
    EXECUTABLE="dist/gogrepoc-backend"
elif [[ "$PLATFORM" == MINGW* ]] || [[ "$PLATFORM" == MSYS* ]] || [[ "$PLATFORM" == CYGWIN* ]]; then
    EXECUTABLE="dist/gogrepoc-backend.exe"
else
    EXECUTABLE="dist/gogrepoc-backend"
fi

if [ ! -f "$EXECUTABLE" ]; then
    echo "ERROR: Build failed - executable not found at $EXECUTABLE"
    exit 1
fi

# Make executable (Unix/Linux/macOS)
if [ "$PLATFORM" = "Darwin" ] || [ "$PLATFORM" = "Linux" ]; then
    chmod +x "$EXECUTABLE"
    echo "Made executable: $EXECUTABLE"
fi

# Verify executable is actually executable
if [ "$PLATFORM" = "Darwin" ] || [ "$PLATFORM" = "Linux" ]; then
    if [ ! -x "$EXECUTABLE" ]; then
        echo "ERROR: Executable is not executable: $EXECUTABLE"
        exit 1
    fi
fi

echo "==================================="
echo "Build completed successfully!"
echo "Executable: $EXECUTABLE"
echo "==================================="
