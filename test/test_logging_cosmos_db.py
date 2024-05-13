import json
import uuid
from unittest.mock import Mock, patch

import pytest
from openai import AzureOpenAI

from autogen.logger.logger_utils import get_current_ts, to_dict
from autogen.runtime_logging import log_chat_completion, start, stop

# Sample data for testing
SAMPLE_CHAT_REQUEST = json.loads(
    """
{
    "messages": [
        {
            "content": "Can you explain the difference between eigenvalues and singular values again?",
            "role": "assistant"
        }
    ],
    "model": "gpt-4"
}
"""
)

SAMPLE_CHAT_RESPONSE = json.loads(
    """
{
    "id": "chatcmpl-8k57oSg1fz2JwpMcEOWMqUvwjf0cb",
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {
                "content": "Eigenvalues are...",
                "role": "assistant"
            }
        }
    ],
    "model": "gpt-4"
}
"""
)

@pytest.fixture(scope="function")
def cosmos_db_setup():
    with patch('autogen.runtime_logging.LoggerFactory.get_logger') as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_logger.log_queue.put = Mock()

        config = {
            "connection_string": "AccountEndpoint=https://example.documents.azure.com:443/;AccountKey=dGVzdA==",
            "database_id": "TestDatabase",
            "container_id": "TestContainer",
        }

        start(logger_type="cosmos", config=config)
        yield mock_logger  # This correctly passes mock_logger to your test
        stop()

class TestCosmosDBLogging:
    def get_sample_chat_completion(self, response):
        return {
            "invocation_id": str(uuid.uuid4()),
            "client_id": 140609438577184,
            "wrapper_id": 140610167717744,
            "request": SAMPLE_CHAT_REQUEST,
            "response": response,
            "is_cached": 0,
            "cost": 0.347,
            "start_time": get_current_ts(),
        }

    @pytest.mark.usefixtures("cosmos_db_setup")
    def test_log_completion_cosmos(self, cosmos_db_setup):  # Use cosmos_db_setup here
        sample_completion = self.get_sample_chat_completion(SAMPLE_CHAT_RESPONSE)
        log_chat_completion(**sample_completion)

        expected_document = {
            "type": "chat_completion",
            "invocation_id": sample_completion["invocation_id"],
            "client_id": sample_completion["client_id"],
            "wrapper_id": sample_completion["wrapper_id"],
            "session_id": cosmos_db_setup.session_id,  # Ensure session_id is handled correctly
            "request": sample_completion["request"],
            "response": SAMPLE_CHAT_RESPONSE,
            "is_cached": sample_completion["is_cached"],
            "cost": sample_completion["cost"],
            "start_time": sample_completion["start_time"],
            "end_time": get_current_ts(),
        }

        cosmos_db_setup.log_queue.put.assert_called_once_with(expected_document)
