# ruff: noqa: E722
import json
import traceback
import copy
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Callable, Literal, Tuple
from autogen import Agent, ConversableAgent, GroupChatManager, GroupChat, OpenAIWrapper


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
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
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

        self._agents = agents
        self.orchestrated_messages = []

        # NOTE: Async reply functions are not yet supported with this contrib agent
        self._reply_func_list = []
        self.register_reply([Agent, None], Orchestrator.run_chat)
        self.register_reply([Agent, None], ConversableAgent.generate_code_execution_reply)
        self.register_reply([Agent, None], ConversableAgent.generate_function_call_reply)
        self.register_reply([Agent, None], ConversableAgent.check_termination_and_human_reply)

    def _print_consideration(self, message):
        #print(self.name + " (consideration)\n")
        #print(message.strip() + "\n")
        #print("\n", "-" * 80, flush=True, sep="")
        pass

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
        self.orchestrated_messages = copy.deepcopy(messages)

        # Pop the last message, which is the task
        task = self.orchestrated_messages.pop()["content"]

        # Reset all the agents
        for a in self._agents:
            a.reset()

        # Start by writing what we know
        closed_book_prompt = f"""Below I will present you a request. Your job right now is JUST to LIST ALL THE RELEVANT FACTS that might be necessary for someone to address the request. In some cases, those facts are not yet knowable, and can be listed simply as 'to be determined' or 'TBD'. Other facts can be filled-in from your memory, including some specific names, numbers and statistics. You are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from. Here is the request:

{task}
""".strip()

        self._print_consideration(closed_book_prompt)
        self.orchestrated_messages.append({"role": "user", "content": closed_book_prompt, "name": sender.name})
        self._broadcast(self.orchestrated_messages[-1])

        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
            max_tokens=1024,
        )

        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        self.orchestrated_messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        self._broadcast(self.orchestrated_messages[-1])
        self._print_thought(extracted_response)

        descriptions = "\n".join([a.name + ": " + a.description for a in self._agents])
        names = ", ".join([a.name for a in self._agents])

        # Send a round of itroductions
        intro_prompt = f"""Fantastic. We've now assembled a team to answer the request. In attendance are:

{descriptions}
""".strip()
        self._print_consideration(intro_prompt)

        self.orchestrated_messages.append({"role": "user", "content": intro_prompt, "name": sender.name})
        self._broadcast(self.orchestrated_messages[-1])

        # Make an initial plan
        plan_prompt = """Based on these known and unknown facts, and the team that has been assembled, please divise an initial solution sketch. I.e., a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task.""".strip()
        self._print_consideration(plan_prompt)

        self.orchestrated_messages.append({"role": "user", "content": plan_prompt, "name": sender.name})
        self._broadcast(self.orchestrated_messages[-1])

        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
            max_tokens=1024,
        )

        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        self.orchestrated_messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        self._broadcast(self.orchestrated_messages[-1])
        self._print_thought(extracted_response)

        # Main loop
        stalled_count = 0
        for i in range(0, 20):
            step_prompt = f"""
Consider again the task:

{task}

To make make progress on the request, please answer the following qusetions, including necessary reasoning:

    - Is the request fully satisfied? (True if complete, or False if there is more to do)
    - Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)
    - Who should speak next? (select from: {names})
    - What instruction or question would you give this team member? (Phrase as if speaking directly to them, and include any specific information they may need)

Remember, the teams roles are as follows:

{descriptions}

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
            response = self.client.create(
                messages=self.orchestrated_messages,
                cache=self.client_cache,
                response_format={"type": "json_object"},
            )
            self.orchestrated_messages.pop()

            extracted_response = self.client.extract_text_or_completion_object(response)[0]
            data = json.loads(extracted_response)
            self._print_thought(json.dumps(data, indent=4))

            if data["is_request_satisfied"]["answer"]:
                return True, "TERMINATE"

            if data["is_progress_being_made"]["answer"]:
                stalled_count = 0
            else:
                stalled_count += 1
            if stalled_count >= 3:
                return True, "TERMINATE"

            # Broadcast the message to all agents
            m = {"role": "user", "content": data["instruction_or_question"]["answer"], "name": self.name}
            self._broadcast(m, out_loud=[data["next_speaker"]["answer"]])

            # Keep a copy
            m["role"] = "assistant"
            self.orchestrated_messages.append(m)

            # Request a reply
            for a in self._agents:
                if a.name == data["next_speaker"]["answer"]:
                    reply = {"role": "user", "name": a.name, "content": a.generate_reply(sender=self)}
                    self.orchestrated_messages.append(reply)
                    a.send(reply, self, request_reply=False)
                    self._broadcast(reply, exclude=[a])
                    break

        return True, "TERMINATE"
