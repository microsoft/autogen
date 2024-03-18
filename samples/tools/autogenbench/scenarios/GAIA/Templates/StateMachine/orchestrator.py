# ruff: noqa: E722
from datetime import datetime
import json
import copy
from string import Template
from dataclasses import dataclass
from typing import Dict, List, Optional, Type, TypeVar, Union, Callable, Literal, Tuple, TypedDict
from autogen import Agent, ConversableAgent, OpenAIWrapper, AssistantAgent
import logging


class OrchestratorPromptTemplates(TypedDict):
    closed_book_prompt: Template
    plan_prompt: Template
    step_prompt: Template
    team_update: Template
    rethink_facts: Template
    new_plan: Template


defaultPromptTemplates: OrchestratorPromptTemplates = {
    "closed_book_prompt": Template(
        """Below I will present you a request. Before we begin addressing the request, please answer the following pre-survey to the best of your ability. Keep in mind that you are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from.

Here is the request:

$task

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
"""
    ),
    "plan_prompt": Template(
        """Fantastic. To address this request we have assembled the following team:

$team

Based on the team composition, and known and unknown facts, please devise a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task."""
    ),
    "step_prompt": Template(
        """
Recall we are working on the following request:

$task

And we have assembled the following team:

$team

To make progress on the request, please answer the following questions, including necessary reasoning:

$bullet_points

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

$json_schema
"""
    ),
    "team_update": Template(
        """
We are working to address the following user request:

$task


To answer this request we have assembled the following team:

$team

Some additional points to consider:

$facts

$plan
"""
    ),
    "rethink_facts": Template(
        """It's clear we aren't making as much progress as we would like, but we may have learned something new. Please rewrite the following fact sheet, updating it to include anything new we have learned. This is also a good time to update educated guesses (please add or update at least one educated guess or hunch, and explain your reasoning). 

$prev_facts
"""
    ),
    "new_plan": Template(
        """Please come up with a new plan expressed in bullet points. Keep in mind the following team composition, and do not involve any other outside people in the plan -- we cannot contact anyone else.

Team membership:
$team
"""
    ),
}


@dataclass
class NextStepCriteria:
    name: str
    prompt_msg: str
    answer_spec: str
    pre_execute_hook: Optional[Callable] = None
    post_execute_hook: Optional[Callable] = None

    def to_bullet_point(self):
        return f"    - {self.prompt_msg}"

    def to_json_schema_str(self):
        return f"""    "{self.name}": {{
        "reason": string,
        "answer": {self.answer_spec}
    }}"""


class TemplateUtils:
    @staticmethod
    def generate_next_step_prompt(
        prompt_template: Template, criteria_list: List[NextStepCriteria], task: str, team: str
    ) -> str:
        bullet_points = "\n".join([criteria.to_bullet_point() for criteria in criteria_list])
        inner_json = ",\n".join([criteria.to_json_schema_str() for criteria in criteria_list])
        json_schema = f"{{\n{inner_json}\n}}"

        step_prompt = prompt_template.substitute(
            task=task, team=team, bullet_points=bullet_points, json_schema=json_schema
        ).strip()
        return step_prompt

    @staticmethod
    def generate_team_update_prompt(
        prompt_template: Template, task: str, team: str, facts: str, plan: str, **kwargs
    ) -> str:
        return prompt_template.substitute(task=task, team=team, facts=facts, plan=plan).strip()


class Quantifier(AssistantAgent):
    def __init__(
        self, name: str, llm_config: Optional[Union[Dict, Literal[False]]], system_message: str = None, **kwargs
    ):
        llm_config = copy.deepcopy(llm_config)
        llm_config["max_retries"] = 10
        if system_message is None:
            system_message = """You are a helpful assistant. You quantify the output of different tasks based on the given criteria. 
        The criterion is given in a dictionary format where each key is a distinct criteria. 
        The value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key} 
        You are going to quantify each of the criteria for a given task based on the task description. 
        Return a dictionary where the keys are the criteria and the values are the assessed performance based on accepted values for each criteria. 
        Return only the dictionary."""
        super().__init__(name=name, llm_config=llm_config, system_message=system_message, **kwargs)

    def quantify(self) -> str:
        criterion = {
            "TERMINATE": {
                "description": "If we have a correct answer - is it ok to terminate?",
                "accepted_values": ["Appropriate", "Inappropriate"],
            }
        }
        task = {"question:": "2+2", "answer": "4"}

        quantifyTemplate = Template(
            f"""criterion = $criterion_json
task = $task_json\n"""
        )

        message = {
            "role": "user",
            "content": quantifyTemplate.substitute(criterion_json=json.dumps(criterion), task_json=json.dumps(task)),
            "name": "user",
        }
        reply = self.generate_reply(messages=[message])
        return reply


class DefaultStateMachineTransitions:
    # proc_next_step -> decision_to_terminate -> move to state of termination
    @staticmethod
    def decision_to_terminate(CURRENT_STATE: str, context: Dict):
        next_step = context["next_step"]
        if next_step["is_request_satisfied"]["answer"]:
            # return True, "TERMINATE"
            CURRENT_STATE = "TERMINATE_TRUE"
        return CURRENT_STATE

    # proc_next_step -> update_local_state -> continue/reset_current_run_with_introspect
    @staticmethod
    def stall_update_and_check(CURRENT_STATE: str, context: Dict):
        next_step = context["next_step"]
        if "stalled_count" not in context:
            context["stalled_count"] = 0

        if next_step["is_progress_being_made"]["answer"]:
            context["stalled_count"] -= 1
            context["stalled_count"] = max(context["stalled_count"], 0)
        else:
            context["stalled_count"] += 1

        if context["stalled_count"] >= 3:
            # facts, plan = self._prepare_new_facts_and_plan(facts=facts, sender=sender, team=team)
            # break
            CURRENT_STATE = "INTROSPECT_AND_RESET"
        return CURRENT_STATE


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
        prompt_templates: OrchestratorPromptTemplates = defaultPromptTemplates,
        quantifier: Quantifier = None,
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

        self._prompt_templates = prompt_templates

        self._quantifier: Quantifier = quantifier

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

    def _think_and_respond(self, messages: List[dict], message: str, sender: Optional[Agent]):
        messages.append({"role": "user", "content": message, "name": sender.name})

        response = self.client.create(
            messages=messages,
            cache=self.client_cache,
        )
        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        messages.append({"role": "assistant", "content": extracted_response, "name": self.name})
        return extracted_response

    def _think_next_step(self, step_prompt: str, sender: Optional[Agent]):
        # This is a temporary message we will immediately pop
        self.orchestrated_messages.append({"role": "user", "content": step_prompt, "name": sender.name})
        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
            response_format={"type": "json_object"},
        )
        self.orchestrated_messages.pop()

        extracted_response = self.client.extract_text_or_completion_object(response)[0]
        next_step = json.loads(extracted_response)
        self._print_thought(json.dumps(next_step, indent=4))
        return next_step

    def _prepare_new_facts_and_plan(self, facts, sender: Optional[Agent], team):
        self._print_thought("We aren't making progress. Let's reset.")
        new_facts_prompt = self._prompt_templates["rethink_facts"].substitute(prev_facts=facts).strip()
        facts = self._think_and_respond(self.orchestrated_messages, new_facts_prompt, sender)

        new_plan_prompt = self._prompt_templates["new_plan"].substitute(team=team).strip()
        self.orchestrated_messages.append({"role": "user", "content": new_plan_prompt, "name": sender.name})
        response = self.client.create(
            messages=self.orchestrated_messages,
            cache=self.client_cache,
        )

        # plan is an exception - we dont log it as a message
        plan = self.client.extract_text_or_completion_object(response)[0]

        return facts, plan

    def _broadcast_next_step_and_request_reply(self, next_prompt, next_speaker):
        # Broadcast the message to all agents
        m = {"role": "user", "content": next_prompt, "name": self.name}
        if m["content"] is None:
            m["content"] = ""
        self._broadcast(m, out_loud=[next_speaker])

        # Keep a copy
        m["role"] = "assistant"
        self.orchestrated_messages.append(m)

        # Request a reply
        for a in self._agents:
            if a.name == next_speaker:
                reply = {"role": "user", "name": a.name, "content": a.generate_reply(sender=self)}
                self.orchestrated_messages.append(reply)
                a.send(reply, self, request_reply=False)
                self._broadcast(reply, exclude=[a])
                break

    def _update_team_with_facts_and_plan(self, team_update_prompt: str):
        self.orchestrated_messages.append({"role": "assistant", "content": team_update_prompt, "name": self.name})
        self._broadcast(self.orchestrated_messages[-1])
        self._print_thought(self.orchestrated_messages[-1]["content"])

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

        METADATA = {}

        # Pop the last message, which is the task
        METADATA["task"] = _messages.pop()["content"]

        # A reusable description of the team
        METADATA["team"] = "\n".join([a.name + ": " + a.description for a in self._agents])
        METADATA["names"] = ", ".join([a.name for a in self._agents])

        # A place to store relevant facts
        METADATA["facts"] = ""

        # A place to store the plan
        METADATA["plan"] = ""

        #################

        # Start by writing what we know
        closed_book_prompt = self._prompt_templates["closed_book_prompt"].substitute(task=METADATA["task"]).strip()
        METADATA["facts"] = self._think_and_respond(_messages, closed_book_prompt, sender)

        # Make an initial plan
        plan_prompt = self._prompt_templates["plan_prompt"].substitute(team=METADATA["plan"]).strip()
        METADATA["plan"] = self._think_and_respond(_messages, plan_prompt, sender)

        # Main loop
        total_turns = 0
        max_turns = 30
        while total_turns < max_turns:

            # Populate the message histories
            self.orchestrated_messages = []
            for a in self._agents:
                a.reset()

            team_update_prompt = TemplateUtils.generate_team_update_prompt(
                prompt_template=self._prompt_templates["team_update"], **METADATA
            )
            self._update_team_with_facts_and_plan(team_update_prompt=team_update_prompt)

            CURRENT_STATE = "OBTAIN_NEXTSTEP"
            context = {}
            criteria_list = [
                NextStepCriteria(
                    name="is_request_satisfied",
                    prompt_msg="Is the request fully satisfied? (True if complete, or False if the original request has yet to be SUCCESSFULLY addressed)",
                    answer_spec="boolean",
                    pre_execute_hook=DefaultStateMachineTransitions.decision_to_terminate,
                ),
                NextStepCriteria(
                    name="is_progress_being_made",
                    prompt_msg="Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)",
                    answer_spec="boolean",
                    pre_execute_hook=DefaultStateMachineTransitions.stall_update_and_check,
                ),
                NextStepCriteria(
                    name="next_speaker",
                    prompt_msg=f"Who should speak next? (select from: {METADATA['names']})",
                    answer_spec=f"string (select from: {METADATA['names']})",
                ),
                NextStepCriteria(
                    name="instruction_or_question",
                    prompt_msg="What instruction or question would you give this team member? (Phrase as if speaking directly to them, and include any specific information they may need)",
                    answer_spec="string",
                ),
            ]

            # Inner loop
            while total_turns < max_turns:
                PREVIOUS_STATE = CURRENT_STATE

                # obtain next step
                if CURRENT_STATE == "OBTAIN_NEXTSTEP":
                    total_turns += 1
                    try:
                        step_prompt = TemplateUtils.generate_next_step_prompt(
                            prompt_template=self._prompt_templates["step_prompt"],
                            criteria_list=criteria_list,
                            task=METADATA["task"],
                            team=METADATA["team"],
                        )
                        context["next_step"] = self._think_next_step(
                            step_prompt=step_prompt,
                            sender=sender,
                        )
                        CURRENT_STATE = "PRE_EXECUTION_NEXTSTEP"
                    except json.decoder.JSONDecodeError as e:
                        # Something went wrong. Restart this loop.
                        self._print_thought(str(e))
                        # break
                        CURRENT_STATE = "RESET"

                # before 'executing' the next step we run registered funcs
                elif CURRENT_STATE == "PRE_EXECUTION_NEXTSTEP":
                    for criteria in criteria_list:
                        func = criteria.pre_execute_hook
                        if func is None:
                            continue
                        logging.info(f"{CURRENT_STATE}: Running {func.__module__}:{func.__name__}")
                        print(
                            f"%%% {datetime.now()} orchestrator [state machine] {CURRENT_STATE}: Running {func.__module__}:{func.__name__}"
                        )
                        CURRENT_STATE = func(CURRENT_STATE, context)

                        # hooks are able to early exit, or 'fail' and ask for a reset
                        if CURRENT_STATE in ("TERMINATE_TRUE", "RESET", "INTROSPECT_AND_RESET"):
                            logging.info(f"{CURRENT_STATE}: Breaking out of loop")
                            break

                    if "PRE_EXECUTION_NEXTSTEP" == CURRENT_STATE:
                        CURRENT_STATE = "EXECUTE_NEXTSTEP"

                # we actually 'execute' the next step
                elif CURRENT_STATE == "EXECUTE_NEXTSTEP":
                    self._broadcast_next_step_and_request_reply(
                        next_prompt=context["next_step"]["instruction_or_question"]["answer"],
                        next_speaker=context["next_step"]["next_speaker"]["answer"],
                    )
                    CURRENT_STATE = "POST_EXECUTION_NEXTSTEP"

                # after 'executing' the next step we run registered funcs
                elif CURRENT_STATE == "POST_EXECUTION_NEXTSTEP":
                    CURRENT_STATE = "OBTAIN_NEXTSTEP"

                logging.info(f"Moved from {PREVIOUS_STATE} to {CURRENT_STATE}")
                print(
                    f"%%% {datetime.now()} orchestrator [state machine] from {PREVIOUS_STATE} to {CURRENT_STATE} Current turn: {total_turns}"
                )

                ### RESET STATE / TERMINATE ###

                if CURRENT_STATE == "INTROSPECT_AND_RESET":
                    METADATA["facts"], METADATA["plan"] = self._prepare_new_facts_and_plan(
                        facts=METADATA["facts"], sender=sender, team=METADATA["team"]
                    )
                    CURRENT_STATE = "RESET"

                if CURRENT_STATE == "TERMINATE_TRUE":
                    reply = self._quantifier.quantify()
                    print("*******")
                    print(reply)
                    return True, "TERMINATE"

                if CURRENT_STATE == "RESET":
                    break

        return True, "TERMINATE"
