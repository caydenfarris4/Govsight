#!/usr/bin/env python3
"""
Build script to protect GovSight source code

This script creates a protected version of your codebase with:
- Encrypted source code
- Obfuscated file names and structures
- Decoy files to confuse code readers
- Compiled bytecode only distribution
- Anti-debugging protection
"""

import os
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.getcwd())

try:
    from modules.security.source_protection import source_protector
    from modules.security.code_protection import code_obfuscator
except ImportError as e:
    print(f"Error importing protection modules: {e}")
    print("Make sure the security modules are available")
    sys.exit(1)

class GovSightProtectionBuilder:
    """Main builder for protected GovSight deployment"""
    
    def __init__(self):
        self.source_dir = "."
        self.protected_dir = "protected_dist"
        self.backup_dir = "source_backup"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_protected_distribution(self):
        """Create complete protected distribution"""
        print("=" * 60)
        print("GovSight Source Code Protection System")
        print("=" * 60)
        
        # Step 1: Create backup
        print("1. Creating source code backup...")
        self._create_backup()
        
        # Step 2: Prepare protected directory
        print("2. Preparing protected distribution...")
        self._prepare_protected_dir()
        
        # Step 3: Protect Python files
        print("3. Encrypting and obfuscating Python files...")
        self._protect_python_files()
        
        # Step 4: Create decoy files
        print("4. Creating decoy files...")
        self._create_decoy_files()
        
        # Step 5: Compile to bytecode
        print("5. Compiling to bytecode...")
        self._compile_to_bytecode()
        
        # Step 6: Create deployment package
        print("6. Creating deployment package...")
        self._create_deployment_package()
        
        # Step 7: Create run script
        print("7. Creating protected run script...")
        self._create_run_script()
        
        print("=" * 60)
        print("SUCCESS: Protected distribution created!")
        print(f"Protected code: {self.protected_dir}")
        print(f"Deployment package: govsight_protected_{self.timestamp}.zip")
        print(f"Source backup: {self.backup_dir}")
        print("=" * 60)
    
    def _create_backup(self):
        """Create backup of original source code"""
        backup_name = f"{self.backup_dir}_{self.timestamp}"
        
        if os.path.exists(backup_name):
            shutil.rmtree(backup_name)
        
        # Copy entire directory structure
        shutil.copytree(self.source_dir, backup_name, ignore=shutil.ignore_patterns(
            '*.pyc', '__pycache__', '.git', '*.log', 'protected_dist', 'source_backup*'
        ))
        
        print(f"   Backup created: {backup_name}")
    
    def _prepare_protected_dir(self):
        """Prepare protected directory structure"""
        if os.path.exists(self.protected_dir):
            shutil.rmtree(self.protected_dir)
        
        os.makedirs(self.protected_dir)
        
        # Copy non-Python files
        for root, dirs, files in os.walk(self.source_dir):
            # Skip protected directories
            if 'protected_dist' in root or 'source_backup' in root:
                continue
            
            for file in files:
                if not file.endswith('.py'):
                    source_file = os.path.join(root, file)
                    relative_path = os.path.relpath(source_file, self.source_dir)
                    target_file = os.path.join(self.protected_dir, relative_path)
                    
                    target_dir = os.path.dirname(target_file)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    
                    shutil.copy2(source_file, target_file)
    
    def _protect_python_files(self):
        """Protect all Python files"""
        protected_count = 0
        
        for root, dirs, files in os.walk(self.source_dir):
            # Skip protected directories
            if 'protected_dist' in root or 'source_backup' in root:
                continue
            
            for file in files:
                if file.endswith('.py'):
                    source_file = os.path.join(root, file)
                    relative_path = os.path.relpath(source_file, self.source_dir)
                    
                    # Read source code
                    with open(source_file, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    # Create protected version
                    module_name = os.path.splitext(file)[0]
                    protected_code = source_protector.create_protected_module(module_name, source_code)
                    
                    # Write protected file
                    target_file = os.path.join(self.protected_dir, relative_path)
                    target_dir = os.path.dirname(target_file)
                    
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(protected_code)
                    
                    protected_count += 1
        
        print(f"   Protected {protected_count} Python files")
    
    def _create_decoy_files(self):
        """Create decoy files to confuse code readers"""
        decoy_dir = os.path.join(self.protected_dir, 'system_modules')
        source_protector.create_decoy_files(decoy_dir, 20)
        
        # Create fake main files
        fake_mains = [
            'main_backup.py',
            'main_debug.py',
            'main_test.py',
            'main_dev.py'
        ]
        
        for fake_main in fake_mains:
            fake_content = '''
# Fake main file - decoy
print("This is a decoy file")
import sys
sys.exit(0)
'''
            with open(os.path.join(self.protected_dir, fake_main), 'w') as f:
                f.write(fake_content)
        
        print("   Created decoy files and fake modules")
    
    def _compile_to_bytecode(self):
        """Compile protected files to bytecode"""
        compiled_count = 0
        
        for root, dirs, files in os.walk(self.protected_dir):
            for file in files:
                if file.endswith('.py'):
                    py_file = os.path.join(root, file)
                    try:
                        source_protector.compile_source_to_bytecode(py_file)
                        compiled_count += 1
                    except Exception as e:
                        print(f"   Warning: Could not compile {file}: {e}")
        
        print(f"   Compiled {compiled_count} files to bytecode")
    
    def _create_deployment_package(self):
        """Create deployment ZIP package"""
        package_name = f"govsight_protected_{self.timestamp}.zip"
        
        with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.protected_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.protected_dir)
                    zipf.write(file_path, arcname)
        
        print(f"   Created deployment package: {package_name}")
    
    def _create_run_script(self):
        """Create protected run script"""
        run_script = f'''#!/usr/bin/env python3
"""
GovSight Protected Application Runner
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This is the protected version of GovSight Financial Analyzer.
Source code is encrypted and obfuscated for security.
"""

import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

def check_environment():
    """Check if environment is suitable for running protected code"""
    # Anti-debugging check
    if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
        print("Error: Debugging detected. Cannot run protected application.")
        sys.exit(1)
    
    # Check for required modules
    required_modules = ['streamlit', 'pandas', 'plotly']
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            print(f"Error: Required module '{module}' not found.")
            print("Please install required dependencies.")
            sys.exit(1)

def main():
    """Main entry point for protected application"""
    print("Starting GovSight Financial Analyzer (Protected Version)")
    print("=" * 50)
    
    # Check environment
    check_environment()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Import and run main application
    try:
        from main_app import *
        print("Application loaded successfully")
    except Exception as e:
        print(f"Error loading application: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        run_script_path = os.path.join(self.protected_dir, 'run_protected.py')
        with open(run_script_path, 'w') as f:
            f.write(run_script)
        
        # Create batch file for Windows
        batch_script = '''@echo off
echo Starting GovSight Protected Application...
python run_protected.py
pause
'''
        
        with open(os.path.join(self.protected_dir, 'run_protected.bat'), 'w') as f:
            f.write(batch_script)
        
        # Create shell script for Unix
        shell_script = '''#!/bin/bash
echo "Starting GovSight Protected Application..."
python3 run_protected.py
'''
        
        shell_path = os.path.join(self.protected_dir, 'run_protected.sh')
        with open(shell_path, 'w') as f:
            f.write(shell_script)
        
        # Make shell script executable
        os.chmod(shell_path, 0o755)
        
        print("   Created run scripts for all platforms")

def main():
    """Main build process"""
    try:
        builder = GovSightProtectionBuilder()
        builder.create_protected_distribution()
        
        print("\nNEXT STEPS:")
        print("1. Test the protected version in the 'protected_dist' directory")
        print("2. Deploy the ZIP package to your target environment")
        print("3. Run using 'python run_protected.py' or run_protected.bat/sh")
        print("4. Keep the source backup in a secure location")
        
    except Exception as e:
        print(f"Error during build process: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()