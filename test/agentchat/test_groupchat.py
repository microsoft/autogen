import pytest
import autogen
import random
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST


def skip_if_openai_not_available():
    try:
        import openai
    except ImportError:
        pytest.skip("OpenAI API key not found.")


def test_group_chat_when_group_chat_llm_config_is_none():
    """
    Test group chat when groupchat's llm config is None.
    In this case, the group chat manager will simply select the next agent.
    """
    alice = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    bob = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    groupchat = autogen.GroupChat(agents=[alice, bob], messages=[], max_round=2)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    alice.initiate_chat(group_chat_manager, message="hello")

    assert len(groupchat.messages) == 2
    assert len(alice.chat_messages[group_chat_manager]) == 2

    assert alice.chat_messages[group_chat_manager][0]["content"] == "hello"
    assert alice.chat_messages[group_chat_manager][0]["role"] == "assistant"
    assert alice.chat_messages[group_chat_manager][1]["content"] == "From bob<eof_name>:\nThis is bob speaking."
    assert alice.chat_messages[group_chat_manager][1]["role"] == "user"
    assert bob.chat_messages[group_chat_manager][0]["content"] == "From alice<eof_name>:\nhello"
    assert bob.chat_messages[group_chat_manager][0]["role"] == "user"
    assert bob.chat_messages[group_chat_manager][1]["content"] == "This is bob speaking."
    assert bob.chat_messages[group_chat_manager][1]["role"] == "assistant"

    group_chat_manager.reset()
    assert len(groupchat.messages) == 0
    alice.reset()
    bob.reset()
    bob.initiate_chat(group_chat_manager, message="hello")
    assert len(groupchat.messages) == 2


def test_group_chat_math_class():
    """
    This test case is to simulate a math class.
    where teacher creates math questions and student resolves the questions.
    teacher will create a question, student will resolve the question and tell teacher the answer.
    If the answer is correct, teacher will create another question, otherwise, teacher will ask student to resolve the question again.
    The class will end when teacher has created 10 questions.

    This test case is created to test the following features:
    - speaker selection should work under a continuous q&a scenario among two agents and GPT 3.5 model.
    - admin should end the class when teacher has created 10 questions.
    """
    skip_if_openai_not_available()
    config_list = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": ["gpt-3.5-turbo"],
        },
    )
    gpt3_5_config = {
        "model": "gpt-3.5-turbo",
        "seed": random.randint(0, 100),  # change the seed for different trials
        "temperature": 0,
        "config_list": config_list,
        "request_timeout": 120,
    }
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="You say TERMINATE when teacher says [COMPLETE].",
        code_execution_config=False,
        llm_config=gpt3_5_config,
        human_input_mode="NEVER",
    )
    teacher = autogen.AssistantAgent(
        "teacher",
        system_message="""You are a pre-school math teacher, you create 10 math questions for student to resolve.
        Create 1 question at a time, then ask student to resolve the question and check the answer.
        If the answer is correct, you create another question, otherwise, you ask student to resolve the question again.

        Here are a few examples of questions:
        ## question 1
        1 + 1 = ?
        student, please resolve the question and tell me the answer.

        ## question 2
        1 + 2 = ?
        student, please resolve the question and tell me the answer.

        Repeat the process until you have created 10 questions. Then say [COMPLETE] to let admin know the task is completed.
        """,
        llm_config=gpt3_5_config,
    )

    student = autogen.AssistantAgent(
        "student",
        system_message="""You are a pre-school student, you resolve the math questions from teacher.
        Teacher will create a question, you resolve the question and tell teacher the answer.
        If the answer is correct, teacher will create another question, otherwise, teacher will ask you to resolve the question again.

        Here are a few examples of answers:
        ## answer 1
        hello teacher, the answer is 2.

        ## answer 2
        hello teacher, the answer is 3.
        """,
        llm_config=gpt3_5_config,
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, student, teacher], messages=[], max_round=50)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt3_5_config)
    user_proxy.send(
        "welcome to the class. I'm admin here. Teacher, you create 10 math questions for student to answer. Let me know when student resolve all questions.",
        manager,
    )

    teacher.send("I'm teacher, I will create 10 math questions for student to answer.", manager)
    student.send("I'm student, I will answer teacher's questions.", manager)

    user_proxy.initiate_chat(
        manager,
        message="""teacher, please start""",
    )

    assert len(groupchat.messages) < 50
    # verify if teacher's last message is [COMPLETE]
    teacher.chat_messages[manager][-1]["content"] == "[COMPLETE]"

    # verify if admin's last message is TERMINATE
    user_proxy.chat_messages[manager][-1]["content"] == "TERMINATE"


def test_group_chat_coding_class():
    """
    This test case is to simulate a coding class.
    where teacher creates algorithm questions and student resolves the questions.
    teacher will create a question, student will resolve the question with python code and execute the code. Student will fix the code if there is any error.
    If the code is correct, teacher will create another question, otherwise, teacher will help student fix the code.
    The class will end when teacher has created 5 questions.

    This test case is created to test the following features:
    - speaker selection should work under a continuous q&a scenario among multiple agents with back and forth conversation using GPT 3.5 model.
    - admin should end the class when teacher has created 5 questions.
    """
    skip_if_openai_not_available()
    config_list_gpt_35 = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        file_location=KEY_LOC,
        filter_dict={
            "model": ["gpt-3.5-turbo"],
        },
    )
    gpt_3_5_config = {
        "model": "gpt-3.5-turbo",
        "seed": random.randint(0, 100),  # change the seed for different trials
        "temperature": 0,
        "config_list": config_list_gpt_35,
        "request_timeout": 120,
    }
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="You say TERMINATE when teacher says [COMPLETE].",
        code_execution_config=False,
        llm_config=gpt_3_5_config,
        human_input_mode="NEVER",
    )

    teacher = autogen.AssistantAgent(
        "teacher",
        system_message="""You are a python teacher, you create 5 mid-level leetcode algorithm questions for student to resolve.
        Create 1 question at a time, then ask student to resolve the question using python.
        If the answer is correct, you create another question, otherwise, you provide hint to help student fix the bug and ask student to resolve the question again.

        Here are a few examples of questions:
        ## question 1
        // a leetcode question
        student, please resolve the question and tell me the answer.

        ## question 2
        // a leetcode question
        student, please resolve the question and tell me the answer.

        Repeat the process until student successfully resolve 5 questions. Then say [COMPLETE] to let admin know the task is completed.
        """,
        llm_config=gpt_3_5_config,
    )

    student = autogen.AssistantAgent(
        "student",
        system_message="""You are a student who wants to learn python, you resolve the algorithm questions from teacher.
        Teacher will create a question, you resolve the question by providing python code. Teacher will help you fix the code if there is any error.
        If the code is bug-free and correct, teacher will create another question, otherwise, teacher will ask you to resolve the question again.

        Here are a few examples of answers:
        ## answer 1
        ```python
        #code
        ```

        executer, please run the code. teacher, please check the result and let me know if the code is correct.

        ## answer 2
        ```python
        #code
        ```
        executer, please run the code. teacher, please check the result and let me know if the code is correct.
        """,
        llm_config=gpt_3_5_config,
    )

    executor = autogen.UserProxyAgent(
        name="executor",
        system_message="You are the executor. You run student's code and report result.",
        code_execution_config={"last_n_messages": 3, "work_dir": "leetcode"},
        llm_config=gpt_3_5_config,
        human_input_mode="NEVER",
        default_auto_reply="no code received, student please send code.",
    )

    groupchat = autogen.GroupChat(agents=[user_proxy, student, teacher, executor], messages=[], max_round=50)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt_3_5_config)
    user_proxy.send(
        "welcome to the class. I'm admin here. Teacher, you create 5 easy-level leetcode questions for student to resolve . Let me know when student resolve all questions.",
        manager,
    )

    teacher.send("I'm teacher, I will create 5 easy-level leetcode question for student to answer.", manager)
    student.send(
        "I'm student, I will provide python code to resolve leetcode question. I'll try to fix the bug if there's any.",
        manager,
    )
    executor.send("I'm executor, I will run student's code and report result.", manager)

    user_proxy.initiate_chat(
        manager,
        message="""teacher, please start""",
    )

    assert len(groupchat.messages) < 50
    # verify if teacher's last message is [COMPLETE]
    teacher.chat_messages[manager][-1]["content"] == "[COMPLETE]"

    # verify if admin's last message is TERMINATE
    user_proxy.chat_messages[manager][-1]["content"] == "TERMINATE"


def test_plugin():
    # Give another Agent class ability to manage group chat
    agent1 = autogen.ConversableAgent(
        "alice",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        max_consecutive_auto_reply=2,
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2], messages=[], max_round=2)
    group_chat_manager = autogen.ConversableAgent(name="deputy_manager", llm_config=False)
    group_chat_manager.register_reply(
        autogen.Agent,
        reply_func=autogen.GroupChatManager.run_chat,
        config=groupchat,
        reset_config=autogen.GroupChat.reset,
    )
    agent1.initiate_chat(group_chat_manager, message="hello")

    assert len(agent1.chat_messages[group_chat_manager]) == 2
    assert len(groupchat.messages) == 2


if __name__ == "__main__":
    # test_broadcast()
    # test_chat_manager()
    test_group_chat_math_class()
    # test_group_chat_coding_class()
    # test_plugin()
