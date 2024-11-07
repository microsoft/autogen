import os
import json
from typing import Optional, Union, List, Dict
from loguru import logger

from ..datamodel import (
    Model, ModelConfig, Team, TeamConfig,
    Agent, AgentConfig, Tool, ToolConfig,
    LinkTypes,
    Response, ComponentTypes
)

from .agent_factory import AgentFactory
from .db_manager import DatabaseManager


class ConfigurationManager:
    """Manages loading, validation, and storage of configurations for teams, agents, models, and tools."""

    # Configurable uniqueness fields for each component type
    DEFAULT_UNIQUENESS_FIELDS = {
        ComponentTypes.MODEL: ['model_type', 'model'],
        ComponentTypes.TOOL: ['name'],
        ComponentTypes.AGENT: ['agent_type', 'name'],
        ComponentTypes.TEAM: ['team_type', 'name']
    }

    def __init__(self, db_manager: DatabaseManager, uniqueness_fields: Dict[ComponentTypes, List[str]] = None):
        """
        Initialize Configuration Manager.

        Args:
            db_manager: Database manager instance for storage operations
            uniqueness_fields: Optional custom uniqueness fields configuration
        """
        self.db_manager = db_manager
        self.agent_factory: AgentFactory = AgentFactory()
        self.uniqueness_fields = uniqueness_fields or self.DEFAULT_UNIQUENESS_FIELDS

    def _load_config_file(self, path: str) -> Response:
        """Load configuration from JSON or YAML file."""
        try:
            ext = path.lower().split('.')[-1]

            with open(path) as f:
                if ext == 'json':
                    config = json.load(f)
                elif ext in ('yaml', 'yml'):
                    import yaml
                    config = yaml.safe_load(f)
                else:
                    return Response(
                        message=f"Unsupported file format: {ext}",
                        status=False
                    )

            return Response(message="Config loaded successfully", status=True, data=config)
        except Exception as e:
            logger.error(f"Failed to load config file {path}: {str(e)}")
            return Response(message=f"Failed to load config file: {str(e)}", status=False)

    def _check_exists(self, component_type: ComponentTypes, config: dict, user_id: str) -> Optional[Union[Model, Tool, Agent, Team]]:
        """
        Check if component exists based on configured uniqueness fields.

        Args:
            component_type: Type of component to check
            config: Configuration to check
            user_id: User ID to check against

        Returns:
            Existing component if found, None otherwise
        """
        # Get uniqueness fields for this component type
        fields = self.uniqueness_fields.get(component_type, [])
        if not fields:
            return None

        # Get all components of this type for the user
        component_class = {
            ComponentTypes.MODEL: Model,
            ComponentTypes.TOOL: Tool,
            ComponentTypes.AGENT: Agent,
            ComponentTypes.TEAM: Team
        }.get(component_type)

        components = self.db_manager.get(
            component_class, {"user_id": user_id}).data

        # Check each component for matching uniqueness fields
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

    def import_model_config(self, config: dict, user_id: str, check_exists: bool = True) -> Response:
        """
        Import model configuration.

        Args:
            config: Model configuration dictionary
            user_id: User ID to associate with the model
            check_exists: Whether to check for existing models

        Returns:
            Response containing imported model details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_model(config)

            # Check existence if requested
            if check_exists:
                existing = self._check_exists(
                    ComponentTypes.MODEL, config, user_id)
                if existing:
                    return Response(
                        message=self._format_exists_message(
                            ComponentTypes.MODEL, config),
                        status=True,
                        data={"id": existing.id}
                    )

            # Create model
            model = Model(
                user_id=user_id,
                config=ModelConfig(**config).model_dump()
            )
            return self.db_manager.upsert(model)
        except Exception as e:
            logger.error(f"Failed to import model config: {str(e)}")
            return Response(message=f"Failed to import model: {str(e)}", status=False)

    def import_tool_config(self, config: dict, user_id: str, check_exists: bool = True) -> Response:
        """
        Import tool configuration.

        Args:
            config: Tool configuration dictionary
            user_id: User ID to associate with the tool
            check_exists: Whether to check for existing tools

        Returns:
            Response containing imported tool details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_tool(config)

            # Check existence if requested
            if check_exists:
                existing = self._check_exists(
                    ComponentTypes.TOOL, config, user_id)
                if existing:
                    return Response(
                        message=self._format_exists_message(
                            ComponentTypes.TOOL, config),
                        status=True,
                        data={"id": existing.id}
                    )

            tool = Tool(
                user_id=user_id,
                config=ToolConfig(**config).model_dump()
            )
            return self.db_manager.upsert(tool)
        except Exception as e:
            logger.error(f"Failed to import tool config: {str(e)}")
            return Response(message=f"Failed to import tool: {str(e)}", status=False)

    def import_agent_config(self, config: dict, user_id: str, check_exists: bool = True) -> Response:
        """
        Import agent configuration and its dependencies.

        Args:
            config: Agent configuration dictionary
            user_id: User ID to associate with the agent
            check_exists: Whether to check for existing agents

        Returns:
            Response containing imported agent details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_agent(config)

            # Check existence if requested
            if check_exists:
                existing = self._check_exists(
                    ComponentTypes.AGENT, config, user_id)
                if existing:
                    return Response(
                        message=self._format_exists_message(
                            ComponentTypes.AGENT, config),
                        status=True,
                        data={"id": existing.id}
                    )

            # Import model if present
            model_id = None
            if "model_client" in config:
                model_result = self.import_model_config(
                    config["model_client"], user_id, check_exists=check_exists)
                if not model_result.status:
                    return model_result
                model_id = model_result.data["id"]

            # Import tools if present
            tool_ids = []
            for tool_config in config.get("tools", []):
                tool_result = self.import_tool_config(
                    tool_config, user_id, check_exists=check_exists)
                if not tool_result.status:
                    return tool_result
                tool_ids.append(tool_result.data["id"])

            # Create agent
            agent = Agent(
                user_id=user_id,
                config=AgentConfig(**config).model_dump()
            )
            agent_result = self.db_manager.upsert(agent)
            if not agent_result.status:
                return agent_result

            agent_id = agent_result.data["id"]

            # Create links
            if model_id:
                self.db_manager.link(LinkTypes.AGENT_MODEL, agent_id, model_id)
            for tool_id in tool_ids:
                self.db_manager.link(LinkTypes.AGENT_TOOL, agent_id, tool_id)

            return agent_result

        except Exception as e:
            logger.error(f"Failed to import agent config: {str(e)}")
            return Response(message=f"Failed to import agent: {str(e)}", status=False)

    def import_team_config(self, config: dict, user_id: str, check_exists: bool = True) -> Response:
        """
        Import team configuration and all its dependencies.

        Args:
            config: Team configuration dictionary
            user_id: User ID to associate with the team
            check_exists: Whether to check for existing teams

        Returns:
            Response containing imported team details or error
        """
        try:
            # Validate full config using provider
            self.agent_factory.load_team(config)

            # Check existence if requested
            if check_exists:
                existing = self._check_exists(
                    ComponentTypes.TEAM, config, user_id)
                if existing:
                    return Response(
                        message=self._format_exists_message(
                            ComponentTypes.TEAM, config),
                        status=True,
                        data={"id": existing.id}
                    )

            # Import all agents first
            agent_ids = []
            for participant in config["participants"]:
                agent_result = self.import_agent_config(
                    participant, user_id, check_exists=check_exists)
                if not agent_result.status:
                    return agent_result
                agent_ids.append(agent_result.data["id"])

            # Create team
            team = Team(
                user_id=user_id,
                config=TeamConfig(**config).model_dump()
            )
            team_result = self.db_manager.upsert(team)
            if not team_result.status:
                return team_result

            # Link team to agents
            for agent_id in agent_ids:
                self.db_manager.link(LinkTypes.TEAM_AGENT,
                                     team_result.data["id"], agent_id)

            return team_result

        except Exception as e:
            logger.error(f"Failed to import team config: {str(e)}")
            return Response(message=f"Failed to import team: {str(e)}", status=False)

    def _determine_component_type(self, config: dict) -> Optional[ComponentTypes]:
        """Determine component type from configuration dictionary"""
        if "team_type" in config:
            return ComponentTypes.TEAM
        elif "agent_type" in config:
            return ComponentTypes.AGENT
        elif "model_type" in config:
            return ComponentTypes.MODEL
        elif "name" in config and "content" in config:  # Tool signature
            return ComponentTypes.TOOL
        return None

    def import_config(self, config: Union[str, dict], user_id: str,
                      component_type: Optional[ComponentTypes] = None,
                      check_exists: bool = True) -> Response:
        """
        Import any type of configuration from file or dict.

        Args:
            config: Configuration file path or dictionary
            user_id: User ID to associate with imported items
            component_type: Optional explicit ComponentTypes to override automatic detection
            check_exists: Whether to check for existing components

        Returns:
            Response containing import results or error
        """
        # Load if it's a file path
        if isinstance(config, str):
            load_result = self._load_config_file(config)
            if not load_result.status:
                return load_result
            config = load_result.data

        # Determine type if not explicitly provided
        detected_type = component_type or self._determine_component_type(
            config)
        if not detected_type:
            return Response(
                message="Could not determine configuration type",
                status=False
            )

        # Import based on type
        try:
            import_methods = {
                ComponentTypes.TEAM: self.import_team_config,
                ComponentTypes.AGENT: self.import_agent_config,
                ComponentTypes.MODEL: self.import_model_config,
                ComponentTypes.TOOL: self.import_tool_config
            }
            return import_methods[detected_type](config, user_id, check_exists=check_exists)
        except Exception as e:
            logger.error(
                f"Failed to import {detected_type.value} config: {str(e)}")
            return Response(
                message=f"Failed to import {detected_type.value}: {str(e)}",
                status=False
            )

    def import_from_directory(self, directory: str, user_id: str, check_exists: bool = True) -> Response:
        """
        Import all configurations from a directory.

        Args:
            directory: Path to directory containing configuration files
            user_id: User ID to associate with imported items
            check_exists: Whether to check for existing components

        Returns:
            Response containing import results for all files
        """
        try:
            results = []
            for filename in os.listdir(directory):
                if filename.lower().endswith(('.json', '.yaml', '.yml')):
                    path = os.path.join(directory, filename)
                    result = self.import_config(
                        path, user_id, check_exists=check_exists)
                    results.append({
                        "file": filename,
                        "status": result.status,
                        "message": result.message
                    })

            return Response(
                message="Directory import complete",
                status=True,
                data=results
            )
        except Exception as e:
            logger.error(f"Failed to import directory {directory}: {str(e)}")
            return Response(message=f"Failed to import directory: {str(e)}", status=False)
