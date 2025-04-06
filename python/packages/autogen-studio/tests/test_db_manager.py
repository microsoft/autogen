import asyncio 
import pytest
from sqlmodel import Session, text, select
from typing import Generator

from autogenstudio.database import DatabaseManager
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.conditions import TextMentionTermination
from autogenstudio.datamodel.db import Team, Session as SessionModel, Run, Message, RunStatus, MessageConfig


@pytest.fixture
def test_db(tmp_path) -> Generator[DatabaseManager, None, None]:
    """Fixture for test database using temporary paths"""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
    db.reset_db()
    # Initialize database instead of create_db_and_tables
    db.initialize_database(auto_upgrade=False)
    yield db
    # Clean up
    asyncio.run(db.close())
    db.reset_db()
    # No need to manually remove files - tmp_path is cleaned up automatically


@pytest.fixture
def test_user() -> str:
    return "test_user@example.com"


@pytest.fixture
def sample_team(test_user: str) -> Team:
    """Create a sample team with proper config"""
    agent = AssistantAgent(
        name="weather_agent",
        model_client=OpenAIChatCompletionClient(
            model="gpt-4",
        ), 
    )

    agent_team = RoundRobinGroupChat([agent], termination_condition=TextMentionTermination("TERMINATE"))
    team_component = agent_team.dump_component()

    return Team(
        user_id=test_user,
        component=team_component.model_dump(),
    )


class TestDatabaseOperations:
    def test_basic_setup(self, test_db: DatabaseManager):
        """Test basic database setup and connection"""
        with Session(test_db.engine) as session:
            result = session.exec(text("SELECT 1")).first() # type: ignore
            assert result[0] == 1
            result = session.exec(select(1)).first()
            assert result == 1

    def test_basic_entity_creation(self, test_db: DatabaseManager, sample_team: Team):
        """Test creating all entity types with proper configs"""
        # Use upsert instead of raw session
        response = test_db.upsert(sample_team)
        assert response.status is True
        
        with Session(test_db.engine) as session:
            saved_team = session.get(Team, sample_team.id)
            assert saved_team is not None

    def test_upsert_operations(self, test_db: DatabaseManager, sample_team: Team):
        """Test upsert for both create and update scenarios"""
        # Test Create
        response = test_db.upsert(sample_team)
        assert response.status is True
        assert "Created Successfully" in response.message

        # Test Update
        team_id = sample_team.id
        sample_team.version = "0.0.2"
        response = test_db.upsert(sample_team)
        assert response.status is True

        # Verify Update
        result = test_db.get(Team, {"id": team_id})
        assert result.status is True
        assert result.data and result.data[0].version == "0.0.2"

    def test_delete_operations(self, test_db: DatabaseManager, sample_team: Team):
        """Test delete with various filters"""
        # First insert the model
        response = test_db.upsert(sample_team)
        assert response.status is True  # Verify insert worked
        
        # Get the ID that was actually saved
        team_id = sample_team.id
        
        # Test deletion by id
        response = test_db.delete(Team, {"id": team_id})
        assert response.status is True
        assert "Deleted Successfully" in response.message

        # Verify deletion
        result = test_db.get(Team, {"id": team_id})
        assert result.data and len(result.data) == 0
        
    def test_cascade_delete(self, test_db: DatabaseManager, test_user: str):
        """Test all levels of cascade delete"""
        # Enable foreign keys for SQLite (crucial for cascade delete)
        with Session(test_db.engine) as session:
            session.execute(text("PRAGMA foreign_keys=ON"))
            session.commit()

        # Test Run -> Message cascade
        team1 = Team(user_id=test_user, component={"name": "Team1", "type": "team"})
        test_db.upsert(team1)
        session1 = SessionModel(user_id=test_user, team_id=team1.id, name="Session1")
        test_db.upsert(session1)
        run1_id = 1
        test_db.upsert(Run(
            id=run1_id, 
            user_id=test_user, 
            session_id=session1.id, 
            status=RunStatus.COMPLETE, 
            task=MessageConfig(content="Task1", source="user").model_dump()
        ))
        test_db.upsert(Message(
            user_id=test_user, 
            session_id=session1.id, 
            run_id=run1_id, 
            config=MessageConfig(content="Message1", source="assistant").model_dump()
        ))
        
        test_db.delete(Run, {"id": run1_id})
        db_message = test_db.get(Message, {"run_id": run1_id})
        assert db_message.data and len(db_message.data) == 0, "Run->Message cascade failed"

        # Test Session -> Run -> Message cascade
        session2 = SessionModel(user_id=test_user, team_id=team1.id, name="Session2")
        test_db.upsert(session2)
        run2_id = 2
        test_db.upsert(Run(
            id=run2_id, 
            user_id=test_user, 
            session_id=session2.id, 
            status=RunStatus.COMPLETE, 
            task=MessageConfig(content="Task2", source="user").model_dump()
        ))
        test_db.upsert(Message(
            user_id=test_user, 
            session_id=session2.id, 
            run_id=run2_id, 
            config=MessageConfig(content="Message2", source="assistant").model_dump()
        ))
        
        test_db.delete(SessionModel, {"id": session2.id})
        session = test_db.get(SessionModel, {"id": session2.id})
        run = test_db.get(Run, {"id": run2_id})
        assert session.data and len(session.data) == 0, "Session->Run cascade failed"
        assert run.data and len(run.data) == 0, "Session->Run->Message cascade failed"

        # Clean up
        test_db.delete(Team, {"id": team1.id})

    def test_initialize_database_scenarios(self, tmp_path, monkeypatch):
        """Test different initialize_database parameters"""
        db_path = tmp_path / "test_init.db"
        db = DatabaseManager(f"sqlite:///{db_path}", base_dir=tmp_path)
        
        # Mock the schema manager's check_schema_status to avoid migration issues
        monkeypatch.setattr(db.schema_manager, "check_schema_status", lambda: (False, None))
        monkeypatch.setattr(db.schema_manager, "ensure_schema_up_to_date", lambda: True)

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