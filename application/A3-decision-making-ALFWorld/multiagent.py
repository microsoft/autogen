import os
os.environ["ALFWORLD_DATA"] = "/data/alfworld"

import argparse
from autogen.agentchat import AssistantAgent
import json
from src.multichat_utils import ALFAgent, get_all_game_files, set_context, GroundingAgent, add_auto_reply, AssistantAgentAlf

config_list = [
    {
        'api_key': '',
        'model': "gpt-3.5-turbo"
    }
]
game_files = get_all_game_files("src/tasks/base_config.yaml")
game_files.sort()
print(f"Loaded a total of {len(game_files)} game files.")
prefixs = ['pick_and_place', 'pick_clean_then_place', 'pick_heat_then_place', 'pick_cool_then_place', 'look_at_obj', 'pick_two_obj']

seed = [12354, 4752, 12435, 21354, 31452, 31453]
base_dir = "logs_multiagent/"
success = 0

for prefix in prefixs:
    os.makedirs(base_dir + f"{prefix}/", exist_ok=True)

for i, file in enumerate(game_files):
    
    for prefix in prefixs:
        if prefix in file:
            path = base_dir + f"{prefix}/{i}.json"

    print(f"Evaluating file {i}...")
    
    grounding_agent = GroundingAgent(name="GroundingAgent")
    
    for cnt in range(3):
        try:
            user_proxy = ALFAgent(
                name="ALFWorld user proxy agent",
                task_path=file,
                grounding_agent=grounding_agent
            )
            assistant = AssistantAgentAlf(
                name="assistant",
                system_message="You are a helpful assistant",
                llm_config={
                    "config_list": config_list,
                    "temperature": 0,
                    # "seed": seed[cnt],
                }
            )
            add_auto_reply(grounding_agent, user_proxy)
            context = user_proxy.get_examples()
            set_context(context, user_proxy, assistant)
            user_proxy.initiate_chat(assistant, clear_history=False, agent=grounding_agent)
            
            history = assistant.chat_messages[user_proxy]
            reply = history[-3]['content']
            with open(path, "w") as f:
                json.dump(history, f, indent=4)

            if (
                "Task success, now reply TERMINATE" in reply 
                and history[-3]['role'] == 'user'
            ):
                success += 1
                break
    
        except Exception as e:
            # May encounter context overflow error, we should just skip it.
            print(e)

print("Success task number: ", success)
print("Success rate: ", success * 100 // 134)