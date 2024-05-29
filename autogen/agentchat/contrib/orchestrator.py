# ruff: noqa: E722
import json
import traceback
import copy
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, GroupChatManager, GroupChat, OpenAIWrapper
from autogen.code_utils import extract_code, content_str


class Orchestrator(ConversableAgent):
    def __init__(
        self,
        name: str,
        agents: List[ConversableAgent] = [],
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Union[Dict, Literal[False]] = False,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        response_format_is_supported: bool = True,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        max_images: int = 1,
    ):
        super().__init__(
            name=name,
            system_message="",
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
        )

        self.max_images = max_images
        self._temperature_bonus = 0.0
        self._agents = agents
        self.response_format_is_supported = response_format_is_supported
        self.orchestrated_messages = []

        # NOTE: Async reply functions are not yet supported with this contrib agent
        self._reply_func_list = []
        self.register_reply([Agent, None], Orchestrator.run_chat)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def _print_thought(self, message):
        print(self.name + " (thought)\n")
        print(message.strip() + "\n")
        print("\n", "-" * 80, flush=True, sep="")

    def _broadcast(self, message, out_loud=[], exclude=[]):
        m = copy.deepcopy(message)
        m["role"] = "user"
        for a in self._agents:
            if a in exclude or a.name in exclude:
                continue
            if a in out_loud or a.name in out_loud:
                self.send(message, a, request_reply=False, silent=False)
            else:
                self.send(message, a, request_reply=False, silent=True)

    def _has_image(self, message):
        if isinstance(message["content"], list):
            for elm in message["content"]:
                if elm.get("type", "") == "image_url":
                    return True
        return False

    def _create_with_images(self, messages, max_images=1, **kwargs):
        # Clone the messages to give context, but remove old screenshots
        history = []
        n_images = 0
        for m in messages[::-1]:
            # Create a shallow copy
            message = {}
            message.update(m)

            # If there's an image, then consider replacing it with a string
            if self._has_image(message):
                n_images += 1
                if n_images > max_images:
                    message["content"] = content_str(message["content"])

            # Prepend the message -- since we are iterating backwards
            history.insert(0, message)

        # Increase the temperature by a fixed amount (up to a max)
        if "temperature" in kwargs:
            kwargs["temperature"] = min(2.0, kwargs["temperature"] + self._temperature_bonus)

        return self.client.create(messages=history, **kwargs)

    def _create_with_retry(self, max_tries=10, *args, **kwargs):
        """Create a JSON response, retrying up to `max_tries` times."""

        assert self.client is not None

        if not self.response_format_is_supported and "response_format" in kwargs:
            del kwargs["response_format"]

        # kwargs["max_tokens"] = 4096

        messages = copy.deepcopy(kwargs.pop("messages", []))

        messages.append(
            {
                "role": "user",
                "content": """Do not use code blocks for JSON. No need to use indentation or new lines.""",
            }
        )

        for _ in range(max_tries):
            # print(json.dumps(messages, indent=2))
            response = self._create_with_images(*args, messages=messages, **kwargs)
            extracted_response = str(self.client.extract_text_or_completion_object(response)[0])
            try:
                json.loads(extracted_response)
                return response
            except json.decoder.JSONDecodeError as e:
                self._print_thought(str(e))
                messages.append({"role": "assistant", "content": extracted_response})
                messages.append(
                    {
                        "role": "user",
                        "content": """Your last response wasn't a valid JSON. Please
generate a valid json. json.loads() should be able to directly parse it. No need to use
code blocks for the json that you generate.""",
                    }
                )
        raise RuntimeError("The orchestrator failed to create a JSON response after multiple attempts.")

    def run_chat(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        # We should probably raise an error in this case.
        if self.client is None:
            return False, None

        if messages is None:
            messages = self._oai_messages[sender]

        # Work with a copy of the messages
        _messages = copy.deepcopy(messages)

        ##### Memory ####

        # Pop the last message, which is the task
        task = _messages.pop()["content"]

        # A reusable description of the team
        team = "\n".join([a.name + ": " + a.description for a in self._agents])
        names = ", ".join([a.name for a in self._agents])

        execution_enabled_agents = [a for a in self._agents if isinstance(a._code_execution_config, dict)]

        # A place to store relevant facts
        facts = ""

        # A place to store the plan
        plan = ""

        #################

        # Start by writing what we know
        closed_book_prompt = f"""Below I will present you a request. Before we begin addressing the request, please answer the following pre-survey to the best of your ability. Keep in mind that you are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from.

Here is the request:

{task}

Here is the pre-survey:

    1. Please list any specific facts or figures that are GIVEN in the request itself. It is possible that there are none.
    2. Please list any facts that may need to be looked up, and WHERE SPECIFICALLY they might be found. In some cases, authoritative sources are mentioned in the request itself.
    3. Please list any facts that may need to be derived (e.g., via logical deduction, simulation, or computation)
    4. Please list any facts that are recalled from memory, hunches, well-reasoned guesses, etc.

When answering this survey, keep in mind that "facts" will typically be specific names, dates, statistics, etc. Your answer should use headings:

    1. GIVEN OR VERIFIED FACTS
    2. FACTS TO LOOK UP
    3. FACTS TO DERIVE
    4. EDUCATED GUESSES
""".strip()

        _messages.append({"role": "user", "content": closed_book_prompt, "name": sender.name})

        response = self._create_with_images(
            messages=_messages,
            cache=self.client_cache,
            max_images=self.max_images,
        )
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        _messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        facts = extracted_response

        # Make an initial plan
        plan_prompt = f"""Fantastic. To address this request we have assembled the following team:

{team}

Based on the team composition, and known and unknown facts, please devise a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task.""".strip()
        _messages.append({"role": "user", "content": plan_prompt, "name": sender.name})

        response = self._create_with_images(
            messages=_messages,
            cache=self.client_cache,
            max_images=self.max_images,
        )

        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        _messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        plan = extracted_response

        # Main loop
        total_turns = 0
        max_turns = 20  # 30
        while total_turns < max_turns:

            # Populate the message histories
            self.orchestrated_messages = []
            for a in self._agents:
                a.reset()

            self.orchestrated_messages.append(
                {
                    "role": "assistant",
                    "content": f"""
We are working to address the following user request:

{task}


To answer this request we have assembled the following team:

{team}

Some additional points to consider:

{facts}

{plan}
""".strip(),
                    "name": self.name,
                }
            )
            self._broadcast(self.orchestrated_messages[-1])
            self._print_thought(self.orchestrated_messages[-1]["content"])

            # Inner loop
            stalled_count = 0
            while total_turns < max_turns:
                total_turns += 1

                prev_message = self.orchestrated_messages[-1]["content"]
                code_blocks = [t for t in extract_code(prev_message) if t[0] in ["python", "sh"]]

                data = None
                if len(code_blocks) > 0 and len(execution_enabled_agents) > 0:
                    step_prompt = f"""
Recall we are working on the following request:

{task}

To make progress on the request, please answer the following questions, including necessary reasoning:

    - Is the request fully satisfied? (True if complete, or False if the original request has yet to be SUCCESSFULLY addressed)
    - Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

    {{
        "is_request_satisfied": {{
            "reason": string,
            "answer": boolean
        }},
        "is_progress_being_made": {{
            "reason": string,
            "answer": boolean
        }}
    }}
""".strip()

                    # This is a temporary message we will immediately pop
                    self.orchestrated_messages.append({"role": "user", "content": step_prompt, "name": sender.name})
                    response = self._create_with_retry(
                        messages=self.orchestrated_messages,
                        cache=self.client_cache,
                        response_format={"type": "json_object"},
                        max_images=self.max_images,
                    )
                    self.orchestrated_messages.pop()

                    extracted_response = self.client.extract_text_or_completion_object(response)[0]
                    try:
                        data = json.loads(extracted_response)
                        data["next_speaker"] = {
                            "reason": "Assigning to an agent that can execute the script.",
                            "answer": execution_enabled_agents[0].name,
                        }
                        data["instruction_or_question"] = {
                            "reason": "Assigning to an agent that can execute the script.",
                            "answer": "Please execute the above script.",
                        }
                    except json.decoder.JSONDecodeError as e:
                        # Something went wrong. Restart this loop.
                        self._print_thought(str(e))
                        break
                else:
                    step_prompt = f"""
Recall we are working on the following request:

{task}

And we have assembled the following team:

{team}

To make progress on the request, please answer the following questions, including necessary reasoning:

    - Is the request fully satisfied? (True if complete, or False if the original request has yet to be SUCCESSFULLY addressed)
    - Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)
    - Who should speak next? (select from: {names})
    - What instruction or question would you give this team member? (Phrase as if speaking directly to them, and include any specific information they may need)

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

    {{
        "is_request_satisfied": {{
            "reason": string,
            "answer": boolean
        }},
        "is_progress_being_made": {{
            "reason": string,
            "answer": boolean
        }},
        "next_speaker": {{
            "reason": string,
            "answer": string (select from: {names})
        }},
        "instruction_or_question": {{
            "reason": string,
            "answer": string
        }}
    }}
""".strip()
                    # This is a temporary message we will immediately pop
                    self.orchestrated_messages.append({"role": "user", "content": step_prompt, "name": sender.name})
                    response = self._create_with_retry(
                        messages=self.orchestrated_messages,
                        cache=self.client_cache,
                        response_format={"type": "json_object"},
                        max_images=self.max_images,
                    )
                    self.orchestrated_messages.pop()

                    extracted_response = self.client.extract_text_or_completion_object(response)[0]
                    try:
                        data = json.loads(extracted_response)
                    except json.decoder.JSONDecodeError as e:
                        # Something went wrong. Restart this loop.
                        self._print_thought(str(e))
                        break

                self._print_thought(json.dumps(data, indent=4))

                if data["is_request_satisfied"]["answer"]:
                    return True, "TERMINATE"

                if data["is_progress_being_made"]["answer"]:
                    stalled_count -= 1
                    stalled_count = max(stalled_count, 0)
                else:
                    stalled_count += 1

                if stalled_count >= 3:
                    self._temperature_bonus += 0.5 # Be more creative.

                    self._print_thought("We aren't making progress. Let's reset.")
                    new_facts_prompt = f"""It's clear we aren't making as much progress as we would like, but we may have learned something new. Please rewrite the following fact sheet, updating it to include anything new we have learned. This is also a good time to update educated guesses (please add or update at least one educated guess or hunch, and explain your reasoning).

{facts}
""".strip()
                    self.orchestrated_messages.append(
                        {"role": "user", "content": new_facts_prompt, "name": sender.name}
                    )
                    response = self._create_with_images(
                        messages=self.orchestrated_messages,
                        cache=self.client_cache,
                        max_images=self.max_images,
                    )
                    facts = self.client.extract_text_or_completion_object(response)[0]
                    self.orchestrated_messages.append({"role": "assistant", "content": facts, "name": self.name})

                    new_plan_prompt = f"""Please come up with a new plan expressed in bullet points. Keep in mind the following team composition, and do not involve any other outside people in the plan -- we cannot contact anyone else.

Team membership:
{team}
""".strip()
                    self.orchestrated_messages.append({"role": "user", "content": new_plan_prompt, "name": sender.name})
                    response = self._create_with_images(
                        messages=self.orchestrated_messages,
                        cache=self.client_cache,
                        max_images=self.max_images,
                    )

                    plan = self.client.extract_text_or_completion_object(response)[0]
                    break

                # Broadcast the message to all agents
                m = {"role": "user", "content": data["instruction_or_question"]["answer"], "name": self.name}
                if m["content"] is None:
                    m["content"] = ""
                self._broadcast(m, out_loud=[data["next_speaker"]["answer"]])

                # Keep a copy
                m["role"] = "assistant"
                self.orchestrated_messages.append(m)

                # Request a reply
                for a in self._agents:
                    if a.name == data["next_speaker"]["answer"]:
                        reply = a.generate_reply(sender=self)
                        if isinstance(reply, str):
                            reply = {"role": "user", "name": a.name, "content": reply}
                        elif isinstance(reply, dict):
                            reply["role"] = "user"
                            reply["name"] = a.name
                        self.orchestrated_messages.append(reply)
                        a.send(reply, self, request_reply=False)
                        self._broadcast(reply, exclude=[a])
                        break

        return True, "TERMINATE"
