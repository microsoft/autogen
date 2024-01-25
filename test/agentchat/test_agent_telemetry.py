import pytest
import autogen
import autogen.telemetry
import json
import sys
import uuid

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
            "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )

###############################################################


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
    cur = con.cursor()

    # Test completions table
    cur.execute(
        "SELECT id, invocation_id, client_id, wrapper_id, session_id, request, response, is_cached, cost, start_time, end_time FROM chat_completions;"
    )
    rows = cur.fetchall()

    assert len(rows) == 3

    # verify session id
    session_id = rows[0][4]
    assert all(row[4] == session_id for row in rows)

    for idx, row in enumerate(rows):
        assert row[1] and str(uuid.UUID(row[1], version=4)) == row[1], "invocation id is not valid uuid"
        assert row[2], "client id is empty"
        assert row[3], "wrapper id is empty"
        assert row[4] and row[4] == session_id

        request = json.loads(row[5])
        first_request_message = request["messages"][0]["content"]
        first_request_role = request["messages"][0]["role"]

        if idx == 0 or idx == 2:
            assert first_request_message == teacher_message
        elif idx == 1:
            assert first_request_message == student_message
        assert first_request_role == "system"

        response = json.loads(row[6])
        assert "choices" in response and len(response["choices"]) > 0

        assert row[8] > 0  # cost
        assert row[9], "start timestamp is empty"
        assert row[10], "end timestamp is empty"

    # Test agents table
    cur.execute("SELECT id, agent_id, wrapper_id, session_id, name, class, init_args, timestamp FROM agents")
    rows = cur.fetchall()

    assert len(rows) == 2

    session_id = rows[0][3]

    for idx, row in enumerate(rows):
        assert row[2], "wrapper id is empty"
        assert row[3] and row[3] == session_id

        agent = json.loads(row[6])
        if idx == 0:
            assert row[4] == "teacher"
            assert agent["name"] == "teacher"
            agent["system_message"] == teacher_message
        elif idx == 1:
            assert row[4] == "student"
            assert agent["name"] == "student"
            agent["system_message"] = student_message

        assert "api_key" not in row[6]
        assert "api-key" not in row[6]

        assert row[7], "timestamp is empty"
    autogen.telemetry.stop_logging()
