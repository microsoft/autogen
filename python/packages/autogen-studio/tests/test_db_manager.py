import os
import asyncio
import pytest
from sqlmodel import Session, text, select
from typing import Generator

from autogenstudio.database import DatabaseManager
from autogenstudio.datamodel.types import (
    ToolConfig,
    OpenAIModelConfig,
    RoundRobinTeamConfig,
    StopMessageTerminationConfig,
    AssistantAgentConfig,
    ModelTypes, AgentTypes, TeamTypes, ComponentTypes,
    TerminationTypes,  ToolTypes
)
from autogenstudio.datamodel.db import Model, Tool, Agent, Team, LinkTypes


@pytest.fixture
def test_db() -> Generator[DatabaseManager, None, None]:
    """Fixture for test database"""
    db_path = "test.db"
    db = DatabaseManager(f"sqlite:///{db_path}")
    db.reset_db()
    # Initialize database instead of create_db_and_tables
    db.initialize_database(auto_upgrade=False)
    yield db
    # Clean up
    asyncio.run(db.close())
    db.reset_db()
    try:
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
        config=OpenAIModelConfig(
            model="gpt-4",
            model_type=ModelTypes.OPENAI,
            component_type=ComponentTypes.MODEL,
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
            component_type=ComponentTypes.TOOL,
            version="1.0.0"
        ).model_dump()
    )


@pytest.fixture
def sample_agent(test_user: str, sample_model: Model, sample_tool: Tool) -> Agent:
    """Create a sample agent with proper config and relationships"""
    return Agent(
        user_id=test_user,
        config=AssistantAgentConfig(
            name="test_agent",
            agent_type=AgentTypes.ASSISTANT,
            model_client=OpenAIModelConfig.model_validate(sample_model.config),
            tools=[ToolConfig.model_validate(sample_tool.config)],
            component_type=ComponentTypes.AGENT,
            version="1.0.0"
        ).model_dump()
    )


@pytest.fixture
def sample_team(test_user: str, sample_agent: Agent) -> Team:
    """Create a sample team with proper config"""
    return Team(
        user_id=test_user,
        config=RoundRobinTeamConfig(
            name="test_team",
            participants=[AssistantAgentConfig.model_validate(
                sample_agent.config)],
            termination_condition=StopMessageTerminationConfig(
                termination_type=TerminationTypes.STOP_MESSAGE,
                component_type=ComponentTypes.TERMINATION,
                version="1.0.0"
            ).model_dump(),
            team_type=TeamTypes.ROUND_ROBIN,
            component_type=ComponentTypes.TEAM,
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
                config=OpenAIModelConfig(
                    model="gpt-4",
                    model_type=ModelTypes.OPENAI,
                    component_type=ComponentTypes.MODEL,
                    version="1.0.0"
                ).model_dump()
            )
            model2 = Model(
                user_id="test_user",
                config=OpenAIModelConfig(
                    model="gpt-3.5",
                    model_type=ModelTypes.OPENAI,
                    component_type=ComponentTypes.MODEL,
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

    def test_upsert_operations(self, test_db: DatabaseManager, sample_model: Model):
        """Test upsert for both create and update scenarios"""
        # Test Create
        response = test_db.upsert(sample_model)
        assert response.status is True
        assert "Created Successfully" in response.message

        # Test Update
        sample_model.config["model"] = "gpt-4-turbo"
        response = test_db.upsert(sample_model)
        assert response.status is True
        assert "Updated Successfully" in response.message

        # Verify Update
        result = test_db.get(Model, {"id": sample_model.id})
        assert result.status is True
        assert result.data[0].config["model"] == "gpt-4-turbo"

    def test_delete_operations(self, test_db: DatabaseManager, sample_model: Model):
        """Test delete with various filters"""
        # First insert the model
        test_db.upsert(sample_model)

        # Test deletion by id
        response = test_db.delete(Model, {"id": sample_model.id})
        assert response.status is True
        assert "Deleted Successfully" in response.message

        # Verify deletion
        result = test_db.get(Model, {"id": sample_model.id})
        assert len(result.data) == 0

        # Test deletion with non-existent id
        response = test_db.delete(Model, {"id": 999999})
        assert "Row not found" in response.message

    def test_initialize_database_scenarios(self):
        """Test different initialize_database parameters"""
        db_path = "test_init.db"
        db = DatabaseManager(f"sqlite:///{db_path}")

        try:
            # Test basic initialization
            response = db.initialize_database()
            assert response.status is True

            # Test with auto_upgrade
            response = db.initialize_database(auto_upgrade=True)
            assert response.status is True

        finally:
            asyncio.run(db.close())
            db.reset_db()
            if os.path.exists(db_path):
                os.remove(db_path)
