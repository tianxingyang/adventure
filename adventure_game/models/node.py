"""
GameNode model for individual nodes in adventure games.

This module defines the GameNode model which represents individual story nodes
in an adventure game, including their content, position in the editor, and
relationships to other game elements.
"""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Column, String, Text, Float, Index, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel

# Avoid circular imports
if TYPE_CHECKING:
    from .project import Project
    from .choice import Choice


class GameNode(BaseModel):
    """
    GameNode model representing a single node in an adventure game.
    
    Each node contains story content, choices for the player, and position
    information for the visual editor. Nodes are connected through choices
    to form the branching narrative structure.
    
    Attributes:
        project_id: ID of the project this node belongs to
        title: Short title/name for the node (used in editor)
        content: Main narrative text displayed to the player
        position_x: X coordinate for visual editor positioning
        position_y: Y coordinate for visual editor positioning
        is_start_node: Whether this is the starting node of the game
        is_end_node: Whether this is an ending node of the game
        project: Relationship to the parent Project
        choices: Relationship to Choice objects originating from this node
    """
    
    __tablename__ = "game_nodes"
    
    # Foreign key to project
    project_id: str = Column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the project this node belongs to"
    )
    
    # Node identification and content
    title: str = Column(
        String(255),
        nullable=False,
        doc="Short title or name for this node (displayed in editor)"
    )
    
    content: str = Column(
        Text,
        nullable=False,
        doc="Main narrative text content displayed to players"
    )
    
    # Visual editor positioning
    position_x: float = Column(
        Float,
        nullable=False,
        default=0.0,
        doc="X coordinate for positioning in the visual editor"
    )
    
    position_y: float = Column(
        Float,
        nullable=False,
        default=0.0,
        doc="Y coordinate for positioning in the visual editor"
    )
    
    # Node type flags
    is_start_node: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this node is the starting point of the game"
    )
    
    is_end_node: bool = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this node represents an ending of the game"
    )
    
    # Relationships
    project: "Project" = relationship(
        "Project",
        back_populates="nodes",
        doc="The project this node belongs to"
    )
    
    choices: List["Choice"] = relationship(
        "Choice",
        back_populates="source_node",
        cascade="all, delete-orphan",
        doc="All choices that originate from this node"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index("ix_game_nodes_project_id", "project_id"),
        Index("ix_game_nodes_is_start", "is_start_node"),
        Index("ix_game_nodes_is_end", "is_end_node"),
        Index("ix_game_nodes_title", "title"),
    )
    
    def get_available_choices(self, game_state: dict) -> List["Choice"]:
        """
        Get all choices available from this node based on current game state.
        
        Args:
            game_state: Current game state dictionary with variables
            
        Returns:
            List of choices that meet their conditions
        """
        available_choices = []
        
        for choice in self.choices:
            if choice.is_available(game_state):
                available_choices.append(choice)
        
        return available_choices
    
    def get_outgoing_connections(self) -> List[str]:
        """
        Get list of node IDs that this node connects to.
        
        Returns:
            List of target node IDs from all choices
        """
        target_ids = []
        for choice in self.choices:
            if choice.target_node_id:
                target_ids.append(choice.target_node_id)
        return target_ids
    
    def has_choices(self) -> bool:
        """
        Check if this node has any choices.
        
        Returns:
            True if node has choices, False otherwise
        """
        return len(self.choices) > 0
    
    def set_as_start_node(self, session: Session) -> None:
        """
        Mark this node as the start node, removing start flag from others.
        
        Args:
            session: Database session
        """
        # Remove start flag from all other nodes in the project
        session.query(GameNode).filter(
            GameNode.project_id == self.project_id,
            GameNode.id != self.id
        ).update({"is_start_node": False})
        
        # Set this node as start
        self.is_start_node = True
        session.add(self)
    
    def update_position(self, session: Session, x: float, y: float) -> None:
        """
        Update the visual position of this node.
        
        Args:
            session: Database session
            x: New X coordinate
            y: New Y coordinate
        """
        self.position_x = x
        self.position_y = y
        session.add(self)
    
    def validate_content(self) -> List[str]:
        """
        Validate node content and return any issues.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check title length
        if not self.title or len(self.title.strip()) == 0:
            errors.append("Node title cannot be empty")
        elif len(self.title) > 255:
            errors.append("Node title cannot exceed 255 characters")
        
        # Check content
        if not self.content or len(self.content.strip()) == 0:
            errors.append("Node content cannot be empty")
        
        # End nodes should not have choices
        if self.is_end_node and self.has_choices():
            errors.append("End nodes cannot have outgoing choices")
        
        # Non-end nodes should have at least one choice
        if not self.is_end_node and not self.has_choices():
            errors.append("Non-end nodes must have at least one choice")
        
        return errors
    
    def clone(self, session: Session, new_project_id: str, title_suffix: str = " (Copy)") -> "GameNode":
        """
        Create a copy of this node in the same or different project.
        
        Args:
            session: Database session
            new_project_id: ID of the project to copy to
            title_suffix: Suffix to add to the cloned node's title
            
        Returns:
            New GameNode instance (not yet committed)
        """
        cloned_node = GameNode(
            project_id=new_project_id,
            title=self.title + title_suffix,
            content=self.content,
            position_x=self.position_x + 50,  # Slight offset
            position_y=self.position_y + 50,
            is_start_node=False,  # Don't copy start/end flags
            is_end_node=self.is_end_node
        )
        
        session.add(cloned_node)
        return cloned_node
    
    def __repr__(self) -> str:
        """String representation of the game node."""
        return f"<GameNode(id='{self.id}', title='{self.title}', project_id='{self.project_id}')>"