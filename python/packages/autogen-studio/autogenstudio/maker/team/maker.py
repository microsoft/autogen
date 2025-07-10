"""TeamMaker - Creates team configurations from task descriptions."""

from typing import AsyncGenerator, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from autogen_core import ComponentModel
from autogen_core.models import ChatCompletionClient, UserMessage, SystemMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ._models import (
    TeamMakerEvent, Team, Agent, TeamBlueprint, AgentSet, AgentDesign, 
    SelectorLogic, RoundRobinConfig, SelectorConfig, SwarmConfig, Termination
)
from ._converters import team_to_component_model
from ._blueprint import BlueprintMaker


class TaskConfig(BaseModel):
    """Configuration for task processing."""
    enrich: bool = False


class TeamMakerConfig(BaseModel):
    """Configuration for TeamMaker."""
    task: TaskConfig = Field(default_factory=TaskConfig)


class TeamMaker:
    """Creates team configurations from task descriptions."""
    
    def __init__(
        self, 
        model_client: Optional[ChatCompletionClient] = None,
        config: Optional[TeamMakerConfig] = None
    ):
        self.model_client = model_client or OpenAIChatCompletionClient(
            model="gpt-4o",
        )
        self.config = config or TeamMakerConfig()
        self.blueprint_maker = BlueprintMaker(self.model_client)
    
    async def create_team(
        self, 
        task: str, 
        enrich: Optional[bool] = None
    ) -> AsyncGenerator[Union[TeamMakerEvent, str, TeamBlueprint, AgentSet, SelectorLogic, Team], None]:
        """Generate a team configuration."""
        
        # Use config default or explicit parameter
        should_enrich = enrich if enrich is not None else self.config.task.enrich
        
        # Step 1: Task Analysis & Enrichment
        yield TeamMakerEvent(status="analyzing", content="Analyzing task requirements...")
        enriched_task = task
        if should_enrich:
            yield TeamMakerEvent(status="enriching", content="Enriching task description...")
            enriched_task = await self._enrich_task(task)
            yield enriched_task
        
        # Step 2: Architecture Selection
        yield TeamMakerEvent(status="architecting", content="Selecting team architecture...")
        blueprint = await self._create_blueprint(enriched_task)
        yield blueprint
        
        # Step 3: Agent Design
        yield TeamMakerEvent(status="designing_agents", content="Designing agent configurations...")
        agent_set = await self._design_agents(enriched_task, blueprint)
        yield agent_set
        
        # Step 4: Selector Logic (if needed)
        if blueprint.orchestration == "selector":
            yield TeamMakerEvent(status="selector_logic", content="Creating selection logic...")
            selector_logic = await self._create_selector_logic(enriched_task, agent_set)
            yield selector_logic
        else:
            selector_logic = None
        
        # Step 5: Assemble Team
        yield TeamMakerEvent(status="assembling", content="Assembling team configuration...")
        team = await self._assemble_team(enriched_task, blueprint, agent_set, selector_logic)
        yield team
    
    async def create_team_component(
        self,
        task: str,
        enrich: Optional[bool] = None
    ) -> AsyncGenerator[Union[TeamMakerEvent, str, TeamBlueprint, AgentSet, SelectorLogic, Team, ComponentModel], None]:
        """Generate a team configuration and convert to ComponentModel."""
        
        # Generate the team first
        async for result in self.create_team(task, enrich):
            yield result
            
            # When we get the final team, also yield the ComponentModel
            if isinstance(result, Team):
                yield TeamMakerEvent(status="converting", content="Converting to ComponentModel...")
                component_model = team_to_component_model(result)
                yield component_model
    
    async def _enrich_task(self, task: str) -> str:
        """Enrich the task description using the model client."""
        system_message = SystemMessage(
            content="""You are a task enrichment assistant. Your job is to take a brief task description and expand it with more context, clarity, and actionable details while preserving the original intent.

Guidelines:
- Add relevant context and background information
- Clarify ambiguous requirements
- Suggest success criteria
- Maintain the original scope and intent
- Keep the enriched description concise but comprehensive
- Do not change the fundamental nature of the task

Return only the enriched task description, nothing else."""
        )
        
        user_message = UserMessage(
            content=f"Please enrich this task description:\n\n{task}",
            source="user"
        )
        
        try:
            result = await self.model_client.create(
                messages=[system_message, user_message],
                json_output=False
            )
            # Handle the case where result.content might be a list of function calls
            if isinstance(result.content, str):
                return result.content
            else:
                return task  # Fallback to original if not a string
        except Exception:
            # If enrichment fails, return original task
            return task
    
    async def _create_blueprint(self, task: str) -> TeamBlueprint:
        """Create initial team blueprint using BlueprintMaker."""
        return await self.blueprint_maker.create_blueprint(task)
    
    async def _design_agents(self, task: str, blueprint: TeamBlueprint) -> AgentSet:
        """Design detailed agent configurations."""
        # TODO: Use structured output
        
        agents: List[AgentDesign] = []
        for agent_name in blueprint.agents:
            # Generate agent details based on name/role
            if agent_name in ["assistant", "helper"]:
                key_behaviors = ["be helpful", "solve problems systematically", "be thorough"]
                system_elements = [
                    "You are a helpful assistant.",
                    "Solve tasks carefully and systematically.",
                    "When the task is complete, say TERMINATE."
                ]
                tools = ["calculator"] if "analysis" in task.lower() else []
                interaction_style = "professional and helpful"
                
            elif agent_name in ["critic", "reviewer"]:
                key_behaviors = ["review critically", "suggest improvements", "verify accuracy"]
                system_elements = [
                    "You are a critical reviewer.",
                    "Review solutions carefully and suggest improvements.",
                    "Focus on accuracy, completeness, and quality.",
                    "When satisfied with the solution, say TERMINATE."
                ]
                tools = []
                interaction_style = "constructively critical"
                
            elif agent_name in ["researcher", "investigator"]:
                key_behaviors = ["gather information", "verify sources", "synthesize findings"]
                system_elements = [
                    "You are a researcher.",
                    "Gather comprehensive and accurate information.",
                    "Verify your sources and provide citations.",
                    "Present findings clearly and concisely."
                ]
                tools = ["web_search"] if "web" in task.lower() or "research" in task.lower() else []
                interaction_style = "thorough and methodical"
                
            elif agent_name in ["user_proxy", "human_proxy"]:
                key_behaviors = ["facilitate human interaction", "ask clarifying questions"]
                system_elements = [
                    "You are a user proxy agent.",
                    "Facilitate communication between AI agents and humans.",
                    "Ask for clarification when needed."
                ]
                tools = []
                interaction_style = "friendly and facilitating"
                
            else:
                # Default for other roles
                key_behaviors = ["be helpful", "fulfill assigned role"]
                system_elements = [
                    f"You are a {agent_name} agent.",
                    "Perform your role effectively.",
                    "When done, say TERMINATE."
                ]
                tools = []
                interaction_style = "professional"
            
            agent = AgentDesign(
                name=f"{agent_name.replace(' ', '_')}_agent",
                role=agent_name,
                purpose=f"Act as {agent_name} for the task",
                key_behaviors=key_behaviors,
                system_message_elements=system_elements,
                suggested_tools=tools,
                interaction_style=interaction_style
            )
            agents.append(agent)
        
        # Generate interaction flow description
        if len(agents) == 1:
            interaction_flow = f"{agents[0].name} handles the entire task."
        elif blueprint.orchestration == "roundrobin":
            flow_parts = [f"{agent.name} → " for agent in agents]
            interaction_flow = "".join(flow_parts)[:-3]  # Remove last arrow
        else:  # selector or swarm
            interaction_flow = f"Dynamic coordination between: {', '.join([agent.name for agent in agents])}"
        
        return AgentSet(
            agents=agents,
            interaction_flow=interaction_flow,
            handoff_logic=None  # TODO: Implement for Swarm teams
        )
    
    async def _create_selector_logic(self, task: str, agent_set: AgentSet) -> SelectorLogic:
        """Create selector logic for Selector teams."""
        # TODO: Use structured output
        
        # Basic selection criteria
        criteria = [
            "Current stage of task completion",
            "Type of last message (question, solution, critique, etc.)",
            "Agent expertise match for current need"
        ]
        
        # Stage transitions based on agent roles
        stage_transitions = {}
        agent_roles = [agent.role for agent in agent_set.agents]
        
        if "assistant" in agent_roles and "critic" in agent_roles:
            stage_transitions = {
                "initial": "assistant",
                "solution_proposed": "critic", 
                "critique_provided": "assistant",
                "verified": "complete"
            }
        elif "researcher" in agent_roles:
            stage_transitions = {
                "initial": "researcher",
                "research_complete": "assistant",
                "solution_proposed": "critic" if "critic" in agent_roles else "complete"
            }
        
        # Human involvement rules
        human_rules = [
            "If agents disagree after 3 rounds, involve human for guidance",
            "If task requirements are unclear, ask human for clarification"
        ]
        
        # Add human input rule if "human" or "user" mentioned in task
        if "human" in task.lower() or "user" in task.lower():
            human_rules.append("Regularly check with human for feedback and direction")
        
        # Example selections
        examples: List[Dict[str, str]] = []
        for agent in agent_set.agents:
            if agent.role == "assistant":
                examples.append({
                    "context": "Initial task or need for problem solving",
                    "select": agent.name
                })
            elif agent.role == "critic":
                examples.append({
                    "context": "Solution has been proposed and needs review",
                    "select": agent.name
                })
            elif agent.role == "researcher":
                examples.append({
                    "context": "Information gathering or research is needed",
                    "select": agent.name
                })
        
        return SelectorLogic(
            selection_criteria=criteria,
            stage_transitions=stage_transitions if stage_transitions else None,
            human_involvement_rules=human_rules,
            example_selections=examples
        )
    
    async def _assemble_team(
        self, 
        task: str,
        blueprint: TeamBlueprint,
        agent_set: AgentSet,
        selector_logic: Optional[SelectorLogic]
    ) -> Team:
        """Assemble the final team configuration."""
        
        # Convert agents to final format
        agents: List[Agent] = []
        for agent in agent_set.agents:
            final_agent = Agent(
                name=agent.name,
                role=agent.role,  # type: ignore
                description=agent.purpose,
                system_message=" ".join(agent.system_message_elements),
                tools=agent.suggested_tools,
                handoffs=[]  # TODO: Implement for Swarm
            )
            agents.append(final_agent)
        
        # Create team config based on orchestration type
        arch_type = blueprint.orchestration
        
        if arch_type == "roundrobin":
            config = RoundRobinConfig()
        elif arch_type == "selector":
            selector_prompt = self._build_selector_prompt(selector_logic, agents) if selector_logic else ""
            config = SelectorConfig(
                selection_mode="task_stage",
                selector_prompt=selector_prompt,
                allow_repeated_speaker=len(agents) <= 2  # Allow repetition for small teams
            )
        else:  # swarm
            config = SwarmConfig()
        
        # Create termination configuration based on blueprint
        if blueprint.termination_condition == "message_budget":
            strategy = "budget_limited"
            max_messages = 20  # Default budget
        else:  # text_mention
            strategy = "task_complete"
            max_messages = 10  # Fallback
        
        termination = Termination(
            strategy=strategy,  # type: ignore
            text="TERMINATE",
            max_messages=max_messages,
            timeout_seconds=None
        )
        
        # Generate team name and description
        team_name = f"{arch_type}_team"
        team_description = f"A {arch_type} team for: {task}"
        
        return Team(
            name=team_name,
            description=team_description,
            participants=agents,
            config=config,
            termination=termination,
            model="gpt-4o-mini"
        )
    
    def _build_selector_prompt(self, logic: Optional[SelectorLogic], agents: List[Agent]) -> str:
        """Build selector prompt from logic and agents."""
        if not logic:
            return self._build_default_selector_prompt(agents)
        
        # Build comprehensive selector prompt
        agent_descriptions = "\n".join([
            f"- {agent.name}: {agent.description} (Role: {agent.role})"
            for agent in agents
        ])
        
        criteria_text = "\n".join([f"- {c}" for c in logic.selection_criteria])
        
        rules_text = "\n".join([f"- {r}" for r in logic.human_involvement_rules])
        
        examples_text = "\n".join([
            f"- When: {ex['context']} → Select: {ex['select']}"
            for ex in logic.example_selections
        ])
        
        prompt = f"""You are coordinating a multi-agent team to solve tasks. Your role is to select the most appropriate agent to speak next.

AVAILABLE AGENTS:
{agent_descriptions}

SELECTION CRITERIA:
{criteria_text}

DECISION GUIDELINES:
{rules_text}

EXAMPLES:
{examples_text}

INSTRUCTIONS:
Read the conversation history carefully. Based on the current context, task progress, and the criteria above, select the most appropriate agent to speak next.

Available participants: {{participants}}
Conversation history: {{history}}

Select the next speaker by returning only their name."""
        
        return prompt
    
    def _build_default_selector_prompt(self, agents: List[Agent]) -> str:
        """Build a default selector prompt when no logic is provided."""
        agent_list = ", ".join([agent.name for agent in agents])
        
        return f"""You are coordinating a team discussion. Select the most appropriate next speaker based on:
- The current conversation context
- Each agent's role and expertise
- The natural flow of the discussion

Available agents: {agent_list}
Select the next speaker: {{participants}}

Read the conversation history and select the most appropriate next speaker.""" 
