import logging
from typing import Optional, Union, Dict, Any, List
from pathlib import Path
from loguru import logger
from ..datamodel import (
    Model, Team, Agent, Tool,
    Response, ComponentTypes, LinkTypes,
    ComponentConfigInput
)

from .component_factory import ComponentFactory
from .db_manager import DatabaseManager


class ConfigurationManager:
    """Manages persistence and relationships of components using ComponentFactory for validation"""

    DEFAULT_UNIQUENESS_FIELDS = {
        ComponentTypes.MODEL: ['model_type', 'model'],
        ComponentTypes.TOOL: ['name'],
        ComponentTypes.AGENT: ['agent_type', 'name'],
        ComponentTypes.TEAM: ['team_type', 'name']
    }

    def __init__(self, db_manager: DatabaseManager, uniqueness_fields: Dict[ComponentTypes, List[str]] = None):
        self.db_manager = db_manager
        self.component_factory = ComponentFactory()
        self.uniqueness_fields = uniqueness_fields or self.DEFAULT_UNIQUENESS_FIELDS

    async def import_component(self, component_config: ComponentConfigInput, user_id: str, check_exists: bool = False) -> Response:
        """
        Import a component configuration, validate it, and store the resulting component.

        Args:
            component_config: Configuration for the component (file path, dict, or ComponentConfig)
            user_id: User ID to associate with imported component
            check_exists: Whether to check for existing components before storing (default: False)

        Returns:
            Response containing import results or error
        """
        try:
            # Get validated config as dict
            config = await self.component_factory.load(component_config, return_type='dict')

            # Get component type
            component_type = self._determine_component_type(config)
            if not component_type:
                raise ValueError(
                    f"Unable to determine component type from config")

            # Check existence if requested
            if check_exists:
                existing = self._check_exists(component_type, config, user_id)
                if existing:
                    return Response(
                        message=self._format_exists_message(
                            component_type, config),
                        status=True,
                        data={"id": existing.id}
                    )

            # Route to appropriate storage method
            if component_type == ComponentTypes.TEAM:
                return await self._store_team(config, user_id, check_exists)
            elif component_type == ComponentTypes.AGENT:
                return await self._store_agent(config, user_id, check_exists)
            elif component_type == ComponentTypes.MODEL:
                return await self._store_model(config, user_id)
            elif component_type == ComponentTypes.TOOL:
                return await self._store_tool(config, user_id)
            else:
                raise ValueError(
                    f"Unsupported component type: {component_type}")

        except Exception as e:
            logger.error(f"Failed to import component: {str(e)}")
            return Response(message=str(e), status=False)

    async def import_directory(self, directory: Union[str, Path], user_id: str, check_exists: bool = False) -> Response:
        """
        Import all component configurations from a directory.

        Args:
            directory: Path to directory containing configuration files
            user_id: User ID to associate with imported components
            check_exists: Whether to check for existing components before storing (default: False)

        Returns:
            Response containing import results for all files
        """
        try:
            configs = await self.component_factory.load_directory(directory, return_type='dict')

            results = []
            for config in configs:
                result = await self.import_component(config, user_id, check_exists)
                results.append({
                    "component": self._get_component_type(config),
                    "status": result.status,
                    "message": result.message,
                    "id": result.data.get("id") if result.status else None
                })

            return Response(
                message="Directory import complete",
                status=True,
                data=results
            )

        except Exception as e:
            logger.error(f"Failed to import directory: {str(e)}")
            return Response(message=str(e), status=False)

    async def _store_team(self, config: dict, user_id: str, check_exists: bool = False) -> Response:
        """Store team component and manage its relationships with agents"""
        try:
            # Store the team
            team_db = Team(
                user_id=user_id,
                config=config
            )
            team_result = self.db_manager.upsert(team_db)
            if not team_result.status:
                return team_result

            team_id = team_result.data["id"]

            # Handle participants (agents)
            for participant in config.get("participants", []):
                if check_exists:
                    # Check for existing agent
                    agent_type = self._determine_component_type(participant)
                    existing_agent = self._check_exists(
                        agent_type, participant, user_id)
                    if existing_agent:
                        # Link existing agent
                        self.db_manager.link(
                            LinkTypes.TEAM_AGENT,
                            team_id,
                            existing_agent.id
                        )
                        logger.info(
                            f"Linked existing agent to team: {existing_agent}")
                        continue

                # Store and link new agent
                agent_result = await self._store_agent(participant, user_id, check_exists)
                if agent_result.status:
                    self.db_manager.link(
                        LinkTypes.TEAM_AGENT,
                        team_id,
                        agent_result.data["id"]
                    )

            return team_result

        except Exception as e:
            logger.error(f"Failed to store team: {str(e)}")
            return Response(message=str(e), status=False)

    async def _store_agent(self, config: dict, user_id: str, check_exists: bool = False) -> Response:
        """Store agent component and manage its relationships with tools and model"""
        try:
            # Store the agent
            agent_db = Agent(
                user_id=user_id,
                config=config
            )
            agent_result = self.db_manager.upsert(agent_db)
            if not agent_result.status:
                return agent_result

            agent_id = agent_result.data["id"]

            # Handle model client
            if "model_client" in config:
                if check_exists:
                    # Check for existing model
                    model_type = self._determine_component_type(
                        config["model_client"])
                    existing_model = self._check_exists(
                        model_type, config["model_client"], user_id)
                    if existing_model:
                        # Link existing model
                        self.db_manager.link(
                            LinkTypes.AGENT_MODEL,
                            agent_id,
                            existing_model.id
                        )
                        logger.info(
                            f"Linked existing model to agent: {existing_model.config.model_type}")
                    else:
                        # Store and link new model
                        model_result = await self._store_model(config["model_client"], user_id)
                        if model_result.status:
                            self.db_manager.link(
                                LinkTypes.AGENT_MODEL,
                                agent_id,
                                model_result.data["id"]
                            )
                else:
                    # Store and link new model without checking
                    model_result = await self._store_model(config["model_client"], user_id)
                    if model_result.status:
                        self.db_manager.link(
                            LinkTypes.AGENT_MODEL,
                            agent_id,
                            model_result.data["id"]
                        )

            # Handle tools
            for tool_config in config.get("tools", []):
                if check_exists:
                    # Check for existing tool
                    tool_type = self._determine_component_type(tool_config)
                    existing_tool = self._check_exists(
                        tool_type, tool_config, user_id)
                    if existing_tool:
                        # Link existing tool
                        self.db_manager.link(
                            LinkTypes.AGENT_TOOL,
                            agent_id,
                            existing_tool.id
                        )
                        logger.info(
                            f"Linked existing tool to agent: {existing_tool.config.name}")
                        continue

                # Store and link new tool
                tool_result = await self._store_tool(tool_config, user_id)
                if tool_result.status:
                    self.db_manager.link(
                        LinkTypes.AGENT_TOOL,
                        agent_id,
                        tool_result.data["id"]
                    )

            return agent_result

        except Exception as e:
            logger.error(f"Failed to store agent: {str(e)}")
            return Response(message=str(e), status=False)

    async def _store_model(self, config: dict, user_id: str) -> Response:
        """Store model component (leaf node - no relationships)"""
        try:
            model_db = Model(
                user_id=user_id,
                config=config
            )
            return self.db_manager.upsert(model_db)

        except Exception as e:
            logger.error(f"Failed to store model: {str(e)}")
            return Response(message=str(e), status=False)

    async def _store_tool(self, config: dict, user_id: str) -> Response:
        """Store tool component (leaf node - no relationships)"""
        try:
            tool_db = Tool(
                user_id=user_id,
                config=config
            )
            return self.db_manager.upsert(tool_db)

        except Exception as e:
            logger.error(f"Failed to store tool: {str(e)}")
            return Response(message=str(e), status=False)

    def _check_exists(self, component_type: ComponentTypes, config: dict, user_id: str) -> Optional[Union[Model, Tool, Agent, Team]]:
        """Check if component exists based on configured uniqueness fields."""
        fields = self.uniqueness_fields.get(component_type, [])
        if not fields:
            return None

        component_class = {
            ComponentTypes.MODEL: Model,
            ComponentTypes.TOOL: Tool,
            ComponentTypes.AGENT: Agent,
            ComponentTypes.TEAM: Team
        }.get(component_type)

        components = self.db_manager.get(
            component_class, {"user_id": user_id}).data

        for component in components:
            matches = all(
                component.config.get(field) == config.get(field)
                for field in fields
            )
            if matches:
                return component

        return None

    def _format_exists_message(self, component_type: ComponentTypes, config: dict) -> str:
        """Format existence message with identifying fields."""
        fields = self.uniqueness_fields.get(component_type, [])
        field_values = [f"{field}='{config.get(field)}'" for field in fields]
        return f"{component_type.value} with {' and '.join(field_values)} already exists"

    def _determine_component_type(self, config: dict) -> Optional[ComponentTypes]:
        """Determine component type from configuration dictionary"""
        if "team_type" in config:
            return ComponentTypes.TEAM
        elif "agent_type" in config:
            return ComponentTypes.AGENT
        elif "model_type" in config:
            return ComponentTypes.MODEL
        elif "tool_type" in config:
            return ComponentTypes.TOOL
        return None

    def _get_component_type(self, config: dict) -> str:
        """Helper to get component type string from config"""
        component_type = self._determine_component_type(config)
        return component_type.value if component_type else "unknown"

    async def cleanup(self):
        """Cleanup resources"""
        await self.component_factory.cleanup()
