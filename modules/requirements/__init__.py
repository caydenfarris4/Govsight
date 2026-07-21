"""
GovSight Requirements Management

This module manages dependency requirements for different environments:
- base.txt: Core application dependencies
- development.txt: Development and testing tools
- production.txt: Production deployment dependencies
- security.txt: Enhanced security dependencies

Usage:
    pip install -r modules/requirements/base.txt
    pip install -r modules/requirements/development.txt  # For development
    pip install -r modules/requirements/production.txt   # For production
    pip install -r modules/requirements/security.txt     # For enhanced security
"""

import os
from pathlib import Path

REQUIREMENTS_DIR = Path(__file__).parent

def get_requirements_path(environment='base'):
    """
    Get the path to a specific requirements file
    
    Args:
        environment (str): Environment type ('base', 'development', 'production', 'security')
        
    Returns:
        Path: Path to the requirements file
    """
    filename = f"{environment}.txt"
    filepath = REQUIREMENTS_DIR / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Requirements file not found: {filepath}")
    
    return filepath

def list_requirements_files():
    """
    List all available requirements files
    
    Returns:
        list: List of available requirement file names
    """
    txt_files = [f.stem for f in REQUIREMENTS_DIR.glob("*.txt")]
    return sorted(txt_files)

def validate_requirements():
    """
    Validate that all requirements files exist and are readable
    
    Returns:
        dict: Validation results for each requirements file
    """
    results = {}
    
    for req_file in list_requirements_files():
        try:
            filepath = get_requirements_path(req_file)
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            results[req_file] = {
                'exists': True,
                'readable': True,
                'line_count': len(lines),
                'dependencies': len([l for l in lines if l.strip() and not l.startswith('#') and not l.startswith('-r')])
            }
        except Exception as e:
            results[req_file] = {
                'exists': False,
                'readable': False,
                'error': str(e)
            }
    
    return results

if __name__ == "__main__":
    # Print validation results when run directly
    print("GovSight Requirements Validation")
    print("=" * 40)
    
    validation = validate_requirements()
    for env, result in validation.items():
        print(f"\n{env}.txt:")
        if result.get('exists'):
            print(f"  ✓ File exists and readable")
            print(f"  ✓ {result['line_count']} total lines")
            print(f"  ✓ {result['dependencies']} dependencies")
        else:
            print(f"  ✗ Error: {result.get('error', 'Unknown error')}")