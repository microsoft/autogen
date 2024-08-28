import hashlib
import importlib
import json
import logging
import re
import socket
import subprocess as sp
import time
from typing import Dict, List, Optional, Tuple, Union

import requests
from termcolor import colored

import autogen

logger = logging.getLogger(__name__)


def _config_check(config: Dict):
    # check config loading
    assert config.get("coding", None) is not None, 'Missing "coding" in your config.'
    assert config.get("default_llm_config", None) is not None, 'Missing "default_llm_config" in your config.'
    assert config.get("code_execution_config", None) is not None, 'Missing "code_execution_config" in your config.'

    for agent_config in config["agent_configs"]:
        assert agent_config.get("name", None) is not None, 'Missing agent "name" in your agent_configs.'
        assert (
            agent_config.get("system_message", None) is not None
        ), 'Missing agent "system_message" in your agent_configs.'
        assert agent_config.get("description", None) is not None, 'Missing agent "description" in your agent_configs.'


def _retrieve_json(text):
    match = re.findall(autogen.code_utils.CODE_BLOCK_PATTERN, text, flags=re.DOTALL)
    if not match:
        return text
    code_blocks = []
    for _, code in match:
        code_blocks.append(code)
    return code_blocks[0]


class AgentBuilder:
    """
    AgentBuilder can help user build an automatic task solving process powered by multi-agent system.
    Specifically, our building pipeline includes initialize and build.
    """

    online_server_name = "online"

    DEFAULT_PROXY_AUTO_REPLY = 'There is no code from the last 1 message for me to execute. Group chat manager should let other participants to continue the conversation. If the group chat manager want to end the conversation, you should let other participant reply me only with "TERMINATE"'

    GROUP_CHAT_DESCRIPTION = """ # Group chat instruction
You are now working in a group chat with different expert and a group chat manager.
You should refer to the previous message from other participant members or yourself, follow their topic and reply to them.

**Your role is**: {name}
Group chat members: {members}{user_proxy_desc}

When the task is complete and the result has been carefully verified, after obtaining agreement from the other members, you can end the conversation by replying only with "TERMINATE".

# Your profile
{sys_msg}
"""

    DEFAULT_DESCRIPTION = """## Your role
[Complete this part with expert's name and skill description]

## Task and skill instructions
- [Complete this part with task description]
- [Complete this part with skill description]
- [(Optional) Complete this part with other information]
"""

    CODING_AND_TASK_SKILL_INSTRUCTION = """## Useful instructions for task-solving
- Solve the task step by step if you need to.
- When you find an answer, verify the answer carefully. Include verifiable evidence with possible test case in your response if possible.
- All your reply should be based on the provided facts.

## How to verify?
**You have to keep believing that everyone else's answers are wrong until they provide clear enough evidence.**
- Verifying with step-by-step backward reasoning.
- Write test cases according to the general task.

## How to use code?
- Suggest python code (in a python coding block) or shell script (in a sh coding block) for the Computer_terminal to execute.
- If missing python packages, you can install the package by suggesting a `pip install` code in the ```sh ... ``` block.
- When using code, you must indicate the script type in the coding block.
- Do not the coding block which requires users to modify.
- Do not suggest a coding block if it's not intended to be executed by the Computer_terminal.
- The Computer_terminal cannot modify your code.
- **Use 'print' function for the output when relevant**.
- Check the execution result returned by the Computer_terminal.
- Do not ask Computer_terminal to copy and paste the result.
- If the result indicates there is an error, fix the error and output the code again. """

    CODING_PROMPT = """Does the following task need programming (i.e., access external API or tool by coding) to solve,
or coding may help the following task become easier?

TASK: {task}

Answer only YES or NO.
"""

    AGENT_NAME_PROMPT = """# Your task
Suggest no more then {max_agents} experts with their name according to the following user requirement.

## User requirement
{task}

# Task requirement
- Expert's name should follow the format: [skill]_Expert.
- Only reply the names of the experts, separated by ",".
For example: Python_Expert, Math_Expert, ... """

    AGENT_SYS_MSG_PROMPT = """# Your goal
- According to the task and expert name, write a high-quality description for the expert by filling the given template.
- Ensure that your description are clear and unambiguous, and include all necessary information.

# Task
{task}

# Expert name
{position}

# Template
{default_sys_msg}
"""

    AGENT_DESCRIPTION_PROMPT = """# Your goal
Summarize the following expert's description in a sentence.

# Expert name
{position}

# Expert's description
{sys_msg}
"""

    AGENT_SEARCHING_PROMPT = """# Your goal
Considering the following task, what experts should be involved to the task?

# TASK
{task}

# EXPERT LIST
{agent_list}

# Requirement
- You should consider if the experts' name and profile match the task.
- Considering the effort, you should select less then {max_agents} experts; less is better.
- Separate expert names by commas and use "_" instead of space. For example, Product_manager,Programmer
- Only return the list of expert names.
"""

    AGENT_SELECTION_PROMPT = """# Your goal
Match roles in the role set to each expert in expert set.

# Skill set
{skills}

# Expert pool (formatting with name: description)
{expert_pool}

# Answer format
```json
{{
    "skill_1 description": "expert_name: expert_description", // if there exists an expert that suitable for skill_1
    "skill_2 description": "None", // if there is no experts that suitable for skill_2
    ...
}}
```
"""

    def __init__(
        self,
        config_file_or_env: Optional[str] = "OAI_CONFIG_LIST",
        config_file_location: Optional[str] = "",
        builder_model: Optional[Union[str, list]] = [],
        agent_model: Optional[Union[str, list]] = [],
        builder_model_tags: Optional[list] = [],
        agent_model_tags: Optional[list] = [],
        max_agents: Optional[int] = 5,
    ):
        """
        (These APIs are experimental and may change in the future.)
        Args:
            config_file_or_env: path or environment of the OpenAI api configs.
            builder_model: specify a model as the backbone of build manager.
            agent_model: specify a model as the backbone of participant agents.
            endpoint_building_timeout: timeout for building up an endpoint server.
            max_agents: max agents for each task.
        """
        builder_model = builder_model if isinstance(builder_model, list) else [builder_model]
        builder_filter_dict = {}
        if len(builder_model) != 0:
            builder_filter_dict.update({"model": builder_model})
        if len(builder_model_tags) != 0:
            builder_filter_dict.update({"tags": builder_model_tags})
        builder_config_list = autogen.config_list_from_json(config_file_or_env, filter_dict=builder_filter_dict)
        if len(builder_config_list) == 0:
            raise RuntimeError(
                f"Fail to initialize build manager: {builder_model}{builder_model_tags} does not exist in {config_file_or_env}. "
                f'If you want to change this model, please specify the "builder_model" in the constructor.'
            )
        self.builder_model = autogen.OpenAIWrapper(config_list=builder_config_list)

        self.agent_model = agent_model if isinstance(agent_model, list) else [agent_model]
        self.agent_model_tags = agent_model_tags
        self.config_file_or_env = config_file_or_env
        self.config_file_location = config_file_location

        self.building_task: str = None
        self.agent_configs: List[Dict] = []
        self.open_ports: List[str] = []
        self.agent_procs: Dict[str, Tuple[sp.Popen, str]] = {}
        self.agent_procs_assign: Dict[str, Tuple[autogen.ConversableAgent, str]] = {}
        self.cached_configs: Dict = {}

        self.max_agents = max_agents

    def set_builder_model(self, model: str):
        self.builder_model = model

    def set_agent_model(self, model: str):
        self.agent_model = model

    def _create_agent(
        self,
        agent_config: Dict,
        member_name: List[str],
        llm_config: dict,
        use_oai_assistant: Optional[bool] = False,
    ) -> autogen.AssistantAgent:
        """
        Create a group chat participant agent.

        If the agent rely on an open-source model, this function will automatically set up an endpoint for that agent.
        The API address of that endpoint will be "localhost:{free port}".

        Args:
            agent_config: agent's config. It should include the following information:
                1. model_name: backbone model of an agent, e.g., gpt-4-1106-preview, meta/Llama-2-70b-chat
                2. agent_name: use to identify an agent in the group chat.
                3. system_message: including persona, task solving instruction, etc.
                4. description: brief description of an agent that help group chat manager to pick the speaker.
            llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            world_size: the max size of parallel tensors (in most of the cases, this is identical to the amount of GPUs).

        Returns:
            agent: a set-up agent.
        """
        model_name_or_hf_repo = agent_config.get("model", [])
        model_name_or_hf_repo = (
            model_name_or_hf_repo if isinstance(model_name_or_hf_repo, list) else [model_name_or_hf_repo]
        )
        model_tags = agent_config.get("tags", [])
        agent_name = agent_config["name"]
        system_message = agent_config["system_message"]
        description = agent_config["description"]

        # Path to the customize **ConversableAgent** class.
        model_path = agent_config.get("model_path", None)
        filter_dict = {}
        if len(model_name_or_hf_repo) > 0:
            filter_dict.update({"model": model_name_or_hf_repo})
        if len(model_tags) > 0:
            filter_dict.update({"tags": model_tags})
        config_list = autogen.config_list_from_json(
            self.config_file_or_env, file_location=self.config_file_location, filter_dict=filter_dict
        )
        if len(config_list) == 0:
            raise RuntimeError(
                f"Fail to initialize agent {agent_name}: {model_name_or_hf_repo}{model_tags} does not exist in {self.config_file_or_env}.\n"
                f'If you would like to change this model, please specify the "agent_model" in the constructor.\n'
                f"If you load configs from json, make sure the model in agent_configs is in the {self.config_file_or_env}."
            )
        server_id = self.online_server_name
        current_config = llm_config.copy()
        current_config.update({"config_list": config_list})
        if use_oai_assistant:
            from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

            agent = GPTAssistantAgent(
                name=agent_name,
                llm_config={**current_config, "assistant_id": None},
                instructions=system_message,
                overwrite_instructions=False,
            )
        else:
            user_proxy_desc = ""
            if self.cached_configs["coding"] is True:
                user_proxy_desc = (
                    "\nThe group also include a Computer_terminal to help you run the python and shell code."
                )

            model_class = autogen.AssistantAgent
            if model_path:
                module_path, model_class_name = model_path.replace("/", ".").rsplit(".", 1)
                module = importlib.import_module(module_path)
                model_class = getattr(module, model_class_name)
                if not issubclass(model_class, autogen.ConversableAgent):
                    logger.error(f"{model_class} is not a ConversableAgent. Use AssistantAgent as default")
                    model_class = autogen.AssistantAgent

            additional_config = {
                k: v
                for k, v in agent_config.items()
                if k not in ["model", "name", "system_message", "description", "model_path", "tags"]
            }
            agent = model_class(
                name=agent_name, llm_config=current_config.copy(), description=description, **additional_config
            )
            if system_message == "":
                system_message = agent.system_message
            else:
                system_message = f"{system_message}\n\n{self.CODING_AND_TASK_SKILL_INSTRUCTION}"

            enhanced_sys_msg = self.GROUP_CHAT_DESCRIPTION.format(
                name=agent_name, members=member_name, user_proxy_desc=user_proxy_desc, sys_msg=system_message
            )
            agent.update_system_message(enhanced_sys_msg)
        self.agent_procs_assign[agent_name] = (agent, server_id)
        return agent

    def clear_agent(self, agent_name: str, recycle_endpoint: Optional[bool] = True):
        """
        Clear a specific agent by name.

        Args:
            agent_name: the name of agent.
            recycle_endpoint: trigger for recycle the endpoint server. If true, the endpoint will be recycled
                when there is no agent depending on.
        """
        _, server_id = self.agent_procs_assign[agent_name]
        del self.agent_procs_assign[agent_name]
        if recycle_endpoint:
            if server_id == self.online_server_name:
                return
            else:
                for _, iter_sid in self.agent_procs_assign.values():
                    if server_id == iter_sid:
                        return
                self.agent_procs[server_id][0].terminate()
                self.open_ports.append(server_id.split("_")[-1])
        print(colored(f"Agent {agent_name} has been cleared.", "yellow"), flush=True)

    def clear_all_agents(self, recycle_endpoint: Optional[bool] = True):
        """
        Clear all cached agents.
        """
        for agent_name in [agent_name for agent_name in self.agent_procs_assign.keys()]:
            self.clear_agent(agent_name, recycle_endpoint)
        print(colored("All agents have been cleared.", "yellow"), flush=True)

    def build(
        self,
        building_task: str,
        default_llm_config: Dict,
        coding: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
        user_proxy: Optional[autogen.ConversableAgent] = None,
        max_agents: Optional[int] = None,
        **kwargs,
    ) -> Tuple[List[autogen.ConversableAgent], Dict]:
        """
        Auto build agents based on the building task.

        Args:
            building_task: instruction that helps build manager (gpt-4) to decide what agent should be built.
            coding: use to identify if the user proxy (a code interpreter) should be added.
            code_execution_config: specific configs for user proxy (e.g., last_n_messages, work_dir, ...).
            default_llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            user_proxy: user proxy's class that can be used to replace the default user proxy.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        if code_execution_config is None:
            code_execution_config = {
                "last_n_messages": 1,
                "work_dir": "groupchat",
                "use_docker": False,
                "timeout": 10,
            }

        if max_agents is None:
            max_agents = self.max_agents

        agent_configs = []
        self.building_task = building_task

        print(colored("==> Generating agents...", "green"), flush=True)
        resp_agent_name = (
            self.builder_model.create(
                messages=[
                    {
                        "role": "user",
                        "content": self.AGENT_NAME_PROMPT.format(task=building_task, max_agents=max_agents),
                    }
                ]
            )
            .choices[0]
            .message.content
        )
        agent_name_list = [agent_name.strip().replace(" ", "_") for agent_name in resp_agent_name.split(",")]
        print(f"{agent_name_list} are generated.", flush=True)

        print(colored("==> Generating system message...", "green"), flush=True)
        agent_sys_msg_list = []
        for name in agent_name_list:
            print(f"Preparing system message for {name}", flush=True)
            resp_agent_sys_msg = (
                self.builder_model.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_SYS_MSG_PROMPT.format(
                                task=building_task,
                                position=name,
                                default_sys_msg=self.DEFAULT_DESCRIPTION,
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_sys_msg_list.append(resp_agent_sys_msg)

        print(colored("==> Generating description...", "green"), flush=True)
        agent_description_list = []
        for name, sys_msg in list(zip(agent_name_list, agent_sys_msg_list)):
            print(f"Preparing description for {name}", flush=True)
            resp_agent_description = (
                self.builder_model.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_DESCRIPTION_PROMPT.format(position=name, sys_msg=sys_msg),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_description_list.append(resp_agent_description)

        for name, sys_msg, description in list(zip(agent_name_list, agent_sys_msg_list, agent_description_list)):
            agent_configs.append(
                {
                    "name": name,
                    "model": self.agent_model,
                    "tags": self.agent_model_tags,
                    "system_message": sys_msg,
                    "description": description,
                }
            )

        if coding is None:
            resp = (
                self.builder_model.create(
                    messages=[{"role": "user", "content": self.CODING_PROMPT.format(task=building_task)}]
                )
                .choices[0]
                .message.content
            )
            coding = True if resp == "YES" else False

        self.cached_configs.update(
            {
                "building_task": building_task,
                "agent_configs": agent_configs,
                "coding": coding,
                "default_llm_config": default_llm_config,
                "code_execution_config": code_execution_config,
            }
        )
        _config_check(self.cached_configs)
        return self._build_agents(use_oai_assistant, user_proxy=user_proxy, **kwargs)

    def build_from_library(
        self,
        building_task: str,
        library_path_or_json: str,
        default_llm_config: Dict,
        top_k: int = 3,
        coding: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
        embedding_model: Optional[str] = "all-mpnet-base-v2",
        user_proxy: Optional[autogen.ConversableAgent] = None,
        **kwargs,
    ) -> Tuple[List[autogen.ConversableAgent], Dict]:
        """
        Build agents from a library.
        The library is a list of agent configs, which contains the name and system_message for each agent.
        We use a build manager to decide what agent in that library should be involved to the task.

        Args:
            building_task: instruction that helps build manager (gpt-4) to decide what agent should be built.
            library_path_or_json: path or JSON string config of agent library.
            default_llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            coding: use to identify if the user proxy (a code interpreter) should be added.
            code_execution_config: specific configs for user proxy (e.g., last_n_messages, work_dir, ...).
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            embedding_model: a Sentence-Transformers model use for embedding similarity to select agents from library.
                As reference, chromadb use "all-mpnet-base-v2" as default.
            user_proxy: user proxy's class that can be used to replace the default user proxy.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        import sqlite3

        # Some system will have an unexcepted sqlite3 version.
        # Check if the user has installed pysqlite3.
        if int(sqlite3.version.split(".")[0]) < 3:
            try:
                __import__("pysqlite3")
                import sys

                sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
            except Exception as e:
                raise e
        import chromadb
        from chromadb.utils import embedding_functions

        if code_execution_config is None:
            code_execution_config = {
                "last_n_messages": 1,
                "work_dir": "groupchat",
                "use_docker": False,
                "timeout": 120,
            }

        try:
            agent_library = json.loads(library_path_or_json)
        except json.decoder.JSONDecodeError:
            with open(library_path_or_json, "r") as f:
                agent_library = json.load(f)
        except Exception as e:
            raise e

        print(colored("==> Looking for suitable agents in the library...", "green"), flush=True)
        skills = building_task.replace(":", " ").split("\n")
        # skills = [line.split("-", 1)[1].strip() if line.startswith("-") else line for line in lines]
        if len(skills) == 0:
            skills = [building_task]

        chroma_client = chromadb.Client()
        collection = chroma_client.create_collection(
            name="agent_list",
            embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_model),
        )
        collection.add(
            documents=[agent["description"] for agent in agent_library],
            metadatas=[{"source": "agent_profile"} for _ in range(len(agent_library))],
            ids=[f"agent_{i}" for i in range(len(agent_library))],
        )
        agent_desc_list = set()
        for skill in skills:
            recall = set(collection.query(query_texts=[skill], n_results=top_k)["documents"][0])
            agent_desc_list = agent_desc_list.union(recall)

        agent_config_list = []
        for description in list(agent_desc_list):
            for agent in agent_library:
                if agent["description"] == description:
                    agent_config_list.append(agent.copy())
                    break
        chroma_client.delete_collection(collection.name)

        # double recall from the searching result
        expert_pool = [f"{agent['name']}: {agent['description']}" for agent in agent_config_list]
        while True:
            skill_agent_pair_json = (
                self.builder_model.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_SELECTION_PROMPT.format(
                                skills=building_task, expert_pool=expert_pool, max_agents=self.max_agents
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            try:
                skill_agent_pair_json = _retrieve_json(skill_agent_pair_json)
                skill_agent_pair = json.loads(skill_agent_pair_json)
                break
            except Exception as e:
                print(e, flush=True)
                time.sleep(5)
                continue

        recalled_agent_config_list = []
        recalled_name_desc = []
        for skill, agent_profile in skill_agent_pair.items():
            # If no suitable agent, generate an agent
            if agent_profile == "None":
                _, agent_config_temp = self.build(
                    building_task=skill,
                    default_llm_config=default_llm_config.copy(),
                    coding=False,
                    use_oai_assistant=use_oai_assistant,
                    max_agents=1,
                )
                self.clear_agent(agent_config_temp["agent_configs"][0]["name"])
                recalled_agent_config_list.append(agent_config_temp["agent_configs"][0])
            else:
                if agent_profile in recalled_name_desc:
                    # prevent identical agents
                    continue
                recalled_name_desc.append(agent_profile)
                name = agent_profile.split(":")[0].strip()
                desc = agent_profile.split(":")[1].strip()
                for agent in agent_config_list:
                    if name == agent["name"] and desc == agent["description"]:
                        recalled_agent_config_list.append(agent.copy())

        print(f"{[agent['name'] for agent in recalled_agent_config_list]} are selected.", flush=True)

        if coding is None:
            resp = (
                self.builder_model.create(
                    messages=[{"role": "user", "content": self.CODING_PROMPT.format(task=building_task)}]
                )
                .choices[0]
                .message.content
            )
            coding = True if resp == "YES" else False

        self.cached_configs.update(
            {
                "building_task": building_task,
                "agent_configs": recalled_agent_config_list,
                "coding": coding,
                "default_llm_config": default_llm_config,
                "code_execution_config": code_execution_config,
            }
        )
        _config_check(self.cached_configs)

        return self._build_agents(use_oai_assistant, user_proxy=user_proxy, **kwargs)

    def _build_agents(
        self, use_oai_assistant: Optional[bool] = False, user_proxy: Optional[autogen.ConversableAgent] = None, **kwargs
    ) -> Tuple[List[autogen.ConversableAgent], Dict]:
        """
        Build agents with generated configs.

        Args:
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            user_proxy: user proxy's class that can be used to replace the default user proxy.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        agent_configs = self.cached_configs["agent_configs"]
        default_llm_config = self.cached_configs["default_llm_config"]
        coding = self.cached_configs["coding"]
        code_execution_config = self.cached_configs["code_execution_config"]

        print(colored("==> Creating agents...", "green"), flush=True)
        for config in agent_configs:
            print(f"Creating agent {config['name']}...", flush=True)
            self._create_agent(
                agent_config=config.copy(),
                member_name=[agent["name"] for agent in agent_configs],
                llm_config=default_llm_config,
                use_oai_assistant=use_oai_assistant,
                **kwargs,
            )
        agent_list = [agent_config[0] for agent_config in self.agent_procs_assign.values()]

        if coding is True:
            print("Adding user console proxy...", flush=True)
            if user_proxy is None:
                user_proxy = autogen.UserProxyAgent(
                    name="Computer_terminal",
                    is_termination_msg=lambda x: x == "TERMINATE" or x == "TERMINATE.",
                    code_execution_config=code_execution_config,
                    human_input_mode="NEVER",
                    default_auto_reply=self.DEFAULT_PROXY_AUTO_REPLY,
                )
            agent_list = agent_list + [user_proxy]

        return agent_list, self.cached_configs.copy()

    def save(self, filepath: Optional[str] = None) -> str:
        """
        Save building configs. If the filepath is not specific, this function will create a filename by encrypt the
        building_task string by md5 with "save_config_" prefix, and save config to the local path.

        Args:
            filepath: save path.

        Return:
            filepath: path save.
        """
        if filepath is None:
            filepath = f'./save_config_{hashlib.md5(self.building_task.encode("utf-8")).hexdigest()}.json'
        with open(filepath, "w") as save_file:
            json.dump(self.cached_configs, save_file, indent=4)
        print(colored(f"Building config saved to {filepath}", "green"), flush=True)

        return filepath

    def load(
        self,
        filepath: Optional[str] = None,
        config_json: Optional[str] = None,
        use_oai_assistant: Optional[bool] = False,
        **kwargs,
    ) -> Tuple[List[autogen.ConversableAgent], Dict]:
        """
        Load building configs and call the build function to complete building without calling online LLMs' api.

        Args:
            filepath: filepath or JSON string for the save config.
            config_json: JSON string for the save config.
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        # load json string.
        if config_json is not None:
            print(colored("Loading config from JSON...", "green"), flush=True)
            cached_configs = json.loads(config_json)

        # load from path.
        if filepath is not None:
            print(colored(f"Loading config from {filepath}", "green"), flush=True)
            with open(filepath) as f:
                cached_configs = json.load(f)

        _config_check(cached_configs)

        agent_configs = cached_configs["agent_configs"]
        default_llm_config = cached_configs["default_llm_config"]
        coding = cached_configs["coding"]

        if kwargs.get("code_execution_config", None) is not None:
            # for test
            self.cached_configs.update(
                {
                    "building_task": cached_configs["building_task"],
                    "agent_configs": agent_configs,
                    "coding": coding,
                    "default_llm_config": default_llm_config,
                    "code_execution_config": kwargs["code_execution_config"],
                }
            )
            del kwargs["code_execution_config"]
            return self._build_agents(use_oai_assistant, **kwargs)
        else:
            code_execution_config = cached_configs["code_execution_config"]
            self.cached_configs.update(
                {
                    "building_task": cached_configs["building_task"],
                    "agent_configs": agent_configs,
                    "coding": coding,
                    "default_llm_config": default_llm_config,
                    "code_execution_config": code_execution_config,
                }
            )
            return self._build_agents(use_oai_assistant, **kwargs)
