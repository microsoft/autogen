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

    llm_config = {"config_list": config_list}

    teacher_message = """
        You are roleplaying a math teacher, and your job is to help your students with linear algebra.
        Keep your explanations short.
    """

    student_message = """
        You are roleplaying a high school student strugling with linear algebra.
        Regardless how well the teacher explains things to you, you just don't quite get it.
        Keep your questions short.
    """

    log_completions_query = """SELECT id, invocation_id, client_id, wrapper_id, session_id,
        request, response, is_cached, cost, start_time, end_time FROM chat_completions;"""

    agents_query = """SELECT id, agent_id, wrapper_id, session_id, name, class, init_args, timestamp FROM agents"""

###############################################################

@pytest.fixture(scope="function")
def setup_test():
    autogen.telemetry.start_logging(dbpath=":memory:")
    con = autogen.telemetry.get_connection()
    con.row_factory = sqlite3.Row

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

    yield con, teacher, student

    autogen.telemetry.stop_logging()


def fetch_rows(cur, query):
    cur.execute(query)
    return cur.fetchall()


def verify_two_agents_log_completions(rows):
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


def verify_agents(rows):
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


def verify_oai_client_table(cur, num_of_clients):
    cur.execute("SELECT id, client_id, wrapper_id, session_id, class, init_args, timestamp FROM oai_clients")
    rows = cur.fetchall()

    assert len(rows) == num_of_clients
    session_id = rows[0]["session_id"]

    for row in rows:
        assert row["client_id"], "client id is empty"
        assert row["wrapper_id"], "wrapper id is empty"
        assert row["session_id"] and row["session_id"] == session_id
        assert row["class"] in ["AzureOpenAI", "OpenAI"]
        init_args = json.loads(row["init_args"])
        assert "api_version" in init_args
        assert row["timestamp"], "timestamp is empty"


def verify_oai_wrapper_table(cur, num_of_wrappers):
    cur.execute("SELECT id, wrapper_id, session_id, init_args, timestamp FROM oai_wrappers")
    rows = cur.fetchall()

    assert len(rows) == num_of_wrappers
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
def test_two_agents_logging(setup_test):
    con, teacher, student = setup_test
    cur = con.cursor()

    student.initiate_chat(
        teacher,
        message="Can you explain the difference between eigenvalues and singular values again?",
    )

    log_completions_rows = fetch_rows(cur, log_completions_query)
    verify_two_agents_log_completions(log_completions_rows)

    agents_rows = fetch_rows(cur, agents_query)
    verify_agents(agents_rows)

    verify_oai_client_table(cur, num_of_clients=2)
    verify_oai_wrapper_table(cur, num_of_wrappers=2)
    verify_keys_are_matching(cur)


def test_group_chat_logging(setup_test):
    con, teacher, student = setup_test
    cur = con.cursor()

    groupchat = autogen.GroupChat(agents=[teacher, student], messages=[], max_round=3, speaker_selection_method="round_robin")
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    student.initiate_chat(
        group_chat_manager,
        message="Can you explain the difference between eigenvalues and singular values again?",
    )

    agents_rows = fetch_rows(cur, agents_query)
    verify_agents(agents_rows[:2])
    assert agents_rows[2]["name"] == "chat_manager"
    init_args = json.loads(agents_rows[2]["init_args"])
    assert len(init_args["groupchat"]["agents"]) == 2
    verify_oai_client_table(cur, num_of_clients=3)
    verify_oai_wrapper_table(cur, num_of_wrappers=3)
