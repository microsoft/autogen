import pytest
import autogen
import autogen.runtime_logging
import json
import sys
import uuid
import sqlite3

from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from conftest import skip_openai


TEACHER_MESSAGE = """
    You are roleplaying a math teacher, and your job is to help your students with linear algebra.
    Keep your explanations short.
"""

STUDENT_MESSAGE = """
    You are roleplaying a high school student strugling with linear algebra.
    Regardless how well the teacher explains things to you, you just don't quite get it.
    Keep your questions short.
"""

CHAT_COMPLETIONS_QUERY = """SELECT id, invocation_id, client_id, wrapper_id, session_id,
    request, response, is_cached, cost, start_time, end_time FROM chat_completions;"""

AGENTS_QUERY = "SELECT id, agent_id, wrapper_id, session_id, name, class, init_args, timestamp FROM agents"

OAI_CLIENTS_QUERY = "SELECT id, client_id, wrapper_id, session_id, class, init_args, timestamp FROM oai_clients"

OAI_WRAPPERS_QUERY = "SELECT id, wrapper_id, session_id, init_args, timestamp FROM oai_wrappers"


if not skip_openai:
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )

    llm_config = {"config_list": config_list}

    num_of_configs = len(config_list)
###############################################################


@pytest.fixture(scope="function")
def db_connection():
    autogen.runtime_logging.start(config={"dbname": ":memory:"})
    con = autogen.runtime_logging.get_connection()
    con.row_factory = sqlite3.Row
    yield con

    autogen.runtime_logging.stop()


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_openai,
    reason="do not run on MacOS or windows OR dependency is not installed OR requested to skip",
)
def test_two_agents_logging(db_connection):
    cur = db_connection.cursor()

    teacher = autogen.AssistantAgent(
        "teacher",
        system_message=TEACHER_MESSAGE,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=2,
    )

    student = autogen.AssistantAgent(
        "student",
        system_message=STUDENT_MESSAGE,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
    )

    student.initiate_chat(
        teacher,
        message="Can you explain the difference between eigenvalues and singular values again?",
    )

    # Verify log completions table
    cur.execute(CHAT_COMPLETIONS_QUERY)
    rows = cur.fetchall()

    assert len(rows) >= 3  # some config may fail
    session_id = rows[0]["session_id"]

    for idx, row in enumerate(rows):
        assert (
            row["invocation_id"] and str(uuid.UUID(row["invocation_id"], version=4)) == row["invocation_id"]
        ), "invocation id is not valid uuid"
        assert row["client_id"], "client id is empty"
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id

        request = json.loads(row["request"])
        first_request_message = request["messages"][0]["content"]
        first_request_role = request["messages"][0]["role"]

        if idx == 0 or idx == 2:
            assert first_request_message == TEACHER_MESSAGE
        elif idx == 1:
            assert first_request_message == STUDENT_MESSAGE
        assert first_request_role == "system"

        response = json.loads(row["response"])

        if "response" in response:  # config failed or response was empty
            assert response["response"] is None or "error_code" in response["response"]
        else:
            assert "choices" in response and len(response["choices"]) > 0

        assert row["cost"] > 0
        assert row["start_time"], "start timestamp is empty"
        assert row["end_time"], "end timestamp is empty"

    # Verify agents table
    cur.execute(AGENTS_QUERY)
    rows = cur.fetchall()

    assert len(rows) == 2

    session_id = rows[0]["session_id"]
    for idx, row in enumerate(rows):
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id

        agent = json.loads(row["init_args"])
        if idx == 0:
            assert row["name"] == "teacher"
            assert agent["name"] == "teacher"
            agent["system_message"] == TEACHER_MESSAGE
        elif idx == 1:
            assert row["name"] == "student"
            assert agent["name"] == "student"
            agent["system_message"] = STUDENT_MESSAGE

        assert "api_key" not in row["init_args"]
        assert row["timestamp"], "timestamp is empty"

    # Verify oai client table
    cur.execute(OAI_CLIENTS_QUERY)
    rows = cur.fetchall()

    assert len(rows) == num_of_configs * 2  # two agents

    session_id = rows[0]["session_id"]
    for row in rows:
        assert row["client_id"], "client id is empty"
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id
        assert row["class"] in ["AzureOpenAI", "OpenAI"]
        init_args = json.loads(row["init_args"])
        if row["class"] == "AzureOpenAI":
            assert "api_version" in init_args
        assert row["timestamp"], "timestamp is empty"

    # Verify oai wrapper table
    cur.execute(OAI_WRAPPERS_QUERY)
    rows = cur.fetchall()

    session_id = rows[0]["session_id"]

    for row in rows:
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id
        init_args = json.loads(row["init_args"])
        assert "config_list" in init_args
        assert len(init_args["config_list"]) > 0
        assert row["timestamp"], "timestamp is empty"


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip_openai,
    reason="do not run on MacOS or windows OR dependency is not installed OR requested to skip",
)
def test_groupchat_logging(db_connection):
    cur = db_connection.cursor()

    teacher = autogen.AssistantAgent(
        "teacher",
        system_message=TEACHER_MESSAGE,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=2,
    )

    student = autogen.AssistantAgent(
        "student",
        system_message=STUDENT_MESSAGE,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
    )

    groupchat = autogen.GroupChat(
        agents=[teacher, student], messages=[], max_round=3, speaker_selection_method="round_robin"
    )

    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    student.initiate_chat(
        group_chat_manager,
        message="Can you explain the difference between eigenvalues and singular values again?",
    )

    # Verify chat_completions message
    cur.execute(CHAT_COMPLETIONS_QUERY)
    rows = cur.fetchall()
    assert len(rows) >= 2  # some config may fail

    # Verify group chat manager agent
    cur.execute(AGENTS_QUERY)
    rows = cur.fetchall()
    assert len(rows) == 3

    chat_manager_query = "SELECT agent_id, name, class, init_args FROM agents WHERE name = 'chat_manager'"
    cur.execute(chat_manager_query)
    rows = cur.fetchall()
    assert len(rows) == 1

    # Verify oai clients
    cur.execute(OAI_CLIENTS_QUERY)
    rows = cur.fetchall()
    assert len(rows) == num_of_configs * 3  # three agents

    # Verify oai wrappers
    cur.execute(OAI_WRAPPERS_QUERY)
    rows = cur.fetchall()
    assert len(rows) == 3

    # Verify schema version
    version_query = "SELECT id, version_number from version"
    cur.execute(version_query)
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == 1 and rows[0]["version_number"] == 1
