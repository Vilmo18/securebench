import json
from pathlib import Path
from typing import Any, Dict, Optional

# Define a whitelist of allowed Python built-in functions
ALLOWED_FUNCTIONS = ["abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable", "chr", "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate", "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr", "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len", "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open", "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr", "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip"]

# Define a function to validate the script content
def validate_script(script: str) -> bool:
    # Check if the script contains any disallowed characters
    if not script.isalnum():
        return False
    
    # Check if the script contains any built-in functions that are not in the whitelist
    for function in ALLOWED_FUNCTIONS:
        if function in script:
            return True
    
    return False

# Define a function to resolve the log path
def resolve_log_path(log_path: str) -> Optional[str]:
    # Check if the log path is valid and does not contain any null bytes or segments that start with "../"
    if not log_path.startswith("/") and not log_path.endswith(".txt") and not ".." in log_path:
        return None
    
    # Resolve the log path against a configured logs directory
    resolved_log_path = Path("logs/") / log_path
    
    # Check if the resolved log path is within the configured logs directory
    if not resolved_log_path.is_relative_to("logs/"):
        return None
    
    return str(resolved_log_path)

# Define a function to execute the script and capture its output
def execute_script(script: str, log_path: str) -> Any:
    # Validate the script content
    if not validate_script(script):
        raise ValueError("Invalid script")
    
    # Resolve the log path
    resolved_log_path = resolve_log_path(log_path)
    if resolved_log_path is None:
        raise ValueError("Invalid log path")
    
    # Execute the script and capture its output
    with open(resolved_log_path, "w") as f:
        exec(script, {"__builtins__": {}}, {"f": f})
    
    return None