import hashlib
import importlib
import json
import logging
import re
import socket
import subprocess as sp
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

import requests
from termcolor import colored
import yaml

from autogen_agentchat.agents import AssistantAgent
from autogen_core._component_config import ComponentModel
from autogen_core.tools._base import BaseTool
from autogen_ext.code_executors._common import CODE_BLOCK_PATTERN
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import AssistantMessage, ChatCompletionClient, UserMessage
from autogen_agentchat.agents._code_executor_agent import CodeExecutorAgent
from autogen_core.tools import FunctionTool, Tool, ToolSchema
from ._prompts import AGENT_DESCRIPTION_PROMPT, AGENT_FUNCTION_MAP_PROMPT, AGENT_NAME_PROMPT, AGENT_SELECTION_PROMPT, AGENT_SYS_MSG_PROMPT, CODING_AND_TASK_SKILL_INSTRUCTION, CODING_PROMPT, DEFAULT_DESCRIPTION, GROUP_CHAT_DESCRIPTION, UPDATED_AGENT_SYSTEM_MESSAGE

logger = logging.getLogger(__name__)

def _config_check(config: Dict):
    # check config loading
    assert config.get("coding", None) is not None, 'Missing "coding" in your config.'
    assert config.get("code_execution_config", None) is not None, 'Missing "code_execution_config" in your config.'

    for agent_config in config["agent_configs"]:
        assert agent_config.get("name", None) is not None, 'Missing agent "name" in your agent_configs.'
        assert (
            agent_config.get("system_message", None) is not None
        ), 'Missing agent "system_message" in your agent_configs.'
        assert agent_config.get("description", None) is not None, 'Missing agent "description" in your agent_configs.'


def _retrieve_json(text):
    match = re.findall(CODE_BLOCK_PATTERN, text, flags=re.DOTALL)
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

    def __init__(
        self,
        builder_model_config: ComponentModel | Dict[str, Any],
        agents_model_config: ComponentModel | Dict[str, Any],
        max_agents: Optional[int] = 5,
    ):
        """
        (These APIs are experimental and may change in the future.)
        Args:
            builder_model_config: specify a model config as the backbone of build manager.
            agent_model_config: specify a model config as the backbone of participant agents.
            max_agents: max agents for each task.
        """

        builder_client = ChatCompletionClient.load_component(model=builder_model_config)
        self.builder_model_client = builder_client

        agent_client = ChatCompletionClient.load_component(model=agents_model_config)
        self.agent_model_client = agent_client
        self.agent_model_name = agents_model_config['config']['model']

        self.building_task: str = None
        self.agent_configs: List[Dict] = []
        self.open_ports: List[str] = []
        self.agent_procs: Dict[str, Tuple[sp.Popen, str]] = {}
        self.agent_procs_assign: Dict[str, Tuple[AssistantAgent, str]] = {}
        self.cached_configs: Dict = {}

        self.max_agents = max_agents

    async def _create_agent(
        self,
        agent_config: Dict,
        member_name: List[str],
        use_oai_assistant: Optional[bool] = False,
    ) -> AssistantAgent:
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
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            world_size: the max size of parallel tensors (in most of the cases, this is identical to the amount of GPUs).

        Returns:
            agent: a set-up agent.
        """
        agent_name = agent_config["name"]
        system_message = agent_config["system_message"]
        description = agent_config["description"]

        # Path to the customize **ConversableAgent** class.
        model_path = agent_config.get("model_path", None)
        
        server_id = self.online_server_name

        if use_oai_assistant:
            from autogen_ext.agents.openai._openai_assistant_agent import OpenAIAssistantAgent

            agent = OpenAIAssistantAgent(
                name=agent_name,
                description=description,
                client=self.agent_model_client,
                model='gpt-4',
                instructions=system_message            
            )
        else:
            code_executor_desc = ""
            if self.cached_configs["coding"] is True:
                code_executor_desc = (
                    "\nThe group also include a Computer_terminal to help you run the python and shell code."
                )

            model_class = AssistantAgent
            if model_path:
                module_path, model_class_name = model_path.replace("/", ".").rsplit(".", 1)
                module = importlib.import_module(module_path)
                model_class = getattr(module, model_class_name)
                if not issubclass(model_class, AssistantAgent):
                    logger.error(f"{model_class} is not a AssistantAgent. Use AssistantAgent as default")
                    model_class = AssistantAgent

            additional_config = {
                k: v
                for k, v in agent_config.items()
                if k not in ["model", "name", "system_message", "description", "model_path"]
            }
            agent = model_class(
                name=agent_name, model_client=self.agent_model_client, system_message=system_message, description=description, **additional_config
            )
         
            if system_message == "":
                system_message = agent._system_messages[0].content
            else:
                system_message = f"{system_message}\n\n{CODING_AND_TASK_SKILL_INSTRUCTION}"

            enhanced_sys_msg = GROUP_CHAT_DESCRIPTION.format(
                name=agent_name, members=member_name, code_executor_desc=code_executor_desc, sys_msg=system_message
            )
            await agent.update_system_message(enhanced_sys_msg)
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

    async def build(
        self,
        building_task: str,
        list_of_functions: Optional[List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]]] = None,
        coding: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
        code_executor: Optional[CodeExecutorAgent] = None,
        max_agents: Optional[int] = None,
        **kwargs,
    ) -> Tuple[List[AssistantAgent], Dict]:
        """
        Auto build agents based on the building task.

        Args:
            building_task: instruction that helps build manager (gpt-4) to decide what agent should be built.
            list_of_functions: list of functions to be associated with Agents
            coding: use to identify if the user proxy (a code interpreter) should be added.
            code_execution_config: specific configs for user proxy (e.g., last_n_messages, work_dir, ...).
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
        resp_agent_name = (await self.builder_model_client.create(
                [UserMessage(content = AGENT_NAME_PROMPT.format(task=building_task, max_agents=max_agents), source="user")])).content
        agent_name_list = [agent_name.strip().replace(" ", "_") for agent_name in resp_agent_name.split(",")]
        print(f"{agent_name_list} are generated.", flush=True)

        print(colored("==> Generating system message...", "green"), flush=True)
        agent_sys_msg_list = []
        for name in agent_name_list:
            print(f"Preparing system message for {name}", flush=True)
            resp_agent_sys_msg = (await self.builder_model_client.create(
                [UserMessage(content=AGENT_SYS_MSG_PROMPT.format(
                                task=building_task,
                                position=name,
                                default_sys_msg=DEFAULT_DESCRIPTION
                            ), source="user")])).content
            agent_sys_msg_list.append(resp_agent_sys_msg)

        print(colored("==> Generating description...", "green"), flush=True)
        agent_description_list = []
        for name, sys_msg in list(zip(agent_name_list, agent_sys_msg_list)):
            print(f"Preparing description for {name}", flush=True)
            resp_agent_description = (await self.builder_model_client.create(
                [UserMessage(content=AGENT_DESCRIPTION_PROMPT.format(
                                position=name, 
                                sys_msg=sys_msg
                            ), source="user")])).content
            agent_description_list.append(resp_agent_description)

        for name, sys_msg, description in list(zip(agent_name_list, agent_sys_msg_list, agent_description_list)):
            agent_configs.append(
                {
                    "name": name,
                    "system_message": sys_msg,
                    "description": description,
                }
            )

        if coding is None:
            resp = (await self.builder_model_client.create(
                [UserMessage(content=CODING_PROMPT.format(task=building_task), source="user")])).content
            coding = True if resp == "YES" else False

        self.cached_configs.update(
            {
                "building_task": building_task,
                "agent_configs": agent_configs,
                "coding": coding,
                "code_execution_config": code_execution_config,
            }
        )

        _config_check(self.cached_configs)
        return await self._build_agents(use_oai_assistant, list_of_functions, code_executor=code_executor, **kwargs)

    async def build_from_library(
        self,
        building_task: str,
        library_path_or_json: str,
        top_k: int = 3,
        coding: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
        embedding_model: Optional[str] = "all-mpnet-base-v2",
        code_executor: Optional[CodeExecutorAgent] = None,
        **kwargs,
    ) -> Tuple[List[AssistantAgent], Dict]:
        """
        Build agents from a library.
        The library is a list of agent configs, which contains the name and system_message for each agent.
        We use a build manager to decide what agent in that library should be involved to the task.

        Args:
            building_task: instruction that helps build manager (gpt-4) to decide what agent should be built.
            library_path_or_json: path or JSON string config of agent library.
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
                await self.builder_model_client.create(
                    messages=[
                        {
                            "role": "user",
                            "content": AGENT_SELECTION_PROMPT.format(
                                skills=building_task, expert_pool=expert_pool, max_agents=self.max_agents
                            ),
                        }
                    ]
                )
            ).content
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
                await self.builder_model_client.create(
                    messages=[{"role": "user", "content": CODING_PROMPT.format(task=building_task)}]
                )
            ).content
            coding = True if resp == "YES" else False

        self.cached_configs.update(
            {
                "building_task": building_task,
                "agent_configs": recalled_agent_config_list,
                "coding": coding,
                "code_execution_config": code_execution_config,
            }
        )
        _config_check(self.cached_configs)

        return self._build_agents(use_oai_assistant, code_executor=code_executor, **kwargs)

    async def _build_agents(
        self,
        use_oai_assistant: Optional[bool] = False,
        list_of_functions: Optional[List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]]] = None,
        code_executor: Optional[CodeExecutorAgent] = None,
        **kwargs,
    ) -> Tuple[List[AssistantAgent], Dict]:
        """
        Build agents with generated configs.

        Args:
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            list_of_functions: list of functions to be associated to Agents
            user_proxy: user proxy's class that can be used to replace the default user proxy.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        agent_configs = self.cached_configs["agent_configs"]
        coding = self.cached_configs["coding"]
        code_execution_config = self.cached_configs["code_execution_config"]

        print(colored("==> Creating agents...", "green"), flush=True)
        for config in agent_configs:
            print(f"Creating agent {config['name']}...", flush=True)
            await self._create_agent(
                agent_config=config.copy(),
                member_name=[agent["name"] for agent in agent_configs],
                use_oai_assistant=use_oai_assistant,
                **kwargs,
            )
        agent_list = [agent_config[0] for agent_config in self.agent_procs_assign.values()]

        if coding is True:
            print("Adding code executor...", flush=True)
            if code_executor is None:
                
                # todo
                local_CodeExecutor = LocalCommandLineCodeExecutor()
                coding_agent = CodeExecutorAgent(
                    name="Computer_terminal",
                    code_executor=local_CodeExecutor
                )
            agent_list = agent_list + [coding_agent]

            agent_details = []

            for agent in agent_list[:-1]:
                agent_details.append({"name": agent.name, "description": agent.description})

            if list_of_functions:
                for func in list_of_functions:
                  
                    perferred_agent_name = (await self.builder_model_client.create(
                        [UserMessage(content = AGENT_FUNCTION_MAP_PROMPT.format(
                                        function_name=func.name,
                                        function_description=func.description,
                                        format_agent_details='[{"name": "agent_name", "description": "agent description"}, ...]',
                                        agent_details=str(json.dumps(agent_details)),
                                    ), source="user")])).content

                    if perferred_agent_name in self.agent_procs_assign.keys():
                        await self.agent_procs_assign[perferred_agent_name][0].register_tools([func])

                        agents_current_system_message = [
                            agent["system_message"] for agent in agent_configs if agent["name"] == perferred_agent_name
                        ][0]

                        # todo 
                        await self.agent_procs_assign[perferred_agent_name][0].update_system_message(
                            UPDATED_AGENT_SYSTEM_MESSAGE.format(
                                agent_system_message=agents_current_system_message,
                                function_name=func.name,
                                function_description=func.description
                            )
                        )

                        print(f"Function {func.name} is registered to agent {perferred_agent_name}.")
                    else:
                        print(f"Function {func['name']} is not registered to any agent.")
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

    async def load(
        self,
        filepath: Optional[str] = None,
        config_json: Optional[str] = None,
        use_oai_assistant: Optional[bool] = False,
        list_of_functions: Optional[List[BaseTool[Any, Any] | Callable[..., Any] | Callable[..., Awaitable[Any]]]] = None,
        **kwargs,
    ) -> Tuple[List[AssistantAgent], Dict]:
        """
        Load building configs and call the build function to complete building without calling online LLMs' api.

        Args:
            filepath: filepath or JSON string for the save config.
            config_json: JSON string for the save config.
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            list_of_functions: list of functions to be associated with Agents

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
        coding = cached_configs["coding"]

        if kwargs.get("code_execution_config", None) is not None:
            # for test
            self.cached_configs.update(
                {
                    "building_task": cached_configs["building_task"],
                    "agent_configs": agent_configs,
                    "coding": coding,
                    "code_execution_config": kwargs["code_execution_config"],
                }
            )
            del kwargs["code_execution_config"]
            return await self._build_agents(use_oai_assistant, **kwargs)
        else:
            code_execution_config = cached_configs["code_execution_config"]
            self.cached_configs.update(
                {
                    "building_task": cached_configs["building_task"],
                    "agent_configs": agent_configs,
                    "coding": coding,
                    "code_execution_config": code_execution_config,
                }
            )
            return await self._build_agents(use_oai_assistant, list_of_functions,**kwargs)
