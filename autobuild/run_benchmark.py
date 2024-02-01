import os
import json
import autogen
from autobuild.src.utils import get_dataset_from_scene
from autogen.agentchat.contrib.agent_builder import AgentBuilder
from autobuild.src.prompt import scene_prompt_map
from autobuild.src.specific_proxy import task_proxy_map


# Task parameters
max_agents = 10
config = 'OAI_CONFIG_LIST'
default_llm_config = {
    'temperature': 0.3,
    # 'cache_seed': None,
}

def init_proxy_agent(task: str):
    if task == 'math':
        return task_proxy_map[task](
            name="math_problem_solving_assistant",
            code_execution_config={
                "work_dir": "groupchat",
                "use_docker": False,
            },
            description="""A math problem solving helper with a code interpreter interface. This helper can provide the code execution results and collect the final answer.
Call this helper when there is a code block in the message. The code block should be quoted in ```python ...```.
It should be called before the task ends.""")

def start_task(execution_task: str, agent_list: list, llm_config: dict, config_list: list):
    group_chat = autogen.GroupChat(agents=agent_list, messages=[], max_round=20)
    manager = autogen.GroupChatManager(
        groupchat=group_chat, llm_config={"config_list": config_list, **llm_config}
    )
    logs, chat_history = agent_list[0].initiate_chat(manager, message=execution_task)
    return logs, chat_history


def build_agents(building_task, builder_model, agent_model, config_file_or_env, llm_config, user_proxy):
    builder = AgentBuilder(config_file_or_env=config_file_or_env,
                           builder_model=builder_model,
                           agent_model=agent_model,
                           max_agents=max_agents)
    return builder.build(building_task, llm_config, user_proxy=user_proxy, coding=True)



if __name__ == "__main__":
    scene = 'math'
    dev = False

    config_list = autogen.config_list_from_json(config, filter_dict={"model": ["gpt-4-1106-preview"]})
    agent_list, agent_configs = build_agents(scene_prompt_map[scene],
                                             'gpt-4-1106-preview',
                                             'gpt-4-1106-preview',
                                             config,
                                             default_llm_config,
                                             user_proxy=init_proxy_agent(scene))

    dataset = get_dataset_from_scene(scene, data_path="autobuild/datasets")["test"]
    if dev:
        dataset = dataset.select(range(1))

    if not os.path.exists(f'autobuild/results/{scene}'):
        os.makedirs(f'autobuild/results/{scene}')

    with open(f'autobuild/results/{scene}/conversation_history.json', 'w') as f:
        history_list = {}
        for index, instance in enumerate(dataset):
            history = start_task(instance, agent_list, default_llm_config, config_list)
            history_list[f'conversation: {index}'] = history

        json.dump(history_list, f, indent=4)




