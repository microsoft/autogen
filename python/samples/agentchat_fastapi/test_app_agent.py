import asyncio
import json

import app_agent
import httpx
import pytest
from autogen_agentchat.messages import TextMessage


class _FakeAgent:
    async def on_messages(self, messages, cancellation_token):
        await asyncio.sleep(0)
        return _FakeResponse(TextMessage(content="ok", source="assistant"))

    async def save_state(self):
        return {"turns": 1}


class _FakeResponse:
    def __init__(self, chat_message):
        self.chat_message = chat_message


@pytest.fixture
def chat_client(tmp_path, monkeypatch):
    history_path = tmp_path / "agent_history.json"
    state_path = tmp_path / "agent_state.json"
    monkeypatch.setattr(app_agent, "history_path", str(history_path))
    monkeypatch.setattr(app_agent, "state_path", str(state_path))

    async def fake_get_agent():
        return _FakeAgent()

    monkeypatch.setattr(app_agent, "get_agent", fake_get_agent)

    transport = httpx.ASGITransport(app=app_agent.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test"), history_path


@pytest.mark.asyncio
async def test_concurrent_chats_keep_state_and_history_valid(chat_client):
    client, history_path = chat_client
    async with client:
        responses = await asyncio.gather(
            *[
                client.post(
                    "/chat",
                    json={"source": "user", "content": f"message {i}", "type": "TextMessage"},
                )
                for i in range(10)
            ]
        )

    for response in responses:
        assert response.status_code == 200

    history = json.loads(history_path.read_text())
    assert len(history) == 20
    assert all(isinstance(item, dict) for item in history)
