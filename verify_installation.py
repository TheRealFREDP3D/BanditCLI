#!/usr/bin/env python3
"""
BanditCLI Installation Verifier

This script verifies that all required dependencies are properly installed
and can be imported by the application.
"""

import importlib
import sys
import platform
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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

def get_package_version(package_name: str) -> Optional[str]:
    """Get the installed version of a package."""
    try:
        module = importlib.import_module(package_name.split('.')[0])
        return getattr(module, '__version__', 'unknown')
    except (ImportError, AttributeError):
        return None

def verify_dependency(name: str, import_path: str, test_code: str = None) -> Tuple[bool, str]:
    """Verify if a dependency can be imported and optionally tested."""
    try:
        # Import the package
        module = importlib.import_module(import_path.split('.')[0])
        
        # Test specific import if provided
        if test_code:
            exec(test_code, globals(), {'module': module})
            
        # Get version if available
        version = getattr(module, '__version__', 'unknown')
        return True, f"{name} v{version}"
    except ImportError as e:
        return False, f"Not installed: {e}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def verify_application_import(module_name: str, class_name: str = None) -> Tuple[bool, str]:
    """Verify if an application module can be imported."""
    try:
        # Add src directory to path
        src_dir = str(Path(__file__).parent / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # Import the module
        module = importlib.import_module(module_name)
        
        # Check for class if specified
        if class_name:
            getattr(module, class_name)
            return True, f"{module_name}.{class_name}"
        return True, module_name
    except ImportError as e:
        return False, f"Import failed: {e}"
    except AttributeError:
        return False, f"Class {class_name} not found in {module_name}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is sufficient."""
    if sys.version_info >= (3, 7):
        return True, f"Python {platform.python_version()}"
    return False, f"Python {platform.python_version()} (3.7+ required)"

def main() -> int:
    """Main verification function."""
    print(f"{Colors.HEADER}{'='*80}")
    print(f"{'BanditCLI Installation Verifier':^80}")
    print(f"{'='*80}{Colors.ENDC}")
    
    # System information
    print(f"Platform: {platform.platform()}")
    print(f"Python: {sys.executable}")
    
    # Check Python version
    py_ok, py_msg = check_python_version()
    print(f"\n{'Python Version:':<20}", end="")
    if py_ok:
        print_success(py_msg)
    else:
        print_error(py_msg)
    
    # Dependencies to verify
    dependencies = [
        ("textual", "textual.app", "from textual.app import App"),
        ("paramiko", "paramiko", "from paramiko import SSHClient"),
        ("python-dotenv", "dotenv", "from dotenv import load_dotenv"),
        ("litellm", "litellm", "import litellm")
    ]
    
    # Application modules to verify
    app_modules = [
        ("main", "BanditCLIApp"),
        ("ssh_manager", "SSHManager"),
        ("ai_mentor", "BanditAIMentor"),
        ("level_info", "BanditLevelInfo")
    ]
    
    # Environment checks
    env_checks = [
        (".env file", (Path(__file__).parent / ".env").exists()),
        ("requirements.txt", (Path(__file__).parent / "requirements.txt").exists()),
        ("src directory", (Path(__file__).parent / "src").exists())
    ]
    
    # Verify dependencies
    print_header("DEPENDENCIES")
    all_deps_ok = True
    for name, import_path, test_code in dependencies:
        success, message = verify_dependency(name, import_path, test_code)
        print(f"{name}:{' '*(20-len(name))}", end="")
        if success:
            print_success(message)
        else:
            print_error(message)
            all_deps_ok = False
    
    # Verify application imports
    print_header("APPLICATION MODULES")
    all_imports_ok = True
    for module_name, class_name in app_modules:
        success, message = verify_application_import(module_name, class_name)
        print(f"{module_name}.{class_name}:{' '*(30-len(module_name)-len(class_name))}", end="")
        if success:
            print_success("OK")
        else:
            print_error(message)
            all_imports_ok = False
    
    # Check environment
    print_header("ENVIRONMENT CHECKS")
    all_env_ok = True
    for check_name, exists in env_checks:
        print(f"{check_name}:{' '*(20-len(check_name))}", end="")
        if exists:
            print_success("Found")
        else:
            print_warning("Not found")
            all_env_ok = False
    
    # Print summary
    print_header("VERIFICATION SUMMARY")
    
    if all_deps_ok and all_imports_ok and py_ok:
        print_success("All checks passed! BanditCLI is ready to use.")
        print("You can now run the application using 'python run.py'")
        return 0
    else:
        print_error("Some issues were found:")
        if not py_ok:
            print("- Python version is too old. Please upgrade to Python 3.7 or higher.")
        if not all_deps_ok:
            print("- Some dependencies are missing or have issues. Try running 'pip install -r requirements.txt'")
        if not all_imports_ok:
            print("- Some application modules failed to import. Make sure the src directory is in your PYTHONPATH.")
        if not all_env_ok:
            print("- Some environment files are missing. Check the warnings above.")
        
        print("\nFor help troubleshooting, please refer to the documentation or open an issue on GitHub.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
