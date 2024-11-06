import pytest
from sqlmodel import Session, text, select
from typing import Generator

from autogenstudio.database import DatabaseManager
from autogenstudio.datamodel import (
    Model, ModelConfig, Agent, AgentConfig, Tool, ToolConfig,
    Team, TeamConfig, ModelTypes, AgentTypes, TeamTypes,
    TerminationConfig, TerminationTypes, LinkTypes
)


@pytest.fixture
def test_db() -> Generator[DatabaseManager, None, None]:
    """Fixture for test database"""
    db = DatabaseManager("sqlite:///test.db")
    db.reset_db()
    db.create_db_and_tables()
    yield db
    db.reset_db()


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
            model_type=ModelTypes.openai
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
            content="async def test_func(x: str) -> str:\n    return f'Test {x}'"
        ).model_dump()
    )


@pytest.fixture
def sample_agent(test_user: str, sample_model: Model, sample_tool: Tool) -> Agent:
    """Create a sample agent with proper config and relationships"""
    return Agent(
        user_id=test_user,
        config=AgentConfig(
            name="test_agent",
            model_client=sample_model.config,
            tools=[sample_tool.config],
            agent_type=AgentTypes.assistant
        ).model_dump()
    )


@pytest.fixture
def sample_team(test_user: str, sample_agent: Agent) -> Team:
    """Create a sample team with proper config"""
    return Team(
        user_id=test_user,
        config=TeamConfig(
            name="test_team",
            participants=[sample_agent.config],
            termination_condition=TerminationConfig(
                termination_type=TerminationTypes.stop_message
            ).model_dump(),
            team_type=TeamTypes.round_robin
        ).model_dump()
    )


class TestDatabaseOperations:
    def test_basic_setup(self, test_db: DatabaseManager):
        """Test basic database setup and connection"""
        with Session(test_db.engine) as session:
            # Using raw SQL - returns tuple
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

    def test_complex_relationships(self, test_db: DatabaseManager, sample_model: Model,
                                   sample_tool: Tool, sample_agent: Agent, sample_team: Team):
        """Test creating and querying complex relationships between entities"""
        # Store IDs for later use
        with Session(test_db.engine) as session:
            # Add all entities
            session.add(sample_model)
            session.add(sample_tool)
            session.add(sample_agent)
            session.add(sample_team)
            session.commit()

            # Store IDs before session closes
            model_id = sample_model.id
            tool_id = sample_tool.id
            agent_id = sample_agent.id
            team_id = sample_team.id

        # Create relationships using IDs
        test_db.link(LinkTypes.AGENT_MODEL, agent_id, model_id)
        test_db.link(LinkTypes.AGENT_TOOL, agent_id, tool_id)
        test_db.link(LinkTypes.TEAM_AGENT, team_id, agent_id)

        # Verify relationships
        agent_models = test_db.get_linked_entities(
            LinkTypes.AGENT_MODEL, agent_id)
        assert len(agent_models.data) == 1
        assert agent_models.data[0].id == model_id

        agent_tools = test_db.get_linked_entities(
            LinkTypes.AGENT_TOOL, agent_id)
        assert len(agent_tools.data) == 1
        assert agent_tools.data[0].id == tool_id

        team_agents = test_db.get_linked_entities(
            LinkTypes.TEAM_AGENT, team_id)
        assert len(team_agents.data) == 1
        assert team_agents.data[0].id == agent_id

    def test_multiple_links(self, test_db: DatabaseManager, sample_agent: Agent):
        """Test linking multiple models to an agent"""
        with Session(test_db.engine) as session:
            # Create two models
            model1 = Model(user_id="test_user",
                           config=ModelConfig(model="gpt-4",
                                              model_type=ModelTypes.openai).model_dump())
            model2 = Model(user_id="test_user",
                           config=ModelConfig(model="gpt-3.5",
                                              model_type=ModelTypes.openai).model_dump())

            # Add and commit all entities
            session.add(model1)
            session.add(model2)
            session.add(sample_agent)
            session.commit()

            # Store IDs before closing session
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

        # Verify sequence ordering
        model_names = [model.config["model"] for model in linked_models.data]
        assert "gpt-4" in model_names
        assert "gpt-3.5" in model_names

    def test_entity_queries(self, test_db: DatabaseManager, test_user: str, sample_agent: Agent):
        """Test querying entities with filters"""
        with Session(test_db.engine) as session:
            session.add(sample_agent)
            session.commit()
            agent_id = sample_agent.id

        # Test getting all agents
        all_agents = test_db.get(Agent)
        assert len(all_agents.data) == 1
        assert all_agents.data[0].id == agent_id

        # Test filtering by user
        user_agents = test_db.get(Agent, {"user_id": test_user})
        assert len(user_agents.data) == 1
        assert user_agents.data[0].id == agent_id
        assert user_agents.data[0].user_id == test_user

    def test_error_handling(self, test_db: DatabaseManager, sample_agent: Agent):
        """Test error handling scenarios"""
        # Test linking non-existent entities
        response = test_db.link(LinkTypes.AGENT_MODEL, 999, 888)
        assert not response.status
        assert "entities do not exist" in response.message.lower(
        ) or "one or both entities do not exist" in response.message.lower()

        # Test duplicate links
        with Session(test_db.engine) as session:
            model = Model(user_id="test_user",
                          config=ModelConfig(model="gpt-4",
                                             model_type=ModelTypes.openai).model_dump())
            session.add(model)
            session.add(sample_agent)
            session.commit()

            model_id = model.id
            agent_id = sample_agent.id

        # Create first link
        test_db.link(LinkTypes.AGENT_MODEL, agent_id, model_id)

        # Try to create duplicate link
        response = test_db.link(LinkTypes.AGENT_MODEL, agent_id, model_id)
        assert not response.status
        assert "already exists" in response.message.lower()

    def test_delete_cascade(self, test_db: DatabaseManager, sample_model: Model,
                            sample_tool: Tool, sample_agent: Agent, sample_team: Team):
        """Test deletion with cascading relationships"""
        with Session(test_db.engine) as session:
            session.add(sample_model)
            session.add(sample_tool)
            session.add(sample_agent)
            session.add(sample_team)
            session.commit()

            model_id = sample_model.id
            tool_id = sample_tool.id
            agent_id = sample_agent.id
            team_id = sample_team.id

        # Create relationships
        test_db.link(LinkTypes.AGENT_MODEL, agent_id, model_id)
        test_db.link(LinkTypes.AGENT_TOOL, agent_id, tool_id)
        test_db.link(LinkTypes.TEAM_AGENT, team_id, agent_id)

        # Delete the agent
        response = test_db.delete(Agent, {"id": agent_id})
        assert response.status

        # Verify relationships are cleaned up
        with Session(test_db.engine) as session:
            # Agent should be gone
            assert session.get(Agent, agent_id) is None

            # Other entities should still exist
            assert session.get(Model, model_id) is not None
            assert session.get(Tool, tool_id) is not None
            assert session.get(Team, team_id) is not None

            # Links should be gone
            agent_models = test_db.get_linked_entities(
                LinkTypes.AGENT_MODEL, agent_id)
            assert len(agent_models.data) == 0

            agent_tools = test_db.get_linked_entities(
                LinkTypes.AGENT_TOOL, agent_id)
            assert len(agent_tools.data) == 0

            team_agents = test_db.get_linked_entities(
                LinkTypes.TEAM_AGENT, team_id)
            assert len(team_agents.data) == 0
