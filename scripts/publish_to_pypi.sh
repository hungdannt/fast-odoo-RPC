#!/bin/bash

# Zenoo RPC PyPI Publication Script
# This script automates the process of publishing Zenoo RPC to PyPI

set -e  # Exit on any error

echo "🚀 Zenoo RPC v0.1.0 PyPI Publication Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d "src/zenoo_rpc" ]; then
    print_error "Please run this script from the zenoo-rpc root directory"
    exit 1
fi

# Check if required tools are installed
print_status "Checking required tools..."

if ! command -v python &> /dev/null; then
    print_error "Python is not installed"
    exit 1
fi

if ! python -m build --help &> /dev/null; then
    print_error "build module not found. Install with: pip install build"
    exit 1
fi

if ! command -v twine &> /dev/null; then
    print_error "twine is not installed. Install with: pip install twine"
    exit 1
fi

print_success "All required tools are available"

# Verify package version
print_status "Verifying package version..."
VERSION=$(python -c "import sys; sys.path.insert(0, 'src'); import zenoo_rpc; print(zenoo_rpc.__version__)")
print_success "Package version: $VERSION"

# Ask for confirmation
echo ""
read -p "🤔 Do you want to publish Zenoo RPC v$VERSION to PyPI? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Publication cancelled by user"
    exit 0
fi

# Clean previous builds
print_status "Cleaning previous builds..."
rm -rf dist/ build/ src/zenoo_rpc.egg-info/
print_success "Previous builds cleaned"

# Build package
print_status "Building package..."
python -m build

if [ $? -eq 0 ]; then
    print_success "Package built successfully"
else
    print_error "Package build failed"
    exit 1
fi

# List built files
print_status "Built files:"
ls -la dist/

# Validate package
print_status "Validating package with twine..."
twine check dist/*

if [ $? -eq 0 ]; then
    print_success "Package validation passed"
else
    print_error "Package validation failed"
    exit 1
fi

# Ask about TestPyPI
echo ""
read -p "🧪 Do you want to test upload to TestPyPI first? (Y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    print_status "Uploading to TestPyPI..."
    print_warning "You'll need to enter your TestPyPI API token"
    
    twine upload --repository testpypi dist/*
    
    if [ $? -eq 0 ]; then
        print_success "TestPyPI upload successful"
        print_status "Check: https://test.pypi.org/project/zenoo-rpc/"
        
        echo ""
        read -p "✅ TestPyPI looks good? Continue to production PyPI? (y/N): " -n 1 -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Production upload cancelled"
            exit 0
        fi
    else
        print_error "TestPyPI upload failed"
        exit 1
    fi
fi

# Upload to production PyPI
print_status "Uploading to production PyPI..."
print_warning "You'll need to enter your PyPI API token"

twine upload dist/*

if [ $? -eq 0 ]; then
    print_success "🎉 PyPI upload successful!"
    print_success "Package is now available at: https://pypi.org/project/zenoo-rpc/"
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Check the PyPI page: https://pypi.org/project/zenoo-rpc/"
    echo "2. Test installation: pip install zenoo-rpc"
    echo "3. Create GitHub release: git tag v$VERSION && git push origin v$VERSION"
    echo "4. Update documentation badges"
    echo "5. Announce the release!"
    
else
    print_error "PyPI upload failed"
    exit 1
fi

print_success "🚀 Zenoo RPC v$VERSION published successfully!"
