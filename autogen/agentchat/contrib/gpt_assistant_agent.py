import copy
import json
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

from autogen import OpenAIWrapper
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import AssistantAgent, ConversableAgent
from autogen.oai.openai_utils import create_gpt_assistant, retrieve_assistants_by_name, update_gpt_assistant
from autogen.runtime_logging import log_new_agent, logging_enabled

logger = logging.getLogger(__name__)


class GPTAssistantAgent(ConversableAgent):
    """
    An experimental AutoGen agent class that leverages the OpenAI Assistant API for conversational capabilities.
    This agent is unique in its reliance on the OpenAI Assistant for state management, differing from other agents like ConversableAgent.
    """

    DEFAULT_MODEL_NAME = "gpt-4-0125-preview"

    def __init__(
        self,
        name="GPT Assistant",
        instructions: Optional[str] = None,
        llm_config: Optional[Union[Dict, bool]] = None,
        assistant_config: Optional[Dict] = None,
        overwrite_instructions: bool = False,
        overwrite_tools: bool = False,
        **kwargs,
    ):
        """
        Args:
            name (str): name of the agent. It will be used to find the existing assistant by name. Please remember to delete an old assistant with the same name if you intend to create a new assistant with the same name.
            instructions (str): instructions for the OpenAI assistant configuration.
            When instructions is not None, the system message of the agent will be
            set to the provided instructions and used in the assistant run, irrespective
            of the overwrite_instructions flag. But when instructions is None,
            and the assistant does not exist, the system message will be set to
            AssistantAgent.DEFAULT_SYSTEM_MESSAGE. If the assistant exists, the
            system message will be set to the existing assistant instructions.
            llm_config (dict or False): llm inference configuration.
                - model: Model to use for the assistant (gpt-4-1106-preview, gpt-3.5-turbo-1106).
            assistant_config
                - assistant_id: ID of the assistant to use. If None, a new assistant will be created.
                - check_every_ms: check thread run status interval
                - tools: Give Assistants access to OpenAI-hosted tools like Code Interpreter and Knowledge Retrieval,
                        or build your own tools using Function calling. ref https://platform.openai.com/docs/assistants/tools
                - file_ids: (Deprecated) files used by retrieval in run. It is Deprecated, use tool_resources instead. https://platform.openai.com/docs/assistants/migration/what-has-changed.
                - tool_resources: A set of resources that are used by the assistant's tools. The resources are specific to the type of tool.
            overwrite_instructions (bool): whether to overwrite the instructions of an existing assistant. This parameter is in effect only when assistant_id is specified in llm_config.
            overwrite_tools (bool): whether to overwrite the tools of an existing assistant. This parameter is in effect only when assistant_id is specified in llm_config.
            kwargs (dict): Additional configuration options for the agent.
                - verbose (bool): If set to True, enables more detailed output from the assistant thread.
                - Other kwargs: Except verbose, others are passed directly to ConversableAgent.
        """

        self._verbose = kwargs.pop("verbose", False)
        openai_client_cfg, openai_assistant_cfg = self._process_assistant_config(llm_config, assistant_config)

        super().__init__(
            name=name, system_message=instructions, human_input_mode="NEVER", llm_config=openai_client_cfg, **kwargs
        )
        if logging_enabled():
            log_new_agent(self, locals())

        # GPTAssistantAgent's azure_deployment param may cause NotFoundError (404) in client.beta.assistants.list()
        # See: https://github.com/microsoft/autogen/pull/1721
        model_name = self.DEFAULT_MODEL_NAME
        if openai_client_cfg.get("config_list") is not None and len(openai_client_cfg["config_list"]) > 0:
            model_name = openai_client_cfg["config_list"][0].pop("model", self.DEFAULT_MODEL_NAME)
        else:
            model_name = openai_client_cfg.pop("model", self.DEFAULT_MODEL_NAME)

        logger.warning("OpenAI client config of GPTAssistantAgent(%s) - model: %s", name, model_name)

        oai_wrapper = OpenAIWrapper(**openai_client_cfg)
        if len(oai_wrapper._clients) > 1:
            logger.warning("GPT Assistant only supports one OpenAI client. Using the first client in the list.")

        self._openai_client = oai_wrapper._clients[0]._oai_client
        openai_assistant_id = openai_assistant_cfg.get("assistant_id", None)
        if openai_assistant_id is None:
            # try to find assistant by name first
            candidate_assistants = retrieve_assistants_by_name(self._openai_client, name)
            if len(candidate_assistants) > 0:
                # Filter out candidates with the same name but different instructions, file IDs, and function names.
                candidate_assistants = self.find_matching_assistant(
                    candidate_assistants,
                    instructions,
                    openai_assistant_cfg.get("tools", []),
                )

            if len(candidate_assistants) == 0:
                logger.warning("No matching assistant found, creating a new assistant")
                # create a new assistant
                if instructions is None:
                    logger.warning(
                        "No instructions were provided for new assistant. Using default instructions from AssistantAgent.DEFAULT_SYSTEM_MESSAGE."
                    )
                    instructions = AssistantAgent.DEFAULT_SYSTEM_MESSAGE
                self._openai_assistant = create_gpt_assistant(
                    self._openai_client,
                    name=name,
                    instructions=instructions,
                    model=model_name,
                    assistant_config=openai_assistant_cfg,
                )
            else:
                logger.warning(
                    "Matching assistant found, using the first matching assistant: %s",
                    candidate_assistants[0].__dict__,
                )
                self._openai_assistant = candidate_assistants[0]
        else:
            # retrieve an existing assistant
            self._openai_assistant = self._openai_client.beta.assistants.retrieve(openai_assistant_id)
            # if no instructions are provided, set the instructions to the existing instructions
            if instructions is None:
                logger.warning(
                    "No instructions were provided for given assistant. Using existing instructions from assistant API."
                )
                instructions = self.get_assistant_instructions()
            elif overwrite_instructions is True:
                logger.warning(
                    "overwrite_instructions is True. Provided instructions will be used and will modify the assistant in the API"
                )
                self._openai_assistant = update_gpt_assistant(
                    self._openai_client,
                    assistant_id=openai_assistant_id,
                    assistant_config={
                        "instructions": instructions,
                    },
                )
            else:
                logger.warning(
                    "overwrite_instructions is False. Provided instructions will be used without permanently modifying the assistant in the API."
                )

            # Check if tools are specified in assistant_config
            specified_tools = openai_assistant_cfg.get("tools", None)

            if specified_tools is None:
                # Check if the current assistant has tools defined
                if self._openai_assistant.tools:
                    logger.warning(
                        "No tools were provided for given assistant. Using existing tools from assistant API."
                    )
                else:
                    logger.info(
                        "No tools were provided for the assistant, and the assistant currently has no tools set."
                    )
            elif overwrite_tools is True:
                # Tools are specified and overwrite_tools is True; update the assistant's tools
                logger.warning(
                    "overwrite_tools is True. Provided tools will be used and will modify the assistant in the API"
                )
                self._openai_assistant = update_gpt_assistant(
                    self._openai_client,
                    assistant_id=openai_assistant_id,
                    assistant_config={
                        "tools": specified_tools,
                        "tool_resources": openai_assistant_cfg.get("tool_resources", None),
                    },
                )
            else:
                # Tools are specified but overwrite_tools is False; do not update the assistant's tools
                logger.warning("overwrite_tools is False. Using existing tools from assistant API.")

        self.update_system_message(self._openai_assistant.instructions)
        # lazily create threads
        self._openai_threads = {}
        self._unread_index = defaultdict(int)
        self.register_reply([Agent, None], GPTAssistantAgent._invoke_assistant, position=2)

    def _invoke_assistant(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """
        Invokes the OpenAI assistant to generate a reply based on the given messages.

        Args:
            messages: A list of messages in the conversation history with the sender.
            sender: The agent instance that sent the message.
            config: Optional configuration for message processing.

        Returns:
            A tuple containing a boolean indicating success and the assistant's reply.
        """

        if messages is None:
            messages = self._oai_messages[sender]
        unread_index = self._unread_index[sender] or 0
        pending_messages = messages[unread_index:]

        # Check and initiate a new thread if necessary
        if self._openai_threads.get(sender, None) is None:
            self._openai_threads[sender] = self._openai_client.beta.threads.create(
                messages=[],
            )
        assistant_thread = self._openai_threads[sender]
        # Process each unread message
        for message in pending_messages:
            if message["content"].strip() == "":
                continue
            self._openai_client.beta.threads.messages.create(
                thread_id=assistant_thread.id,
                content=message["content"],
                role=message["role"],
            )

        # Create a new run to get responses from the assistant
        run = self._openai_client.beta.threads.runs.create(
            thread_id=assistant_thread.id,
            assistant_id=self._openai_assistant.id,
            # pass the latest system message as instructions
            instructions=self.system_message,
        )

        run_response_messages = self._get_run_response(assistant_thread, run)
        assert len(run_response_messages) > 0, "No response from the assistant."

        response = {
            "role": run_response_messages[-1]["role"],
            "content": "",
        }
        for message in run_response_messages:
            # just logging or do something with the intermediate messages?
            # if current response is not empty and there is more, append new lines
            if len(response["content"]) > 0:
                response["content"] += "\n\n"
            response["content"] += message["content"]

        self._unread_index[sender] = len(self._oai_messages[sender]) + 1
        return True, response

    def _get_run_response(self, thread, run):
        """
        Waits for and processes the response of a run from the OpenAI assistant.

        Args:
            run: The run object initiated with the OpenAI assistant.

        Returns:
            Updated run object, status of the run, and response messages.
        """
        while True:
            run = self._wait_for_run(run.id, thread.id)
            if run.status == "completed":
                response_messages = self._openai_client.beta.threads.messages.list(thread.id, order="asc")

                new_messages = []
                for msg in response_messages:
                    if msg.run_id == run.id:
                        for content in msg.content:
                            if content.type == "text":
                                new_messages.append(
                                    {"role": msg.role, "content": self._format_assistant_message(content.text)}
                                )
                            elif content.type == "image_file":
                                new_messages.append(
                                    {
                                        "role": msg.role,
                                        "content": f"Received file id={content.image_file.file_id}",
                                    }
                                )
                return new_messages
            elif run.status == "requires_action":
                actions = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function = tool_call.function
                    is_exec_success, tool_response = self.execute_function(function.dict(), self._verbose)
                    tool_response["metadata"] = {
                        "tool_call_id": tool_call.id,
                        "run_id": run.id,
                        "thread_id": thread.id,
                    }

                    logger.info(
                        "Intermediate executing(%s, Success: %s) : %s",
                        tool_response["name"],
                        is_exec_success,
                        tool_response["content"],
                    )
                    actions.append(tool_response)

                submit_tool_outputs = {
                    "tool_outputs": [
                        {"output": action["content"], "tool_call_id": action["metadata"]["tool_call_id"]}
                        for action in actions
                    ],
                    "run_id": run.id,
                    "thread_id": thread.id,
                }

                run = self._openai_client.beta.threads.runs.submit_tool_outputs(**submit_tool_outputs)
            else:
                run_info = json.dumps(run.dict(), indent=2)
                raise ValueError(f"Unexpected run status: {run.status}. Full run info:\n\n{run_info})")

    def _wait_for_run(self, run_id: str, thread_id: str) -> Any:
        """
        Waits for a run to complete or reach a final state.

        Args:
            run_id: The ID of the run.
            thread_id: The ID of the thread associated with the run.

        Returns:
            The updated run object after completion or reaching a final state.
        """
        in_progress = True
        while in_progress:
            run = self._openai_client.beta.threads.runs.retrieve(run_id, thread_id=thread_id)
            in_progress = run.status in ("in_progress", "queued")
            if in_progress:
                time.sleep(self.llm_config.get("check_every_ms", 1000) / 1000)
        return run

    def _format_assistant_message(self, message_content):
        """
        Formats the assistant's message to include annotations and citations.
        """

        annotations = message_content.annotations
        citations = []

        # Iterate over the annotations and add footnotes
        for index, annotation in enumerate(annotations):
            # Replace the text with a footnote
            message_content.value = message_content.value.replace(annotation.text, f" [{index}]")

            # Gather citations based on annotation attributes
            if file_citation := getattr(annotation, "file_citation", None):
                try:
                    cited_file = self._openai_client.files.retrieve(file_citation.file_id)
                    citations.append(f"[{index}] {cited_file.filename}: {file_citation.quote}")
                except Exception as e:
                    logger.error(f"Error retrieving file citation: {e}")
            elif file_path := getattr(annotation, "file_path", None):
                try:
                    cited_file = self._openai_client.files.retrieve(file_path.file_id)
                    citations.append(f"[{index}] Click <here> to download {cited_file.filename}")
                except Exception as e:
                    logger.error(f"Error retrieving file citation: {e}")
                # Note: File download functionality not implemented above for brevity

        # Add footnotes to the end of the message before displaying to user
        message_content.value += "\n" + "\n".join(citations)
        return message_content.value

    def can_execute_function(self, name: str) -> bool:
        """Whether the agent can execute the function."""
        return False

    def reset(self):
        """
        Resets the agent, clearing any existing conversation thread and unread message indices.
        """
        super().reset()
        for thread in self._openai_threads.values():
            # Delete the existing thread to start fresh in the next conversation
            self._openai_client.beta.threads.delete(thread.id)
        self._openai_threads = {}
        # Clear the record of unread messages
        self._unread_index.clear()

    def clear_history(self, agent: Optional[Agent] = None):
        """Clear the chat history of the agent.

        Args:
            agent: the agent with whom the chat history to clear. If None, clear the chat history with all agents.
        """
        super().clear_history(agent)
        if self._openai_threads.get(agent, None) is not None:
            # Delete the existing thread to start fresh in the next conversation
            thread = self._openai_threads[agent]
            logger.info("Clearing thread %s", thread.id)
            self._openai_client.beta.threads.delete(thread.id)
            self._openai_threads.pop(agent)
            self._unread_index[agent] = 0

    def pretty_print_thread(self, thread):
        """Pretty print the thread."""
        if thread is None:
            print("No thread to print")
            return
        # NOTE: that list may not be in order, sorting by created_at is important
        messages = self._openai_client.beta.threads.messages.list(
            thread_id=thread.id,
        )
        messages = sorted(messages.data, key=lambda x: x.created_at)
        print("~~~~~~~THREAD CONTENTS~~~~~~~")
        for message in messages:
            content_types = [content.type for content in message.content]
            print(f"[{message.created_at}]", message.role, ": [", ", ".join(content_types), "]")
            for content in message.content:
                content_type = content.type
                if content_type == "text":
                    print(content.type, ": ", content.text.value)
                elif content_type == "image_file":
                    print(content.type, ": ", content.image_file.file_id)
                else:
                    print(content.type, ": ", content)
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    @property
    def oai_threads(self) -> Dict[Agent, Any]:
        """Return the threads of the agent."""
        return self._openai_threads

    @property
    def assistant_id(self):
        """Return the assistant id"""
        return self._openai_assistant.id

    @property
    def openai_client(self):
        return self._openai_client

    @property
    def openai_assistant(self):
        return self._openai_assistant

    def get_assistant_instructions(self):
        """Return the assistant instructions from OAI assistant API"""
        return self._openai_assistant.instructions

    def delete_assistant(self):
        """Delete the assistant from OAI assistant API"""
        logger.warning("Permanently deleting assistant...")
        self._openai_client.beta.assistants.delete(self.assistant_id)

    def find_matching_assistant(self, candidate_assistants, instructions, tools):
        """
        Find the matching assistant from a list of candidate assistants.
        Filter out candidates with the same name but different instructions, and function names.
        """
        matching_assistants = []

        # Preprocess the required tools for faster comparison
        required_tool_types = set(
            "file_search" if tool.get("type") in ["retrieval", "file_search"] else tool.get("type") for tool in tools
        )

        required_function_names = set(
            tool.get("function", {}).get("name")
            for tool in tools
            if tool.get("type") not in ["code_interpreter", "retrieval", "file_search"]
        )

        for assistant in candidate_assistants:
            # Check if instructions are similar
            if instructions and instructions != getattr(assistant, "instructions", None):
                logger.warning(
                    "instructions not match, skip assistant(%s): %s",
                    assistant.id,
                    getattr(assistant, "instructions", None),
                )
                continue

            # Preprocess the assistant's tools
            assistant_tool_types = set(
                "file_search" if tool.type in ["retrieval", "file_search"] else tool.type for tool in assistant.tools
            )
            assistant_function_names = set(tool.function.name for tool in assistant.tools if hasattr(tool, "function"))

            # Check if the tool types, function names match
            if required_tool_types != assistant_tool_types or required_function_names != assistant_function_names:
                logger.warning(
                    "tools not match, skip assistant(%s): tools %s, functions %s",
                    assistant.id,
                    assistant_tool_types,
                    assistant_function_names,
                )
                continue

            # Append assistant to matching list if all conditions are met
            matching_assistants.append(assistant)

        return matching_assistants

    def _process_assistant_config(self, llm_config, assistant_config):
        """
        Process the llm_config and assistant_config to extract the model name and assistant related configurations.
        """

        if llm_config is False:
            raise ValueError("llm_config=False is not supported for GPTAssistantAgent.")

        if llm_config is None:
            openai_client_cfg = {}
        else:
            openai_client_cfg = copy.deepcopy(llm_config)

        if assistant_config is None:
            openai_assistant_cfg = {}
        else:
            openai_assistant_cfg = copy.deepcopy(assistant_config)

        # Move the assistant related configurations to assistant_config
        # It's important to keep forward compatibility
        assistant_config_items = ["assistant_id", "tools", "file_ids", "tool_resources", "check_every_ms"]
        for item in assistant_config_items:
            if openai_client_cfg.get(item) is not None and openai_assistant_cfg.get(item) is None:
                openai_assistant_cfg[item] = openai_client_cfg[item]
            openai_client_cfg.pop(item, None)

        return openai_client_cfg, openai_assistant_cfg
