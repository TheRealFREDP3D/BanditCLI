#!/usr/bin/env python3
"""
BanditCLI Dependency Installer

This script installs and verifies all required dependencies for BanditCLI.
"""

import importlib
import subprocess
import sys
import platform
from pathlib import Path
from typing import Dict, Tuple, List

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{'='*80}\n{text}\n{'='*80}{Colors.ENDC}")

def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠  {text}{Colors.ENDC}")

def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def run_command(command: List[str], cwd: str = None) -> Tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.output

def install_packages() -> bool:
    """Install all packages from requirements.txt using uv."""
    print_header("INSTALLING DEPENDENCIES")
    
    # Check if uv is installed
    uv_installed, _ = run_command(["uv", "--version"])
    if not uv_installed:
        print("Installing uv...")
        success, output = run_command(["pip", "install", "uv"])
        if not success:
            print_error("Failed to install uv. Please install it manually: pip install uv")
            return False
    
    # Create or use existing .venv
    venv_dir = Path(__file__).parent / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment using uv...")
        success, output = run_command(["uv", "venv"])
        if not success:
            print_error(f"Failed to create virtual environment: {output}")
            return False
        print_success("Virtual environment created")
    
    # Activate virtual environment and install packages
    requirements_file = Path(__file__).parent / "requirements.txt"
    print(f"\nInstalling packages from {requirements_file}...")
    
    # Use uv pip to install requirements
    pip_cmd = ["uv", "pip", "install", "-r", str(requirements_file)]
    success, output = run_command(pip_cmd)
    
    if success:
        print_success("All packages installed successfully")
        return True
    else:
        print_error("Failed to install some packages")
        print(output)
        return False

def verify_imports() -> bool:
    """Verify that all required imports work."""
    print_header("VERIFYING IMPORTS")
    
    test_cases = [
        # (module_name, package_name, import_path, test_code)
        ("textual", "textual", "textual.app", "import textual.app"),
        ("paramiko", "paramiko", "paramiko.SSHClient", "import paramiko"),
        ("python-dotenv", "dotenv", "dotenv.load_dotenv", "from dotenv import load_dotenv"),
        ("litellm", "litellm", "litellm", "import litellm")
    ]
    
    all_success = True
    
    for module_name, package_name, import_path, test_code in test_cases:
        try:
            print(f"Testing {module_name}...", end=" ")
            # Test if the module can be imported
            importlib.import_module(package_name.split('.')[0])
            # Test specific imports
            exec(test_code)
            print_success(f"{module_name} OK")
        except ImportError as e:
            print_error(f"Failed to import {module_name}: {e}")
            all_success = False
        except Exception as e:
            print_error(f"Error testing {module_name}: {e}")
            all_success = False
    
    return all_success

def verify_application_imports() -> bool:
    """Verify that application modules can be imported."""
    print_header("VERIFYING APPLICATION IMPORTS")
    
    # Add src directory to path like run.py does
    src_dir = str(Path(__file__).parent / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    test_cases = [
        ("main", "BanditCLIApp"),
        ("ssh_manager", "SSHManager"),
        ("ai_mentor", "BanditAIMentor"),
        ("level_info", "BanditLevelInfo")
    ]
    
    all_success = True
    
    for module_name, class_name in test_cases:
        try:
            print(f"Testing import of {module_name}.{class_name}...", end=" ")
            module = importlib.import_module(module_name)
            getattr(module, class_name)
            print_success(f"{module_name}.{class_name} OK")
        except ImportError as e:
            print_error(f"Failed to import {module_name}: {e}")
            all_success = False
        except AttributeError:
            print_error(f"Class {class_name} not found in {module_name}")
            all_success = False
        except Exception as e:
            print_error(f"Error testing {module_name}: {e}")
            all_success = False
    
    return all_success

def main() -> int:
    """Main installation and verification function."""
    print(f"{Colors.HEADER}{'='*80}")
    print(f"{'BanditCLI Dependency Installer':^80}")
    print(f"{'='*80}{Colors.ENDC}")
    
    # Print system information
    print(f"Python: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Executable: {sys.executable}")
    
    # Install packages
    if not install_packages():
        print_warning("Some packages failed to install. Trying to continue with verification...")
    
    # Verify imports
    imports_ok = verify_imports()
    app_imports_ok = verify_application_imports()
    
    # Print summary
    print_header("INSTALLATION SUMMARY")
    
    if imports_ok and app_imports_ok:
        print_success("All dependencies installed and verified successfully!")
        print("You can now run BanditCLI using 'python run.py'")
        return 0
    else:
        print_error("Some dependencies failed to install or verify")
        print("\nTroubleshooting steps:")
        print("1. Make sure you have Python 3.7+ installed")
        print("2. Try running with administrator/root privileges")
        print("3. Check if there are any error messages above")
        print("4. Try installing the packages manually: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
