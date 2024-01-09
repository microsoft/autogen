from void_terminal.toolbox import get_log_folder
from void_terminal.toolbox import update_ui
from void_terminal.toolbox import gen_time_str
from void_terminal.toolbox import get_conf
from void_terminal.toolbox import promote_file_to_downloadzone
from void_terminal.toolbox import ChatBotWithCookies
from void_terminal.crazy_functions.agent_fns.watchdog import WatchDog
import time
import os


class PipeCom:
    """
    Represents a command and content for piped communication.

    Args:
        cmd (str): The command to be executed.
        content (str): The content to be passed to the command.

    Attributes:
        cmd (str): The command to be executed.
        content (str): The content to be passed to the command.
    """

    def __init__(self, cmd, content) -> None:
        self.cmd = cmd
        self.content = content


class PluginMultiprocessManager:
    """A class for managing and controlling subprocesses through inter-process communication.
    ⭐ Please keep in mind that some of the class method runs in subprocess, which is distinguished by method comments.
       - (⭐ run in main process) means a method runs in main process.
       - (⭐⭐ run in subprocess) means a method runs in subprocess.
    Additionally, heartbeat_watchdog is a watch dog that kill the instance when user leaving the web page for a long time.

    Attributes:
        llm_kwargs (dict): The keyword arguments for llm.
        plugin_kwargs (dict): The keyword arguments for the plugin.
        chatbot (Chatbot): The chatbot instance.
        history (History): The history instance.
        system_prompt (Prompt): The system prompt instance.
        web_port (int): The web port number for communication.

    """

    def __init__(
        self,
        llm_kwargs: dict,
        plugin_kwargs: dict,
        chatbot: ChatBotWithCookies,
        history: list,
        system_prompt: str,
        web_port,
    ):
        # ⭐ run in main process
        self.autogen_work_dir = os.path.join(get_log_folder("autogen"), gen_time_str())
        self.previous_work_dir_files = {}
        self.plugin_kwargs = plugin_kwargs
        self.chatbot = chatbot
        self.history = history
        self.system_prompt = system_prompt
        # self.web_port = web_port
        self.alive = True
        self.use_docker = get_conf("AUTOGEN_USE_DOCKER")

        # create a thread to monitor self.heartbeat, terminate the instance if no heartbeat for a long time
        timeout_seconds = 5 * 60
        self.heartbeat_watchdog = WatchDog(timeout=timeout_seconds, bark_fn=self.terminate, interval=5)
        self.heartbeat_watchdog.begin_watch()

    def feed_heartbeat_watchdog(self):
        # feed this `dog`, so the dog will not `bark` (bark_fn will terminate the instance)
        self.heartbeat_watchdog.feed()

    def is_alive(self):
        return self.alive

    def launch_subprocess_with_pipe(self):
        # ⭐ run in main process
        from multiprocessing import Process, Pipe

        parent_conn, child_conn = Pipe()
        self.p = Process(target=self.subprocess_worker, args=(child_conn,))
        self.p.daemon = True
        self.p.start()
        return parent_conn

    def terminate(self):
        self.p.terminate()
        self.alive = False
        print("[debug] instance terminated")

    def subprocess_worker(self, child_conn):
        # ⭐⭐ run in subprocess
        raise NotImplementedError

    def send_command(self, cmd):
        # ⭐ run in main process
        self.parent_conn.send(PipeCom("user_input", cmd))

    def immediate_showoff_when_possible(self, fp: str):
        # ⭐ run in main process
        # get the extension name of file fp
        file_type = fp.split(".")[-1]
        # if jpg or png, show the image in the chatbot
        if file_type.lower() in ["png", "jpg"]:
            image_path = os.path.abspath(fp)
            self.chatbot.append(
                [
                    "new image file detected and can be displayed:",
                    f'image preview: <br/><div align="center"><img src="file={image_path}"></div>',
                ]
            )
            yield from update_ui(chatbot=self.chatbot, history=self.history)

    def overwatch_workdir_file_change(self):
        # ⭐ run in main process Docker
        # monitor docker container's workdir, if there is any new file, or any file's last_modified_time
        path_to_overwatch = self.autogen_work_dir
        change_list = []
        for root, dirs, files in os.walk(path_to_overwatch):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path not in self.previous_work_dir_files.keys():
                    last_modified_time = os.stat(file_path).st_mtime
                    self.previous_work_dir_files.update({file_path: last_modified_time})
                    change_list.append(file_path)
                else:
                    last_modified_time = os.stat(file_path).st_mtime
                    if last_modified_time != self.previous_work_dir_files[file_path]:
                        self.previous_work_dir_files[file_path] = last_modified_time
                        change_list.append(file_path)
        if len(change_list) > 0:
            file_links = ""
            for f in change_list:
                res = promote_file_to_downloadzone(f)
                file_links += f'<br/><a href="file={res}" target="_blank">{res}</a>'
                yield from self.immediate_showoff_when_possible(f)

            self.chatbot.append(["detected new files generated.", f"new file manifest: {file_links}"])
            yield from update_ui(chatbot=self.chatbot, history=self.history)
        return change_list

    def main_process_ui_control(self, txt: str, create_or_resume: str) -> str:
        # ⭐ run in main process
        if create_or_resume == "create":
            self.cnt = 1
            self.parent_conn = self.launch_subprocess_with_pipe()  # ⭐⭐⭐
        else:
            if "Waiting for further instructions." in self.chatbot[-1][-1]:
                self.chatbot.pop(-1)  # remove the last line
        self.send_command(txt)

        if txt == "exit":
            self.chatbot.append(
                ["terminate", "the termination signal from user is accepted, terminate autogen plugin."]
            )
            yield from update_ui(chatbot=self.chatbot, history=self.history)
            self.terminate()
            return "terminate"

        while True:
            time.sleep(0.5)
            if self.parent_conn.poll():
                if "[GPT-Academic] waiting" in self.chatbot[-1][-1]:
                    self.chatbot.pop(-1)  # remove the last line
                if "Waiting for further instructions." in self.chatbot[-1][-1]:
                    self.chatbot.pop(-1)  # remove the last line
                msg = self.parent_conn.recv()  # PipeCom
                if msg.cmd == "done":
                    self.chatbot.append(["terminate", msg.content])
                    self.cnt += 1
                    yield from update_ui(chatbot=self.chatbot, history=self.history)
                    self.terminate()
                    break
                if msg.cmd == "show":
                    yield from self.overwatch_workdir_file_change()
                    self.chatbot.append([f"autogen phase-{self.cnt}", msg.content])
                    self.cnt += 1
                    yield from update_ui(chatbot=self.chatbot, history=self.history)
                if msg.cmd == "interact":
                    yield from self.overwatch_workdir_file_change()
                    self.chatbot.append(
                        [
                            "Program has reached the user feedback node.",
                            msg.content
                            + "\n\nWaiting for further instructions."
                            + "\n\n(1) In general, you don't need to say anything, clear the input area, and then click 'Submit' to continue."
                            + "\n\n(2) If you need to add something, enter the content you want to provide, and then click 'Submit' to continue."
                            + "\n\n(3) If you want to terminate the program, enter 'exit' and click 'Submit' to terminate AutoGen and unlock.",
                        ]
                    )
                    yield from update_ui(chatbot=self.chatbot, history=self.history)
                    # do not terminate here, leave the subprocess_worker instance alive
                    return "wait_feedback"
            else:
                if "[GPT-Academic] waiting" not in self.chatbot[-1][-1]:
                    self.chatbot.append(
                        ["[GPT-Academic] waiting for AutoGen execution results...", "[GPT-Academic] waiting"]
                    )
                self.chatbot[-1] = [
                    self.chatbot[-1][0],
                    self.chatbot[-1][1].replace("[GPT-Academic] waiting", "[GPT-Academic] waiting."),
                ]
                yield from update_ui(chatbot=self.chatbot, history=self.history)

        self.terminate()
        return "terminate"

    def subprocess_worker_wait_user_feedback(self, wait_msg="wait user feedback"):
        # ⭐⭐ run in subprocess
        patience = 5 * 60
        begin_waiting_time = time.time()
        self.child_conn.send(PipeCom("interact", wait_msg))
        while True:
            time.sleep(0.5)
            if self.child_conn.poll():
                wait_success = True
                break
            if time.time() - begin_waiting_time > patience:
                self.child_conn.send(PipeCom("done", ""))
                wait_success = False
                break
        return wait_success
