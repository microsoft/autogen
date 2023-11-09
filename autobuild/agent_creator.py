import autogen
import time
import subprocess as sp
import socket
import os
import json
import hashlib
from typing import *


class AgentCreator:
    """
    Descriptions
    """
    open_ports: List[str] = []
    agent_procs: Dict[str, Tuple[sp.Popen, str]] = {}
    openai_server_name: str = 'openai'
    endpoint_building_timeout: Optional[int]
    agent_procs_assign: Dict[str, Tuple[autogen.AssistantAgent, str]] = {}
    max_tokens: int = 945

    user_proxy: autogen.UserProxyAgent = None
    group_chat_manager_config: dict = None
    initiate_agent_name: str = 'user'
    manager_system_message: str = 'Group chat manager.'

    CODING_PROMPT: str = '''Does the following task need programming 
    (i.e., access external API or tool by coding) to solve?

    TASK: {task}

    Answer only YES or NO.
    '''

    def __init__(
            self,
            host: str = 'localhost',
            config_path: str = 'OAI_CONFIG_LIST',
            build_config_path: Optional[str] = './.build_cache',
            endpoint_building_timeout: Optional[int] = 180
    ):
        """
        Args:
            endpoint_building_timeout: timeout for building up an endpoint server.
            config_path: path of the OpenAI api configs.
            build_config_path: path of the build configs.
            host: endpoint host.
        """
        self.endpoint_building_timeout = endpoint_building_timeout
        self.config_path = config_path
        self.host = host
        self.build_config_path = build_config_path
        if not os.path.exists(build_config_path):
            os.makedirs(build_config_path)

        print('Initializing usable port...')
        for port in range(8000, 65535):
            if self._is_port_open(host, port):
                self.open_ports.append(str(port))
        print(f'{len(self.open_ports)} ports found.')

    @staticmethod
    def _is_port_open(host, port):
        """Check if a port is open."""
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
            world_size: Optional[int] = 1
    ) -> autogen.AssistantAgent:
        """
        Descriptions

        Args:
            agent_name: the name that identify the function of the agent (e.g., Coder, Product Manager,...)
            model_name_or_hf_repo:
            llm_config: specific configs for LLM (e.g., config_list, seed, temperature, ...).
            system_message: system prompt use to format an agent's behavior.
            world_size: the max size of parallel tensors (in most of the cases, this is identical to the amount of GPUs).

        Returns:
            agent: a set-up agent.
        """
        config_list = autogen.config_list_from_json(
            self.config_path,
            filter_dict={
                'model': [model_name_or_hf_repo]
            }
        )
        if 'gpt-' in model_name_or_hf_repo:
            server_id = self.openai_server_name
        else:
            model_name = model_name_or_hf_repo.split('/')[-1]
            server_id = f'{model_name}_{self.host}'
            if self.agent_procs.get(server_id, None) is None:
                while True:
                    port = self.open_ports.pop()
                    if self._is_port_open(self.host, port):
                        break

                # Use vLLM to set up a server with OpenAI API support.
                agent_proc = sp.Popen(['python', '-m', 'vllm.entrypoints.openai.api_server',
                                       f'--host', f'{self.host}',
                                       f'--port', f'{port}',
                                       f'--model', f'{model_name_or_hf_repo}',
                                       f'--tensor-parallel-size', f'{world_size}'], stdout=sp.PIPE, stderr=sp.STDOUT)
                timeout_start = time.time()

                while True:
                    server_stdout = agent_proc.stdout.readline()
                    if server_stdout != b'':
                        print(server_stdout)
                    timeout_end = time.time()
                    if b"running" in server_stdout:
                        print(
                            f'Running {model_name_or_hf_repo} on http://{self.host}:{port} '
                            f'with tensor parallel size {world_size}.')
                        break
                    elif b"address already in use" in server_stdout:
                        raise RuntimeError(f'{self.host}:{port} already in use. Fail to set up the endpoint for '
                                           f'{model_name_or_hf_repo} on {self.host}:{port}.')
                    elif timeout_end - timeout_start > self.endpoint_building_timeout:
                        raise RuntimeError(f'Timeout exceed. Fail to set up the endpoint for '
                                           f'{model_name_or_hf_repo} on {self.host}:{port}.')
                self.agent_procs[server_id] = (agent_proc, port)
            else:
                port = self.agent_procs[server_id][1]

            config_list[0]['api_base'] = f'http://{self.host}:{port}/v1'

        current_config = llm_config.copy()
        current_config.update({
            'config_list': config_list,
            'model': model_name_or_hf_repo,
            'max_tokens': self.max_tokens
        })
        agent = autogen.AssistantAgent(name=agent_name,
                                       llm_config=current_config.copy(),
                                       system_message=system_message)
        self.agent_procs_assign[agent_name] = (agent, server_id)
        return agent

    def clear_agent(
            self,
            agent_name: str = None,
            recycle_endpoint: bool = True
    ):
        """
        Descriptions

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
                self.open_ports.append(server_id.split('_')[-1])

    def clear_all_agents(self):
        """
        Clear all cached agents.
        """
        for agent_name in [agent_name for agent_name in self.agent_procs_assign.keys()]:
            self.clear_agent(agent_name)

    def build(
            self,
            task: str,
            default_llm_config: dict,
            coding: bool = None,
            use_cache: Optional[bool] = True
    ):
        use_api = False
        build_configs = {}

        if use_cache:
            build_configs = self._load_config(task)

        if build_configs == {}:
            use_api = True
        else:
            agent_configs = build_configs['agent_configs']
            coding = build_configs['coding']
            self.manager_system_message = build_configs['manager_system_message']

        config_list = autogen.config_list_from_json(
            self.config_path,
            filter_dict={
                'model': ['gpt-4']
            }
        )
        build_manager = autogen.OpenAIWrapper(config_list=config_list)

        # TODO: use the build manager to decide what agent should be created,
        #  and generate system message for each agent and group chat manager.
        if use_api:
            pass

        agent_configs = [
            {
                'name': 'Coder_gpt_35',
                'model': 'gpt-3.5-turbo',
                'system_message': autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            },
            {
                'name': 'Product_manager',
                'model': 'gpt-3.5-turbo',
                'system_message': autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE
            }
        ]

        for agent_config in agent_configs:
            self.create_agent(agent_config['name'],
                              agent_config['model'],
                              default_llm_config,
                              system_message=agent_config['system_message'])

        if coding is None:
            resp = build_manager.create(
                messages=[{"role": "user", "content": self.CODING_PROMPT.format(task=task)}]
            ).choices[0].message.content
            coding = True if resp == 'YES' else False

        if coding is True:
            self.user_proxy = autogen.UserProxyAgent(
                name="User_proxy",
                system_message="A human admin.",
                code_execution_config={"last_n_messages": 2, "work_dir": "groupchat"},
                human_input_mode="TERMINATE"
            )
        else:
            self.initiate_agent_name = agent_configs[0]['name']

        self.group_chat_manager_config = default_llm_config.copy()
        self.group_chat_manager_config['config_list'] = config_list
        self.manager_system_message = 'Group chat manager.'

        # TODO: save config.
        save_config = {
            'agent_configs': agent_configs,
            'manager_system_message': self.manager_system_message,
            'coding': coding
        }
        self._save_config(task, save_config)

    def _save_config(self, task: str, config: dict):
        filename = hashlib.md5(task.encode('utf-8')).hexdigest()
        json.dump(config, open(f'{self.build_config_path}/{filename}.json', 'w'), indent=4)

    def _load_config(self, task: str):
        filename = hashlib.md5(task.encode('utf-8')).hexdigest()
        filepath = f'{self.build_config_path}/{filename}.json'
        if os.path.isfile(filepath):
            return json.load(open(filepath))
        else:
            return {}

    def start(
            self,
            task: str,
            max_round: Optional[int] = 12,
            init_messages: Optional[List[dict]] = []
    ):
        """
        Descriptions

        Args:
            task: description of a task.
            max_round: the maximum number of rounds.
            init_messages: input messages before the task start. This can be the chat history from other group chat
                or some preliminary of the task.
        """
        agent_list = [agent for agent, _ in self.agent_procs_assign.values()]
        if self.user_proxy is not None:
            agent_list.append(self.user_proxy)
        group_chat = autogen.GroupChat(agents=agent_list, messages=init_messages, max_round=max_round)

        manager = autogen.GroupChatManager(groupchat=group_chat,
                                           llm_config=self.group_chat_manager_config,
                                           system_message=self.manager_system_message)

        if self.initiate_agent_name == "user" and self.user_proxy is not None:
            self.user_proxy.initiate_chat(manager, message=task)
        else:
            for agent in agent_list:
                if self.initiate_agent_name == agent.name():
                    agent.initiate_chat(manager, message=task)


if __name__ == '__main__':
    config_path = '/home/elpis_ubuntu/LLM/autogen/OAI_CONFIG_LIST'
    default_llm_config = {
        'temperature': 0
    }
    task = "Find a latest paper about gpt-4 on arxiv and find its potential applications in software."

    administrator = AgentCreator(
        config_path=config_path
    )
    administrator.build(task, default_llm_config)
    administrator.start(task)
    administrator.clear_all_agents()

