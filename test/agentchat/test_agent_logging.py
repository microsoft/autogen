import pytest
import autogen
import autogen.runtime_logging
import json
import sys
import uuid
import sqlite3

from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from conftest import skip_openai


teacher_message = """
    You are roleplaying a math teacher, and your job is to help your students with linear algebra.
    Keep your explanations short.
"""

student_message = """
    You are roleplaying a high school student strugling with linear algebra.
    Regardless how well the teacher explains things to you, you just don't quite get it.
    Keep your questions short.
"""

chat_completions_query = """SELECT id, invocation_id, client_id, wrapper_id, session_id,
    request, response, is_cached, cost, start_time, end_time FROM chat_completions;"""

agents_query = """SELECT id, agent_id, wrapper_id, session_id, name, class, init_args, timestamp FROM agents"""

if not skip_openai:
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )

    llm_config = {"config_list": config_list}

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
        system_message=teacher_message,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=2,
    )

    student = autogen.AssistantAgent(
        "student",
        system_message=student_message,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
    )

    student.initiate_chat(
        teacher,
        message="Can you explain the difference between eigenvalues and singular values again?",
    )

    # Verify log completions table
    cur.execute(chat_completions_query)
    rows = cur.fetchall()

    assert len(rows) == 3
    session_id = rows[0]["session_id"]

    print("***log completions table: ")
    for idx, row in enumerate(rows):
        print(
            idx,
            row["invocation_id"],
            row["client_id"],
            row["wrapper_id"],
            row["session_id"],
            row["request"],
            row["response"],
        )

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
            assert first_request_message == teacher_message
        elif idx == 1:
            assert first_request_message == student_message
        assert first_request_role == "system"

        response = json.loads(row["response"])
        assert "choices" in response and len(response["choices"]) > 0

        assert row["cost"] > 0
        assert row["start_time"], "start timestamp is empty"
        assert row["end_time"], "end timestamp is empty"

    # Verify agents table
    cur.execute(agents_query)
    rows = cur.fetchall()

    print("***Agents table: ")
    for idx, row in enumerate(rows):
        print(idx, row["agent_id"], row["wrapper_id"], row["session_id"], row["name"], row["class"], row["init_args"])

    assert len(rows) == 2

    session_id = rows[0]["session_id"]
    for idx, row in enumerate(rows):
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id

        agent = json.loads(row["init_args"])
        if idx == 0:
            assert row["name"] == "teacher"
            assert agent["name"] == "teacher"
            agent["system_message"] == teacher_message
        elif idx == 1:
            assert row["name"] == "student"
            assert agent["name"] == "student"
            agent["system_message"] = student_message

        assert "api_key" not in row["init_args"]
        assert row["timestamp"], "timestamp is empty"

    # Verify oai client table
    oai_clients_query = "SELECT id, client_id, wrapper_id, session_id, class, init_args, timestamp FROM oai_clients"
    cur.execute(oai_clients_query)
    rows = cur.fetchall()

    print("***oai client table: ", len(rows))
    for idx, row in enumerate(rows):
        print(idx, row["client_id"], row["wrapper_id"], row["session_id"], row["class"], row["init_args"])
