#!/usr/bin/env python3 -m pytest

import os
import sys
import uuid
from unittest.mock import MagicMock

import openai
import pytest

import autogen
from autogen import OpenAIWrapper, UserProxyAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from autogen.oai.openai_utils import detect_gpt_assistant_api_version, retrieve_assistants_by_name

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import reason, skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

if not skip_openai:
    openai_config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        # The Retrieval tool requires at least gpt-3.5-turbo-1106 (newer versions are supported) or gpt-4-turbo-preview models.
        # https://platform.openai.com/docs/models/overview
        filter_dict={
            "api_type": ["openai"],
            "model": [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4-turbo",
                "gpt-4-turbo-preview",
                "gpt-4-0125-preview",
                "gpt-4-1106-preview",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-0125",
                "gpt-3.5-turbo-1106",
            ],
        },
    )
    aoai_config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={"api_type": ["azure"], "tags": ["assistant"]},
    )


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_config_list() -> None:
    assert len(openai_config_list) > 0
    assert len(aoai_config_list) > 0


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_gpt_assistant_chat() -> None:
    for gpt_config in [openai_config_list, aoai_config_list]:
        _test_gpt_assistant_chat({"config_list": gpt_config})
        _test_gpt_assistant_chat(gpt_config[0])


def _test_gpt_assistant_chat(gpt_config) -> None:
    ossinsight_api_schema = {
        "name": "ossinsight_data_api",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Enter your GitHub data question in the form of a clear and specific question to ensure the returned data is accurate and valuable. For optimal results, specify the desired format for the data table in your request.",
                }
            },
            "required": ["question"],
        },
        "description": "This is an API endpoint allowing users (analysts) to input question about GitHub in text format to retrieve the related and structured data.",
    }
    ask_ossinsight_mock = MagicMock()

    def ask_ossinsight(question: str) -> str:
        ask_ossinsight_mock(question)
        return "The repository microsoft/autogen has 123,456 stars on GitHub."

    name = f"For test_gpt_assistant_chat {uuid.uuid4()}"
    analyst = GPTAssistantAgent(
        name=name,
        llm_config=gpt_config,
        assistant_config={"tools": [{"type": "function", "function": ossinsight_api_schema}]},
        instructions="Hello, Open Source Project Analyst. You'll conduct comprehensive evaluations of open source projects or organizations on the GitHub platform",
    )
    try:
        analyst.register_function(
            function_map={
                "ossinsight_data_api": ask_ossinsight,
            }
        )

        ok, response = analyst._invoke_assistant(
            [{"role": "user", "content": "How many stars microsoft/autogen has on GitHub?"}]
        )
        executable = analyst.can_execute_function("ossinsight_data_api")
        analyst.reset()
        threads_count = len(analyst._openai_threads)
    finally:
        analyst.delete_assistant()

    # check response
    assert ok is True
    assert response.get("role", "") == "assistant"

    # check the question asked
    ask_ossinsight_mock.assert_called_once()
    question_asked = ask_ossinsight_mock.call_args[0][0].lower()
    for word in "microsoft autogen star".split(" "):
        assert word in question_asked

    # check the answer
    response_content = response.get("content", "").lower()
    assert len(response_content) > 0
    for word in "microsoft autogen 123 456".split(" "):
        assert word in response_content

    assert executable is False
    assert threads_count == 0


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_get_assistant_instructions() -> None:
    for gpt_config in [openai_config_list, aoai_config_list]:
        _test_get_assistant_instructions(gpt_config)


def _test_get_assistant_instructions(gpt_config) -> None:
    """
    Test function to create a new GPTAssistantAgent, set its instructions, retrieve the instructions,
    and assert that the retrieved instructions match the set instructions.
    """
    name = f"For test_get_assistant_instructions {uuid.uuid4()}"
    assistant = GPTAssistantAgent(
        name,
        instructions="This is a test",
        llm_config={
            "config_list": gpt_config,
        },
    )

    instruction_match = assistant.get_assistant_instructions() == "This is a test"
    assistant.delete_assistant()

    assert instruction_match is True


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_gpt_assistant_instructions_overwrite() -> None:
    for gpt_config in [openai_config_list, aoai_config_list]:
        _test_gpt_assistant_instructions_overwrite(gpt_config)


def _test_gpt_assistant_instructions_overwrite(gpt_config) -> None:
    """
    Test that the instructions of a GPTAssistantAgent can be overwritten or not depending on the value of the
    `overwrite_instructions` parameter when creating a new assistant with the same ID.

    Steps:
    1. Create a new GPTAssistantAgent with some instructions.
    2. Get the ID of the assistant.
    3. Create a new GPTAssistantAgent with the same ID but different instructions and `overwrite_instructions=True`.
    4. Check that the instructions of the assistant have been overwritten with the new ones.
    """

    name = f"For test_gpt_assistant_instructions_overwrite {uuid.uuid4()}"
    instructions1 = "This is a test #1"
    instructions2 = "This is a test #2"

    assistant = GPTAssistantAgent(
        name,
        instructions=instructions1,
        llm_config={
            "config_list": gpt_config,
        },
    )

    try:
        assistant_id = assistant.assistant_id
        assistant = GPTAssistantAgent(
            name,
            instructions=instructions2,
            llm_config={
                "config_list": gpt_config,
                # keep it to test older version of assistant config
                "assistant_id": assistant_id,
            },
            overwrite_instructions=True,
        )

        instruction_match = assistant.get_assistant_instructions() == instructions2

    finally:
        assistant.delete_assistant()

    assert instruction_match is True


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_gpt_assistant_existing_no_instructions() -> None:
    """
    Test function to check if the GPTAssistantAgent can retrieve instructions for an existing assistant
    even if the assistant was created with no instructions initially.
    """
    name = f"For test_gpt_assistant_existing_no_instructions {uuid.uuid4()}"
    instructions = "This is a test #1"

    assistant = GPTAssistantAgent(
        name,
        instructions=instructions,
        llm_config={
            "config_list": openai_config_list,
        },
    )

    try:
        assistant_id = assistant.assistant_id

        # create a new assistant with the same ID but no instructions
        assistant = GPTAssistantAgent(
            name,
            llm_config={
                "config_list": openai_config_list,
            },
            assistant_config={"assistant_id": assistant_id},
        )

        instruction_match = assistant.get_assistant_instructions() == instructions

    finally:
        assistant.delete_assistant()

    assert instruction_match is True


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_get_assistant_files() -> None:
    """
    Test function to create a new GPTAssistantAgent, set its instructions, retrieve the instructions,
    and assert that the retrieved instructions match the set instructions.
    """
    current_file_path = os.path.abspath(__file__)
    openai_client = OpenAIWrapper(config_list=openai_config_list)._clients[0]._oai_client
    file = openai_client.files.create(file=open(current_file_path, "rb"), purpose="assistants")
    name = f"For test_get_assistant_files {uuid.uuid4()}"
    gpt_assistant_api_version = detect_gpt_assistant_api_version()

    # keep it to test older version of assistant config
    assistant = GPTAssistantAgent(
        name,
        instructions="This is a test",
        llm_config={
            "config_list": openai_config_list,
            "tools": [{"type": "retrieval"}],
            "file_ids": [file.id],
        },
    )

    try:
        if gpt_assistant_api_version == "v1":
            files = assistant.openai_client.beta.assistants.files.list(assistant_id=assistant.assistant_id)
            retrieved_file_ids = [fild.id for fild in files]
        elif gpt_assistant_api_version == "v2":
            oas_assistant = assistant.openai_client.beta.assistants.retrieve(assistant_id=assistant.assistant_id)
            vectorstore_ids = oas_assistant.tool_resources.file_search.vector_store_ids
            retrieved_file_ids = []
            for vectorstore_id in vectorstore_ids:
                files = assistant.openai_client.beta.vector_stores.files.list(vector_store_id=vectorstore_id)
                retrieved_file_ids.extend([fild.id for fild in files])
        expected_file_id = file.id
    finally:
        assistant.delete_assistant()
        openai_client.files.delete(file.id)

    assert expected_file_id in retrieved_file_ids


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_assistant_retrieval() -> None:
    """
    Test function to check if the GPTAssistantAgent can retrieve the same assistant
    """

    name = f"For test_assistant_retrieval {uuid.uuid4()}"

    function_1_schema = {
        "name": "call_function_1",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "description": "This is a test function 1",
    }
    function_2_schema = {
        "name": "call_function_2",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "description": "This is a test function 2",
    }

    openai_client = OpenAIWrapper(config_list=openai_config_list)._clients[0]._oai_client
    current_file_path = os.path.abspath(__file__)

    file_1 = openai_client.files.create(file=open(current_file_path, "rb"), purpose="assistants")
    file_2 = openai_client.files.create(file=open(current_file_path, "rb"), purpose="assistants")

    try:
        all_llm_config = {
            "config_list": openai_config_list,
        }
        assistant_config = {
            "tools": [
                {"type": "function", "function": function_1_schema},
                {"type": "function", "function": function_2_schema},
                {"type": "retrieval"},
                {"type": "code_interpreter"},
            ],
            "file_ids": [file_1.id, file_2.id],
        }

        name = f"For test_assistant_retrieval {uuid.uuid4()}"

        assistant_first = GPTAssistantAgent(
            name,
            instructions="This is a test",
            llm_config=all_llm_config,
            assistant_config=assistant_config,
        )
        candidate_first = retrieve_assistants_by_name(assistant_first.openai_client, name)

        try:
            assistant_second = GPTAssistantAgent(
                name,
                instructions="This is a test",
                llm_config=all_llm_config,
                assistant_config=assistant_config,
            )
            candidate_second = retrieve_assistants_by_name(assistant_second.openai_client, name)

        finally:
            assistant_first.delete_assistant()
            with pytest.raises(openai.NotFoundError):
                assistant_second.delete_assistant()

    finally:
        openai_client.files.delete(file_1.id)
        openai_client.files.delete(file_2.id)

    assert candidate_first == candidate_second
    assert len(candidate_first) == 1

    candidates = retrieve_assistants_by_name(openai_client, name)
    assert len(candidates) == 0


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_assistant_mismatch_retrieval() -> None:
    """Test function to check if the GPTAssistantAgent can filter out the mismatch assistant"""

    name = f"For test_assistant_retrieval {uuid.uuid4()}"

    function_1_schema = {
        "name": "call_function_1",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "description": "This is a test function 1",
    }
    function_2_schema = {
        "name": "call_function_2",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "description": "This is a test function 2",
    }
    function_3_schema = {
        "name": "call_function_other",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "description": "This is a test function 3",
    }

    openai_client = OpenAIWrapper(config_list=openai_config_list)._clients[0]._oai_client
    current_file_path = os.path.abspath(__file__)
    file_1 = openai_client.files.create(file=open(current_file_path, "rb"), purpose="assistants")
    file_2 = openai_client.files.create(file=open(current_file_path, "rb"), purpose="assistants")

    try:
        # keep it to test older version of assistant config
        all_llm_config = {
            "tools": [
                {"type": "function", "function": function_1_schema},
                {"type": "function", "function": function_2_schema},
                {"type": "file_search"},
                {"type": "code_interpreter"},
            ],
            "file_ids": [file_1.id, file_2.id],
            "config_list": openai_config_list,
        }

        name = f"For test_assistant_retrieval {uuid.uuid4()}"

        assistant_first, assistant_instructions_mistaching = None, None
        try:
            assistant_first = GPTAssistantAgent(
                name,
                instructions="This is a test",
                llm_config=all_llm_config,
            )
            candidate_first = retrieve_assistants_by_name(assistant_first.openai_client, name)
            assert len(candidate_first) == 1

            # test instructions mismatch
            assistant_instructions_mistaching = GPTAssistantAgent(
                name,
                instructions="This is a test for mismatch instructions",
                llm_config=all_llm_config,
            )
            candidate_instructions_mistaching = retrieve_assistants_by_name(
                assistant_instructions_mistaching.openai_client, name
            )
            assert len(candidate_instructions_mistaching) == 2

            # test tools mismatch
            tools_mismatch_llm_config = {
                "tools": [
                    {"type": "code_interpreter"},
                    {"type": "file_search"},
                    {"type": "function", "function": function_3_schema},
                ],
                "file_ids": [file_2.id, file_1.id],
                "config_list": openai_config_list,
            }
            assistant_tools_mistaching = GPTAssistantAgent(
                name,
                instructions="This is a test",
                llm_config=tools_mismatch_llm_config,
            )
            candidate_tools_mismatch = retrieve_assistants_by_name(assistant_tools_mistaching.openai_client, name)
            assert len(candidate_tools_mismatch) == 3

        finally:
            if assistant_first:
                assistant_first.delete_assistant()
            if assistant_instructions_mistaching:
                assistant_instructions_mistaching.delete_assistant()
            if assistant_tools_mistaching:
                assistant_tools_mistaching.delete_assistant()

    finally:
        openai_client.files.delete(file_1.id)
        openai_client.files.delete(file_2.id)

    candidates = retrieve_assistants_by_name(openai_client, name)
    assert len(candidates) == 0


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_gpt_assistant_tools_overwrite() -> None:
    """
    Test that the tools of a GPTAssistantAgent can be overwritten or not depending on the value of the
    `overwrite_tools` parameter when creating a new assistant with the same ID.

    Steps:
    1. Create a new GPTAssistantAgent with a set of tools.
    2. Get the ID of the assistant.
    3. Create a new GPTAssistantAgent with the same ID but different tools and `overwrite_tools=True`.
    4. Check that the tools of the assistant have been overwritten with the new ones.
    """

    original_tools = [
        {
            "type": "function",
            "function": {
                "name": "calculateTax",
                "description": "Calculate tax for a given amount",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "The amount to calculate tax on"},
                        "tax_rate": {"type": "number", "description": "The tax rate to apply"},
                    },
                    "required": ["amount", "tax_rate"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "convertCurrency",
                "description": "Convert currency from one type to another",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "The amount to convert"},
                        "from_currency": {"type": "string", "description": "Currency type to convert from"},
                        "to_currency": {"type": "string", "description": "Currency type to convert to"},
                    },
                    "required": ["amount", "from_currency", "to_currency"],
                },
            },
        },
    ]

    new_tools = [
        {
            "type": "function",
            "function": {
                "name": "findRestaurant",
                "description": "Find a restaurant based on cuisine type and location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cuisine": {"type": "string", "description": "Type of cuisine"},
                        "location": {"type": "string", "description": "City or area for the restaurant search"},
                    },
                    "required": ["cuisine", "location"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculateMortgage",
                "description": "Calculate monthly mortgage payments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "principal": {"type": "number", "description": "The principal loan amount"},
                        "interest_rate": {"type": "number", "description": "Annual interest rate"},
                        "years": {"type": "integer", "description": "Number of years for the loan"},
                    },
                    "required": ["principal", "interest_rate", "years"],
                },
            },
        },
    ]

    name = f"For test_gpt_assistant_tools_overwrite {uuid.uuid4()}"

    # Create an assistant with original tools
    assistant_org = GPTAssistantAgent(
        name,
        llm_config={
            "config_list": openai_config_list,
        },
        assistant_config={
            "tools": original_tools,
        },
    )

    assistant_id = assistant_org.assistant_id

    try:
        # Create a new assistant with new tools and overwrite_tools set to True
        assistant = GPTAssistantAgent(
            name,
            llm_config={
                "config_list": openai_config_list,
            },
            assistant_config={
                "assistant_id": assistant_id,
                "tools": new_tools,
            },
            overwrite_tools=True,
        )

        # Add logic to retrieve the tools from the assistant and assert
        retrieved_tools = assistant.openai_assistant.tools
        retrieved_tools_name = [tool.function.name for tool in retrieved_tools]
    finally:
        assistant_org.delete_assistant()

    assert retrieved_tools_name == [tool["function"]["name"] for tool in new_tools]


@pytest.mark.skipif(
    skip_openai,
    reason=reason,
)
def test_gpt_reflection_with_llm() -> None:
    gpt_assistant = GPTAssistantAgent(
        name="assistant", llm_config={"config_list": openai_config_list, "assistant_id": None}
    )

    user_proxy = UserProxyAgent(
        name="user_proxy",
        code_execution_config=False,
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1,
    )
    result = user_proxy.initiate_chat(gpt_assistant, message="Write a Joke!", summary_method="reflection_with_llm")
    assert result is not None

    # use the assistant configuration
    agent_using_assistant_config = GPTAssistantAgent(
        name="assistant",
        llm_config={"config_list": openai_config_list},
        assistant_config={"assistant_id": gpt_assistant.assistant_id},
    )
    result = user_proxy.initiate_chat(
        agent_using_assistant_config, message="Write a Joke!", summary_method="reflection_with_llm"
    )
    assert result is not None


if __name__ == "__main__":
    # test_gpt_assistant_chat()
    # test_get_assistant_instructions()
    # test_gpt_assistant_instructions_overwrite()
    # test_gpt_assistant_existing_no_instructions()
    test_get_assistant_files()
    # test_assistant_mismatch_retrieval()
    # test_gpt_assistant_tools_overwrite()
