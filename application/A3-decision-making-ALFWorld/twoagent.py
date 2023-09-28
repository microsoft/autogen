import os
# os.environ["ALFWORLD_DATA"] = "/data/alfworld"

import autogen
# from flaml.autogen.agentchat import AssistantAgent
from autogen.agentchat import AssistantAgent
import json
from src.chat_utils import ALFAgent, get_all_game_files, set_context

config_list = [{'api_key': '', 'model': 'gpt-3.5-turbo'}]

game_files = get_all_game_files("src/tasks/base_config.yaml")
game_files.sort()
print(f"Loaded a total of {len(game_files)} game files.")
prefixs = ['pick_and_place', 'pick_clean_then_place', 'pick_heat_then_place', 'pick_cool_then_place', 'look_at_obj', 'pick_two_obj']
seed = [41, 42, 43]

for prefix in prefixs:
    if not os.path.exists(f"logs_twoagent/{prefix}/"):
        os.mkdir(f"logs_twoagent/{prefix}/")

for i, file in enumerate(game_files):
    
    for prefix in prefixs:
        if prefix in file:
            save_path = f"logs_twoagent/{prefix}/{i}.json"
            fail_path = f"logs_twoagent/{prefix}/{i}_failed.json"
    
    print(f"Evaluating file {i}...")
    
    for test_counter in range(3):
        try:
            user_proxy = ALFAgent(
                name="ALFWorld user proxy agent",
                task_path=file
            )
            assistant = AssistantAgent(
                name="assistant",
                system_message="You are a helpful assistant.",
                llm_config={
                    "config_list": config_list,
                    "temperature": 0,
                    "seed": seed[test_counter],
                    "top_p": 1
                }
            )
            # get in-context examples and inject them into conversation history
            context = user_proxy.get_examples()
            set_context(context, user_proxy, assistant)
            user_proxy.initiate_chat(assistant, clear_history=False)
            
            history = assistant.chat_messages[user_proxy]
            reply = history[-3]['content']
            if "Task success, now reply TERMINATE" in reply and history[-3]['role'] == 'user':
                with open(save_path, "w") as f:
                    json.dump(assistant.chat_messages[user_proxy], f, indent=4)
                break
            else:
                with open(fail_path, "w") as f:
                    json.dump(assistant.chat_messages[user_proxy], f, indent=4)
                    
        except Exception as e:
            print(e)
