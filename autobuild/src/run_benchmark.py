import autogen
import textwrap
from autobuild.src.utils import get_dataset_from_task
from autobuild.src.specific_proxy import MathUserProxyAgent
from autogen.agentchat.contrib.agent_builder import AgentBuilder



MATH_PROMPT = textwrap.dedent("""We need a group of math experts to solve some math problems. 
Those problems are in the fields of algebra, counting and probability, geometry, intermediate algebra, number theory, pre-algebra, and pre-calculus.
They need to write python code themselves if needed.
""")

ML_BENCH_PROMPT = textwrap.dedent("""We need a group of machine learning experts to solve some machine learning problems.
Agents need to solve the problems by leveraging different machine learning frameworks or models like DGL, BERT, PyTorch-GAN, etc.
Their final goal is to write a python command to run the training task with those machine learning frameworks or models.
""")

SCI_BENCH_PROMPT = textwrap.dedent("""We need a group of science experts to solve some scientific problems.
Those problems are in the "Fundamentals of Physics", "Statistical Thermodynamics", "Classical Dynamics of Particles and Systems", "Quantum Chemistry", "Physical Chemistry", and "Physical Chemistry, Quanta, Matter, and Change".
They can use tools or write python code themselves if needed.
""")

max_agents = 3

config = 'OAI_CONFIG_LIST'

default_llm_config = {
    'temperature': 0.3,
    'cache_seed': None,
}

task_prompt_map = {
    'math': MATH_PROMPT,
    'ml-bench': ML_BENCH_PROMPT,
    'sci-bench': SCI_BENCH_PROMPT,
}

task_proxy_map = {
    'math': MathUserProxyAgent,
    'ml-bench': 'TabMWPAgentProxy',
    'sci-bench': 'TabMWPAgentProxy',
}

def init_proxy_agent(task: str):
    if task == 'math':
        return MathUserProxyAgent(
            name="math_problem_solving_assistant",
            code_execution_config={
                "work_dir": "groupchat",
                "use_docker": False,
            },
            description="""A math problem solving helper with a code interpreter interface.
It can provide the code execution results. Select this player when other players provide some code that needs to be executed.
DO NOT SELECT THIS PLAYER WHEN NO CODE TO EXECUTE; IT WILL NOT ANSWER ANYTHING."""
        )

def start_task(execution_task: str, agent_list: list, llm_config: dict, config_list: list):
    group_chat = autogen.GroupChat(agents=agent_list, messages=[], max_round=12)
    manager = autogen.GroupChatManager(
        groupchat=group_chat, llm_config={"config_list": config_list, **llm_config}
    )
    agent_list[0].initiate_chat(manager, message=execution_task)


def build_agents(building_task, builder_model, agent_model, config_file_or_env, llm_config, user_proxy):
    builder = AgentBuilder(config_file_or_env=config_file_or_env,
                           builder_model=builder_model,
                           agent_model=agent_model,
                           max_agents=max_agents)
    return builder.build(building_task, llm_config, user_proxy=user_proxy, coding=True)



if __name__ == "__main__":
    task = 'math'
    dev = True

    config_list = autogen.config_list_from_json(config, filter_dict={"model": ["gpt-4-1106-preview"]})
    agent_list, agent_configs = build_agents(task_prompt_map[task],
                                             'gpt-4-1106-preview',
                                             'gpt-4-1106-preview',
                                             config,
                                             default_llm_config,
                                             user_proxy=init_proxy_agent(task))

    dataset = get_dataset_from_task(task, data_path="autobuild/datasets")["test"]
    if dev:
        dataset = dataset.select(range(1))

    for index, instance in enumerate(dataset):
        start_task(instance['question'], agent_list, default_llm_config, config_list)




