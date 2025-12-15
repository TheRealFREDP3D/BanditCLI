#!/usr/bin/env python3

"""
Entry point for the Bandit Wargame CLI application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import BanditCLIApp

if __name__ == "__main__":
    app = BanditCLIApp()
    app.run()