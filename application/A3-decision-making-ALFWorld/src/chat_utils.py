import json
from typing import Callable, Dict, Optional, Union, List
import yaml
import numpy as np
from autogen.agentchat import ConversableAgent
from alfworld.agents.environment.alfred_tw_env import AlfredTWEnv
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

def bleu_score(reference, candidate):
    reference_tokens = reference.split()
    candidate_tokens = candidate.split()

    smoothie = SmoothingFunction().method4
    score = sentence_bleu([reference_tokens], candidate_tokens, smoothing_function=smoothie)
    return score

def load_prompts(prompts_file):
    with open(prompts_file, 'r') as f:
        d = json.load(f)
    return d

def load_base_prompts(filepath):
    with open(filepath, "r") as f:
        prompt = f.read()
    return prompt

def to_conversation(history: List[str]):
    message = []
    current_role = "user"
    traverse = {"user": "assistant", "assistant": "user"}
    for his in history:
        message.append({"role": current_role, "content": his})
        current_role = traverse[current_role]
    return message

def load_task_prompt(path="src/tasks/task_desc.json"):
    with open(path, "r") as f:
        prompt_dict = json.load(f)
    return prompt_dict
    

def process_action(action, choices, limit=0.01, to_print=False):
    if "ACTION: " in action:
        action = action[action.find("ACTION: ") + 8:]
    
    if to_print:
        print("preprocess action: ", action)
    action = action.strip().lower()
    action_splits = action.split(".")
    if len(action_splits[0].strip()) < 3 and len(action_splits) > 1:
        action = action_splits[1].strip()
    else:
        action = action_splits[0].strip()
    if not choices:
        return action
    bleus = [bleu_score(choice, action) for choice in choices]
    max_index = np.argmax(np.array(bleus))
    max_score = bleus[max_index]
    if max_score > limit:
        if to_print:
            print("processed action: ", choices[max_index], " score: ", max_score)
        return choices[max_index]
    return action


class ContextManager(object):
    user_proxy = None
    assistant: ConversableAgent = None
    
    def __init__(self, user_proxy = None, assistant = None) -> None:
        self.user_proxy = user_proxy
        self.assistant = assistant
        
    def set_message(self, message):
        last_message = self.assistant._oai_messages[self.user_proxy].pop()
        content = last_message["content"]
        content = content[:content.find("ACTION:")] + "ACTION: " + message
        last_message["content"] = content
        self.assistant._oai_messages[self.user_proxy].append(last_message)


class ALFAgent(ConversableAgent):
    
    MAX_CONSECUTIVE_AUTO_REPLY = (
        50  # maximum number of consecutive auto replies (subject to future change)
    )
    
    def __init__(
        self, 
        name: str, 
        task_config = "src/tasks/base_config.yaml",
        task_path = None,
        prompts_path = "src/tasks/prompts/alfworld_react.json",
        base_prompts_path = "src/tasks/base.txt",
        is_termination_msg = lambda x: "terminate" in x.get("content").lower(), 
        max_consecutive_auto_reply: Optional[int] = None, 
        human_input_mode: Optional[str] = "NEVER", 
        function_map: Optional[Dict[str, Callable]] = None, 
        code_execution_config: Optional[Union[Dict, bool]] = None,
        llm_config: Optional[Union[Dict, bool]] = False,
        **kwargs
    ):
        super().__init__(
            name, 
            is_termination_msg, 
            max_consecutive_auto_reply, 
            human_input_mode, 
            function_map, 
            code_execution_config, 
            llm_config, 
            **kwargs,
        )
        self.env = SingleAlfredTWEnv(get_config(task_config), task_path, "eval_out_of_distribution")
        self.env = self.env.init_env(batch_size=1)
        self.prompts = load_prompts(prompts_path)
        self.prefixes = {
            'pick_and_place': ['put_1', 'put_2'],
            'pick_clean_then_place': ['clean_1', 'clean_2'],
            'pick_heat_then_place': ['heat_1', 'heat_2'],
            'pick_cool_then_place': ['cool_1', 'cool_2'],
            'look_at_obj': ['examine_1', 'examine_2'],
            'pick_two_obj': ['puttwo_1', 'puttwo_2']
        }
        self.base_prompt = load_base_prompts(base_prompts_path)
        self.observation, self.info = self.env.reset()
        self.invalid_counter = 0
        self.action_counter = 0
        self.last_action = None
        self.task_prompt = load_task_prompt()
        self.task_description = None
        self.register_auto_reply(ConversableAgent, ALFAgent._generate_reply_for_assistant)
        
    
    def get_prompt(self, filename: str = None):
        if filename is None:
            return " "
        
        for k, v in self.prefixes.items():
            if filename.startswith(k):
                print(filename)
                example = []
                for s in v:
                    example.extend(self.prompts[s])
                return example
        raise Exception(f"unsupported name: {filename}")
    
    def get_examples(self):
        name = '/'.join(self.info['extra.gamefile'][0].split('/')[-3:-1])
        history = self.get_prompt(name)
        history[0] = self.base_prompt + history[0]
        return history
    
    def generate_init_message(self):
        message = "Your task now begins. " + '\n'.join(self.observation[0].split('\n\n')[1:])
        return message
    
    def get_admissible_actions(self):
        return self.info.get('admissible_commands', [[]])[0]
    
    def _generate_reply_for_assistant(self, messages=None, sender=None, config=None):
        message = messages[-1].get("content", "")
        if "terminate" in message.lower():
            return True, "TERMINATE"
        
        action = process_action(message, self.info.get('admissible_commands', [[]])[0])
        self.observation, reward, done, self.info = self.env.step([action])
        self.observation, reward, done = process_ob(self.observation[0]), self.info['won'][0], done[0]
        
        self.manager.set_message(action)
        reply = self.observation
        
        if done:
            reply += "Task success, now reply TERMINATE\n"
            return True, reply
        
        if self.last_action == action:
            self.action_counter += 1
        else:
            self.action_counter = 0
            self.last_action = action
            
        if "Nothing happens" in self.observation:
            self.invalid_counter += 1
        else:
            self.invalid_counter = 0
            
        if self.invalid_counter == 3 or self.action_counter == 3:
            reply = "Task failed. Reply TERMINATE."
        
        return True, reply
    
    def initiate_chat(self, recipient: ConversableAgent, **kwargs):
        self.manager = ContextManager(self, recipient)
        super().initiate_chat(recipient,**kwargs)
        
    

def set_context(message, user: ALFAgent, assistant: ConversableAgent):
    current_role = "user"
    traverse = {"user": "assistant", "assistant": "user"}
    for his in message:
        user._append_oai_message(his, current_role, assistant)
        assistant._append_oai_message(his, current_role, user)
        current_role = traverse[current_role]
        

class SingleAlfredTWEnv(AlfredTWEnv):
    '''
    Interface for Textworld Env 
    Contains only one game_file per environment
    '''

    def __init__(self, config, name, train_eval="eval_out_of_distribution"):
        print("Initializing AlfredTWEnv...")
        self.config = config
        self.train_eval = train_eval

        self.goal_desc_human_anns_prob = self.config['env']['goal_desc_human_anns_prob']
        self.get_game_logic()
        # self.gen_game_files(regen_game_files=self.config['env']['regen_game_files'])

        self.random_seed = 42

        self.game_files = [name]
        self.num_games = 1

def process_ob(ob: str):
    if ob.startswith('You arrive at loc '):
        ob = ob[ob.find('. ')+2:]    
    return ob

def get_config(path="src/tasks/base_config.yaml"):
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config


def get_all_game_files(config, split="eval_out_of_distribution"):
    config = get_config(config)
    env = AlfredTWEnv(config, train_eval=split)
    game_files = env.game_files
    del env
    return game_files