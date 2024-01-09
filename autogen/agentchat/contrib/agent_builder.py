import autogen
import time
import subprocess as sp
import socket
import json
import hashlib
from typing import Optional, List, Dict, Tuple


def _config_check(config: Dict):
    # check config loading
    assert config.get("coding", None) is not None, 'Missing "coding" in your config.'
    assert config.get("default_llm_config", None) is not None, 'Missing "default_llm_config" in your config.'
    assert config.get("code_execution_config", None) is not None, 'Missing "code_execution_config" in your config.'

    for agent_config in config["agent_configs"]:
        assert agent_config.get("name", None) is not None, 'Missing agent "name" in your agent_configs.'
        assert agent_config.get("model", None) is not None, 'Missing agent "model" in your agent_configs.'
        assert (
            agent_config.get("system_message", None) is not None
        ), 'Missing agent "system_message" in your agent_configs.'
        assert agent_config.get("description", None) is not None, 'Missing agent "description" in your agent_configs.'


class AgentBuilder:
    """
    AgentBuilder can help user build an automatic task solving process powered by multi-agent system.
    Specifically, our building pipeline includes initialize and build.
    In build(), we prompt a LLM to create multiple participant agents, and specify whether this task need programming to solve.
    User can save the built agents' config by calling save(), and load the saved configs by load(), which can skip the
        building process.
    """

    online_server_name = "online"

    CODING_PROMPT = """Does the following task need programming (i.e., access external API or tool by coding) to solve,
    or coding may help the following task become easier?

    TASK: {task}

    Hint:
    # Answer only YES or NO.
    """

    AGENT_NAME_PROMPT = """To complete the following task, what positions/jobs should be set to maximize efficiency?

    TASK: {task}

    Hint:
    # Considering the effort, the position in this task should be no more than {max_agents}; less is better.
    # These positions' name should include enough information that can help a group chat manager know when to let this position speak.
    # The position name should be as specific as possible. For example, use "python_programmer" instead of "programmer".
    # Do not use ambiguous position name, such as "domain expert" with no specific description of domain or "technical writer" with no description of what it should write.
    # Each position should have a unique function and the position name should reflect this.
    # The positions should relate to the task and significantly different in function.
    # Add ONLY ONE programming related position if the task needs coding.
    # Generated agent's name should follow the format of ^[a-zA-Z0-9_-]{{1,64}}$, use "_" to split words.
    # Answer the names of those positions/jobs, separated names by commas.
    # Only return the list of positions.
    """

    AGENT_SYS_MSG_PROMPT = """Considering the following position and task:

    TASK: {task}
    POSITION: {position}

    Modify the following position requirement, making it more suitable for the above task and position:

    REQUIREMENT: {default_sys_msg}

    Hint:
    # Your answer should be natural, starting from "You are now in a group chat. You need to complete a task with other participants. As a ...".
    # [IMPORTANT] You should let them reply "TERMINATE" when they think the task is completed (the user's need has actually been satisfied).
    # The modified requirement should not contain the code interpreter skill.
    # You should remove the related skill description when the position is not a programmer or developer.
    # Coding skill is limited to Python.
    # Your answer should omit the word "REQUIREMENT".
    # People with the above position can doubt previous messages or code in the group chat (for example, if there is no
output after executing the code) and provide a corrected answer or code.
    # People in the above position should ask for help from the group chat manager when confused and let the manager select another participant.
    """

    AGENT_DESCRIPTION_PROMPT = """Considering the following position:

    POSITION: {position}

    What requirements should this position be satisfied?

    Hint:
    # This description should include enough information that can help a group chat manager know when to let this position speak.
    # People with the above position can doubt previous messages or code in the group chat (for example, if there is no
output after executing the code) and provide a corrected answer or code.
    # Your answer should be in at most three sentences.
    # Your answer should be natural, starting from "[POSITION's name] is a ...".
    # Your answer should include the skills that this position should have.
    # Your answer should not contain coding-related skills when the position is not a programmer or developer.
    # Coding skills should be limited to Python.
    """

    AGENT_SEARCHING_PROMPT = """Considering the following task:

    TASK: {task}

    What following agents should be involved to the task?

    AGENT LIST:
    {agent_list}

    Hint:
    # You should consider if the agent's name and profile match the task.
    # Considering the effort, you should select less then {max_agents} agents; less is better.
    # Separate agent names by commas and use "_" instead of space. For example, Product_manager,Programmer
    # Only return the list of agent names.
    """

    def __init__(
        self,
        config_file_or_env: Optional[str] = "OAI_CONFIG_LIST",
        config_file_location: Optional[str] = "",
        builder_model: Optional[str] = "gpt-4",
        agent_model: Optional[str] = "gpt-4",
        host: Optional[str] = "localhost",
        endpoint_building_timeout: Optional[int] = 600,
        max_tokens: Optional[int] = 945,
        max_agents: Optional[int] = 5,
    ):
        """
        (These APIs are experimental and may change in the future.)
        Args:
            config_file_or_env: path or environment of the OpenAI api configs.
            builder_model: specify a model as the backbone of build manager.
            agent_model: specify a model as the backbone of participant agents.
            host: endpoint host.
            endpoint_building_timeout: timeout for building up an endpoint server.
            max_tokens: max tokens for each agent.
            max_agents: max agents for each task.
        """
        self.host = host
        self.builder_model = builder_model
        self.agent_model = agent_model
        self.config_file_or_env = config_file_or_env
        self.config_file_location = config_file_location
        self.endpoint_building_timeout = endpoint_building_timeout

        self.building_task: str = None
        self.agent_configs: List[Dict] = []
        self.open_ports: List[str] = []
        self.agent_procs: Dict[str, Tuple[sp.Popen, str]] = {}
        self.agent_procs_assign: Dict[str, Tuple[autogen.ConversableAgent, str]] = {}
        self.cached_configs: Dict = {}

        self.max_tokens = max_tokens
        self.max_agents = max_agents

        for port in range(8000, 65535):
            if self._is_port_open(host, port):
                self.open_ports.append(str(port))

    def set_builder_model(self, model: str):
        self.builder_model = model

    def set_agent_model(self, model: str):
        self.agent_model = model

    @staticmethod
    def _is_port_open(host, port):
        """Check if a tcp port is open."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.bind((host, int(port)))
            s.close()
            return True
        except OSError:
            return False

    def _create_agent(
        self,
        agent_name: str,
        model_name_or_hf_repo: str,
        llm_config: dict,
        system_message: Optional[str] = autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
        description: Optional[str] = autogen.AssistantAgent.DEFAULT_DESCRIPTION,
        use_oai_assistant: Optional[bool] = False,
        world_size: Optional[int] = 1,
    ) -> autogen.AssistantAgent:
        """
        Create a group chat participant agent.

        If the agent rely on an open-source model, this function will automatically set up an endpoint for that agent.
        The API address of that endpoint will be "localhost:{free port}".

        Args:
            agent_name: the name that identify the function of the agent (e.g., Coder, Product Manager,...)
            model_name_or_hf_repo: the name of the model or the huggingface repo.
            llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            system_message: system prompt use to format an agent's behavior.
            description: a brief description of the agent. This will improve the group chat performance.
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.
            world_size: the max size of parallel tensors (in most of the cases, this is identical to the amount of GPUs).

        Returns:
            agent: a set-up agent.
        """
        from huggingface_hub import HfApi
        from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

        config_list = autogen.config_list_from_json(
            self.config_file_or_env,
            file_location=self.config_file_location,
            filter_dict={"model": [model_name_or_hf_repo]},
        )
        if len(config_list) == 0:
            raise RuntimeError(
                f"Fail to initialize agent {agent_name}: {model_name_or_hf_repo} does not exist in {self.config_file_or_env}.\n"
                f'If you would like to change this model, please specify the "agent_model" in the constructor.\n'
                f"If you load configs from json, make sure the model in agent_configs is in the {self.config_file_or_env}."
            )
        try:
            hf_api = HfApi()
            hf_api.model_info(model_name_or_hf_repo)
            model_name = model_name_or_hf_repo.split("/")[-1]
            server_id = f"{model_name}_{self.host}"
        except GatedRepoError as e:
            raise e
        except RepositoryNotFoundError:
            server_id = self.online_server_name

        if server_id != self.online_server_name:
            # The code in this block is uncovered by tests because online environment does not support gpu use.
            if self.agent_procs.get(server_id, None) is None:
                while True:
                    port = self.open_ports.pop()
                    if self._is_port_open(self.host, port):
                        break

                # Use vLLM to set up a server with OpenAI API support.
                agent_proc = sp.Popen(
                    [
                        "python",
                        "-m",
                        "vllm.entrypoints.openai.api_server",
                        "--host",
                        f"{self.host}",
                        "--port",
                        f"{port}",
                        "--model",
                        f"{model_name_or_hf_repo}",
                        "--tensor-parallel-size",
                        f"{world_size}",
                    ],
                    stdout=sp.PIPE,
                    stderr=sp.STDOUT,
                )
                timeout_start = time.time()

                while True:
                    server_stdout = agent_proc.stdout.readline()
                    if server_stdout != b"":
                        print(server_stdout)
                    timeout_end = time.time()
                    if b"running" in server_stdout:
                        print(
                            f"Running {model_name_or_hf_repo} on http://{self.host}:{port} "
                            f"with tensor parallel size {world_size}."
                        )
                        break
                    elif b"address already in use" in server_stdout:
                        raise RuntimeError(
                            f"{self.host}:{port} already in use. Fail to set up the endpoint for "
                            f"{model_name_or_hf_repo} on {self.host}:{port}."
                        )
                    elif timeout_end - timeout_start > self.endpoint_building_timeout:
                        raise RuntimeError(
                            f"Timeout exceed. Fail to set up the endpoint for "
                            f"{model_name_or_hf_repo} on {self.host}:{port}."
                        )
                self.agent_procs[server_id] = (agent_proc, port)
            else:
                port = self.agent_procs[server_id][1]

            config_list[0]["base_url"] = f"http://{self.host}:{port}/v1"

        current_config = llm_config.copy()
        current_config.update(
            {"config_list": config_list, "model": model_name_or_hf_repo, "max_tokens": self.max_tokens}
        )
        if use_oai_assistant:
            from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

            agent = GPTAssistantAgent(
                name=agent_name,
                llm_config={**current_config, "assistant_id": None},
                instructions=system_message,
                overwrite_instructions=False,
            )
        else:
            agent = autogen.AssistantAgent(
                name=agent_name,
                llm_config=current_config.copy(),
                system_message=system_message,
                description=description,
            )
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
        print(f"Agent {agent_name} has been cleared.")

    def clear_all_agents(self, recycle_endpoint: Optional[bool] = True):
        """
        Clear all cached agents.
        """
        for agent_name in [agent_name for agent_name in self.agent_procs_assign.keys()]:
            self.clear_agent(agent_name, recycle_endpoint)
        print("All agents have been cleared.")

    def build(
        self,
        building_task: str,
        default_llm_config: Dict,
        coding: Optional[bool] = None,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
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

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        if code_execution_config is None:
            code_execution_config = {
                "last_n_messages": 2,
                "work_dir": "groupchat",
                "use_docker": False,
                "timeout": 60,
            }

        agent_configs = []
        self.building_task = building_task

        config_list = autogen.config_list_from_json(
            self.config_file_or_env,
            file_location=self.config_file_location,
            filter_dict={"model": [self.builder_model]},
        )
        if len(config_list) == 0:
            raise RuntimeError(
                f"Fail to initialize build manager: {self.builder_model} does not exist in {self.config_file_or_env}. "
                f'If you want to change this model, please specify the "builder_model" in the constructor.'
            )
        build_manager = autogen.OpenAIWrapper(config_list=config_list)

        print("==> Generating agents...")
        resp_agent_name = (
            build_manager.create(
                messages=[
                    {
                        "role": "user",
                        "content": self.AGENT_NAME_PROMPT.format(task=building_task, max_agents=self.max_agents),
                    }
                ]
            )
            .choices[0]
            .message.content
        )
        agent_name_list = [agent_name.strip().replace(" ", "_") for agent_name in resp_agent_name.split(",")]
        print(f"{agent_name_list} are generated.")

        print("==> Generating system message...")
        agent_sys_msg_list = []
        for name in agent_name_list:
            print(f"Preparing system message for {name}")
            resp_agent_sys_msg = (
                build_manager.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_SYS_MSG_PROMPT.format(
                                task=building_task,
                                position=name,
                                default_sys_msg=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_sys_msg_list.append(resp_agent_sys_msg)

        print("==> Generating description...")
        agent_description_list = []
        for name in agent_name_list:
            print(f"Preparing description for {name}")
            resp_agent_description = (
                build_manager.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_DESCRIPTION_PROMPT.format(position=name),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_description_list.append(resp_agent_description)

        for name, sys_msg, description in list(zip(agent_name_list, agent_sys_msg_list, agent_description_list)):
            agent_configs.append(
                {"name": name, "model": self.agent_model, "system_message": sys_msg, "description": description}
            )

        if coding is None:
            resp = (
                build_manager.create(
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

        return self._build_agents(use_oai_assistant, **kwargs)

    def build_from_library(
        self,
        building_task: str,
        library_path_or_json: str,
        default_llm_config: Dict,
        coding: Optional[bool] = True,
        code_execution_config: Optional[Dict] = None,
        use_oai_assistant: Optional[bool] = False,
        embedding_model: Optional[str] = None,
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
                if None, an openai model will be prompted to select agents. As reference, chromadb use "all-mpnet-base-
                v2" as default.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        import chromadb
        from chromadb.utils import embedding_functions

        if code_execution_config is None:
            code_execution_config = {
                "last_n_messages": 2,
                "work_dir": "groupchat",
                "use_docker": False,
                "timeout": 60,
            }

        agent_configs = []

        config_list = autogen.config_list_from_json(
            self.config_file_or_env,
            file_location=self.config_file_location,
            filter_dict={"model": [self.builder_model]},
        )
        if len(config_list) == 0:
            raise RuntimeError(
                f"Fail to initialize build manager: {self.builder_model} does not exist in {self.config_file_or_env}. "
                f'If you want to change this model, please specify the "builder_model" in the constructor.'
            )
        build_manager = autogen.OpenAIWrapper(config_list=config_list)

        try:
            agent_library = json.loads(library_path_or_json)
        except json.decoder.JSONDecodeError:
            with open(library_path_or_json, "r") as f:
                agent_library = json.load(f)

        print("==> Looking for suitable agents in library...")
        if embedding_model is not None:
            chroma_client = chromadb.Client()
            collection = chroma_client.create_collection(
                name="agent_list",
                embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embedding_model),
            )
            collection.add(
                documents=[agent["profile"] for agent in agent_library],
                metadatas=[{"source": "agent_profile"} for _ in range(len(agent_library))],
                ids=[f"agent_{i}" for i in range(len(agent_library))],
            )
            agent_profile_list = collection.query(query_texts=[building_task], n_results=self.max_agents)["documents"][
                0
            ]

            # search name from library
            agent_name_list = []
            for profile in agent_profile_list:
                for agent in agent_library:
                    if agent["profile"] == profile:
                        agent_name_list.append(agent["name"])
                        break
            chroma_client.delete_collection(collection.name)
            print(f"{agent_name_list} are selected.")
        else:
            agent_profiles = [
                f"No.{i + 1} AGENT's NAME: {agent['name']}\nNo.{i + 1} AGENT's PROFILE: {agent['profile']}\n\n"
                for i, agent in enumerate(agent_library)
            ]
            resp_agent_name = (
                build_manager.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_SEARCHING_PROMPT.format(
                                task=building_task, agent_list="".join(agent_profiles), max_agents=self.max_agents
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_name_list = [agent_name.strip().replace(" ", "_") for agent_name in resp_agent_name.split(",")]

            # search profile from library
            agent_profile_list = []
            for name in agent_name_list:
                for agent in agent_library:
                    if agent["name"] == name:
                        agent_profile_list.append(agent["profile"])
                        break
            print(f"{agent_name_list} are selected.")

        print("==> Generating system message...")
        # generate system message from profile
        agent_sys_msg_list = []
        for name, profile in list(zip(agent_name_list, agent_profile_list)):
            print(f"Preparing system message for {name}...")
            resp_agent_sys_msg = (
                build_manager.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_SYS_MSG_PROMPT.format(
                                task=building_task,
                                position=f"{name}\nPOSITION PROFILE: {profile}",
                                default_sys_msg=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_sys_msg_list.append(resp_agent_sys_msg)

        for name, sys_msg, description in list(zip(agent_name_list, agent_sys_msg_list, agent_profile_list)):
            agent_configs.append(
                {"name": name, "model": self.agent_model, "system_message": sys_msg, "description": description}
            )

        if coding is None:
            resp = (
                build_manager.create(
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

        return self._build_agents(use_oai_assistant, **kwargs)

    def _build_agents(
        self, use_oai_assistant: Optional[bool] = False, **kwargs
    ) -> Tuple[List[autogen.ConversableAgent], Dict]:
        """
        Build agents with generated configs.

        Args:
            use_oai_assistant: use OpenAI assistant api instead of self-constructed agent.

        Returns:
            agent_list: a list of agents.
            cached_configs: cached configs.
        """
        agent_configs = self.cached_configs["agent_configs"]
        default_llm_config = self.cached_configs["default_llm_config"]
        coding = self.cached_configs["coding"]
        code_execution_config = self.cached_configs["code_execution_config"]

        print("==> Creating agents...")
        for config in agent_configs:
            print(f"Creating agent {config['name']} with backbone {config['model']}...")
            self._create_agent(
                config["name"],
                config["model"],
                default_llm_config,
                system_message=config["system_message"],
                description=config["description"],
                use_oai_assistant=use_oai_assistant,
                **kwargs,
            )
        agent_list = [agent_config[0] for agent_config in self.agent_procs_assign.values()]

        if coding is True:
            print("Adding user console proxy...")
            agent_list = (
                [
                    autogen.UserProxyAgent(
                        name="User_console_and_code_interpreter",
                        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
                        system_message="User console with a python code interpreter interface.",
                        description="""A user console with a code interpreter interface.
It can provide the code execution results. Select this player when other players provide some code that needs to be executed.
DO NOT SELECT THIS PLAYER WHEN NO CODE TO EXECUTE; IT WILL NOT ANSWER ANYTHING.""",
                        code_execution_config=code_execution_config,
                        human_input_mode="NEVER",
                    )
                ]
                + agent_list
            )

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
        print(f"Building config saved to {filepath}")

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
            print("Loading config from JSON...")
            cached_configs = json.loads(config_json)

        # load from path.
        if filepath is not None:
            print(f"Loading config from {filepath}")
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
