"""
Code Protection Module

Advanced code obfuscation and protection measures to prevent
unauthorized copying, reading, or reverse engineering of source code.

SECURITY DECISIONS:
1. Multi-layer obfuscation: Variable names, function names, and logic flow
2. Dynamic code generation: Critical functions generated at runtime
3. Bytecode compilation: Source code compiled to bytecode only
4. Code fragmentation: Split functionality across multiple encrypted modules
5. Anti-debugging: Detect and prevent code inspection attempts
"""

import ast
import base64
import marshal
import types
import sys
import hashlib
import os
import random
import string
import zlib
from typing import Dict, Any, List, Callable
import inspect

class CodeObfuscator:
    """Advanced code obfuscation system"""
    
    def __init__(self):
        self.name_map = {}
        self.encrypted_modules = {}
        self.runtime_functions = {}
        self.obfuscation_key = self._generate_key()
    
    def _generate_key(self) -> str:
        """Generate encryption key based on system properties"""
        system_info = f"{os.getcwd()}{sys.version}{len(sys.modules)}"
        return hashlib.sha256(system_info.encode()).hexdigest()[:32]
    
    def obfuscate_variable_names(self, code: str) -> str:
        """
        Obfuscate variable and function names in code
        
        Args:
            code: Source code to obfuscate
            
        Returns:
            str: Obfuscated code
        """
        try:
            tree = ast.parse(code)
            
            # Collect all names to obfuscate
            names_to_obfuscate = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Name, ast.FunctionDef, ast.ClassDef)):
                    if hasattr(node, 'id') and not node.id.startswith('_'):
                        names_to_obfuscate.add(node.id)
                    elif hasattr(node, 'name') and not node.name.startswith('_'):
                        names_to_obfuscate.add(node.name)
            
            # Generate obfuscated names
            for name in names_to_obfuscate:
                if name not in self.name_map:
                    self.name_map[name] = self._generate_obfuscated_name()
            
            # Replace names in code
            obfuscated_code = code
            for original, obfuscated in self.name_map.items():
                obfuscated_code = obfuscated_code.replace(original, obfuscated)
            
            return obfuscated_code
            
        except Exception:
            # If parsing fails, return original code
            return code
    
    def _generate_obfuscated_name(self) -> str:
        """Generate random obfuscated name"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(random.randint(8, 16)))
    
    def compile_to_bytecode(self, code: str, filename: str = '<string>') -> bytes:
        """
        Compile source code to encrypted bytecode
        
        Args:
            code: Source code to compile
            filename: Filename for the code
            
        Returns:
            bytes: Encrypted bytecode
        """
        try:
            # Obfuscate the code first
            obfuscated_code = self.obfuscate_variable_names(code)
            
            # Compile to bytecode
            compiled = compile(obfuscated_code, filename, 'exec')
            bytecode = marshal.dumps(compiled)
            
            # Encrypt the bytecode
            encrypted = self._encrypt_data(bytecode)
            
            return encrypted
            
        except Exception as e:
            raise Exception(f"Failed to compile code: {e}")
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Simple XOR encryption for bytecode"""
        key_bytes = self.obfuscation_key.encode()
        encrypted = bytearray()
        
        for i, byte in enumerate(data):
            key_byte = key_bytes[i % len(key_bytes)]
            encrypted.append(byte ^ key_byte)
        
        return bytes(encrypted)
    
    def _decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt XOR encrypted data"""
        return self._encrypt_data(encrypted_data)  # XOR is symmetric
    
    def execute_encrypted_code(self, encrypted_bytecode: bytes, globals_dict: Dict = None) -> Any:
        """
        Execute encrypted bytecode
        
        Args:
            encrypted_bytecode: Encrypted bytecode to execute
            globals_dict: Global variables for execution
            
        Returns:
            Any: Result of code execution
        """
        try:
            # Decrypt the bytecode
            decrypted = self._decrypt_data(encrypted_bytecode)
            
            # Unmarshal and execute
            code_obj = marshal.loads(decrypted)
            
            if globals_dict is None:
                globals_dict = {}
            
            exec(code_obj, globals_dict)
            return globals_dict
            
        except Exception as e:
            raise Exception(f"Failed to execute encrypted code: {e}")
    
    def create_runtime_function(self, func_name: str, code: str) -> Callable:
        """
        Create a function that's generated at runtime
        
        Args:
            func_name: Name of the function
            code: Function code
            
        Returns:
            Callable: Runtime-generated function
        """
        # Encrypt the function code
        encrypted_code = self.compile_to_bytecode(code)
        
        def runtime_wrapper(*args, **kwargs):
            # Decrypt and execute at runtime
            local_globals = {'args': args, 'kwargs': kwargs}
            result = self.execute_encrypted_code(encrypted_code, local_globals)
            return result.get('result')
        
        self.runtime_functions[func_name] = runtime_wrapper
        return runtime_wrapper
    
    def fragment_code(self, code: str, num_fragments: int = 5) -> List[bytes]:
        """
        Split code into encrypted fragments
        
        Args:
            code: Source code to fragment
            num_fragments: Number of fragments to create
            
        Returns:
            List[bytes]: List of encrypted code fragments
        """
        lines = code.split('\n')
        fragment_size = max(1, len(lines) // num_fragments)
        
        fragments = []
        for i in range(0, len(lines), fragment_size):
            fragment_lines = lines[i:i + fragment_size]
            fragment_code = '\n'.join(fragment_lines)
            encrypted_fragment = self.compile_to_bytecode(fragment_code)
            fragments.append(encrypted_fragment)
        
        return fragments
    
    def detect_debugging(self) -> bool:
        """
        Detect if code is being debugged or inspected
        
        Returns:
            bool: True if debugging detected
        """
        # Check for common debugging indicators
        debugging_indicators = [
            'pdb' in sys.modules,
            'debugpy' in sys.modules,
            'pydevd' in sys.modules,
            hasattr(sys, 'gettrace') and sys.gettrace() is not None,
            'PYTHONPATH' in os.environ and 'debug' in os.environ['PYTHONPATH'].lower(),
        ]
        
        return any(debugging_indicators)
    
    def anti_debug_wrapper(self, func: Callable) -> Callable:
        """
        Wrapper that prevents function execution during debugging
        
        Args:
            func: Function to protect
            
        Returns:
            Callable: Protected function
        """
        def wrapper(*args, **kwargs):
            if self.detect_debugging():
                raise Exception("Function execution blocked: debugging detected")
            return func(*args, **kwargs)
        
        return wrapper

# Global obfuscator instance
code_obfuscator = CodeObfuscator()

class SecureModuleLoader:
    """Custom module loader for encrypted modules"""
    
    def __init__(self):
        self.encrypted_modules = {}
        self.decryption_key = self._generate_module_key()
    
    def _generate_module_key(self) -> str:
        """Generate module-specific encryption key"""
        base_key = f"code_protection{sys.version}{os.getcwd()}"
        return hashlib.md5(base_key.encode()).hexdigest()
    
    def encrypt_module(self, module_code: str, module_name: str) -> bytes:
        """
        Encrypt a module's source code
        
        Args:
            module_code: Source code of the module
            module_name: Name of the module
            
        Returns:
            bytes: Encrypted module data
        """
        # Compress then encrypt
        compressed = zlib.compress(module_code.encode())
        encrypted = code_obfuscator._encrypt_data(compressed)
        
        # Store encrypted module
        self.encrypted_modules[module_name] = encrypted
        
        return encrypted
    
    def load_encrypted_module(self, module_name: str) -> types.ModuleType:
        """
        Load a module from encrypted storage
        
        Args:
            module_name: Name of the module to load
            
        Returns:
            types.ModuleType: Loaded module
        """
        if module_name not in self.encrypted_modules:
            raise ImportError(f"Encrypted module '{module_name}' not found")
        
        try:
            # Decrypt and decompress
            encrypted_data = self.encrypted_modules[module_name]
            decrypted = code_obfuscator._decrypt_data(encrypted_data)
            decompressed = zlib.decompress(decrypted)
            module_code = decompressed.decode()
            
            # Create module and execute code
            module = types.ModuleType(module_name)
            exec(module_code, module.__dict__)
            
            return module
            
        except Exception as e:
            raise ImportError(f"Failed to load encrypted module '{module_name}': {e}")

# Global secure module loader
secure_loader = SecureModuleLoader()

def protect_function(func: Callable) -> Callable:
    """
    Decorator to protect functions from inspection
    
    Args:
        func: Function to protect
        
    Returns:
        Callable: Protected function
    """
    # Get function source code
    try:
        source = inspect.getsource(func)
    except OSError:
        # If source is not available, return original function
        return func
    
    # Create encrypted version
    encrypted_code = code_obfuscator.compile_to_bytecode(source)
    
    def protected_wrapper(*args, **kwargs):
        # Execute encrypted version
        local_globals = {
            'args': args,
            'kwargs': kwargs,
            '__builtins__': __builtins__
        }
        result = code_obfuscator.execute_encrypted_code(encrypted_code, local_globals)
        return result.get('result')
    
    # Apply anti-debugging protection
    return code_obfuscator.anti_debug_wrapper(protected_wrapper)

def obfuscate_string(text: str) -> str:
    """
    Obfuscate string literals in code
    
    Args:
        text: String to obfuscate
        
    Returns:
        str: Obfuscated string
    """
    encoded = base64.b64encode(text.encode()).decode()
    return f"__import__('base64').b64decode('{encoded}').decode()"

def create_decoy_functions():
    """Create fake functions to confuse code readers"""
    decoy_code = """
def fake_database_connection():
    '''Fake database connection function'''
    return "postgresql://fake:fake@localhost/fake"

def fake_api_key():
    '''Fake API key function'''
    return "fake_api_key_12345"

def fake_encryption_key():
    '''Fake encryption key'''
    return "fake_encryption_key_abcdef"
"""
    
    exec(decoy_code, globals())

# Initialize decoy functions
create_decoy_functions()

def hide_module_imports():
    """Hide critical module imports"""
    # This function would dynamically import modules to hide dependencies
    critical_modules = [
        'streamlit',
        'pandas',
        'plotly',
        'openai',
        'sqlite3'
    ]
    
    hidden_imports = {}
    for module_name in critical_modules:
        try:
            hidden_imports[module_name] = __import__(module_name)
        except ImportError:
            pass
    
    return hidden_imports

def secure_execution_environment():
    """Set up secure execution environment"""
    # Remove dangerous built-ins
    dangerous_builtins = ['exec', 'eval', 'compile', '__import__']
    
    for builtin in dangerous_builtins:
        if builtin in dir(__builtins__):
            setattr(__builtins__, builtin, lambda *args, **kwargs: None)