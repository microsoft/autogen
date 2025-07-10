"""Team creation functionality for AutoGen Studio."""

# Import key classes from the modules
from ._models import (
    TeamMakerEvent, Team, Agent,  
    TeamBlueprint, 
    AgentSet, SelectorLogic
)
from ._converters import team_to_component_model
from ._blueprint import BlueprintMaker
from .maker import TeamMaker

# Export main classes
__all__ = [
    "TeamMaker",
    "BlueprintMaker",
    "Team", 
    "Agent",
    "TeamMakerEvent", 
    "TeamBlueprint", 
    "AgentSet",
    "SelectorLogic",
    "team_to_component_model"
]