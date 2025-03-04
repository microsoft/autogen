import os
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from autogenstudio.teammanager import TeamManager
from autogenstudio.datamodel.types import TeamResult, EnvironmentVariable
from autogen_core import CancellationToken


@pytest.fixture
def sample_config():
    """Create an actual team and dump its configuration"""
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.teams import RoundRobinGroupChat
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from autogen_agentchat.conditions import TextMentionTermination
    
    agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4o-mini",
        ),
    )
    
    agent_team = RoundRobinGroupChat(
        [agent], 
        termination_condition=TextMentionTermination("TERMINATE")
    )
    
    # Dump component and return as dict
    config = agent_team.dump_component()
    return config.model_dump()


@pytest.fixture
def config_file(sample_config, tmp_path):
    """Create a temporary config file"""
    config_path = tmp_path / "test_config.json"
    with open(config_path, "w") as f:
        json.dump(sample_config, f)
    return config_path


@pytest.fixture
def config_dir(sample_config, tmp_path):
    """Create a temporary directory with multiple config files"""
    # Create JSON config
    json_path = tmp_path / "team1.json"
    with open(json_path, "w") as f:
        json.dump(sample_config, f)
    
    # Create YAML config from the same dict
    import yaml
    yaml_path = tmp_path / "team2.yaml"
    # Create a modified copy to verify we can distinguish between them
    yaml_config = sample_config.copy()
    yaml_config["label"] = "YamlTeam"  # Change a field to identify this as the YAML version
    with open(yaml_path, "w") as f:
        yaml.dump(yaml_config, f)
    
    return tmp_path


class TestTeamManager:
    
    @pytest.mark.asyncio
    async def test_load_from_file(self, config_file, sample_config):
        """Test loading configuration from a file"""
        config = await TeamManager.load_from_file(config_file)
        assert config == sample_config
        
        # Test file not found
        with pytest.raises(FileNotFoundError):
            await TeamManager.load_from_file("nonexistent_file.json")
        
        # Test unsupported format
        wrong_format = config_file.with_suffix(".txt")
        wrong_format.touch()
        with pytest.raises(ValueError, match="Unsupported file format"):
            await TeamManager.load_from_file(wrong_format)
    
    @pytest.mark.asyncio
    async def test_load_from_directory(self, config_dir):
        """Test loading all configurations from a directory"""
        configs = await TeamManager.load_from_directory(config_dir)
        assert len(configs) == 2 
        
        # Check if at least one team has expected label
        team_labels = [config.get("label") for config in configs]
        assert "RoundRobinGroupChat" in team_labels or "YamlTeam" in team_labels
    
    @pytest.mark.asyncio
    async def test_create_team(self, sample_config):
        """Test creating a team from config"""
        team_manager = TeamManager()
        
        # Mock Team.load_component
        with patch("autogen_agentchat.base.Team.load_component") as mock_load:
            mock_team = MagicMock()
            mock_load.return_value = mock_team
            
            team = await team_manager._create_team(sample_config)
            assert team == mock_team
            mock_load.assert_called_once_with(sample_config)
    
 
    
    @pytest.mark.asyncio
    async def test_run_stream(self, sample_config):
        """Test streaming team execution results"""
        team_manager = TeamManager()
        
        # Mock _create_team and team.run_stream
        with patch.object(team_manager, "_create_team") as mock_create:
            mock_team = MagicMock()
            
            # Create some mock messages to stream
            mock_messages = [MagicMock(), MagicMock()]
            mock_result = MagicMock()  # TaskResult from run
            mock_messages.append(mock_result)  # Last message is the result
            
            # Set up the async generator for run_stream
            async def mock_run_stream(*args, **kwargs):
                for msg in mock_messages:
                    yield msg
            
            mock_team.run_stream = mock_run_stream
            mock_create.return_value = mock_team
            
            # Call run_stream and collect results
            streamed_messages = []
            async for message in team_manager.run_stream(
                task="Test task",
                team_config=sample_config
            ):
                streamed_messages.append(message)
            
            # Verify the team was created
            mock_create.assert_called_once()
            
            # Check that we got the expected number of messages +1 for the TeamResult
            assert len(streamed_messages) == len(mock_messages)
            
            # Verify the last message is a TeamResult
            assert isinstance(streamed_messages[-1], type(mock_messages[-1]))
 