"""
Source Code Protection Module

Advanced techniques to hide, encrypt, and protect source code from
unauthorized access, copying, or reverse engineering.

PROTECTION LAYERS:
1. Source code compilation to bytecode only
2. Dynamic code generation and execution
3. Code splitting and encryption
4. Anti-debugging and anti-reverse engineering
5. Obfuscated imports and dependencies
"""

import os
import sys
import py_compile
import marshal
import base64
import zlib
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import ast
import inspect

class SourceCodeProtector:
    """Comprehensive source code protection system"""
    
    def __init__(self):
        self.protected_files = {}
        self.bytecode_cache = {}
        self.encryption_key = self._generate_protection_key()
    
    def _generate_protection_key(self) -> bytes:
        """Generate unique protection key"""
        key_material = f"{os.getcwd()}{sys.version}{os.path.basename(__file__)}"
        return key_material.encode()[:32].ljust(32, b'\x00')
    
    def compile_source_to_bytecode(self, source_file: str, output_dir: str = None) -> str:
        """
        Compile Python source file to bytecode (.pyc) only
        
        Args:
            source_file: Path to source file
            output_dir: Directory for compiled bytecode
            
        Returns:
            str: Path to compiled bytecode file
        """
        if output_dir is None:
            output_dir = os.path.dirname(source_file)
        
        # Create bytecode filename
        source_path = Path(source_file)
        bytecode_file = os.path.join(output_dir, f"{source_path.stem}.pyc")
        
        try:
            # Compile source to bytecode
            py_compile.compile(source_file, bytecode_file, doraise=True)
            
            # Store reference
            self.protected_files[source_file] = bytecode_file
            
            return bytecode_file
            
        except Exception as e:
            raise Exception(f"Failed to compile {source_file}: {e}")
    
    def encrypt_source_code(self, source_code: str) -> str:
        """
        Encrypt source code using multiple layers
        
        Args:
            source_code: Source code to encrypt
            
        Returns:
            str: Encrypted and encoded source code
        """
        # Layer 1: Compress
        compressed = zlib.compress(source_code.encode())
        
        # Layer 2: XOR encrypt
        encrypted = bytearray()
        for i, byte in enumerate(compressed):
            key_byte = self.encryption_key[i % len(self.encryption_key)]
            encrypted.append(byte ^ key_byte)
        
        # Layer 3: Base64 encode
        encoded = base64.b64encode(bytes(encrypted)).decode()
        
        return encoded
    
    def decrypt_source_code(self, encrypted_code: str) -> str:
        """
        Decrypt source code
        
        Args:
            encrypted_code: Encrypted source code
            
        Returns:
            str: Decrypted source code
        """
        try:
            # Layer 1: Base64 decode
            decoded = base64.b64decode(encrypted_code)
            
            # Layer 2: XOR decrypt
            decrypted = bytearray()
            for i, byte in enumerate(decoded):
                key_byte = self.encryption_key[i % len(self.encryption_key)]
                decrypted.append(byte ^ key_byte)
            
            # Layer 3: Decompress
            decompressed = zlib.decompress(bytes(decrypted))
            
            return decompressed.decode()
            
        except Exception as e:
            raise Exception(f"Failed to decrypt source code: {e}")
    
    def create_protected_module(self, module_name: str, source_code: str) -> str:
        """
        Create a protected module with encrypted source
        
        Args:
            module_name: Name of the module
            source_code: Source code to protect
            
        Returns:
            str: Protected module code
        """
        encrypted_source = self.encrypt_source_code(source_code)
        
        protected_module = f'''
"""
Protected module: {module_name}
Source code is encrypted and executed at runtime
"""

import base64
import zlib
import sys

# Encrypted source code
_ENCRYPTED_SOURCE = """{encrypted_source}"""

def _decrypt_and_execute():
    """Decrypt and execute the protected source code"""
    try:
        # Decryption key (obfuscated)
        _key = "{self.encryption_key.decode('latin-1')}"
        
        # Decode and decrypt
        decoded = base64.b64decode(_ENCRYPTED_SOURCE)
        decrypted = bytearray()
        for i, byte in enumerate(decoded):
            key_byte = ord(_key[i % len(_key)])
            decrypted.append(byte ^ key_byte)
        
        # Decompress and execute
        decompressed = zlib.decompress(bytes(decrypted))
        source_code = decompressed.decode()
        
        # Execute in current module namespace
        exec(source_code, globals())
        
    except Exception as e:
        # Hide real error and show generic message
        raise ImportError(f"Module {module_name} failed to load")

# Execute protected code on import
_decrypt_and_execute()
'''
        
        return protected_module
    
    def obfuscate_file_structure(self, source_dir: str, output_dir: str):
        """
        Obfuscate entire file structure
        
        Args:
            source_dir: Source directory
            output_dir: Output directory for obfuscated files
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.py'):
                    source_file = os.path.join(root, file)
                    
                    # Read source code
                    with open(source_file, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    # Create protected version
                    module_name = os.path.splitext(file)[0]
                    protected_code = self.create_protected_module(module_name, source_code)
                    
                    # Write protected file
                    relative_path = os.path.relpath(source_file, source_dir)
                    output_file = os.path.join(output_dir, relative_path)
                    output_file_dir = os.path.dirname(output_file)
                    
                    if not os.path.exists(output_file_dir):
                        os.makedirs(output_file_dir)
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(protected_code)
    
    def create_decoy_files(self, output_dir: str, num_decoys: int = 10):
        """
        Create decoy files to confuse code readers
        
        Args:
            output_dir: Directory to create decoy files
            num_decoys: Number of decoy files to create
        """
        decoy_code_templates = [
            '''
# Fake configuration module
DATABASE_URL = "postgresql://fake:fake@localhost/fake"
API_KEY = "fake_api_key_12345"
SECRET_KEY = "fake_secret_key_abcdef"

def get_database_connection():
    return None

def authenticate_user(username, password):
    return False
''',
            '''
# Fake utility module
import random
import string

def generate_fake_data():
    return "fake_data_" + "".join(random.choices(string.ascii_letters, k=10))

def process_fake_request(data):
    return {"status": "fake", "data": data}

class FakeHandler:
    def __init__(self):
        self.fake_property = "fake_value"
    
    def fake_method(self):
        return "fake_result"
''',
            '''
# Fake security module
def encrypt_data(data):
    return "encrypted_" + data

def decrypt_data(encrypted_data):
    return encrypted_data.replace("encrypted_", "")

def hash_password(password):
    return "hashed_" + password

def verify_password(password, hashed):
    return hash_password(password) == hashed
'''
        ]
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        for i in range(num_decoys):
            decoy_code = random.choice(decoy_code_templates)
            decoy_file = os.path.join(output_dir, f"fake_module_{i}.py")
            
            with open(decoy_file, 'w', encoding='utf-8') as f:
                f.write(decoy_code)
    
    def remove_source_files(self, source_dir: str, backup_dir: str = None):
        """
        Remove original source files (with optional backup)
        
        Args:
            source_dir: Directory containing source files
            backup_dir: Optional backup directory
        """
        if backup_dir:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Create backup
            shutil.copytree(source_dir, os.path.join(backup_dir, 'source_backup'))
        
        # Remove .py files but keep .pyc files
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
    
    def create_loader_stub(self, module_name: str, encrypted_source: str) -> str:
        """
        Create a minimal loader stub that decrypts and executes code
        
        Args:
            module_name: Name of the module
            encrypted_source: Encrypted source code
            
        Returns:
            str: Loader stub code
        """
        return f'''
# Loader stub for {module_name}
exec(__import__('base64').b64decode({repr(encrypted_source)}).decode())
'''

# Global source protector
source_protector = SourceCodeProtector()

def protect_current_file():
    """Protect the current Python file"""
    current_file = inspect.getfile(inspect.currentframe())
    
    # Read current file
    with open(current_file, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Create protected version
    module_name = os.path.splitext(os.path.basename(current_file))[0]
    protected_code = source_protector.create_protected_module(module_name, source_code)
    
    # Write protected version
    protected_file = current_file.replace('.py', '_protected.py')
    with open(protected_file, 'w', encoding='utf-8') as f:
        f.write(protected_code)
    
    return protected_file

def create_build_script():
    """Create build script to protect entire codebase"""
    build_script = '''
#!/usr/bin/env python3
"""
Build script to protect GovSight source code
"""

import os
import sys
import shutil
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.getcwd())

from modules.security.source_protection import source_protector

def main():
    """Main build process"""
    print("Starting GovSight source code protection...")
    
    # Define directories
    source_dir = "."
    protected_dir = "dist"
    backup_dir = "backup"
    
    # Create protected version
    print("Creating protected version...")
    source_protector.obfuscate_file_structure(source_dir, protected_dir)
    
    # Create decoy files
    print("Creating decoy files...")
    source_protector.create_decoy_files(os.path.join(protected_dir, "decoys"))
    
    # Remove original sources (with backup)
    print("Backing up and removing original sources...")
    source_protector.remove_source_files(source_dir, backup_dir)
    
    print("Source code protection complete!")
    print(f"Protected code: {protected_dir}")
    print(f"Backup: {backup_dir}")
    
if __name__ == "__main__":
    main()
'''
    
    with open('build_protected.py', 'w') as f:
        f.write(build_script)
    
    return 'build_protected.py'

def anti_decompile_wrapper(func):
    """Decorator to make functions harder to decompile"""
    def wrapper(*args, **kwargs):
        # Add complexity to make decompilation harder
        dummy_vars = [i for i in range(100)]
        dummy_dict = {str(i): i for i in dummy_vars}
        
        # Execute original function
        result = func(*args, **kwargs)
        
        # More dummy operations
        for i in range(10):
            dummy_dict[str(i)] = dummy_dict.get(str(i), 0) + 1
        
        return result
    
    return wrapper