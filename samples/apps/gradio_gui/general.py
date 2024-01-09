from void_terminal.toolbox import trimmed_format_exc, ProxyNetworkActivate
from samples.apps.gradio_gui.pipe import PluginMultiprocessManager, PipeCom
from autogen import Agent
from multiprocessing import Pipe
import time


class AutoGenGeneral(PluginMultiprocessManager):
    """This AutoGenGeneral class is for managing AutoGen functionality (inherit from PluginMultiprocessManager).

    gpt_academic_print_override: Override the print function for autogen.
    gpt_academic_get_human_input: Override the get_human_input function for autogen.
    define_agents: Define agents for autogen.
    exe_autogen: Execute autogen.
    subprocess_worker: initialize subprocess worker.

    """

    def gpt_academic_print_override(self, user_proxy: Agent, message: str, sender: Agent):
        # ⭐⭐ run in subprocess
        self.child_conn.send(PipeCom("show", sender.name + "\n\n---\n\n" + message["content"]))

    def gpt_academic_get_human_input(self, user_proxy: Agent, message: str):
        # ⭐⭐ run in subprocess
        patience = 300
        begin_waiting_time = time.time()
        self.child_conn.send(PipeCom("interact", message))
        while True:
            time.sleep(0.5)
            if self.child_conn.poll():
                wait_success = True
                break
            if time.time() - begin_waiting_time > patience:
                self.child_conn.send(PipeCom("done", ""))
                wait_success = False
                break
        if wait_success:
            return self.child_conn.recv().content
        else:
            raise TimeoutError("waiting user input timeout")

    def define_agents(self):
        raise NotImplementedError

    def exe_autogen(self, input: PipeCom):
        # ⭐⭐ run in subprocess
        input = input.content
        with ProxyNetworkActivate("AutoGen"):
            code_execution_config = {"work_dir": self.autogen_work_dir, "use_docker": self.use_docker}
            agents = self.define_agents()
            user_proxy = None
            assistant = None
            for agent_kwargs in agents:
                agent_cls = agent_kwargs.pop("cls")
                kwargs = {"code_execution_config": code_execution_config}
                kwargs.update(agent_kwargs)
                agent_handle = agent_cls(**kwargs)
                agent_handle._print_received_message = lambda a, b: self.gpt_academic_print_override(agent_kwargs, a, b)
                if agent_kwargs["name"] == "user_proxy":
                    agent_handle.get_human_input = lambda a: self.gpt_academic_get_human_input(user_proxy, a)
                    user_proxy = agent_handle
                if agent_kwargs["name"] == "assistant":
                    assistant = agent_handle
            try:
                if user_proxy is None or assistant is None:
                    raise Exception("user_proxy or assistant is not defined")
                user_proxy.initiate_chat(assistant, message=input)
            except Exception:
                tb_str = "```\n" + trimmed_format_exc() + "```"
                self.child_conn.send(PipeCom("done", "AutoGen exe failed: \n\n" + tb_str))

    def subprocess_worker(self, child_conn: Pipe):
        # ⭐⭐ run in subprocess
        self.child_conn = child_conn
        while True:
            msg = self.child_conn.recv()  # PipeCom
            self.exe_autogen(msg)


class AutoGenGroupChat(AutoGenGeneral):
    """
    This class defines `exe_autogen` for GroupChat functionality. (while inherit from AutoGenGeneral above).

    Raises:
        Exception: If user_proxy is not defined.

    Returns:
        None
    """

    def exe_autogen(self, input: str):
        # ⭐⭐ run in subprocess
        import autogen
        from void_terminal.toolbox import trimmed_format_exc, ProxyNetworkActivate
        from samples.apps.gradio_gui.pipe import PipeCom

        input = input.content
        with ProxyNetworkActivate("AutoGen"):
            code_execution_config = {"work_dir": self.autogen_work_dir, "use_docker": self.use_docker}
            agents = self.define_agents()
            agents_instances = []
            for agent_kwargs in agents:
                agent_cls = agent_kwargs.pop("cls")
                kwargs = {"code_execution_config": code_execution_config}
                kwargs.update(agent_kwargs)
                agent_handle = agent_cls(**kwargs)
                agent_handle._print_received_message = lambda a, b: self.gpt_academic_print_override(agent_kwargs, a, b)
                agents_instances.append(agent_handle)
                if agent_kwargs["name"] == "user_proxy":
                    user_proxy = agent_handle
                    user_proxy.get_human_input = lambda a: self.gpt_academic_get_human_input(user_proxy, a)
            try:
                groupchat = autogen.GroupChat(agents=agents_instances, messages=[], max_round=50)
                manager = autogen.GroupChatManager(groupchat=groupchat, **self.define_group_chat_manager_config())
                manager._print_received_message = lambda a, b: self.gpt_academic_print_override(agent_kwargs, a, b)
                manager.get_human_input = lambda a: self.gpt_academic_get_human_input(manager, a)
                if user_proxy is None:
                    raise Exception("user_proxy is not defined")
                user_proxy.initiate_chat(manager, message=input)
            except Exception:
                tb_str = "```\n" + trimmed_format_exc() + "```"
                self.child_conn.send(PipeCom("done", "AutoGen exe failed: \n\n" + tb_str))

    def define_group_chat_manager_config(self):
        raise NotImplementedError
