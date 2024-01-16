from typing import List, Dict, Tuple
from autogen import Agent


def gather_usage_summary(agents: List[Agent]) -> Tuple[Dict[str, any], Dict[str, any]]:
    """Gather usage summary from all agents.

    Args:
        agents: (list): List of agents.

    Returns:
        tuple: (total_usage_summary, actual_usage_summary)

    Example return:
        total_usage_summary = {
            'total_cost': 0.0006090000000000001,
            'gpt-35-turbo':
                {
                    'cost': 0.0006090000000000001,
                    'prompt_tokens': 242,
                    'completion_tokens': 123,
                    'total_tokens': 365
                }
        }
        `actual_usage_summary` follows the same format.
        If none of the agents incurred any cost (not having a client), then the total_usage_summary and actual_usage_summary will be {'total_cost': 0}.
    """

    def aggregate_summary(usage_summary: Dict[str, any], agent_summary: Dict[str, any]) -> None:
        if agent_summary is None:
            return
        usage_summary["total_cost"] += agent_summary.get("total_cost", 0)
        for model, data in agent_summary.items():
            if model != "total_cost":
                if model not in usage_summary:
                    usage_summary[model] = data.copy()
                else:
                    usage_summary[model]["cost"] += data.get("cost", 0)
                    usage_summary[model]["prompt_tokens"] += data.get("prompt_tokens", 0)
                    usage_summary[model]["completion_tokens"] += data.get("completion_tokens", 0)
                    usage_summary[model]["total_tokens"] += data.get("total_tokens", 0)

    total_usage_summary = {"total_cost": 0}
    actual_usage_summary = {"total_cost": 0}

    for agent in agents:
        if agent.client:
            aggregate_summary(total_usage_summary, agent.client.total_usage_summary)
            aggregate_summary(actual_usage_summary, agent.client.actual_usage_summary)

    return total_usage_summary, actual_usage_summary
