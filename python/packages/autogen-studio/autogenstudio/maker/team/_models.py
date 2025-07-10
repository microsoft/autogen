"""Pydantic models for team creation."""

from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class TeamMakerEvent(BaseModel):
    """Event for streaming team creation progress."""
    status: str
    content: str


# Core Models - Clean and Simple

class Agent(BaseModel):
    """Agent configuration."""
    name: str
    role: Literal["assistant", "critic", "researcher", "verifier", "executor", "coordinator", "user_proxy"]
    description: str
    system_message: str
    tools: List[str] = Field(default_factory=list)  # Just tool names/descriptions
    handoffs: List[str] = Field(default_factory=list)  # For Swarm teams


class Termination(BaseModel):
    """Termination configuration."""
    strategy: Literal["task_complete", "consensus", "budget_limited", "time_boxed"]
    text: str = "TERMINATE"  # Primary termination text
    max_messages: int = 20  # Fallback
    timeout_seconds: Optional[int] = None
    max_tokens: Optional[int] = None


class RoundRobinConfig(BaseModel):
    """RoundRobin configuration."""
    type: Literal["roundrobin"] = "roundrobin"
    # RoundRobin needs nothing special beyond participants and termination


class SelectorConfig(BaseModel):
    """Selector configuration."""
    type: Literal["selector"] = "selector"
    selection_mode: Literal["model_based", "role_play", "task_stage", "capability_match"]
    selector_prompt: str
    allow_repeated_speaker: bool = False
    model: str = "gpt-4o-mini"  # Model for selection


class SwarmConfig(BaseModel):
    """Swarm configuration."""
    type: Literal["swarm"] = "swarm"
    # Swarm config is mainly in agent handoffs


class Team(BaseModel):
    """Team configuration - the main output."""
    name: str
    description: str
    participants: List[Agent]
    config: Union[RoundRobinConfig, SelectorConfig, SwarmConfig]
    termination: Termination
    model: str = "gpt-4o-mini"  # Default model for all agents


class TeamBlueprint(BaseModel):
    """High-level team blueprint."""
    task: str
    orchestration: Literal["roundrobin", "selector", "swarm"]
    termination_condition: Literal["message_budget", "text_mention"]
    agents: List[str]  # List of agent names/roles
    rationale: str  # Explanation of why this configuration will work


# Agent Generation Models

class AgentDesign(BaseModel):
    """Detailed agent design."""
    name: str
    role: str
    purpose: str
    key_behaviors: List[str]
    system_message_elements: List[str]  # Elements to include in system message
    suggested_tools: List[str]
    interaction_style: str  # "helpful", "critical", "analytical", etc.


class AgentSet(BaseModel):
    """Complete set of agents for the team."""
    agents: List[AgentDesign]
    interaction_flow: str  # Description of how agents should interact
    handoff_logic: Optional[Dict[str, List[str]]] = None  # For Swarm


# Selector Prompt Generation (for Selector teams)

class SelectorLogic(BaseModel):
    """Logic for agent selection."""
    selection_criteria: List[str]
    stage_transitions: Optional[Dict[str, str]] = None  # {"research": "verification", ...}
    human_involvement_rules: List[str]
    example_selections: List[Dict[str, str]]  # [{"context": "...", "select": "agent_name"}]
