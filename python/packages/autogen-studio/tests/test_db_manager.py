import os
import pytest
from sqlmodel import Session, text, select
from typing import Generator
from datetime import datetime

from autogenstudio.database import DatabaseManager
from autogenstudio.datamodel import (
    Model, ModelConfig, Agent, AgentConfig, Tool, ToolConfig,
    Team, TeamConfig, ModelTypes, AgentTypes, TeamTypes, ComponentType,
    TerminationConfig, TerminationTypes, LinkTypes, ToolTypes
)


@pytest.fixture
def test_db() -> Generator[DatabaseManager, None, None]:
    """Fixture for test database"""
    db_path = "test.db"
    db = DatabaseManager(f"sqlite:///{db_path}")
    db.reset_db()
    db.create_db_and_tables()
    yield db
    db.reset_db()
    try:
        # Close database connections before removing file
        db.engine.dispose()
        # Remove the database file
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception as e:
        print(f"Warning: Failed to remove test database file: {e}")


@pytest.fixture
def test_user() -> str:
    return "test_user@example.com"


@pytest.fixture
def sample_model(test_user: str) -> Model:
    """Create a sample model with proper config"""
    return Model(
        user_id=test_user,
        config=ModelConfig(
            model="gpt-4",
            model_type=ModelTypes.OPENAI,
            component_type=ComponentType.MODEL,
            version="1.0.0"
        ).model_dump()
    )


@pytest.fixture
def sample_tool(test_user: str) -> Tool:
    """Create a sample tool with proper config"""
    return Tool(
        user_id=test_user,
        config=ToolConfig(
            name="test_tool",
            description="A test tool",
            content="async def test_func(x: str) -> str:\n    return f'Test {x}'",
            tool_type=ToolTypes.PYTHON_FUNCTION,
            component_type=ComponentType.TOOL,
            version="1.0.0"
        ).model_dump()
    )


@pytest.fixture
def sample_agent(test_user: str, sample_model: Model, sample_tool: Tool) -> Agent:
    """Create a sample agent with proper config and relationships"""
    return Agent(
        user_id=test_user,
        config=AgentConfig(
            name="test_agent",
            agent_type=AgentTypes.ASSISTANT,
            model_client=ModelConfig.model_validate(sample_model.config),
            tools=[ToolConfig.model_validate(sample_tool.config)],
            component_type=ComponentType.AGENT,
            version="1.0.0"
        ).model_dump()
    )


@pytest.fixture
def sample_team(test_user: str, sample_agent: Agent) -> Team:
    """Create a sample team with proper config"""
    return Team(
        user_id=test_user,
        config=TeamConfig(
            name="test_team",
            participants=[AgentConfig.model_validate(sample_agent.config)],
            termination_condition=TerminationConfig(
                termination_type=TerminationTypes.STOP_MESSAGE,
                component_type=ComponentType.TERMINATION,
                version="1.0.0"
            ).model_dump(),
            team_type=TeamTypes.ROUND_ROBIN,
            component_type=ComponentType.TEAM,
            version="1.0.0"
        ).model_dump()
    )


class TestDatabaseOperations:
    def test_basic_setup(self, test_db: DatabaseManager):
        """Test basic database setup and connection"""
        with Session(test_db.engine) as session:
            result = session.exec(text("SELECT 1")).first()
            assert result[0] == 1
            result = session.exec(select(1)).first()
            assert result == 1

    def test_basic_entity_creation(self, test_db: DatabaseManager, sample_model: Model,
                                   sample_tool: Tool, sample_agent: Agent, sample_team: Team):
        """Test creating all entity types with proper configs"""
        with Session(test_db.engine) as session:
            # Add all entities
            session.add(sample_model)
            session.add(sample_tool)
            session.add(sample_agent)
            session.add(sample_team)
            session.commit()

            # Store IDs
            model_id = sample_model.id
            tool_id = sample_tool.id
            agent_id = sample_agent.id
            team_id = sample_team.id

        # Verify all entities were created with new session
        with Session(test_db.engine) as session:
            assert session.get(Model, model_id) is not None
            assert session.get(Tool, tool_id) is not None
            assert session.get(Agent, agent_id) is not None
            assert session.get(Team, team_id) is not None

    def test_multiple_links(self, test_db: DatabaseManager, sample_agent: Agent):
        """Test linking multiple models to an agent"""
        with Session(test_db.engine) as session:
            # Create two models with updated configs
            model1 = Model(
                user_id="test_user",
                config=ModelConfig(
                    model="gpt-4",
                    model_type=ModelTypes.OPENAI,
                    component_type=ComponentType.MODEL,
                    version="1.0.0"
                ).model_dump()
            )
            model2 = Model(
                user_id="test_user",
                config=ModelConfig(
                    model="gpt-3.5",
                    model_type=ModelTypes.OPENAI,
                    component_type=ComponentType.MODEL,
                    version="1.0.0"
                ).model_dump()
            )

            # Add and commit all entities
            session.add(model1)
            session.add(model2)
            session.add(sample_agent)
            session.commit()

            model1_id = model1.id
            model2_id = model2.id
            agent_id = sample_agent.id

        # Create links using IDs
        test_db.link(LinkTypes.AGENT_MODEL, agent_id, model1_id)
        test_db.link(LinkTypes.AGENT_MODEL, agent_id, model2_id)

        # Verify links
        linked_models = test_db.get_linked_entities(
            LinkTypes.AGENT_MODEL, agent_id)
        assert len(linked_models.data) == 2

        # Verify model names
        model_names = [model.config["model"] for model in linked_models.data]
        assert "gpt-4" in model_names
        assert "gpt-3.5" in model_names
