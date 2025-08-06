"""
Project model for managing adventure game projects.

This module defines the Project model which represents a complete adventure game
project with metadata, ownership, and publishing status.
"""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Column, String, Text, Index
from sqlalchemy.orm import relationship, Session

from .base import BaseModel

# Avoid circular imports
if TYPE_CHECKING:
    from .node import GameNode


class Project(BaseModel):
    """
    Project model representing an adventure game project.
    
    A project contains all the game nodes, choices, and metadata for a complete
    adventure game. Projects belong to users and can be published for sharing.
    
    Attributes:
        name: Display name of the project
        description: Optional description of the game/story
        user_id: ID of the user who owns this project
        published: Whether the project is published publicly
        nodes: Relationship to GameNode objects in this project
    """
    
    __tablename__ = "projects"
    
    # Basic project information
    name: str = Column(
        String(255),
        nullable=False,
        doc="Display name of the adventure game project"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Optional description of the game story and content"
    )
    
    # User ownership
    user_id: str = Column(
        String(255),
        nullable=False,
        doc="ID of the user who owns this project"
    )
    
    # Publishing status
    published: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this project is published and publicly accessible"
    )
    
    # Relationships
    nodes: List["GameNode"] = relationship(
        "GameNode",
        back_populates="project",
        cascade="all, delete-orphan",
        doc="All game nodes that belong to this project"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index("ix_projects_user_id", "user_id"),
        Index("ix_projects_published", "published"),
        Index("ix_projects_name", "name"),
    )
    
    def get_start_node(self, session: Session) -> Optional["GameNode"]:
        """
        Get the starting node for this project.
        
        Args:
            session: Database session
            
        Returns:
            The start node if found, None otherwise
        """
        from .node import GameNode
        
        return session.query(GameNode).filter(
            GameNode.project_id == self.id,
            GameNode.is_start_node == True
        ).first()
    
    def get_end_nodes(self, session: Session) -> List["GameNode"]:
        """
        Get all ending nodes for this project.
        
        Args:
            session: Database session
            
        Returns:
            List of end nodes
        """
        from .node import GameNode
        
        return session.query(GameNode).filter(
            GameNode.project_id == self.id,
            GameNode.is_end_node == True
        ).all()
    
    def get_node_count(self, session: Session) -> int:
        """
        Get the total number of nodes in this project.
        
        Args:
            session: Database session
            
        Returns:
            Number of nodes in the project
        """
        from .node import GameNode
        
        return session.query(GameNode).filter(
            GameNode.project_id == self.id
        ).count()
    
    def validate_structure(self, session: Session) -> List[str]:
        """
        Validate the project structure and return any issues found.
        
        Args:
            session: Database session
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check if project has at least one start node
        start_node = self.get_start_node(session)
        if not start_node:
            errors.append("Project must have exactly one start node")
        
        # Check if project has at least one end node
        end_nodes = self.get_end_nodes(session)
        if not end_nodes:
            errors.append("Project must have at least one end node")
        
        # Check for orphaned nodes (nodes with no incoming connections except start)
        from .node import GameNode
        from .choice import Choice
        
        all_nodes = session.query(GameNode).filter(
            GameNode.project_id == self.id
        ).all()
        
        # Get all target node IDs from choices
        target_node_ids = set()
        for node in all_nodes:
            for choice in node.choices:
                if choice.target_node_id:
                    target_node_ids.add(choice.target_node_id)
        
        # Find orphaned nodes (not reachable from start and not the start node itself)
        for node in all_nodes:
            if not node.is_start_node and node.id not in target_node_ids:
                errors.append(f"Node '{node.title}' is unreachable from other nodes")
        
        return errors
    
    def publish(self, session: Session) -> List[str]:
        """
        Attempt to publish this project.
        
        Args:
            session: Database session
            
        Returns:
            List of validation errors (empty if published successfully)
        """
        # Validate structure before publishing
        errors = self.validate_structure(session)
        
        if not errors:
            self.published = True
            session.add(self)
        
        return errors
    
    def unpublish(self, session: Session) -> None:
        """
        Unpublish this project.
        
        Args:
            session: Database session
        """
        self.published = False
        session.add(self)
    
    def __repr__(self) -> str:
        """String representation of the project."""
        return f"<Project(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"