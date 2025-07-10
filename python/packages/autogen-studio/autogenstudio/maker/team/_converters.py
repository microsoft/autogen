"""Converters to transform high-level team configs to ComponentModel instances."""

from typing import Dict, Any, List
from autogen_core import ComponentModel
from ._models import Team, Agent, RoundRobinConfig, SelectorConfig, SwarmConfig, Termination


def team_to_component_model(team: Team) -> ComponentModel:
    """Convert a high-level Team to a ComponentModel."""
    
    # Map team type to provider
    provider_map = {
        "roundrobin": "autogen_agentchat.teams.RoundRobinGroupChat",
        "selector": "autogen_agentchat.teams.SelectorGroupChat", 
        "swarm": "autogen_agentchat.teams.Swarm"
    }
    
    # Build base config
    config = {
        "participants": [_agent_to_component_config(agent) for agent in team.participants],
        "termination_condition": _termination_to_component_config(team.termination)
    }
    
    # Add team-specific config
    if isinstance(team.config, SelectorConfig):
        config.update({
            "selector_prompt": team.config.selector_prompt,
            "allow_repeated_speaker": team.config.allow_repeated_speaker,
            "max_selector_attempts": 3,  # Default
            "model_client": {
                "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
                "component_type": "model",
                "version": 1,
                "component_version": 1,
                "description": "Chat completion client for OpenAI hosted models.",
                "label": "OpenAIChatCompletionClient",
                "config": {"model": team.config.model}
            }
        })
    
    return ComponentModel(
        provider=provider_map[team.config.type],
        component_type="team",
        version=1,
        component_version=1,
        description=team.description,
        label=team.name,
        config=config
    )


def _agent_to_component_config(agent: Agent) -> Dict[str, Any]:
    """Convert an Agent to component config."""
    config = {
        "provider": "autogen_agentchat.agents.AssistantAgent",
        "component_type": "agent",
        "version": 2,
        "component_version": 2,
        "description": agent.description,
        "label": f"{agent.role.title()}Agent",
        "config": {
            "name": agent.name,
            "system_message": agent.system_message,
            "model_client": {
                "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
                "component_type": "model", 
                "version": 1,
                "component_version": 1,
                "description": "Chat completion client for OpenAI hosted models.",
                "label": "OpenAIChatCompletionClient",
                "config": {"model": "gpt-4o-mini"}
            }
        }
    }
    
    # Add tools if present
    if agent.tools:
        config["config"]["tools"] = _tools_to_component_config(agent.tools)
    
    # Add handoffs for Swarm teams
    if agent.handoffs:
        config["config"]["handoffs"] = agent.handoffs
    
    # Handle special agent types
    if agent.role == "user_proxy":
        config["provider"] = "autogen_agentchat.agents.UserProxyAgent"
    
    return config


def _tools_to_component_config(tools: List[str]) -> List[Dict[str, Any]]:
    """Convert tool names to component configs."""
    tool_configs = []
    
    for tool_name in tools:
        if tool_name == "calculator":
            tool_configs.append({
                "provider": "autogen_ext.tools.code_execution.PythonCodeExecutionTool",
                "component_type": "tool",
                "version": 1,
                "component_version": 1,
                "description": "A tool for executing Python code.",
                "label": "PythonCodeExecutionTool",
                "config": {}
            })
        elif tool_name == "web_search":
            # Placeholder - would need actual web search tool
            tool_configs.append({
                "provider": "autogen_ext.tools.web.WebSearchTool",
                "component_type": "tool", 
                "version": 1,
                "component_version": 1,
                "description": "A tool for searching the web.",
                "label": "WebSearchTool",
                "config": {}
            })
    
    return tool_configs


def _termination_to_component_config(termination: Termination) -> Dict[str, Any]:
    """Convert Termination to component config."""
    conditions = []
    
    # Primary termination condition
    conditions.append({
        "provider": "autogen_agentchat.conditions.TextMentionTermination",
        "component_type": "termination",
        "version": 1,
        "component_version": 1,
        "description": "Terminate when a specific text is mentioned.",
        "label": "TextMentionTermination",
        "config": {"text": termination.text}
    })
    
    # Fallback termination condition
    conditions.append({
        "provider": "autogen_agentchat.conditions.MaxMessageTermination",
        "component_type": "termination",
        "version": 1,
        "component_version": 1,
        "description": "Terminate after a maximum number of messages.",
        "label": "MaxMessageTermination", 
        "config": {"max_messages": termination.max_messages}
    })
    
    # Add timeout if specified
    if termination.timeout_seconds:
        conditions.append({
            "provider": "autogen_agentchat.conditions.TimeoutTermination",
            "component_type": "termination",
            "version": 1,
            "component_version": 1,
            "description": "Terminate after a timeout.",
            "label": "TimeoutTermination",
            "config": {"timeout_seconds": termination.timeout_seconds}
        })
    
    # Return OR condition with all termination conditions
    return {
        "provider": "autogen_agentchat.base.OrTerminationCondition",
        "component_type": "termination",
        "version": 1,
        "component_version": 1,
        "description": "Terminate when any of the conditions are met.",
        "label": "OrTerminationCondition",
        "config": {"conditions": conditions}
    }
