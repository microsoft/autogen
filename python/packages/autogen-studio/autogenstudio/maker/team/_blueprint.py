"""Blueprint creation for team configuration."""

import json
from autogen_core.models import ChatCompletionClient, UserMessage, SystemMessage

from ._models import TeamBlueprint


class BlueprintMaker:
    """Creates team blueprints using LLM."""
    
    def __init__(self, model_client: ChatCompletionClient):
        self.model_client = model_client
    
    async def create_blueprint(self, task: str) -> TeamBlueprint:
        """Create initial team blueprint using LLM."""
        system_message = SystemMessage(
            content=self._get_system_prompt()
        )
        
        user_message = UserMessage(
            content=f"Design a team configuration for this task: {task}",
            source="user"
        )
        
        try:
            result = await self.model_client.create(
                messages=[system_message, user_message],
                json_output=True
            )
            
            # Parse the JSON response
            if isinstance(result.content, str):
                blueprint_data = json.loads(result.content)
            else:
                # Handle potential list/other formats
                raise ValueError("Unexpected response format")
                
            return TeamBlueprint(**blueprint_data)
            
        except Exception as e:
            # Fallback to a simple default configuration
            return TeamBlueprint(
                task=task,
                orchestration="roundrobin",
                termination_condition="text_mention", 
                agents=["assistant"],
                rationale=f"Fallback configuration due to error: {e}. Simple roundrobin with assistant for general task solving."
            )
     
    def update_system_prompt(self, new_prompt: str) -> None:
        """Update the system prompt for testing/improvement."""
        self._custom_prompt = new_prompt
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for blueprint creation."""
        if hasattr(self, '_custom_prompt'):
            return self._custom_prompt
        return self._get_default_system_prompt()
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt."""
        return """You are a team design expert. Given a task, you need to design a multi-agent team configuration that will effectively solve it.

Your response must be a valid JSON object with these exact fields:
- task: string (the task description)
- orchestration: one of ["roundrobin", "selector", "swarm"]  
- termination_condition: one of ["message_budget", "text_mention"]
- agents: array of strings (agent names/roles like ["researcher", "analyst", "critic"])
- rationale: string (explanation of why this configuration will work)

## Orchestration Types

**RoundRobin**: Agents take turns in a fixed sequence. Best for:
- Sequential workflows where each agent builds on the previous
- Tasks with clear logical progression
- Simple coordination needs

**Selector**: An LLM dynamically chooses which agent speaks next. Best for:
- Complex tasks needing flexible coordination
- Tasks where the next step depends on current context
- Iterative refinement workflows
- Multi-stage processes with decision points

**Swarm**: Agents can directly hand off to each other. Best for:
- Specialized workflows with clear handoff patterns
- Tasks requiring direct agent-to-agent communication
- Complex multi-step processes with branching

## Termination Conditions

**text_mention**: Agents are instructed to say specific text (e.g., "TERMINATE") when done
- Use for tasks with clear completion criteria
- Good when agents can recognize task completion

**message_budget**: Stop after a fixed number of messages/turns
- Use for open-ended or research tasks
- Good for exploration tasks that could continue indefinitely
- Prevents infinite loops

## Agent Design Guidelines

- Keep agent names simple and descriptive (e.g., "researcher", "writer", "critic", "planner")
- Each agent should have a clear, focused role
- Consider what tools each agent might need (they can have multiple tools)
- Think about the natural flow between agents

## Examples

Research task:
{"task": "Research climate change impacts on agriculture", "orchestration": "selector", "termination_condition": "message_budget", "agents": ["researcher", "analyst", "critic"], "rationale": "Selector allows dynamic coordination between research, analysis, and critique phases. Research can trigger analysis, analysis can trigger more research, and critic can request refinements. Message budget prevents endless research loops."}

Writing task:
{"task": "Write a technical blog post", "orchestration": "roundrobin", "termination_condition": "text_mention", "agents": ["planner", "writer", "editor"], "rationale": "Sequential workflow: planner creates outline, writer creates content, editor reviews and finalizes. Each step builds on the previous. Clear completion when editor approves final version."}

Complex analysis:
{"task": "Analyze market trends and recommend investment strategy", "orchestration": "selector", "termination_condition": "message_budget", "agents": ["data_analyst", "market_researcher", "strategist", "critic"], "rationale": "Complex analysis requires flexible coordination. Data analyst provides quantitative insights, researcher provides market context, strategist synthesizes recommendations, critic validates approach. Selector enables iterative refinement between any agents as needed."}

Remember: The rationale should clearly explain how the orchestration type, termination condition, and agent roles work together to solve the specific task effectively."""
