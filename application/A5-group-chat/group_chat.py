import os
import shutil
import logging
import autogen
from autogen import AssistantAgent, UserProxyAgent

def test_group_chat(model, mode, llm_config, work_dir, tasks):
    work_dir = os.path.join(work_dir, f"groupchat-{model}-{mode}")

    # clear work_dir
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.mkdir(work_dir)

    # run the experiment
    for i, task in enumerate(tasks):
        # split index from task
        i = task.split(":", 1)[0]
        task = task.split(":", 1)[1]
        logging.info(f"Task: {task}")
        print(f"Task {i}: {task}")
        group_chat(model, mode, i, task, llm_config, work_dir)

def group_chat(model, mode, problem_id, problem, llm_config, work_dir):
    user_proxy = autogen.UserProxyAgent(
       name="Admin",
       system_message="you are Admin, a human user. You will reply [TERMINATE] if task get resolved.",
        max_consecutive_auto_reply=10,
       human_input_mode="ALWAYS",
    )
    engineer = autogen.AssistantAgent(
        name="Engineer",
        llm_config=llm_config,
        system_message='''Engineer, You write code to resolve given task. If code running fail, you rewrite code.
        Your reply should be in the form of:
        Part 1:
        ```sh 
        // shell script to install python package if needed
        ```
        Part 2:
        ```python
        // python code to resolve task
        ```''',
    )
    critic = autogen.AssistantAgent(
        name="Critic",
        system_message=f'''Critic, find the bug and ask engineer to fix it, you don't write code.''',
        llm_config=llm_config,
    )

    executor = autogen.AssistantAgent(
        name="Executor",
        system_message="Executor, you are python code executor, you run python code automatically. If no code is provided in previous message, you ask engineer to write code.",
        llm_config=False,
        default_auto_reply="no code provided, @engineer, please write code to resolve task.",
        code_execution_config={"last_n_messages": 3, "work_dir": work_dir },
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, engineer, critic, executor], messages=[], max_round=50)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config, mode=mode)

    def init_groupchat():
        groupchat.reset()
        manager.reset()
        for agent in groupchat.agents:
            agent.reset()

        # set inital message to groupchat
        groupchat.messages.append(
            {
                "name": user_proxy.name,
                "content": "Welcome to the group chat! Work together to resolve my task. I'll reply [TERMINATE] when converstion ended.",
                "role": "user",
            }
        )
        groupchat.messages.append(
            {
                "name": user_proxy.name,
                "content": f"critic, if code running fail, you ask engineer to rewrite code.",
                "role": "user",
            }
        )
        
        groupchat.messages.append(
            {
                "name": user_proxy.name,
                "content": f"engineer, you write python code step by step to resolve my task.",
                "role": "user",
            }
        )
        
        groupchat.messages.append(
            {
                "name": user_proxy.name,
                "content": f"executor, you run python code from enginner and report bug",
                "role": "user",
            }
        )

    # run the experiment
    init_groupchat()
    # split index from task
    logging.info(f"Task: {problem}")
    print(f"Task {problem_id}: {problem}")
    prompt = f'''task: {problem}'''
    try:
        user_proxy.initiate_chat(manager, clear_history=False, message=prompt)
        # save chat messages to output/chat_history_{model}_{i}.txt using utf-8 encoding
        output_txt = os.path.join(work_dir, f"chat_history_{model}_{mode}_{problem_id}.txt")
        with open(output_txt, "w", encoding='utf-8') as f:
            for message in groupchat.messages:
                # write a seperator
                f.write("-" * 20 + "\n")
                f.write(f'''###
{message["name"]}
###''' + "\n")
                f.write(message["content"] + "\n")
                f.write("-" * 20 + "\n")
    except Exception as e:
        raise e