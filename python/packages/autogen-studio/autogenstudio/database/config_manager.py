import os
import json
from typing import Optional, Union
from loguru import logger

from sqlmodel import Session, text, select
from ..datamodel import (
    Model, ModelConfig, Team, TeamConfig,
    Agent, AgentConfig, Tool, ToolConfig,
    ModelTypes, TeamTypes, AgentTypes, LinkTypes,
    Response, ComponentTypes
)

from .agent_factory import AgentFactory
from .db_manager import DatabaseManager


class ConfigurationManager:
    """Manages loading, validation, and storage of configurations for teams, agents, models, and tools."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize Configuration Manager.

        Args:
            db_manager: Database manager instance for storage operations 
        """
        self.db_manager = db_manager
        self.agent_factory = AgentFactory()

    def _load_config_file(self, path: str) -> Response:
        """
        Load configuration from JSON or YAML file.

        Args:
            path: Path to configuration file

        Returns:
            Response object containing loaded configuration or error
        """
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

    def validate_config(self, config: dict) -> Response:
        """
        Validate configuration using provider.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Response indicating validation result
        """
        try:
            # Determine config type and validate accordingly
            if "team_type" in config:
                self.agent_factory.load_team(config)
            elif "agent_type" in config:
                self.agent_factory.load_agent(config)
            elif "model_type" in config:
                self.agent_factory.load_model(config)
            elif "name" in config and "content" in config:
                self.agent_factory.load_tool(config)
            else:
                return Response(message="Unknown configuration type", status=False)

            return Response(message="Configuration is valid", status=True)
        except Exception as e:
            return Response(message=f"Configuration validation failed: {str(e)}", status=False)

    def import_model_config(self, config: dict, user_id: str) -> Response:
        """
        Import model configuration.

        Args:
            config: Model configuration dictionary
            user_id: User ID to associate with the model

        Returns:
            Response containing imported model details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_model(config)

            # Create model
            model = Model(
                user_id=user_id,
                config=ModelConfig(**config).model_dump()
            )
            return self.db_manager.upsert(model)
        except Exception as e:
            logger.error(f"Failed to import model config: {str(e)}")
            return Response(message=f"Failed to import model: {str(e)}", status=False)

    def import_tool_config(self, config: dict, user_id: str) -> Response:
        """
        Import tool configuration.

        Args:
            config: Tool configuration dictionary
            user_id: User ID to associate with the tool

        Returns:
            Response containing imported tool details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_tool(config)

            tool = Tool(
                user_id=user_id,
                config=ToolConfig(**config).model_dump()
            )
            return self.db_manager.upsert(tool)
        except Exception as e:
            logger.error(f"Failed to import tool config: {str(e)}")
            return Response(message=f"Failed to import tool: {str(e)}", status=False)

    def import_agent_config(self, config: dict, user_id: str) -> Response:
        """
        Import agent configuration and its dependencies.

        Args:
            config: Agent configuration dictionary
            user_id: User ID to associate with the agent

        Returns:
            Response containing imported agent details or error
        """
        try:
            # Validate using provider
            self.agent_factory.load_agent(config)

            # Import model if present
            model_id = None
            if "model_client" in config:
                model_result = self.import_model_config(
                    config["model_client"], user_id)
                if not model_result.status:
                    return model_result
                model_id = model_result.data["id"]

            # Import tools if present
            tool_ids = []
            for tool_config in config.get("tools", []):
                tool_result = self.import_tool_config(tool_config, user_id)
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

    def import_team_config(self, config: dict, user_id: str) -> Response:
        """
        Import team configuration and all its dependencies.

        Args:
            config: Team configuration dictionary
            user_id: User ID to associate with the team

        Returns:
            Response containing imported team details or error
        """
        try:
            # Validate full config using provider
            self.agent_factory.load_team(config)

            # Import all agents first
            agent_ids = []
            for participant in config["participants"]:
                agent_result = self.import_agent_config(participant, user_id)
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

    def import_config(self, config: Union[str, dict], user_id: str, component_type: Optional[ComponentTypes] = None) -> Response:
        """
        Import any type of configuration from file or dict.

        Args:
            config: Configuration file path or dictionary
            user_id: User ID to associate with imported items
            component_type: Optional explicit ComponentTypes to override automatic detection

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
            return import_methods[detected_type](config, user_id)
        except Exception as e:
            logger.error(
                f"Failed to import {detected_type.value} config: {str(e)}")
            return Response(
                message=f"Failed to import {detected_type.value}: {str(e)}",
                status=False
            )

    def import_from_directory(self, directory: str, user_id: str) -> Response:
        """
        Import all configurations from a directory.

        Args:
            directory: Path to directory containing configuration files
            user_id: User ID to associate with imported items

        Returns:
            Response containing import results for all files
        """
        try:
            results = []
            for filename in os.listdir(directory):
                if filename.lower().endswith(('.json', '.yaml', '.yml')):
                    path = os.path.join(directory, filename)
                    result = self.import_config(path, user_id)
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

    def export_config(self, team_id: int) -> Response:
        """
        Export team configuration to dictionary format.

        Args:
            team_id: ID of team to export

        Returns:
            Response containing complete team configuration or error
        """
        try:
            # Get team
            team_result = self.db_manager.get(Team, {"id": team_id})
            if not team_result.status or not team_result.data:
                return Response(message="Team not found", status=False)

            team = team_result.data[0]
            team_config = team.config  # Base team config

            # Get linked agents
            linked_agents = self.db_manager.get_linked_entities(
                LinkTypes.TEAM_AGENT,
                team_id
            )
            if not linked_agents.status:
                return linked_agents

            # Build participants list
            participants = []
            for agent in linked_agents.data:
                agent_config = agent.config.copy()  # Start with base agent config

                # Get agent's model
                model_result = self.db_manager.get_linked_entities(
                    LinkTypes.AGENT_MODEL,
                    agent.id
                )
                if model_result.status and model_result.data:
                    agent_config["model_client"] = model_result.data[0].config

                # Get agent's tools
                tools_result = self.db_manager.get_linked_entities(
                    LinkTypes.AGENT_TOOL,
                    agent.id
                )
                if tools_result.status and tools_result.data:
                    agent_config["tools"] = [
                        tool.config for tool in tools_result.data
                    ]

                participants.append(agent_config)

            # Reconstruct full team config
            full_config = team_config.copy()
            full_config["participants"] = participants

            return Response(
                message="Team configuration exported successfully",
                status=True,
                data=full_config
            )

        except Exception as e:
            logger.error(f"Failed to export team config: {str(e)}")
            return Response(
                message=f"Failed to export team configuration: {str(e)}",
                status=False
            )

    def export_config_to_file(self, team_id: int, filepath: str) -> Response:
        """
        Export team configuration to a JSON or YAML file.

        Args:
            team_id: ID of team to export
            filepath: Path where to save the configuration file

        Returns:
            Response indicating success or failure
        """
        try:
            # Get configuration
            config_result = self.export_config(team_id)
            if not config_result.status:
                return config_result

            # Determine format from file extension
            ext = filepath.lower().split('.')[-1]

            with open(filepath, 'w') as f:
                if ext == 'json':
                    json.dump(config_result.data, f, indent=2)
                elif ext in ('yaml', 'yml'):
                    import yaml
                    yaml.dump(config_result.data, f, sort_keys=False)
                else:
                    return Response(
                        message=f"Unsupported file format: {ext}",
                        status=False
                    )

            return Response(
                message=f"Configuration exported to {filepath}",
                status=True
            )

        except Exception as e:
            logger.error(f"Failed to export config to file: {str(e)}")
            return Response(
                message=f"Failed to export configuration to file: {str(e)}",
                status=False
            )
