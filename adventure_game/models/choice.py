"""
Choice model for player choices that connect game nodes.

This module defines the Choice model which represents individual choices
available to players at each game node, including conditions for availability
and state changes that occur when selected.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from sqlalchemy import Column, String, Text, Integer, Index, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSON

from .base import BaseModel

# Avoid circular imports
if TYPE_CHECKING:
    from .node import GameNode


class Choice(BaseModel):
    """
    Choice model representing a player choice in an adventure game.
    
    Choices connect game nodes and can have conditions that must be met
    for them to be available to the player. When selected, choices can
    modify the game state through state changes.
    
    Attributes:
        node_id: ID of the source node this choice belongs to
        text: The choice text displayed to the player
        target_node_id: ID of the target node (None for ending choices)
        display_order: Order for displaying choices (lower numbers first)
        conditions: JSON array of condition objects for availability
        state_changes: JSON object of state variables to modify
        source_node: Relationship to the source GameNode
        target_node: Relationship to the target GameNode (if exists)
    """
    
    __tablename__ = "choices"
    
    # Foreign key to source node
    node_id: str = Column(
        UUID(as_uuid=False),
        ForeignKey("game_nodes.id", ondelete="CASCADE"),
        nullable=False,
        doc="ID of the source node this choice belongs to"
    )
    
    # Choice content
    text: str = Column(
        Text,
        nullable=False,
        doc="The choice text displayed to the player"
    )
    
    # Target connection (optional for ending choices)
    target_node_id: Optional[str] = Column(
        UUID(as_uuid=False),
        ForeignKey("game_nodes.id", ondelete="SET NULL"),
        nullable=True,
        doc="ID of the target node (null for ending choices)"
    )
    
    # Display ordering
    display_order: int = Column(
        Integer,
        default=0,
        nullable=False,
        doc="Order for displaying choices (lower numbers shown first)"
    )
    
    # Conditions for choice availability (JSON array)
    conditions: List[Dict[str, Any]] = Column(
        JSON,
        default=list,
        nullable=False,
        doc="JSON array of condition objects that must be met for choice availability"
    )
    
    # State modifications when choice is selected (JSON object)
    state_changes: Dict[str, Any] = Column(
        JSON,
        default=dict,
        nullable=False,
        doc="JSON object of state variables to modify when choice is selected"
    )
    
    # Relationships
    source_node: "GameNode" = relationship(
        "GameNode",
        back_populates="choices",
        foreign_keys=[node_id],
        doc="The source node this choice belongs to"
    )
    
    target_node: Optional["GameNode"] = relationship(
        "GameNode",
        foreign_keys=[target_node_id],
        doc="The target node this choice leads to (if any)"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index("ix_choices_node_id", "node_id"),
        Index("ix_choices_target_node_id", "target_node_id"),
        Index("ix_choices_display_order", "display_order"),
    )
    
    def is_available(self, game_state: Dict[str, Any]) -> bool:
        """
        Check if this choice is available based on current game state.
        
        Args:
            game_state: Dictionary containing current game state variables
            
        Returns:
            True if all conditions are met, False otherwise
        """
        if not self.conditions:
            return True  # No conditions means always available
        
        return self._evaluate_conditions(self.conditions, game_state)
    
    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], game_state: Dict[str, Any]) -> bool:
        """
        Evaluate a list of conditions against the current game state.
        
        Args:
            conditions: List of condition dictionaries
            game_state: Current game state variables
            
        Returns:
            True if conditions are satisfied
        """
        if not conditions:
            return True
        
        results = []
        
        for condition in conditions:
            variable = condition.get("variable", "")
            operator = condition.get("operator", "eq")
            expected_value = condition.get("value")
            
            # Get current value from game state
            current_value = game_state.get(variable)
            
            # Evaluate condition based on operator
            if operator == "eq":
                result = current_value == expected_value
            elif operator == "ne":
                result = current_value != expected_value
            elif operator == "gt":
                result = (current_value or 0) > (expected_value or 0)
            elif operator == "gte":
                result = (current_value or 0) >= (expected_value or 0)
            elif operator == "lt":
                result = (current_value or 0) < (expected_value or 0)
            elif operator == "lte":
                result = (current_value or 0) <= (expected_value or 0)
            elif operator == "contains":
                result = expected_value in (current_value or "")
            elif operator == "not_contains":
                result = expected_value not in (current_value or "")
            elif operator == "in":
                result = current_value in (expected_value or [])
            elif operator == "not_in":
                result = current_value not in (expected_value or [])
            elif operator == "exists":
                result = variable in game_state
            elif operator == "not_exists":
                result = variable not in game_state
            else:
                # Unknown operator defaults to false
                result = False
            
            results.append(result)
        
        # Combine results based on logic (default AND)
        # TODO: Add support for OR logic when needed
        return all(results)
    
    def apply_state_changes(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply this choice's state changes to the current game state.
        
        Args:
            game_state: Current game state dictionary
            
        Returns:
            Updated game state dictionary
        """
        if not self.state_changes:
            return game_state
        
        # Create a copy to avoid modifying the original
        new_state = game_state.copy()
        
        for variable, change in self.state_changes.items():
            if isinstance(change, dict):
                # Handle complex state changes
                operation = change.get("operation", "set")
                value = change.get("value", 0)
                
                if operation == "set":
                    new_state[variable] = value
                elif operation == "add":
                    new_state[variable] = (new_state.get(variable, 0) or 0) + value
                elif operation == "subtract":
                    new_state[variable] = (new_state.get(variable, 0) or 0) - value
                elif operation == "multiply":
                    new_state[variable] = (new_state.get(variable, 0) or 0) * value
                elif operation == "append":
                    if variable not in new_state:
                        new_state[variable] = []
                    if isinstance(new_state[variable], list):
                        new_state[variable].append(value)
                elif operation == "remove":
                    if variable in new_state and isinstance(new_state[variable], list):
                        try:
                            new_state[variable].remove(value)
                        except ValueError:
                            pass  # Value not in list, ignore
            else:
                # Simple value assignment
                new_state[variable] = change
        
        return new_state
    
    def is_ending_choice(self) -> bool:
        """
        Check if this choice leads to a game ending.
        
        Returns:
            True if choice has no target node, False otherwise
        """
        return self.target_node_id is None
    
    def validate_choice(self) -> List[str]:
        """
        Validate choice data and return any issues.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check choice text
        if not self.text or len(self.text.strip()) == 0:
            errors.append("Choice text cannot be empty")
        
        # Validate conditions structure
        if self.conditions:
            for i, condition in enumerate(self.conditions):
                if not isinstance(condition, dict):
                    errors.append(f"Condition {i + 1} must be an object")
                    continue
                
                if "variable" not in condition:
                    errors.append(f"Condition {i + 1} must have a 'variable' field")
                
                if "operator" not in condition:
                    errors.append(f"Condition {i + 1} must have an 'operator' field")
                
                valid_operators = [
                    "eq", "ne", "gt", "gte", "lt", "lte",
                    "contains", "not_contains", "in", "not_in",
                    "exists", "not_exists"
                ]
                
                if condition.get("operator") not in valid_operators:
                    errors.append(f"Condition {i + 1} has invalid operator")
        
        # Validate state changes structure
        if self.state_changes:
            for variable, change in self.state_changes.items():
                if isinstance(change, dict):
                    if "operation" in change:
                        valid_operations = ["set", "add", "subtract", "multiply", "append", "remove"]
                        if change["operation"] not in valid_operations:
                            errors.append(f"Invalid operation for state change '{variable}'")
        
        return errors
    
    def clone(self, session: Session, new_node_id: str) -> "Choice":
        """
        Create a copy of this choice for a different node.
        
        Args:
            session: Database session
            new_node_id: ID of the node to attach the cloned choice to
            
        Returns:
            New Choice instance (not yet committed)
        """
        cloned_choice = Choice(
            node_id=new_node_id,
            text=self.text,
            target_node_id=self.target_node_id,  # Keep same target initially
            display_order=self.display_order,
            conditions=self.conditions.copy() if self.conditions else [],
            state_changes=self.state_changes.copy() if self.state_changes else {}
        )
        
        session.add(cloned_choice)
        return cloned_choice
    
    def __repr__(self) -> str:
        """String representation of the choice."""
        return f"<Choice(id='{self.id}', text='{self.text[:50]}...', node_id='{self.node_id}')>"