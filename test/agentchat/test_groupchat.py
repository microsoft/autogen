import pytest
import autogen
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST
import random

def test_func_call_groupchat():
    agent1 = autogen.ConversableAgent(
        "alice",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is alice sepaking.",
    )
    agent2 = autogen.ConversableAgent(
        "bob",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is bob speaking.",
        function_map={"test_func": lambda x: x},
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2], messages=[], max_round=3)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "test_func", "arguments": '{"x": 1}'}})

    assert len(groupchat.messages) == 3
    assert (
        groupchat.messages[-2]["role"] == "function"
        and groupchat.messages[-2]["name"] == "test_func"
        and groupchat.messages[-2]["content"] == "1"
    )
    assert groupchat.messages[-1]["name"] == "alice"

    agent3 = autogen.ConversableAgent(
        "carol",
        human_input_mode="NEVER",
        llm_config=False,
        default_auto_reply="This is carol speaking.",
        function_map={"test_func": lambda x: x + 1},
    )
    groupchat = autogen.GroupChat(agents=[agent1, agent2, agent3], messages=[], max_round=3)
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent3.initiate_chat(group_chat_manager, message={"function_call": {"name": "test_func", "arguments": '{"x": 1}'}})

    assert (
        groupchat.messages[-2]["role"] == "function"
        and groupchat.messages[-2]["name"] == "test_func"
        and groupchat.messages[-2]["content"] == "1"
    )
    assert groupchat.messages[-1]["name"] == "carol"

    agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "func", "arguments": '{"x": 1}'}})

def test_group_chat_math_class():
    """
    This test case is to simulate a math class.
    where teacher creates math questions and student resolves the questions.
    teacher will create a question, student will resolve the question and tell teacher the answer.
    If the answer is correct, teacher will create another question, otherwise, teacher will ask student to resolve the question again.
    The class will end when teacher has created 3 questions.

    This test case is created to test the following features:
    - speaker selection should work under a continuous q&a scenario among two agents and GPT 3.5 model.
    - admin should end the class when teacher has created 3 questions.
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

    llm_config_for_user_proxy = {
        **gpt3_5_config,
        "functions":[
            {
                "name": "terminate_group_chat",
                "description": "terminate group chat",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "terminate group chat message",
                        },
                    },
                    "required": ["message"],
                },
            }
        ],
    }

    def terminate_group_chat(message):
        return f'[GROUPCHAT_TERMINATE] {message}'

    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="You terminate group chat when teacher says [COMPLETE].",
        code_execution_config=False,
        llm_config=llm_config_for_user_proxy,
        human_input_mode="NEVER",
        function_map={'terminate_group_chat': terminate_group_chat}
    )

    llm_config_for_teacher = {
        **gpt3_5_config,
        "functions":[
            {
                "name": "create_math_question",
                "description": "create pre-school math question for student to resolve",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "pre-school math question",
                        },
                        "i":{
                            "type": "integer",
                            "description": "question index",
                        },
                    },
                    "required": ["question", "i"],
                },
            }
        ],
    }

    def create_math_question(question, i):
        return f'[QUESTION] this is question #{i}: {question}'

    teacher = autogen.AssistantAgent(
        "teacher",
        system_message="""You are a pre-school math teacher, you create 3 math questions for student to resolve.
        Here's your workflow:
        -workflow-
        if question count > 3 say [COMPLETE].
        else create_math_question
        if answer is correct:
            create_math_question
        else:
            ask student to resolve the question again
        """,
        llm_config=llm_config_for_teacher,
        function_map={'create_math_question': create_math_question}
    )

    llm_config_for_student = {
        **gpt3_5_config,
        "functions":[
            {
                "name": "answer_math_question",
                "description": "answer math question from teacher",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                            "type": "string",
                            "description": "answer",
                        },
                    },
                    "required": ["answer"],
                },
            }
        ],
    }

    def answer_math_question(answer):
        return f'[ANSWER] {answer}'
    student = autogen.AssistantAgent(
        "student",
        system_message="""You are a pre-school student, you resolve the math questions from teacher.
        Here's your workflow:
        -workflow-
        if question is received:
            call answer_math_question
        else:
            ask teacher to create a question
        """,
        llm_config=llm_config_for_student,
        function_map={'answer_math_question': answer_math_question}
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, student, teacher], messages=[], max_round=25)
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=gpt3_5_config,
        is_termination_msg=lambda message: message.startswith('[GROUPCHAT_TERMINATE]'),
        )
    user_proxy.send(
        "welcome to the class. I'm admin here. Teacher, you create 3 math questions for student to answer. Let me know when student resolve all questions.",
        manager,
    )

    teacher.send("I'm teacher, I will create 3 math questions for student to answer.", manager)
    student.send("I'm student, I will answer teacher's questions.", manager)

    user_proxy.initiate_chat(
        manager,
        message="""teacher, please start""",
    )

    assert len(groupchat.messages) < 25
    
    # verify if admin says [GROUPCHAT_TERMINATE]
    terminate_message = filter(lambda message: message["content"].startswith("[GROUPCHAT_TERMINATE]"), groupchat.messages)
    assert len(list(terminate_message)) == 1

    # verify if teacher gives 5 questions
    question_message = filter(lambda message: message["content"].startswith("[QUESTION]"), groupchat.messages)
    assert len(list(question_message)) == 3

    # verify if student gives more than 5 answers (student might give more than 5 answers if student's answer is not correct)
    answer_message = filter(lambda message: message["content"].startswith("[ANSWER]"), groupchat.messages)
    assert len(list(answer_message)) >= 3

def test_chat_manager():
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
    group_chat_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=False)
    agent1.initiate_chat(group_chat_manager, message="hello")

    assert len(agent1.chat_messages[group_chat_manager]) == 2
    assert len(groupchat.messages) == 2

    group_chat_manager.reset()
    assert len(groupchat.messages) == 0
    agent1.reset()
    agent2.reset()
    agent2.initiate_chat(group_chat_manager, message="hello")
    assert len(groupchat.messages) == 2

    with pytest.raises(ValueError):
        agent2.initiate_chat(group_chat_manager, message={"function_call": {"name": "func", "arguments": '{"x": 1}'}})


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

def skip_if_openai_not_available():
    try:
        import openai
    except ImportError:
        pytest.skip("OpenAI package not found.")

if __name__ == "__main__":
    test_group_chat_math_class()
    # test_func_call_groupchat()
    # test_broadcast()
    # test_chat_manager()
    # test_plugin()
