"""
GameState model for managing player game sessions and save states.

This module defines the GameState model which represents a player's current
progress through an adventure game, including their current node, variables,
and game history.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Column, String, Integer, Index, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime

from .base import BaseModel, utcnow

# Avoid circular imports
if TYPE_CHECKING:
    from .project import Project
    from .node import GameNode
    from .choice import Choice


class GameState(BaseModel):
    """
    GameState model representing a player's current game session.
    
    This model tracks a player's progress through an adventure game,
    including their current location, variables, choice history, and
    save state information.
    
    Attributes:
        project_id: ID of the project/game being played
        player_id: ID of the player (session or user)
        current_node_id: ID of the current game node
        variables: JSON object containing game state variables
        choice_history: JSON array of previous choice IDs
        save_name: Optional name for this save state
        completed: Whether the game has been completed
        last_played_at: Timestamp of last activity
        project: Relationship to the Project being played
        current_node: Relationship to the current GameNode
    """
    
    __tablename__ = "game_states"
    
    # Game identification
    project_id: str = Column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the project/game being played"
    )
    
    # Player identification
    player_id: str = Column(
        String(255),
        nullable=False,
        doc="ID of the player (session ID or user ID)"
    )
    
    # Current game state
    current_node_id: Optional[str] = Column(
        UUID(as_uuid=False),
        ForeignKey("game_nodes.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the current game node (null if game ended)"
    )
    
    # Game variables and history
    variables: Dict[str, Any] = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="JSON object containing current game state variables"
    )
    
    choice_history: List[str] = Column(
        JSON,
        default=list,
        nullable=False,
        doc="JSON array of choice IDs representing player's path"
    )
    
    # Save state metadata
    save_name: Optional[str] = Column(
        String(255),
        nullable=True,
        doc="Optional name for this save state"
    )
    
    completed: bool = Column(
        String(1),  # Using string to avoid boolean issues with some databases
        default="N",
        nullable=False,
        doc="Whether the game has been completed (Y/N)"
    )
    
    last_played_at: datetime = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
        doc="Timestamp when this game state was last accessed"
    )
    
    # Relationships
    project: "Project" = relationship(
        "Project",
        doc="The project/game being played"
    )
    
    current_node: Optional["GameNode"] = relationship(
        "GameNode",
        doc="The current game node (if game is ongoing)"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index("ix_game_states_project_id", "project_id"),
        Index("ix_game_states_player_id", "player_id"),
        Index("ix_game_states_current_node_id", "current_node_id"),
        Index("ix_game_states_completed", "completed"),
        Index("ix_game_states_last_played", "last_played_at"),
        Index("ix_game_states_player_project", "player_id", "project_id"),
    )
    
    @property
    def is_completed(self) -> bool:
        """Check if the game has been completed."""
        return self.completed == "Y"
    
    @is_completed.setter
    def is_completed(self, value: bool) -> None:
        """Set the completion status."""
        self.completed = "Y" if value else "N"
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a game state variable value.
        
        Args:
            name: Variable name
            default: Default value if variable doesn't exist
            
        Returns:
            Variable value or default
        """
        return self.variables.get(name, default)
    
    def set_variable(self, session: Session, name: str, value: Any) -> None:
        """
        Set a game state variable value.
        
        Args:
            session: Database session
            name: Variable name
            value: Variable value
        """
        if self.variables is None:
            self.variables = {}
        
        self.variables[name] = value
        self.last_played_at = utcnow()
        session.add(self)
    
    def update_variables(self, session: Session, updates: Dict[str, Any]) -> None:
        """
        Update multiple game state variables.
        
        Args:
            session: Database session
            updates: Dictionary of variable updates
        """
        if self.variables is None:
            self.variables = {}
        
        self.variables.update(updates)
        self.last_played_at = utcnow()
        session.add(self)
    
    def add_choice_to_history(self, session: Session, choice_id: str) -> None:
        """
        Add a choice to the player's history.
        
        Args:
            session: Database session
            choice_id: ID of the chosen choice
        """
        if self.choice_history is None:
            self.choice_history = []
        
        self.choice_history.append(choice_id)
        self.last_played_at = utcnow()
        session.add(self)
    
    def move_to_node(self, session: Session, node_id: Optional[str]) -> None:
        """
        Move the player to a different node.
        
        Args:
            session: Database session
            node_id: ID of the target node (None for game ending)
        """
        self.current_node_id = node_id
        self.last_played_at = utcnow()
        
        # If moving to None (game ending), mark as completed
        if node_id is None:
            self.is_completed = True
        
        session.add(self)
    
    def make_choice(self, session: Session, choice: "Choice") -> Dict[str, Any]:
        """
        Process a player's choice and update game state.
        
        Args:
            session: Database session
            choice: The Choice object selected by the player
            
        Returns:
            Dictionary with updated game state information
        """
        from .choice import Choice
        
        # Validate that choice is available
        if not choice.is_available(self.variables):
            raise ValueError("Choice is not available with current game state")
        
        # Apply state changes from the choice
        new_variables = choice.apply_state_changes(self.variables)
        self.variables = new_variables
        
        # Add choice to history
        self.add_choice_to_history(session, choice.id)
        
        # Move to target node
        self.move_to_node(session, choice.target_node_id)
        
        return {
            "new_node_id": choice.target_node_id,
            "updated_variables": new_variables,
            "completed": self.is_completed,
            "choice_history": self.choice_history
        }
    
    def get_available_choices(self, session: Session) -> List["Choice"]:
        """
        Get all choices available from the current node.
        
        Args:
            session: Database session
            
        Returns:
            List of available Choice objects
        """
        if not self.current_node:
            return []
        
        return self.current_node.get_available_choices(self.variables)
    
    def restart_game(self, session: Session) -> None:
        """
        Restart the game from the beginning.
        
        Args:
            session: Database session
        """
        # Find the start node
        start_node = self.project.get_start_node(session)
        if not start_node:
            raise ValueError("Project has no start node")
        
        # Reset game state
        self.current_node_id = start_node.id
        self.variables = {}
        self.choice_history = []
        self.is_completed = False
        self.last_played_at = utcnow()
        
        session.add(self)
    
    def create_save_point(self, session: Session, save_name: str) -> "GameState":
        """
        Create a new save state as a copy of the current state.
        
        Args:
            session: Database session
            save_name: Name for the save state
            
        Returns:
            New GameState instance representing the save point
        """
        save_state = GameState(
            project_id=self.project_id,
            player_id=self.player_id,
            current_node_id=self.current_node_id,
            variables=self.variables.copy() if self.variables else {},
            choice_history=self.choice_history.copy() if self.choice_history else [],
            save_name=save_name,
            completed=self.completed,
            last_played_at=utcnow()
        )
        
        session.add(save_state)
        return save_state
    
    def get_progress_info(self, session: Session) -> Dict[str, Any]:
        """
        Get information about game progress.
        
        Args:
            session: Database session
            
        Returns:
            Dictionary containing progress information
        """
        total_nodes = self.project.get_node_count(session)
        visited_nodes = len(set(
            choice.source_node.id for choice in session.query(Choice).filter(
                Choice.id.in_(self.choice_history or [])
            ).all()
        ))
        
        return {
            "total_nodes": total_nodes,
            "visited_nodes": visited_nodes,
            "completion_percentage": (visited_nodes / total_nodes * 100) if total_nodes > 0 else 0,
            "choices_made": len(self.choice_history or []),
            "current_node": self.current_node.title if self.current_node else None,
            "completed": self.is_completed,
            "last_played": self.last_played_at,
            "save_name": self.save_name
        }
    
    def validate_state(self) -> List[str]:
        """
        Validate game state data and return any issues.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check player ID
        if not self.player_id or len(self.player_id.strip()) == 0:
            errors.append("Player ID cannot be empty")
        
        # Check variables structure
        if self.variables is not None and not isinstance(self.variables, dict):
            errors.append("Variables must be a dictionary/object")
        
        # Check choice history structure
        if self.choice_history is not None and not isinstance(self.choice_history, list):
            errors.append("Choice history must be an array")
        
        # Validate completion status
        if self.completed not in ["Y", "N"]:
            errors.append("Completion status must be 'Y' or 'N'")
        
        return errors
    
    @classmethod
    def create_new_game(cls, session: Session, project_id: str, player_id: str, 
                       save_name: Optional[str] = None) -> "GameState":
        """
        Create a new game state for a player starting a project.
        
        Args:
            session: Database session
            project_id: ID of the project to start
            player_id: ID of the player
            save_name: Optional save name
            
        Returns:
            New GameState instance ready to play
        """
        from .project import Project
        
        # Get the project and find start node
        project = session.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        start_node = project.get_start_node(session)
        if not start_node:
            raise ValueError("Project has no start node")
        
        # Create new game state
        game_state = cls(
            project_id=project_id,
            player_id=player_id,
            current_node_id=start_node.id,
            variables={},
            choice_history=[],
            save_name=save_name,
            completed="N",
            last_played_at=utcnow()
        )
        
        session.add(game_state)
        return game_state
    
    def __repr__(self) -> str:
        """String representation of the game state."""
        return f"<GameState(id='{self.id}', player='{self.player_id}', project='{self.project_id}')>"