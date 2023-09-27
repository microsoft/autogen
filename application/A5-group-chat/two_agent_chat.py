import autogen
import json
import os
import shutil
import logging
from autogen import AssistantAgent, UserProxyAgent

def test_two_agent_chat(model, llm_config, work_dir, tasks):
    work_dir = os.path.join(work_dir, f"twoagent-{model}")

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
        twoagent_chat(model, i, task,llm_config, work_dir)

def twoagent_chat(model, problem_id, problem, config_list, work_dir):    
    autogen.ChatCompletion.start_logging()
    # config_list = autogen.config_list_from_models(key_file_path=KEY_LOC, model_list=["gpt-4"], exclude="aoai")
    # create an AssistantAgent instance named "assistant"
    assistant = AssistantAgent(
        name="assistant",
        llm_config=config_list,
    )
    # create a UserProxyAgent instance named "user"
    user = UserProxyAgent(
        name="user",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config={"last_n_messages": 3, "work_dir": work_dir},
    )

    user.initiate_chat(
    assistant,
    message=problem,
    )
    log = autogen.ChatCompletion.logged_history
    file_path = os.path.join(work_dir, f"twoagent-{model}-" +str(problem_id) +".txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        for message in log:
            messages = json.loads(message)
            for msg in messages:
                # write a seperator
                f.write("-" * 20 + "\n")
                f.write(f'''###
{msg["role"]}
###''' + "\n")
                f.write(msg["content"] + "\n")
                f.write("-" * 20 + "\n")