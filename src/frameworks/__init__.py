"""
Shared frameworks for the SysAIdmin platform.

This module contains reusable frameworks that can be used across multiple use cases.
"""

# Import GraphMCP framework for easy access
try:
    from .graphmcp import *
except ImportError:
    # GraphMCP might not be installed or configured
    pass