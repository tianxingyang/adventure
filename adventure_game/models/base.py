"""
Base database model with common fields and utilities.

This module provides the foundation for all database models in the adventure game framework,
including common fields like id, created_at, updated_at, and utility functions.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session


def generate_uuid() -> str:
    """Generate a new UUID string for use as primary key."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.utcnow()


@as_declarative()
class Base:
    """Base class for all SQLAlchemy models."""
    
    # Generate table name automatically from class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Common attributes for all models
    id: str = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=generate_uuid,
        nullable=False,
        doc="Unique identifier for the record"
    )
    
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        doc="Timestamp when the record was last updated"
    )


class BaseModel(Base):
    """
    Abstract base model with common fields and methods.
    
    All application models should inherit from this class to get:
    - UUID primary key
    - Created/updated timestamps
    - Common utility methods
    """
    
    __abstract__ = True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Returns:
            Dictionary representation of the model
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, session: Session, **kwargs: Any) -> "BaseModel":
        """
        Update model instance with provided values.
        
        Args:
            session: Database session
            **kwargs: Fields to update
            
        Returns:
            Updated model instance
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.updated_at = utcnow()
        session.add(self)
        return self
    
    @classmethod
    def create(cls, session: Session, **kwargs: Any) -> "BaseModel":
        """
        Create a new instance of the model.
        
        Args:
            session: Database session
            **kwargs: Model field values
            
        Returns:
            New model instance
        """
        instance = cls(**kwargs)
        session.add(instance)
        return instance
    
    def delete(self, session: Session) -> None:
        """
        Delete this model instance.
        
        Args:
            session: Database session
        """
        session.delete(self)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id='{self.id}')>"


class TimestampMixin:
    """
    Mixin for models that only need timestamp fields.
    
    Use this for models that don't need the full BaseModel functionality
    but still want created_at/updated_at tracking.
    """
    
    created_at: datetime = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        doc="Timestamp when the record was created"
    )
    
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
        doc="Timestamp when the record was last updated"
    )