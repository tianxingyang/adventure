"""
Adventure Game Models Package

This package contains all SQLAlchemy models for the adventure game framework,
including database tables for projects, nodes, choices, conditions, and game states.
"""

# Import base classes first
from .base import Base, BaseModel, TimestampMixin, generate_uuid, utcnow

# Import models in dependency order
from .project import Project
from .node import GameNode
from .choice import Choice
from .condition import Condition, ConditionOperator
from .game_state import GameState

# Import utility functions
from .condition import evaluate_conditions_list, conditions_from_json_list

# Export all public components
__all__ = [
    # Base classes and utilities
    "Base",
    "BaseModel", 
    "TimestampMixin",
    "generate_uuid",
    "utcnow",
    
    # Core models
    "Project",
    "GameNode",
    "Choice", 
    "Condition",
    "GameState",
    
    # Enums
    "ConditionOperator",
    
    # Utility functions
    "evaluate_conditions_list",
    "conditions_from_json_list",
]

# Ensure all models are registered with SQLAlchemy Base
# This helps with foreign key relationships and migrations
def get_all_models():
    """
    Get list of all model classes for database operations.
    
    Returns:
        List of all SQLAlchemy model classes
    """
    return [
        Project,
        GameNode, 
        Choice,
        Condition,
        GameState,
    ]


def create_all_tables(engine):
    """
    Create all database tables.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine):
    """
    Drop all database tables.
    
    WARNING: This will delete all data!
    
    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.drop_all(bind=engine)


# Version info
__version__ = "1.0.0"