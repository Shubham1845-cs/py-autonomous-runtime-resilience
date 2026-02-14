"""
Timeout Pattern

Enforces a maximum waiting time for service calls.

Uses threading to implement timeout enforcement without external dependencies.
"""

import threading
from typing import Callable, Any


class TimeoutError(Exception):
    """Raised when a function exceeds the timeout"""
    pass


class TimeoutGuard:
    """
    Timeout implementation using threading.
    
    Executes function in a separate thread and enforces maximum wait time.
    """
    
    def __init__(self, max_seconds: float = 5.0):
        """
        Initialize timeout guard.
        
        Args:
            max_seconds: Maximum execution time in seconds (default 5.0)
        """
        self.max_seconds = max_seconds
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with timeout enforcement.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result from function
            
        Raises:
            TimeoutError: If function exceeds max_seconds
            Exception: Any exception from the wrapped function
        """
        result = [None]
        exception = [None]
        
        def target():
            """Wrapper to capture result or exception"""
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        # Start function in thread
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        
        # Wait for max_seconds
        thread.join(timeout=self.max_seconds)
        
        # Check if thread is still alive (timeout occurred)
        if thread.is_alive():
            print(f"[Timeout] Function exceeded {self.max_seconds}s timeout")
            raise TimeoutError(
                f"Function exceeded {self.max_seconds}s timeout"
            )
        
        # Check if exception occurred
        if exception[0]:
            raise exception[0]
        
        return result[0]
