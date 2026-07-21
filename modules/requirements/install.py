#!/usr/bin/env python3
"""
GovSight Requirements Installer

A utility script to install requirements for different environments.
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements(environment='base', upgrade=False):
    """
    Install requirements for a specific environment
    
    Args:
        environment (str): Environment type ('base', 'development', 'production', 'security')
        upgrade (bool): Whether to upgrade existing packages
    """
    req_path = Path(__file__).parent / f"{environment}.txt"
    
    if not req_path.exists():
        print(f"Error: Requirements file not found: {req_path}")
        return False
    
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_path)]
    
    if upgrade:
        cmd.append("--upgrade")
    
    print(f"Installing {environment} requirements...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Installation successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main installer interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Install GovSight requirements")
    parser.add_argument("environment", choices=["base", "development", "production", "security"], 
                       help="Environment to install requirements for")
    parser.add_argument("--upgrade", action="store_true", 
                       help="Upgrade existing packages")
    
    args = parser.parse_args()
    
    success = install_requirements(args.environment, args.upgrade)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()