from collections import defaultdict
import openai
import json
import time
import logging

from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import ConversableAgent
from typing import Dict, Optional, Union, List, Tuple, Any

logger = logging.getLogger(__name__)


class GPTAssistantAgent(ConversableAgent):
    """
    An experimental AutoGen agent class that leverages the OpenAI Assistant API for conversational capabilities.
    This agent is unique in its reliance on the OpenAI Assistant for state management, differing from other agents like ConversableAgent.
    """

    def __init__(
        self,
        name="GPT Assistant",
        instructions: Optional[str] = "You are a helpful GPT Assistant.",
        llm_config: Optional[Union[Dict, bool]] = None,
    ):
        """
        Args:
            name (str): name of the agent.
            instructions (str): instructions for the OpenAI assistant configuration.
            llm_config (dict or False): llm inference configuration.
                - model: Model to use for the assistant (gpt-4-1106-preview, gpt-3.5-turbo-1106).
                - check_every_ms: check thread run status interval
                - tools: Give Assistants access to OpenAI-hosted tools like Code Interpreter and Knowledge Retrieval,
                        or build your own tools using Function calling. ref https://platform.openai.com/docs/assistants/tools
                - file_ids: files used by retrieval in run
        """
        super().__init__(
            name=name,
            system_message=instructions,
            human_input_mode="NEVER",
            llm_config=llm_config,
        )

        self._openai_client = openai.OpenAI()
        openai_assistant_id = llm_config.get("assistant_id", None)
        if openai_assistant_id is None:
            # create a new assistant
            self._openai_assistant = self._openai_client.beta.assistants.create(
                name=name,
                instructions=instructions,
                tools=self.llm_config.get("tools", []),
                model=self.llm_config.get("model", "gpt-4-1106-preview"),
            )
        else:
            # retrieve an existing assistant
            self._openai_assistant = self._openai_client.beta.assistants.retrieve(openai_assistant_id)

        # lazly create thread
        self._openai_thread = None
        self._unread_index = defaultdict(int)
        self.register_reply(Agent, GPTAssistantAgent._invoke_assistant)

    def reset(self):
        """
        Resets the agent, clearing any existing conversation thread and unread message indices.
        """
        super().reset()
        if self._openai_thread:
            # Delete the existing thread to start fresh in the next conversation
            self._openai_client.beta.threads.delete(self._openai_thread.id)
            self._openai_thread = None
        # Clear the record of unread messages
        self._unread_index.clear()

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
        if self._openai_thread is None:
            self._openai_thread = self._openai_client.beta.threads.create(
                messages=[],
            )
        # Process each unread message
        for message in pending_messages:
            self._openai_client.beta.threads.messages.create(
                thread_id=self._openai_thread.id,
                content=message["content"],
                role=message["role"],
            )

        # Create a new run to get responses from the assistant
        run = self._openai_client.beta.threads.runs.create(
            thread_id=self._openai_thread.id,
            assistant_id=self._openai_assistant.id,
        )

        run_response_messages = self._get_run_response(run)
        assert len(run_response_messages) > 0, "No response from the assistant."

        response = {
            "role": run_response_messages[-1]["role"],
            "content": "",
        }
        for message in run_response_messages:
            # just logging or do something with the intermediate messages?
            response["content"] = response["content"] + message["content"] + "\n\n"

        self._unread_index[sender] = len(self._oai_messages[sender]) + 1
        return True, response

    def _get_run_response(self, run):
        """
        Waits for and processes the response of a run from the OpenAI assistant.

        Args:
            run: The run object initiated with the OpenAI assistant.

        Returns:
            Updated run object, status of the run, and response messages.
        """
        while True:
            run = self._wait_for_run(run.id, self._openai_thread.id)
            if run.status == "completed":
                response_messages = self._openai_client.beta.threads.messages.list(self._openai_thread.id, order="asc")
                return [
                    {"role": msg.role, "content": self._format_assistant_message(msg.content[0].text)}
                    for msg in response_messages
                    if msg.run_id == run.id
                ]
            elif run.status == "requires_action":
                actions = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    function = tool_call.function
                    is_exec_success, tool_response = self.execute_function(function.dict())
                    tool_response["metadata"] = {
                        "tool_call_id": tool_call.id,
                        "run_id": run.id,
                        "thread_id": self._openai_thread.id,
                    }

                    logger.info(
                        "Intermediate executing(%s, Sucess: %s) : %s",
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
                    "thread_id": self._openai_thread.id,
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
