#!/bin/bash
# BanditCLI Installer for Unix/Linux
# This script installs all required dependencies for BanditCLI using uv

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print with color
print_color() {
    printf "%b%s%b\n" "$2" "$1" "${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print header
print_color "==========================================================" "${PURPLE}"
print_color "          BanditCLI Unix/Linux Installer (uv)" "${PURPLE}"
print_color "==========================================================" "${PURPLE}"
print_color "This will set up BanditCLI with uv for package management." "${WHITE}"
echo

# Check if Python is installed
if ! command_exists python3; then
    print_color "[ERROR] Python 3 is not installed." "${RED}"
    print_color "Please install Python 3.7 or later using your package manager:" "${YELLOW}"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    echo "  macOS:         brew install python"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
print_color "Found Python version: ${PYTHON_VERSION}" "${CYAN}"

# Check Python version
IFS='.' read -ra VERSION_PARTS <<< "$PYTHON_VERSION"
if [[ "${VERSION_PARTS[0]}" -lt "3" ]] || 
   ([[ "${VERSION_PARTS[0]}" -eq "3" && "${VERSION_PARTS[1]}" -lt "7" ]]); then
    print_color "[ERROR] Python 3.7 or later is required." "${RED}"
    exit 1
fi

# Install or update uv
print_color "Setting up uv..." "${BLUE}"
python3 -m pip install --upgrade uv
if [ $? -ne 0 ]; then
    print_color "[ERROR] Failed to install uv." "${RED}"
    print_color "Please check your internet connection and try again." "${YELLOW}"
    exit 1
fi

# Use existing .venv or create a new one
VENV_DIR=".venv"
if [ -d "$VENV_DIR" ]; then
    print_color "Using existing virtual environment at ./${VENV_DIR}" "${CYAN}"
else
    print_color "Creating virtual environment using uv..." "${BLUE}"
    uv venv
    if [ $? -ne 0 ]; then
        print_color "[ERROR] Failed to create virtual environment." "${RED}"
        exit 1
    fi
    print_color "Virtual environment created at ./${VENV_DIR}" "${GREEN}"
fi

# Activate the virtual environment
if [ -f "${VENV_DIR}/bin/activate" ]; then
    source "${VENV_DIR}/bin/activate"
    print_color "Activated virtual environment." "${GREEN}"
else
    print_color "[ERROR] Virtual environment activation failed." "${RED}"
    exit 1
fi

# Install dependencies using uv
print_color "Installing dependencies using uv..." "${BLUE}"
uv pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_color "[ERROR] Failed to install dependencies." "${RED}"
    print_color "Please check your internet connection and try again." "${YELLOW}"
    exit 1
fi

# Verify installation
print_color "Verifying installation..." "${BLUE}"
"${VENV_DIR}/bin/python" verify_installation.py
if [ $? -ne 0 ]; then
    print_color "Some issues were found during verification." "${YELLOW}"
    print_color "Check the output above for details." "${YELLOW}"
    exit 1
fi

# Create a run script
cat > run.sh << 'EOF'
#!/bin/bash
# Run BanditCLI with the virtual environment
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
"${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/run.py" "$@"
EOF
chmod +x run.sh

# Success
print_color "\nInstallation completed successfully!" "${GREEN}"
print_color "You can now run BanditCLI using:" "${WHITE}"
print_color "  ./run.sh" "${CYAN}"
print_color "\nVirtual environment: ${VENV_DIR}" "${CYAN}"
print_color "To activate the virtual environment manually, run:" "${WHITE}"
print_color "  source ${VENV_DIR}/bin/activate" "${CYAN}"
echo
