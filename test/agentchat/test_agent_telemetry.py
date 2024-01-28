import pytest
import autogen
import autogen.telemetry
import json
import sys
import uuid
import sqlite3

from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
from conftest import skip_openai

try:
    import openai
except ImportError:
    skip = True
else:
    skip = False or skip_openai

if not skip:
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )

###############################################################


def verify_log_completions_table(cur, teacher_message, student_message):
    cur.execute(
        """SELECT id, invocation_id, client_id, wrapper_id, session_id,
            request, response, is_cached, cost, start_time, end_time FROM chat_completions;"""
    )
    rows = cur.fetchall()

    assert len(rows) == 3

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
            assert first_request_message == teacher_message
        elif idx == 1:
            assert first_request_message == student_message
        assert first_request_role == "system"

        response = json.loads(row["response"])
        assert "choices" in response and len(response["choices"]) > 0

        assert row["cost"] > 0
        assert row["start_time"], "start timestamp is empty"
        assert row["end_time"], "end timestamp is empty"


def verify_agents_table(cur, teacher_message, student_message):
    cur.execute("SELECT id, agent_id, wrapper_id, session_id, name, class, init_args, timestamp FROM agents")
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
            agent["system_message"] == teacher_message
        elif idx == 1:
            assert row["name"] == "student"
            assert agent["name"] == "student"
            agent["system_message"] = student_message

        assert "api_key" not in row["init_args"]
        assert row["timestamp"], "timestamp is empty"


def verify_oai_client_table(cur):
    cur.execute("SELECT id, client_id, wrapper_id, session_id, class, init_args, timestamp FROM oai_clients")
    rows = cur.fetchall()

    assert len(rows) == 2
    session_id = rows[0]["session_id"]

    for row in rows:
        assert row["client_id"], "client id is empty"
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id
        assert row["class"] in ["AzureOpenAI", "OpenAI"]
        init_args = json.loads(row["init_args"])
        assert "api_version" in init_args
        assert row["timestamp"], "timestamp is empty"


def verify_oai_wrapper_table(cur):
    cur.execute("SELECT id, wrapper_id, session_id, init_args, timestamp FROM oai_wrappers")
    rows = cur.fetchall()

    assert len(rows) == 2
    session_id = rows[0]["session_id"]

    for row in rows:
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id
        init_args = json.loads(row["init_args"])
        assert "config_list" in init_args
        assert len(init_args["config_list"]) > 0
        assert row["timestamp"], "timestamp is empty"


def verify_keys_are_matching(cur):
    query = """
        SELECT * FROM chat_completions
        INNER JOIN agents
            ON chat_completions.wrapper_id = agents.wrapper_id
            AND chat_completions.session_id = agents.session_id
        INNER JOIN oai_clients
            ON chat_completions.wrapper_id = oai_clients.wrapper_id
            AND chat_completions.session_id = oai_clients.session_id
        INNER JOIN oai_wrappers
            ON chat_completions.wrapper_id = oai_wrappers.wrapper_id
            AND chat_completions.session_id = oai_wrappers.session_id
    """
    cur.execute(query)
    rows = cur.fetchall()
    assert len(rows) == 3


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip,
    reason="do not run on MacOS or windows OR dependency is not installed OR requested to skip",
)
def test_agent_telemetry():
    autogen.telemetry.start_logging(dbname=":memory:")
    llm_config = {"config_list": config_list}

    teacher_message = """
        You are roleplaying a math teacher, and your job is to help your students with linear algebra.
        Keep your explanations short.
    """
    teacher = autogen.AssistantAgent(
        "teacher",
        system_message=teacher_message,
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=2,
    )

    student_message = """
        You are roleplaying a high school student strugling with linear algebra.
        Regardless how well the teacher explains things to you, you just don't quite get it.
        Keep your questions short.
    """
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

    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row

    cur = con.cursor()

    verify_log_completions_table(cur, teacher_message, student_message)
    verify_agents_table(cur, teacher_message, student_message)
    verify_oai_client_table(cur)
    verify_oai_wrapper_table(cur)
    verify_keys_are_matching(cur)

    autogen.telemetry.stop_logging()
