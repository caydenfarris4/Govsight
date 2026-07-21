"""
Runtime Protection Module

Advanced runtime protection to prevent code inspection, debugging,
and reverse engineering during application execution.

RUNTIME PROTECTION FEATURES:
1. Anti-debugging detection and prevention
2. Code injection prevention
3. Memory protection for sensitive data
4. Dynamic code modification detection
5. Execution environment validation
"""

import sys
import os
import threading
import time
import hashlib
import inspect
import gc
from typing import Dict, Any, Callable, List
import functools
import random

class RuntimeProtector:
    """Runtime protection system for GovSight application"""
    
    def __init__(self):
        self.protection_active = True
        self.check_interval = 5.0  # Check every 5 seconds
        self.protection_thread = None
        self.original_functions = {}
        self.protected_globals = set()
        self.execution_checksum = None
        
    def start_protection(self):
        """Start runtime protection monitoring"""
        if self.protection_thread is None or not self.protection_thread.is_alive():
            self.protection_thread = threading.Thread(target=self._protection_loop, daemon=True)
            self.protection_thread.start()
    
    def stop_protection(self):
        """Stop runtime protection monitoring"""
        self.protection_active = False
        if self.protection_thread:
            self.protection_thread.join(timeout=1.0)
    
    def _protection_loop(self):
        """Main protection monitoring loop"""
        while self.protection_active:
            try:
                # Check for debugging
                if self._detect_debugging():
                    self._handle_security_violation("Debugging detected")
                
                # Check for code injection
                if self._detect_code_injection():
                    self._handle_security_violation("Code injection detected")
                
                # Check execution integrity
                if self._check_execution_integrity():
                    self._handle_security_violation("Execution integrity compromised")
                
                # Check for memory tampering
                if self._detect_memory_tampering():
                    self._handle_security_violation("Memory tampering detected")
                
                time.sleep(self.check_interval)
                
            except Exception:
                # Silently handle errors to avoid revealing protection mechanism
                pass
    
    def _detect_debugging(self) -> bool:
        """Detect if application is being debugged"""
        debugging_indicators = [
            # Python debugger check
            hasattr(sys, 'gettrace') and sys.gettrace() is not None,
            
            # Common debugger modules
            'pdb' in sys.modules,
            'pudb' in sys.modules,
            'ipdb' in sys.modules,
            'debugpy' in sys.modules,
            'pydevd' in sys.modules,
            
            # IDE debugging
            'pydev' in str(sys.modules),
            'PYCHARM_HOSTED' in os.environ,
            'PYTHONPATH' in os.environ and 'pycharm' in os.environ.get('PYTHONPATH', '').lower(),
            
            # Timing-based detection
            self._timing_based_debug_detection(),
        ]
        
        return any(debugging_indicators)
    
    def _timing_based_debug_detection(self) -> bool:
        """Detect debugging through timing analysis"""
        start_time = time.time()
        
        # Execute some operations that should be fast
        for i in range(1000):
            dummy = i * 2
        
        execution_time = time.time() - start_time
        
        # If execution is too slow, might be debugging
        return execution_time > 0.1  # 100ms threshold
    
    def _detect_code_injection(self) -> bool:
        """Detect code injection attempts"""
        # Check for new modules that weren't there at startup
        current_modules = set(sys.modules.keys())
        
        # Check for suspicious module names
        suspicious_modules = [
            'inject', 'hook', 'patch', 'monkey', 'override',
            'debug', 'trace', 'profile', 'inspect'
        ]
        
        for module_name in current_modules:
            if any(suspicious in module_name.lower() for suspicious in suspicious_modules):
                return True
        
        return False
    
    def _check_execution_integrity(self) -> bool:
        """Check if execution environment has been compromised"""
        # Check if critical functions have been modified
        critical_functions = [
            'exec', 'eval', 'compile', '__import__',
            'open', 'input', 'raw_input'
        ]
        
        for func_name in critical_functions:
            if hasattr(__builtins__, func_name):
                current_func = getattr(__builtins__, func_name)
                if func_name in self.original_functions:
                    if current_func != self.original_functions[func_name]:
                        return True
                else:
                    self.original_functions[func_name] = current_func
        
        return False
    
    def _detect_memory_tampering(self) -> bool:
        """Detect memory tampering attempts"""
        # Check garbage collection statistics
        gc_stats = gc.get_stats()
        
        # Check for unusual object counts
        if gc_stats and len(gc_stats) > 0:
            if gc_stats[0].get('collections', 0) > 1000:
                return True
        
        return False
    
    def _handle_security_violation(self, violation_type: str):
        """Handle security violations"""
        # Log the violation (silently)
        self._log_security_event(violation_type)
        
        # Take protective action
        if violation_type == "Debugging detected":
            # Obfuscate execution
            self._obfuscate_execution()
        elif violation_type == "Code injection detected":
            # Reset critical functions
            self._reset_critical_functions()
        elif violation_type == "Memory tampering detected":
            # Clear sensitive data
            self._clear_sensitive_data()
        
        # Optionally exit application
        if self._should_exit_on_violation(violation_type):
            sys.exit(1)
    
    def _log_security_event(self, event: str):
        """Log security events (silently)"""
        # Store in a hidden location or encrypt
        pass
    
    def _obfuscate_execution(self):
        """Obfuscate execution to make debugging harder"""
        # Add random delays
        time.sleep(random.uniform(0.1, 0.5))
        
        # Execute dummy operations
        for _ in range(random.randint(100, 1000)):
            dummy = random.random() * random.random()
    
    def _reset_critical_functions(self):
        """Reset critical functions to original state"""
        for func_name, original_func in self.original_functions.items():
            if hasattr(__builtins__, func_name):
                setattr(__builtins__, func_name, original_func)
    
    def _clear_sensitive_data(self):
        """Clear sensitive data from memory"""
        # Force garbage collection
        gc.collect()
        
        # Clear protected globals
        for var_name in self.protected_globals:
            if var_name in globals():
                del globals()[var_name]
    
    def _should_exit_on_violation(self, violation_type: str) -> bool:
        """Determine if application should exit on violation"""
        critical_violations = [
            "Debugging detected",
            "Code injection detected"
        ]
        
        return violation_type in critical_violations
    
    def protect_function(self, func: Callable) -> Callable:
        """Decorator to protect individual functions"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check protection status
            if not self.protection_active:
                return func(*args, **kwargs)
            
            # Anti-debugging check
            if self._detect_debugging():
                # Return fake result or exit
                return None
            
            # Execute with protection
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Handle exceptions securely
                self._handle_exception(e)
                return None
        
        return wrapper
    
    def _handle_exception(self, exception: Exception):
        """Handle exceptions without revealing information"""
        # Log exception securely
        pass
    
    def protect_variable(self, var_name: str, value: Any):
        """Protect a variable from tampering"""
        self.protected_globals.add(var_name)
        globals()[var_name] = value
    
    def create_protected_context(self):
        """Create a protected execution context"""
        # Disable dangerous built-ins
        dangerous_builtins = ['exec', 'eval', 'compile', '__import__']
        
        protected_builtins = {}
        for name in dir(__builtins__):
            if name not in dangerous_builtins:
                protected_builtins[name] = getattr(__builtins__, name)
        
        return {'__builtins__': protected_builtins}
    
    def validate_execution_environment(self) -> bool:
        """Validate that execution environment is safe"""
        checks = [
            # Check Python version
            sys.version_info >= (3, 7),
            
            # Check for standard library
            'os' in sys.modules,
            'sys' in sys.modules,
            
            # Check current directory
            os.path.exists('.'),
            
            # Check write permissions
            os.access('.', os.W_OK),
        ]
        
        return all(checks)

# Global runtime protector instance
runtime_protector = RuntimeProtector()

def protected_function(func: Callable) -> Callable:
    """Decorator for function-level protection"""
    return runtime_protector.protect_function(func)

def start_runtime_protection():
    """Start runtime protection system"""
    runtime_protector.start_protection()

def stop_runtime_protection():
    """Stop runtime protection system"""
    runtime_protector.stop_protection()

def protect_sensitive_data(var_name: str, value: Any):
    """Protect sensitive data from tampering"""
    runtime_protector.protect_variable(var_name, value)

def validate_environment() -> bool:
    """Validate execution environment"""
    return runtime_protector.validate_execution_environment()

# Auto-start protection when module is imported
start_runtime_protection()