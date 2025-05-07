"""
Service lifetime management for the Uno DI container.

This module defines the different service lifetimes that can be used in the dependency injection container.
"""

from enum import Enum


class ServiceLifetime(Enum):
    """Enum representing different service lifetimes."""
    
    TRANSIENT = 'transient'
    """Service is created each time it's requested."""
    
    SCOPED = 'scoped'
    """Service is created once per scope."""
    
    SINGLETON = 'singleton'
    """Service is created once and reused throughout the application."""
