import autogen
import time
import subprocess as sp
import socket
import os
import json
import hashlib
from typing import Optional, List, Dict, Tuple
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent


class AgentBuilder:
    """
    AgentBuilder can help user build an automatic task solving process powered by multi-agent system.
    Specifically, our building pipeline include init(), build(), and start().
    In build(), we prompt a gpt-4 model to create multiple participant agent and initialize a group chat, and specify
        whether this task need programming to solve.
    After that, user can call start() at a proper time to complete the task.
    User can save the built agents' config by calling save(), and load the saved configs by load(), which can skip the
        building process.
    """

    openai_server_name = "openai"
    max_tokens = 945
    max_agents = 5  # maximum number of agents build manager can create.

    CODING_PROMPT = """Does the following task need programming (i.e., access external API or tool by coding) to solve,
    or use program may help the following task become easier?

    TASK: {task}

    Hint:
    # Answer only YES or NO.
    """

    AGENT_NAME_PROMPT = """To complete the following task, what positions/jobs should be set to maximize the efficiency?

    TASK: {task}

    Hint:
    # Considering the effort, the position in this task should be no more then {max_agents}, less is better.
    # Answer the name of those positions/jobs, separated by comma and use "_" instead of space. For example: Product_manager,Programmer
    # Only return the list of positions.
    """

    AGENT_SYS_MSG_PROMPT = """Considering the following position and corresponding task:

    TASK: {task}
    POSITION: {position}

    Modify the following position requirement, let it more suitable for the above task and position:

    REQUIREMENT: {default_sys_msg}

    Hint:
    # The modified requirement should not contain the code interpreter skill.
    # Coding skill is limited to Python.
    # Your answer should omit the word "REQUIREMENT".
    # Your answer should include the description of the behavior when the task complete (user's need has been satisfied).
    """

    def __init__(
        self,
        config_path: Optional[str] = "OAI_CONFIG_LIST",
        builder_model: Optional[str] = "gpt-4-1106-preview",
        agent_model: Optional[str] = "gpt-4-1106-preview",
        host: Optional[str] = "localhost",
        endpoint_building_timeout: Optional[int] = 180,
    ):
        """
        Args:
            config_path: path of the OpenAI api configs.
            builder_model: specify a model as the backbone of build manager.
            host: endpoint host.
            endpoint_building_timeout: timeout for building up an endpoint server.
        """
        self.host = host
        self.builder_model = builder_model
        self.agent_model = agent_model
        self.config_path = config_path
        self.endpoint_building_timeout = endpoint_building_timeout

        self.user_proxy: autogen.UserProxyAgent = None
        self.group_chat_manager_config: dict = None
        self.initiate_agent_name: str = "User_console_and_Python_code_interpreter"
        self.manager_system_message: str = "Group chat manager."
        self.agent_configs: List[Dict] = []
        self.coding: bool = None
        self.default_llm_config: Dict = None
        self.building_task: str = None
        self.open_ports: List[str] = []
        self.agent_procs: Dict[str, Tuple[sp.Popen, str]] = {}
        self.agent_procs_assign: Dict[str, Tuple[autogen.ConversableAgent, str]] = {}

        for port in range(8000, 65535):
            if self._is_port_open(host, port):
                self.open_ports.append(str(port))

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

    def create_agent(
        self,
        agent_name: str,
        model_name_or_hf_repo: str,
        llm_config: dict,
        system_message: Optional[str] = autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
        use_gpts: Optional[bool] = False,
        world_size: Optional[int] = 1,
    ) -> autogen.AssistantAgent:
        """
        Create a group chat agent.

        If the agent rely on an open-source model, this function will automatically set up an endpoint for that agent.
        The API address of that endpoint will be "localhost:{free port}".

        Args:
            agent_name: the name that identify the function of the agent (e.g., Coder, Product Manager,...)
            model_name_or_hf_repo:
            llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            system_message: system prompt use to format an agent's behavior.
            use_gpts: use OpenAI GPTs api instead on self-construct agent.
            world_size: the max size of parallel tensors (in most of the cases, this is identical to the amount of GPUs).

        Returns:
            agent: a set-up agent.
        """
        config_list = autogen.config_list_from_json(self.config_path, filter_dict={"model": [model_name_or_hf_repo]})
        if "gpt-" in model_name_or_hf_repo:
            server_id = self.openai_server_name
        else:
            model_name = model_name_or_hf_repo.split("/")[-1]
            server_id = f"{model_name}_{self.host}"
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
        if use_gpts:
            agent = GPTAssistantAgent(
                name=agent_name,
                llm_config={**current_config, "assistant_id": None},
                instructions=system_message,
                overwrite_instructions=False,
            )
        else:
            agent = autogen.AssistantAgent(
                name=agent_name, llm_config=current_config.copy(), system_message=system_message
            )
        self.agent_procs_assign[agent_name] = (agent, server_id)
        return agent

    def clear_agent(self, agent_name: str = None, recycle_endpoint: bool = True):
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
            if server_id == self.openai_server_name:
                return
            else:
                for _, iter_sid in self.agent_procs_assign.values():
                    if server_id == iter_sid:
                        return
                self.agent_procs[server_id][0].terminate()
                self.open_ports.append(server_id.split("_")[-1])

    def clear_all_agents(self):
        """
        Clear all cached agents.
        """
        for agent_name in [agent_name for agent_name in self.agent_procs_assign.keys()]:
            self.clear_agent(agent_name)

    def build(
        self,
        building_task: Optional[str] = None,
        default_llm_config: Optional[Dict] = None,
        coding: Optional[bool] = None,
        cached_configs: Optional[Dict] = None,
        use_gpts: Optional[bool] = False,
    ):
        """
        Auto build agents based on the building task.

        Args:
            building_task: instruction that helps build manager (gpt-4) to decide what agent should be built.
            default_llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            coding: use to identify if the user proxy (a code interpreter) should be added.
            cached_configs: previously saved agent configs.
            use_gpts: if true, build function will use GPTs api to build agents.
        """
        use_api = False

        if cached_configs is None:
            use_api = True
            self.building_task = building_task
            self.default_llm_config = default_llm_config.copy()
            self.coding = coding
        else:
            self.building_task = cached_configs["building_task"]
            self.default_llm_config = cached_configs["default_llm_config"]
            self.coding = cached_configs["coding"]
            self.agent_configs = cached_configs["agent_configs"]
            self.manager_system_message = cached_configs["manager_system_message"]

        config_list = autogen.config_list_from_json(self.config_path, filter_dict={"model": [self.builder_model]})
        build_manager = autogen.OpenAIWrapper(config_list=config_list)

        if use_api:
            print("Generating agents...")
            resp_agent_name = (
                build_manager.create(
                    messages=[
                        {
                            "role": "user",
                            "content": self.AGENT_NAME_PROMPT.format(
                                task=self.building_task, max_agents=self.max_agents
                            ),
                        }
                    ]
                )
                .choices[0]
                .message.content
            )
            agent_name_list = resp_agent_name.split(",")
            print(f"{resp_agent_name} are generated.")

            agent_sys_msg_list = []
            for name in agent_name_list:
                print(f"Preparing configuration for {name}...")
                resp_agent_sys_msg = (
                    build_manager.create(
                        messages=[
                            {
                                "role": "user",
                                "content": self.AGENT_SYS_MSG_PROMPT.format(
                                    task=self.building_task,
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

            for i in range(len(agent_name_list)):
                self.agent_configs.append(
                    {"name": agent_name_list[i], "model": self.agent_model, "system_message": agent_sys_msg_list[i]}
                )
                print(f"Creating agent {agent_name_list[i]} with backbone {self.agent_model}...")
                self.create_agent(
                    agent_name_list[i],
                    self.agent_model,
                    self.default_llm_config,
                    system_message=agent_sys_msg_list[i],
                    use_gpts=use_gpts,
                )
            self.manager_system_message = "Group chat manager."

        if self.coding is None:
            resp = (
                build_manager.create(
                    messages=[{"role": "user", "content": self.CODING_PROMPT.format(task=self.building_task)}]
                )
                .choices[0]
                .message.content
            )
            self.coding = True if resp == "YES" else False

        if self.coding is True:
            print("Adding user console proxy...")
            self.user_proxy = autogen.UserProxyAgent(
                name="User_console_and_Python_code_interpreter",
                system_message="User console with a python code interpreter interface.",
                code_execution_config={"last_n_messages": 2, "work_dir": "groupchat"},
                human_input_mode="NEVER",
            )
        else:
            self.initiate_agent_name = self.agent_configs[0]["name"]

        self.group_chat_manager_config = self.default_llm_config.copy()
        self.group_chat_manager_config["config_list"] = config_list

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
        json.dump(
            {
                "building_task": self.building_task,
                "agent_configs": self.agent_configs,
                "manager_system_message": self.manager_system_message,
                "coding": self.coding,
                "default_llm_config": self.default_llm_config,
            },
            open(filepath, "w"),
            indent=4,
        )
        print(f"Building config saved to {filepath}")

        return filepath

    def load(self, filepath: str):
        """
        Load building configs and call the build function to complete building without calling online LLMs' api.

        Args:
            filepath: filepath for the save config.
        """
        if os.path.isfile(filepath):
            cached_configs = json.load(open(filepath))
            self.build(cached_configs=cached_configs)
        else:
            raise FileNotFoundError(f"Config file {filepath} does not exist.")

        return self

    def start(self, task: str, max_round: Optional[int] = 12, init_messages: Optional[List[dict]] = []):
        """
        Start a group chat task solving process with built config.

        Args:
            task: description of a task.
            max_round: the maximum number of rounds.
            init_messages: input messages before the task start. This can be the chat history from other group chat
                or some preliminary of the task.
        """
        agent_list = [agent for agent, _ in self.agent_procs_assign.values()]
        if self.user_proxy is not None:
            agent_list.append(self.user_proxy)
        # TODO: add agent trigger
        group_chat = autogen.GroupChat(agents=agent_list, messages=init_messages, max_round=max_round)

        manager = autogen.GroupChatManager(
            groupchat=group_chat, llm_config=self.group_chat_manager_config, system_message=self.manager_system_message
        )

        if self.initiate_agent_name == "User_console_and_Python_code_interpreter" and self.user_proxy is not None:
            self.user_proxy.initiate_chat(manager, message=task)
        else:
            for agent in agent_list:
                if self.initiate_agent_name == agent.name:
                    agent.initiate_chat(manager, message=task)
