import autogen
import random


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


def test_group_chat_research():
    config_list_gpt4 = autogen.config_list_from_json(
        "C:\\Users\\xiaoyuz\\source\\repos\\autogen\\notebook\\OAI_CONFIG_LIST.json",
        filter_dict={
            "model": ["JulyChat"],
        },
    )
    gpt4_config = {
        "model": "JulyChat",
        "seed": random.randint(0, 100),  # change the seed for different trials
        "temperature": 0,
        "config_list": config_list_gpt4,
        "request_timeout": 120,
    }
    user_proxy = autogen.UserProxyAgent(
        name="Admin",
        system_message="You Interact with the planner to discuss the plan and approve the plan from planner. You say TERMINATE to when task completed.",
        code_execution_config=False,
        llm_config=gpt4_config,
        human_input_mode="TERMINATE",
    )
    engineer = autogen.AssistantAgent(
        name="Engineer",
        llm_config=gpt4_config,
        system_message="""You are Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
    )
    scientist = autogen.AssistantAgent(
        name="Scientist",
        llm_config=gpt4_config,
        system_message="""You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code.""",
    )
    planner = autogen.AssistantAgent(
        name="Planner",
        system_message="""You suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval.
    The plan may involve an engineer who can write code and a scientist who doesn't write code.
    Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by a scientist.
    """,
        llm_config=gpt4_config,
    )
    executor = autogen.UserProxyAgent(
        name="Executor",
        system_message="You execute the code written by the engineer and report the result.",
        human_input_mode="NEVER",
        default_auto_reply="no code provided, please provide code to execute",
        code_execution_config={"last_n_messages": 3, "work_dir": "paper"},
    )
    critic = autogen.AssistantAgent(
        name="Critic",
        system_message="you double check plan, claims, code from other agents and provide feedback. Check whether the plan includes adding verifiable info such as source URL.",
        llm_config=gpt4_config,
    )
    groupchat = autogen.GroupChat(
        agents=[user_proxy, engineer, scientist, planner, executor, critic], messages=[], max_round=50
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
    user_proxy.send(
        "welcome to the group, work together to resolve my task, I'll say TERMINATE when task is completed", manager
    )
    engineer.send("I'll write code to solve the task", manager)
    planner.send("I'll suggest a plan for other agents to follow", manager)
    scientist.send("I'll categorize papers after engineer downloads paper.", manager)
    executor.send("I'll execute the code from engineer", manager)
    critic.send("I'll double check the plan, claims, code from other agents and provide feedback", manager)

    user_proxy.initiate_chat(
        manager,
        message="""
    find papers on LLM applications from arxiv in the last week, create a markdown table of different domains.
    planner, you suggest a plan first.
    Other agents, please follow the plan.
    """,
    )


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
    test_plugin()
