"""
Condition model for managing game conditions and state evaluations.

This module defines the Condition model which represents individual conditions
that can be evaluated against game state, used by choices and other game elements
for conditional logic.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Column, String, Text, Index, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID, JSON
from enum import Enum as PyEnum

from .base import BaseModel

# Avoid circular imports
if TYPE_CHECKING:
    from .choice import Choice


class ConditionOperator(PyEnum):
    """Enumeration of supported condition operators."""
    
    EQ = "eq"              # Equal to
    NE = "ne"              # Not equal to
    GT = "gt"              # Greater than
    GTE = "gte"            # Greater than or equal to
    LT = "lt"              # Less than
    LTE = "lte"            # Less than or equal to
    CONTAINS = "contains"  # String/array contains value
    NOT_CONTAINS = "not_contains"  # String/array does not contain value
    IN = "in"              # Value is in array
    NOT_IN = "not_in"      # Value is not in array
    EXISTS = "exists"      # Variable exists in game state
    NOT_EXISTS = "not_exists"  # Variable does not exist in game state


class Condition(BaseModel):
    """
    Condition model representing a single condition for game logic.
    
    Conditions evaluate game state variables against expected values using
    various operators. They can be used by choices, triggers, or other
    game elements that need conditional behavior.
    
    Attributes:
        choice_id: Optional ID of the choice this condition belongs to
        variable: Name of the game state variable to check
        operator: The comparison operator to use
        value: Expected value to compare against (JSON for flexibility)
        description: Optional human-readable description
        choice: Relationship to the parent Choice (if applicable)
    """
    
    __tablename__ = "conditions"
    
    # Optional foreign key to choice (conditions can be standalone)
    choice_id: Optional[str] = Column(
        UUID(as_uuid=False),
        ForeignKey("choices.id", ondelete="CASCADE"),
        nullable=True,
        doc="ID of the choice this condition belongs to (if any)"
    )
    
    # Condition definition
    variable: str = Column(
        String(255),
        nullable=False,
        doc="Name of the game state variable to evaluate"
    )
    
    operator: ConditionOperator = Column(
        SQLEnum(ConditionOperator),
        nullable=False,
        default=ConditionOperator.EQ,
        doc="The comparison operator to use for evaluation"
    )
    
    value: Any = Column(
        JSON,
        nullable=True,
        doc="Expected value to compare against (JSON for type flexibility)"
    )
    
    description: Optional[str] = Column(
        Text,
        nullable=True,
        doc="Optional human-readable description of this condition"
    )
    
    # Relationships
    choice: Optional["Choice"] = relationship(
        "Choice",
        back_populates="condition_objects",
        doc="The choice this condition belongs to (if any)"
    )
    
    # Database indexes for performance
    __table_args__ = (
        Index("ix_conditions_choice_id", "choice_id"),
        Index("ix_conditions_variable", "variable"),
        Index("ix_conditions_operator", "operator"),
    )
    
    def evaluate(self, game_state: Dict[str, Any]) -> bool:
        """
        Evaluate this condition against the current game state.
        
        Args:
            game_state: Dictionary containing current game state variables
            
        Returns:
            True if condition is satisfied, False otherwise
        """
        current_value = game_state.get(self.variable)
        expected_value = self.value
        
        # Handle different operators
        if self.operator == ConditionOperator.EQ:
            return current_value == expected_value
        elif self.operator == ConditionOperator.NE:
            return current_value != expected_value
        elif self.operator == ConditionOperator.GT:
            return (current_value or 0) > (expected_value or 0)
        elif self.operator == ConditionOperator.GTE:
            return (current_value or 0) >= (expected_value or 0)
        elif self.operator == ConditionOperator.LT:
            return (current_value or 0) < (expected_value or 0)
        elif self.operator == ConditionOperator.LTE:
            return (current_value or 0) <= (expected_value or 0)
        elif self.operator == ConditionOperator.CONTAINS:
            return expected_value in (current_value or "")
        elif self.operator == ConditionOperator.NOT_CONTAINS:
            return expected_value not in (current_value or "")
        elif self.operator == ConditionOperator.IN:
            return current_value in (expected_value or [])
        elif self.operator == ConditionOperator.NOT_IN:
            return current_value not in (expected_value or [])
        elif self.operator == ConditionOperator.EXISTS:
            return self.variable in game_state
        elif self.operator == ConditionOperator.NOT_EXISTS:
            return self.variable not in game_state
        else:
            # Unknown operator defaults to false for safety
            return False
    
    def to_json_dict(self) -> Dict[str, Any]:
        """
        Convert condition to JSON dictionary format.
        
        Used for compatibility with the Choice model's JSON conditions field.
        
        Returns:
            Dictionary representation suitable for JSON storage
        """
        return {
            "variable": self.variable,
            "operator": self.operator.value,
            "value": self.value,
            "description": self.description
        }
    
    @classmethod
    def from_json_dict(cls, data: Dict[str, Any], choice_id: Optional[str] = None) -> "Condition":
        """
        Create a Condition instance from JSON dictionary data.
        
        Args:
            data: Dictionary containing condition data
            choice_id: Optional choice ID to associate with
            
        Returns:
            New Condition instance (not yet committed to database)
        """
        # Validate operator
        operator_str = data.get("operator", "eq")
        try:
            operator = ConditionOperator(operator_str)
        except ValueError:
            operator = ConditionOperator.EQ  # Default to equality
        
        return cls(
            choice_id=choice_id,
            variable=data.get("variable", ""),
            operator=operator,
            value=data.get("value"),
            description=data.get("description")
        )
    
    def validate_condition(self) -> List[str]:
        """
        Validate condition data and return any issues.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check variable name
        if not self.variable or len(self.variable.strip()) == 0:
            errors.append("Condition variable name cannot be empty")
        
        # Check variable name format (basic validation)
        if self.variable and not self.variable.replace("_", "").replace("-", "").isalnum():
            errors.append("Variable name should contain only letters, numbers, underscores, and hyphens")
        
        # Operator-specific validations
        if self.operator in [ConditionOperator.GT, ConditionOperator.GTE, 
                           ConditionOperator.LT, ConditionOperator.LTE]:
            # Numeric operators should have numeric values
            if self.value is not None and not isinstance(self.value, (int, float)):
                errors.append(f"Operator '{self.operator.value}' requires a numeric value")
        
        elif self.operator in [ConditionOperator.IN, ConditionOperator.NOT_IN]:
            # Array operators should have array values
            if self.value is not None and not isinstance(self.value, list):
                errors.append(f"Operator '{self.operator.value}' requires an array value")
        
        elif self.operator in [ConditionOperator.EXISTS, ConditionOperator.NOT_EXISTS]:
            # Existence operators don't need a value
            if self.value is not None:
                errors.append(f"Operator '{self.operator.value}' does not use a value")
        
        return errors
    
    def clone(self, session: Session, new_choice_id: Optional[str] = None) -> "Condition":
        """
        Create a copy of this condition.
        
        Args:
            session: Database session
            new_choice_id: Optional new choice ID to associate with
            
        Returns:
            New Condition instance (not yet committed)
        """
        cloned_condition = Condition(
            choice_id=new_choice_id if new_choice_id is not None else self.choice_id,
            variable=self.variable,
            operator=self.operator,
            value=self.value,
            description=self.description
        )
        
        session.add(cloned_condition)
        return cloned_condition
    
    def __repr__(self) -> str:
        """String representation of the condition."""
        return f"<Condition(id='{self.id}', variable='{self.variable}', operator='{self.operator.value}')>"


def evaluate_conditions_list(conditions: List[Condition], game_state: Dict[str, Any]) -> bool:
    """
    Evaluate a list of Condition objects against game state.
    
    Args:
        conditions: List of Condition instances
        game_state: Current game state dictionary
        
    Returns:
        True if all conditions are satisfied (AND logic)
    """
    if not conditions:
        return True
    
    return all(condition.evaluate(game_state) for condition in conditions)


def conditions_from_json_list(json_conditions: List[Dict[str, Any]], 
                            choice_id: Optional[str] = None) -> List[Condition]:
    """
    Convert a list of JSON condition dictionaries to Condition objects.
    
    Args:
        json_conditions: List of condition dictionaries
        choice_id: Optional choice ID to associate conditions with
        
    Returns:
        List of Condition instances (not yet committed to database)
    """
    return [
        Condition.from_json_dict(condition_data, choice_id)
        for condition_data in json_conditions
    ]