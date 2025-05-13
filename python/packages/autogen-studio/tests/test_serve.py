import os
from fastapi.testclient import TestClient
from autogenstudio.web.serve import app

client = TestClient(app)

def test_predict_success(monkeypatch):
    # Mock environment variable
    monkeypatch.setenv("AUTOGENSTUDIO_TEAM_FILE", "test_team_config.json")
    
    # Mock the team_manager.run method
    async def mock_run(*args, **kwargs):
        assert kwargs.get('task') == 'test_task', f"Expected task='test_task', got {kwargs.get('task')}"
        return "Test result"
    
    from autogenstudio.web.serve import team_manager
    team_manager.run = mock_run
    
    response = client.get("/predict/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert data["message"] == "Task successfully completed"
    assert data["data"] == "Test result"

def test_predict_missing_env_var():
    # Ensure environment variable is not set
    if "AUTOGENSTUDIO_TEAM_FILE" in os.environ:
        del os.environ["AUTOGENSTUDIO_TEAM_FILE"]
    
    response = client.get("/predict/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is False
    assert "AUTOGENSTUDIO_TEAM_FILE environment variable is not set" in data["message"]

def test_predict_team_manager_error(monkeypatch):
    # Mock environment variable
    monkeypatch.setenv("AUTOGENSTUDIO_TEAM_FILE", "test_team_config.json")
    
    # Mock the team_manager.run method to raise an exception
    async def mock_run(*args, **kwargs):
        assert kwargs.get('task') == 'test_task', f"Expected task='test_task', got {kwargs.get('task')}"
        raise Exception("Test error")
    
    from autogenstudio.web.serve import team_manager
    team_manager.run = mock_run
    
    response = client.get("/predict/test_task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is False
    assert data["message"] == "Test error" 