import autogen
from autogen import Agent

from utils.code_utils import utils_2_prompt, extract_code_result
from raworkflow.raworkflow_helper import custom_printer, print_messages
from raworkflow.raworkflow import RAWorkflow


class TwoAgentWorkflow(RAWorkflow):
    def define_agents(self):
        trigger_execution = self.ra_config["trigger_execution"]
        personalization_profile = self.ra_config["personalization_profile"]
        human_input_mode = "NEVER" if trigger_execution else "ALWAYS"

        self.human_input_mode = human_input_mode

        # define user proxy agent in ALWAYS mode
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode=human_input_mode,
            code_execution_config={
                "work_dir": self.work_dir,
                "use_docker": False,
            },
            max_consecutive_auto_reply=10,
        )

        self.user_proxy._print_received_message = custom_printer

        self.user_proxy.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

        # Only add the personalization to the non-coding tasks
        personalization_suffix = ""
        if trigger_execution is False and not (personalization_profile is None or personalization_profile == ""):
            personalization_suffix = f"""

As you are working to fulfil the user's requests, please quietly and carefully think about their interests and
their preferences, as inferred from their biography below, then craft your responses to align with this information.

<biography>
{personalization_profile}
</biography>

"""

        prompt_suffix = utils_2_prompt(self.utils_dir)
        self.primary_assistant = autogen.AssistantAgent(
            name="primary_assitant",
            system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE + prompt_suffix + personalization_suffix,
            llm_config=self.llm_config,
        )

        self.primary_assistant._print_received_message = custom_printer

        self.primary_assistant.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

    def _populate_chat_history(self, history_messages):
        """
        Populate the chat history of the agents with the messages from the history.
        """
        for msg in history_messages:
            if msg["role"] == "user":
                self.user_proxy.send(
                    msg["content"],
                    self.primary_assistant,
                    request_reply=False,
                    silent=self.silent,
                )
            elif msg["role"] == "assistant":
                self.primary_assistant.send(
                    msg["content"],
                    self.user_proxy,
                    request_reply=False,
                    silent=self.silent,
                )

    def generate_response(self, message, history_messages):
        """
        Checks if the trigger_execution is True, and if it is, then
        sends the last assistant message to the user proxy agent.
        Else populates the entire history and requests a response from
        from the primary assistant.

        Args:
            message (str): the message from the user
            history_messages (List[Dict]): the list of messages in the chat history

        Returns:
            a tuple of (response, code)
        """

        if self.ra_config["trigger_execution"] is True and len(history_messages) > 0:
            # if the trigger execution is True, then send the last assistant message
            # to the user proxy agent
            assert history_messages[-1]["role"] == "assistant"

            self._populate_chat_history(history_messages[:-1])
            last_assistant_message = history_messages[-1]["content"]

            self.primary_assistant.initiate_chat(
                self.user_proxy,
                message=last_assistant_message,
                clear_history=False,
                silent=self.silent,
            )

            final_code, result = extract_code_result(self.primary_assistant.chat_messages[self.user_proxy])
            return result, final_code
        else:
            # Populate the entire history and request a response from
            # from the primary assistant
            self._populate_chat_history(history_messages)
            self.user_proxy.send(
                message,
                self.primary_assistant,
                request_reply=True,
                silent=self.silent,
            )
            return self.user_proxy.last_message()["content"], None
