import json
from prompt import Prompt
import time
import openai
from pathlib import Path
from selenium.webdriver.common.keys import Keys
import os
import logging
import random
import computergym
import gym
from computergym.miniwob.miniwob_interface.action import (
    MiniWoBType,
    MiniWoBElementClickId,
    MiniWoBElementClickXpath,
    MiniWoBElementClickOption,
    MiniWoBMoveXpath,
)
import re
from autogen.agentchat import ConversableAgent
from autogen.agentchat.agent import Agent
from typing import Any, Callable, Dict, List, Optional, Union

class MiniWobUserProxyAgent(ConversableAgent):
    def __init__(
        self,
        env_name: str,
        headless_miniwob = True,
        rci_plan_loop: int = 1,
        rci_limit: int = 1,
        llm="chatgpt",
        with_task=True,
        state_grounding=True,
        name= "MinWobAgent",
        is_termination_msg = lambda x: "terminate" in x.get("content").lower(),  
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, bool]] = None,
        oai_config: Optional[Union[Dict, bool]] = False,
        system_message: Optional[str] = "",
        problem=None,
        headless=False,
        **kwargs,
    ) -> None:
        super().__init__(
            name=name,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply = max_consecutive_auto_reply,
            human_input_mode = human_input_mode,
            function_map = function_map,
            code_execution_config = code_execution_config,
            llm_config = oai_config,
            system_message = system_message,
            **kwargs,
        )
        
        self.register_reply(trigger="miniwob_assistant", reply_func = MiniWobUserProxyAgent._reply_miniwob, position = 1)        
        with open("config.json") as config_file:
            api_key = json.load(config_file)["api_key"]
            openai.api_key = api_key
        
        self.env_name = env_name
        self.real_env = gym.make("MiniWoBEnv-v0", env_name=env_name, headless=headless_miniwob)
        self.recipient = None
        self.silent = False
        
        self.rci_limit = rci_limit
        self.rci_plan_loop = rci_plan_loop
        self.llm = llm
        self.prompt = Prompt(env=env_name)
        self.state_grounding = state_grounding

        self.html_state = ""
        self.task = ""
        self.with_task = with_task
        self.current_plan = ""
        self.past_plan = []
        self.past_instruction = []
        self.custom_gaol = False
        
        self.plan_stage = True
        self.criticizm = True
        self.unexecuted_steps= 0
        self.ask_action = True
        self.judge_action = True

    def _convert_to_miniwob_action(self, instruction: str):
        instruction = instruction.split(" ")
        inst_type = instruction[0]
        inst_type = inst_type.lower()

        if inst_type == "type":
            characters = " ".join(instruction[1:])
            characters = characters.replace('"', "")
            return MiniWoBType(characters)
        elif inst_type == "clickid":
            element_id = " ".join(instruction[1:])
            return MiniWoBElementClickId(element_id)
        elif inst_type == "press":
            key_type = instruction[1].lower()
            if key_type == "enter":
                return MiniWoBType("\n")
            elif key_type == "space":
                return MiniWoBType(" ")
            elif key_type == "arrowleft":
                return MiniWoBType(Keys.LEFT)
            elif key_type == "arrowright":
                return MiniWoBType(Keys.RIGHT)
            elif key_type == "backspace":
                return MiniWoBType(Keys.BACKSPACE)
            elif key_type == "arrowup":
                return MiniWoBType(Keys.UP)
            elif key_type == "arrowdown":
                return MiniWoBType(Keys.DOWN)
            else:
                raise NotImplemented
        elif inst_type == "movemouse":
            xpath = " ".join(instruction[1:])
            return MiniWoBMoveXpath(xpath)
        elif inst_type == "clickxpath":
            xpath = " ".join(instruction[1:])
            return MiniWoBElementClickXpath(xpath)
        elif inst_type == "clickoption":
            xpath = " ".join(instruction[1:])
            return MiniWoBElementClickOption(xpath)
        else:
            raise ValueError("Invalid instruction")

    def _update_html_state(self, state: str):
        self.html_state = state

        return

    def _set_goal(self, goal: str):
        self.custom_gaol = True
        self.task = goal

        return
   
    def _check_regex(self, instruciton):
        return (
            (not re.search(self.prompt.clickxpath_regex, instruciton, flags=re.I))
            and (not re.search(self.prompt.chatgpt_type_regex, instruciton, flags=re.I))
            and (not re.search(self.prompt.davinci_type_regex, instruciton, flags=re.I))
            and (not re.search(self.prompt.press_regex, instruciton, flags=re.I))
            and (not re.search(self.prompt.clickoption_regex, instruciton, flags=re.I))
            and (not re.search(self.prompt.movemouse_regex, instruciton, flags=re.I))
        )

    def _process_instruction(self, instruciton: str):
        end_idx = instruciton.find("`")
        if end_idx != -1:
            instruciton = instruciton[:end_idx]

        instruciton = instruciton.replace("`", "")
        instruciton = instruciton.replace("\n", "")
        instruciton = instruciton.replace("\\n", "\n")
        instruciton = instruciton.strip()
        instruciton = instruciton.strip("'")

        return instruciton

    def _get_plan_step(self):
        idx = 1
        while True:
            if (str(idx) + ".") not in self.current_plan:
                return (idx - 1) + 1
            idx += 1
                   
    def _get_html_state(self, env_name, states):
        extra_html_task = [
            "click-dialog",
            "click-dialog-2",
            "use-autocomplete",
            "choose-date",
        ]

        html_body = states[0].html_body
        if env_name in extra_html_task:
            html_body += states[0].html_extra
        return html_body

    def _current_plan_prompt(self):
        pt = "\n\n"
        pt += "Here is a plan you are following now.\n"
        pt += f"{self.current_plan}"
        pt += "\n\n"

        return pt

    def _instruction_history_prompt(self):
        pt = "\n\n"
        pt += "We have a history of instructions that have been already executed by the autonomous agent so far.\n"
        if not self.past_instruction:
            pt += "No instruction has been executed yet."
        else:
            for idx, inst in enumerate(self.past_instruction):
                pt += f"{idx+1}: "
                pt += inst
                pt += "\n"
        pt += "\n\n"

        return pt

    def _webpage_state_prompt(self, init_plan: bool = False, with_task=False):
        pt = "\n\n"
        pt += "Below is the HTML code of the webpage where the agent should solve a task.\n"
        pt += self.html_state
        pt += "\n\n"
        if self.prompt.example_prompt and (init_plan or self.rci_plan_loop == -1):
            pt += self.prompt.example_prompt
            pt += "\n\n"
        if with_task:
            pt += "Current task: "
            pt += self.task
            pt += "\n"

        return pt

    def _save_result(self, value):
        path_dir = os.path.join("./result", self.env_name+".json")
        if os.path.exists(path_dir):
            with open(path_dir, 'r') as f:
                data = json.load(f)
        else:
            data = {}

        if 'value' in data:
            if value >0:
                data['value'] += 1
        else:
            if value > 0:
                data['value'] = 1
            else:
                data['value'] = 0
        print(self.env_name)
        print("success rate", data['value'])
        with open(path_dir, 'w') as f:
            json.dump(data, f)
            
    def initiate_chat(
        self,
        recipient: "ConversableAgent",
        clear_history: Optional[bool] = False,
        silent: Optional[bool] = False,
        **context,
    ):
        self._prepare_chat(recipient, clear_history)
        states = self.real_env.reset(seeds=[random.random()], record_screenshots=True)
        self._set_goal(states[0].utterance)
        html_state = self._get_html_state(self.env_name, states)
        self._update_html_state(html_state)
        if not self.custom_gaol:
            if self.with_task:
                self.initialize_task()

        if not self.prompt.init_plan_prompt or self.rci_plan_loop == -1:
            return

        pt = self.prompt.base_prompt
        pt += self._webpage_state_prompt(True, with_task=self.with_task)
        pt += self.prompt.init_plan_prompt
        self.send(pt, recipient, silent=silent)
                
    def _reply_miniwob(self, messages: List[Dict], sender: Optional[Agent] = None, config: Optional[Any] = None) -> Union[str, Dict]:
        messages = messages[-1]
        if not isinstance(messages,str): 
            messages = messages.get("content", "")
            
        if self.plan_stage:         
            if self.rci_plan_loop!=0:
                if self.criticizm:
                    reply = "\n\nFind problems with this plan for the given task compared to the example plans.\n\n"
                    self.criticizm = False
                    return True, reply
                else:
                    reply = "\n\nBased on this, what is the plan for the agent to complete the task?\n\n"
                    self.criticizm = True
                    self.rci_plan_loop -=1
                    return True, reply

            messages = "\n" + messages
            self.current_plan = messages
            self.plan_stage = False
        
        if not self.plan_stage:
            if self.ask_action:
                reply = self._webpage_state_prompt(with_task=self.with_task)
                if self.prompt.init_plan_prompt and self.rci_plan_loop != -1:
                    reply += self._current_plan_prompt()
                reply += self._instruction_history_prompt()
                if self.past_instruction:
                    update_action_prompt = self.prompt.action_prompt.replace(
                        "{prev_inst}", self.past_instruction[-1]
                    )
                    if len(self.past_instruction) == 1:
                        update_action_prompt = self.prompt.action_prompt.replace(
                            "{order}", "2nd"
                        )
                    elif len(self.past_instruction) == 2:
                        update_action_prompt = self.prompt.action_prompt.replace(
                            "{order}", "3rd"
                        )
                    else:
                        update_action_prompt = self.prompt.action_prompt.replace(
                            "{order}", f"{len(self.past_instruction)+1}th"
                        )

                    action_prompt = update_action_prompt
                else:
                    action_prompt = self.prompt.first_action_prompt

                if self.rci_plan_loop == -1:
                    action_prompt = "Based on the task, " + action_prompt
                else:
                    action_prompt = (
                        "Based on the plan and the history of instructions executed so far, "
                        + action_prompt
                    )
                reply += action_prompt
                self.ask_action = False
                return True, reply

            if self.judge_action and self.prompt.update_action and self.state_grounding:
                reply = self.prompt.update_action
                self.judge_action = False
                return True, reply
        
            if self.rci_limit!=0:
                instruciton = self._process_instruction(messages)
                if self._check_regex(instruciton):      
                    reply = self.prompt.rci_action_prompt
                    self.rci_limit -=1
                    return True, reply
                else:
                    instruciton = messages
                    
            instruction = self._process_instruction(messages)
            self.past_instruction.append(instruction)
            try:
                miniwob_action = self._convert_to_miniwob_action(instruction)

                states, rewards, dones, _ = self.real_env.step([miniwob_action])
            except (ValueError, TypeError):
                print("Invalid action or rci action fail")
                rewards = [0]
                dones = [True]
                
            if rewards[0] !=0 or all(dones):   
                if rewards[0] > 0:
                    self._save_result(1)
                    print("SUCCESS!!!!")
                    self.real_env.close()
                    return True, None
                else:
                    self._save_result(-1)
                    print("Fail!!!!")     
                    self.real_env.close()   
                    return True, None
            else:
                html_state = self._get_html_state(self.env_name, states)
                self._update_html_state(html_state)
                self.ask_action = True
                return 'True', 'Hold on, please wait for my next instruction.' 