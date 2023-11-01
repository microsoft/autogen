from void_terminal.toolbox import CatchException, update_ui
from void_terminal.toolbox import get_conf, select_api_key
from void_terminal.toolbox import Singleton
@Singleton
class GradioMultiuserManagerForPersistentClasses():
    def __init__(self):
        self.mapping = {}

    def already_alive(self, key):
        return (key in self.mapping) and (self.mapping[key].is_alive())

    def set(self, key, x):
        self.mapping[key] = x
        return self.mapping[key]

    def get(self, key):
        return self.mapping[key]



def autogen_terminal(txt, llm_kwargs, plugin_kwargs, chatbot, history, system_prompt, web_port, AutoGenFn, Callback):
    """
    txt             Text entered by the user in the input field, for example, a paragraph to be translated or a file path containing files to be processed
    llm_kwargs      Parameters for the gpt model, such as temperature and top_p, typically passed as is
    plugin_kwargs   Parameters for the plugin model
    chatbot         Handle for the chat display box, used to display output to the user
    history         Chat history, context
    system_prompt   Silent reminder for the gpt
    web_port        Port number on which the software is running
    """
    # Check if the current model meets the requirements
    supported_llms = ['gpt-3.5-turbo-16k', 'gpt-4', 'gpt-4-32k', 'azure-gpt-3.5-turbo-16k', 'azure-gpt-4', 'azure-gpt-4-32k']
    llm_kwargs['api_key'] = select_api_key(
        llm_kwargs['api_key'], llm_kwargs['llm_model'])
    if llm_kwargs['llm_model'] not in supported_llms:
        chatbot.append(
            [f"Task: {txt}", f"The current plugin only supports {str(supported_llms)}, current model: {llm_kwargs['llm_model']}."])
        yield from update_ui(chatbot=chatbot, history=history)
        return

    # Check if the current model meets the requirements
    API_URL_REDIRECT = get_conf('API_URL_REDIRECT')
    if len(API_URL_REDIRECT) > 0:
        chatbot.append([f"Task: {txt}", f"Transfers are not supported."])
        yield from update_ui(chatbot=chatbot, history=history)
        return

    # Try to import dependencies, if any are missing, provide installation suggestions
    try:
        import autogen
        if get_conf('AUTOGEN_USE_DOCKER'): import docker
    except:
        chatbot.append([f"Task: {txt}",
                        f"Failed to import software dependencies. Additional dependencies are required to use this module, install with `pip install --upgrade pyautogen docker`."])
        yield from update_ui(chatbot=chatbot, history=history)
        return

    # Try to import dependencies, if any are missing, provide installation suggestions
    try:
        import autogen
        import glob
        import os
        import time
        import subprocess
        if get_conf('AUTOGEN_USE_DOCKER'): subprocess.Popen(['docker', '--version'])
    except:
        chatbot.append([f"Task: {txt}", f"Missing docker runtime environment!"])
        yield from update_ui(chatbot=chatbot, history=history)
        return

    # Unlock the plugin
    chatbot.get_cookies()['lock_plugin'] = None
    persistent_class_multi_user_manager = GradioMultiuserManagerForPersistentClasses()
    user_uuid = chatbot.get_cookies().get('uuid')
    persistent_key = f"{user_uuid}->autogen"
    if persistent_class_multi_user_manager.already_alive(persistent_key):
        # If there is already a running autogen_terminal, pass the user input to it instead of starting a new one
        print('[debug] feed new user input')
        executor = persistent_class_multi_user_manager.get(persistent_key)
        exit_reason = yield from executor.main_process_ui_control(txt, create_or_resume="resume")
    else:
        # Run autogen_terminal (first time)
        print('[debug] create new executor instance')
        history = []
        chatbot.append(["Starting: autogen_terminal",
                       "Dynamic plugin generation, execution started, authors: Microsoft & Binary-Husky."])
        yield from update_ui(chatbot=chatbot, history=history)
        executor = AutoGenFn(llm_kwargs, plugin_kwargs,
                               chatbot, history, system_prompt, web_port)
        persistent_class_multi_user_manager.set(persistent_key, executor)
        exit_reason = yield from executor.main_process_ui_control(txt, create_or_resume="create")

    if exit_reason == "wait_feedback":
        # When the user clicks the "Wait for Feedback" button, store the executor in the cookie, waiting for the user to call it again
        executor.chatbot.get_cookies()['lock_plugin'] = Callback
    else:
        executor.chatbot.get_cookies()['lock_plugin'] = None
    # Update the state
    yield from update_ui(chatbot=executor.chatbot, history=executor.history)