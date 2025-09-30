import os
from fastapi.testclient import TestClient
from autogenstudio.web.serve import app
from autogen_agentchat.messages import TextMessage
from autogen_agentchat.base import TaskResult
from autogenstudio.datamodel.types import TeamResult


client = TestClient(app)

def test_predict_success(monkeypatch):
    monkeypatch.setenv("AUTOGENSTUDIO_TEAM_FILE", "test_team_config.json")

    async def mock_run(*args, **kwargs):
        assert kwargs.get('task') == 'test_task', f"Expected task='test_task', got {kwargs.get('task')}"
        text_message = TextMessage(
            source="agent1",
            content="Mission accomplished.",
            metadata={"topic": "status"}
        )
        task_result = TaskResult(messages=[text_message], stop_reason="test")
        team_result = TeamResult(
            task_result=task_result,
            usage="3 tokens",
            duration=0.45
        )
        return team_result
    
    from autogenstudio.web.serve import team_manager
    team_manager.run = mock_run
    
    response = client.get("/predict/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Task successfully completed"

def test_predict_missing_env_var():
    # Ensure environment variable is not set
    if "AUTOGENSTUDIO_TEAM_FILE" in os.environ:
        del os.environ["AUTOGENSTUDIO_TEAM_FILE"]
    
    response = client.get("/predict/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is False
    assert "AUTOGENSTUDIO_TEAM_FILE environment variable is not set" in data["message"]

def test_predict_team_success(monkeypatch):
    monkeypatch.setenv("AUTOGENSTUDIO_TEAM_FOLDER", "notebooks")

    async def mock_run(*args, **kwargs):
        assert kwargs.get('task') == 'test_task', f"Expected task='test_task', got {kwargs.get('task')}"
        assert kwargs.get('team_config') == 'notebooks/team.json', f"Expected team_config='notebooks/team.json', got {kwargs.get('team_config')}"
        text_message = TextMessage(
            source="agent1",
            content="Mission accomplished.",
            metadata={"topic": "status"}
        )
        task_result = TaskResult(messages=[text_message], stop_reason="test")
        team_result = TeamResult(
            task_result=task_result,
            usage="3 tokens",
            duration=0.45
        )
        return team_result
    
    from autogenstudio.web.serve import team_manager
    team_manager.run = mock_run
    
    response = client.get("/predict_team/team/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Task successfully completed"

def test_predict_team_missing_env_var():
    # Ensure environment variable is not set
    if "AUTOGENSTUDIO_TEAM_FOLDER" in os.environ:
        del os.environ["AUTOGENSTUDIO_TEAM_FOLDER"]
    
    response = client.get("/predict_team/test_team/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is False
    assert "AUTOGENSTUDIO_TEAM_FOLDER environment variable is not set" in data["message"]


def test_predict_team_manager_error(monkeypatch):
    monkeypatch.setenv("AUTOGENSTUDIO_TEAM_FOLDER", "notebooks")
    
    # Mock the team_manager.run method to raise an exception
    async def mock_run(*args, **kwargs):
        assert kwargs.get('task') == 'test_task', f"Expected task='test_task', got {kwargs.get('task')}"
        assert kwargs.get('team_config') == 'notebooks/team.json', f"Expected team_config='notebooks/team.json', got {kwargs.get('team_config')}"
        raise Exception("Test error")
    
    from autogenstudio.web.serve import team_manager
    team_manager.run = mock_run
    
    response = client.get("/predict_team/team/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is False
    assert data["message"] == "Test error" 