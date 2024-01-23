import pytest
import autogen
import autogen.telemetry
import uuid
import sys
import os

from autogen.agentchat import ConversableAgent, UserProxyAgent
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
    autogen.AssistantAgent(
        "teacher",
        system_message="You are roleplaying a math teacher, and your job is to help your students with linear algebra. Keep your explanations short.",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=2,
    )

    autogen.AssistantAgent(
        "student",
        system_message="You are roleplaying a high school student strugling with linear algebra. Regardless how well the teacher explains things to you, you just don't quite get it. Keep your questions short.",
        is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
        llm_config=llm_config,
        max_consecutive_auto_reply=1,
    )

    # student.initiate_chat(
    #    teacher,
    #    message="Can you explain the difference between eigenvalues and singular values again?",
    # )

    # Check what's in the db
    con = autogen.telemetry.get_connection()
    cur = con.cursor()
    for row in cur.execute("SELECT * FROM chat_completions;"):
        print(row)

    autogen.telemetry.stop_logging()


if __name__ == "__main__":
    test_agent_telemetry()
