
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from autogen_ext.tools.cross_chain import CrossChainIntentTool, CrossChainOrder
from autogen_core import CancellationToken
import httpx

@pytest.mark.asyncio
async def test_cross_chain_intent_tool_run():
    solver_url = "https://api.solver.xyz/v1/intents"
    tool = CrossChainIntentTool(solver_url=solver_url)
    
    order = CrossChainOrder(
        swapper="0x123",
        nonce=1,
        originChainId=1,
        expiry=1700000000,
        staticOutput="0x456",
        fillDeadline=1700000100,
        orderData="0x"
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"intentId": "0xabc", "status": "submitted"}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await tool.run(order, CancellationToken())
        
        assert result.intent_id == "0xabc"
        assert result.status == "submitted"
        mock_post.assert_called_once()

def test_tool_schema():
    tool = CrossChainIntentTool(solver_url="http://localhost")
    schema = tool.schema
    assert schema["name"] == "cross_chain_intent"
    assert "swapper" in schema["parameters"]["properties"]
