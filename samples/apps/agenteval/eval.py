''' This python file provides tool to to evaluate the performance of the agents.'''

import autogen
import sys
import os
import json
import time

import json
import numpy as np
import matplotlib.pyplot as plt
from math import sqrt
    
import support_functions as sf ## will remove the lines of code that call this module


original_critic_message_base = """You are a helpful assistant. You suggest criteria for evaluating different tasks. They should be dinstinguishable, quantifieable and not redundant.
    Convert the evaluation criteria into a dictionary where the keys are the criteria.
    The value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key}
    Make sure the keys are criteria for assessing the given task.  "accepted_values" include the acceptable inputs for each key that are fine-grained and preferably multi-graded levels. "description" includes the criterion description.
    Return the json."""

worfklow_critic_message_base = """You are a helpful assistant. You suggest criteria for evaluating different tasks. They should be dinstinguishable, quantifieable and not redundant.
    Convert the evaluation criteria into a dictionary where the keys are the criteria that you want to assess.
    The value of each key is a dictionary as follows {"description": criteria description}
    Make sure the keys are criteria for assessing the given task.  "description" includes the criterion description for assessment. This json will be passed down to a sub critic which will provided sub criteria for each of the criteria provided.
    Return the json."""

sub_critic_message_base = """You are a helpful assistant to the critice message. You suggest sub criteria for evaluating different tasks based on the criteria provided by the critic agent (if you feel it is needed). 
        They should be dinstinguishable, quantifieable and related to the overall theme of the critics provided critieria.
        You operate by taking in the description of the criteria. You then create a new key called sub criteria where you provide the sub criteria for the given criteria. 
        The value of the sub_criteria is a list of dictionaries dictionary as follows {"description": sub criteria description , "accepted_values": possible accepted inputs for this key}
        Do this for each criteria provided by the critic.  "accepted_values" include the acceptable inputs for each key that are numerical from a scale of 1 to 5. "description" includes the criterion description.
        Once you have created the sub criteria for the given criteria, you return the json (make sure to include the contents on the critics dictionary in the final dictionary as well). 
        Make sure to return a valid json and not a python dictionary."""

original_quantifier_message_base = """You are a helpful assistant. You quantify the output of different tasks based on the given criteria.
        The criterion is given in a dictionary format where each key is a dintinct criteria.
        The value of each key is a dictionary as follows {"description": criteria description , "accepted_values": possible accepted inputs for this key}
        You are going to quantify each of the crieria for a given task based on the task description.
        Return a dictionary where the keys are the criteria and the values are the assessed performance based on accepted values for each criteria.
        Return the json"""
        
workflow_quantifier_message_base = """You are a helpful assistant. You quantify the output of different tasks based on the given criteria.
        The criterion is given in a dictionary format where each key is a dintinct criteria.
        The value of each key is a dictionary as follows {"description": criteria description , "sub_criteria": sub criteria for the given criteria with the accepted values for each key}
        You are going to quantify each of the subcrieria for a given task based on the task description for this question denoted by the question_id. Make sure the json is ready to be saved as a file.
        Return a json where the main key is the question_id and in the inner dictionary the keys are the criteria and the values are the subcritieria 
        with the assessed performance based on accepted values for each subcriteria. Make sure to return a valide json and not a python dictionary and do not 
        return anything other then the assessment - no additional text"""

additional_considerations_message_base = "\n You must take into account these considerations provided by the user: "

class EvalWorkflow:
        
        def __init__(self, task, env_var_path, critic_config, subcritic_config, quantifier_config, critic_manager_config=None, restart_generate_config=False):
            
            
            self.task = task
            self.critic = Critic(env_var_path, agent_config=critic_config).agent
            self.subcritic = SubCritic(env_var_path, agent_config=subcritic_config).agent
            self.critic_user = get_default_critic_user()
            self.quantifier = Quantifier(env_var_path, agent_config=quantifier_config).agent
            self.quantifier_user = get_default_quantifier_user()
            self.criteria = None
            self.file_name = None
            
            agents = [self.critic_user, self.critic, self.subcritic]
            
            if critic_manager_config is None:
                critic_manager_config = {'model_list': ['gpt-4'], 'request_timeout': 120, 'temperature': 0.7, 'cache_seed': 42}
            
            config_list = sf.generate_config_list(env_var_path, restart=restart_generate_config)
            
            config_list = [config for config in config_list if config['model'] in critic_manager_config['model_list']]

            groupchat = autogen.GroupChat(
                agents=agents, messages=[], max_round=12, speaker_selection_method="round_robin"
            )
            
            self.critic_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})
            
            
            
        def run_critic_workflow(self, write_file=True):
            
            task_items = '\n'.join([f'{k}: {v}' for k, v in self.task.items()])
            request = f"""I need your help to evaluate the task: {task_items} """
            
            self.critic_user.initiate_chat(self.critic_manager, message=request)
            self.criteria = self.critic_user.last_message()['content']
            
            if write_file:
                self.file_name = f"./{self.task['Task name']}_criteria.json"
                cr_file = open(self.file_name, "w")
                cr_file.write(self.criteria)
                cr_file.close()
                
            return self.criteria
        
        def run_quantifier_workflow(self, response_to_eval, criteria, criteria_to_ignore=None, write_file=True):
            
            if criteria_to_ignore is not None:
                criteria = ignore_criteria(criteria, criteria_to_ignore)
                
            ''' This function assesses the task'''

            
            id_ = list(response_to_eval.keys())[0]
            response = response_to_eval[id_]
            
            request = f"""I need your help to evaluate the task: {'/n'.join([f'{k}: {v}' for k, v in self.task.items()])} 

                    \n Evaluation dictionary: {criteria}
                    \n
                    \n RESPONSE TO EVALUATE: question_id={id_} with response={response}"""

            self.quantifier_user.initiate_chat(self.quantifier, message=request)
            assessment = self.quantifier_user.last_message()['content']
            
            if write_file:
                assess_file = open(f"./{self.task['Task name']}_assessment.json", "a")
                assess_file.write(assessment)                
                assess_file.write('\n\n')
                assess_file.close()

            return assessment
        
        def run_workflow(self, response_to_eval, write_file=True):
            
            if self.criteria is None:
                self.criteria = self.run_critic_workflow(write_file)
            
            assessment_dict = self.run_quantifier_workflow(response_to_eval, self.criteria, write_file=write_file)
            
            return assessment_dict


class Critic:
    
    def __init__(self, env_var_path, critic_with_sub = True, agent_config=None, restart_generate_config=False):
        
        critic_message = worfklow_critic_message_base if critic_with_sub else original_critic_message_base

        if agent_config is None:
            agent_config = {'model_list': ['gpt-4'], 'request_timeout': 120, 'temperature': 0.7, 'cache_seed': 42, 'additional_considerations': None}
               
        config_list = sf.filter_config_list(env_var_path, agent_config['model_list'], restart_generate_config)
    
        if agent_config['additional_considerations']:
            critic_message += additional_considerations_message_base + agent_config['additional_considerations']

        critic_llm_config = {
            "config_list": config_list,
            "timeout": agent_config['request_timeout'], 
            "temperature": agent_config['temperature'], 
            "cache_seed": agent_config['cache_seed']}

        self.agent = autogen.AssistantAgent(
            name="critic",
            system_message=critic_message,
            llm_config=critic_llm_config)
         
    
class SubCritic:
    
    def __init__(self, env_var_path, agent_config=None, restart_generate_config=False):
        
        subcritic_message = sub_critic_message_base

        if agent_config is None:
            agent_config = {'model_list': ['gpt-4'], 'request_timeout': 120, 'temperature': 0.7, 'cache_seed': 42, 'additional_considerations': None}
               
        config_list = sf.filter_config_list(env_var_path, agent_config['model_list'], restart_generate_config)

        if agent_config['additional_considerations']:
            subcritic_message += additional_considerations_message_base + agent_config['additional_considerations']

        subcritic_llm_config = {
            "config_list": config_list,
            "timeout": agent_config['request_timeout'], 
            "temperature": agent_config['temperature'], 
            "cache_seed": agent_config['cache_seed']}

        self.agent = autogen.AssistantAgent(
            name="sub_critic",
            system_message=subcritic_message,
            llm_config=subcritic_llm_config)

class Quantifier:
    ''' Quantifier is give the option to run multiple evaluations - some criteria would require more trials than others.
    Decide which subcriteria is relevant - split quantifier into two parts: code based quantification (proivde a function on how to calculate it) vs llm based quantification
    Take in groundtruth to compare against
    
    
    focus - avoid time and maybe accurarcy for now. First test on the quality of the response. 
    - they will add verifier.'''

    def __init__(self, env_var_path, critic_with_sub=True, agent_config=None, restart_generate_config=False):
        

        quantifier_message = workflow_quantifier_message_base if critic_with_sub else original_quantifier_message_base

        if agent_config is None:
            agent_config = {'model_list': ['gpt-4'], 'request_timeout': 120, 'temperature': 0.7, 'cache_seed': 42, 'additional_considerations': None}
                
        config_list = sf.filter_config_list(env_var_path, agent_config['model_list'], restart_generate_config)

        if agent_config['additional_considerations']:
            quantifier_message += additional_considerations_message_base + agent_config['additional_considerations']

        quantifier_llm_config = {
            "config_list": config_list,
            "timeout": agent_config['request_timeout'], 
            "temperature": agent_config['temperature'], 
            "cache_seed": agent_config['cache_seed']}
        
        self.agent = autogen.AssistantAgent(
        name="quantifier",
        llm_config=quantifier_llm_config,
        system_message=quantifier_message,
        )


def get_default_critic_user():
    ''' This function returns the default critic user'''

    critic_user = autogen.UserProxyAgent(
        name="critic_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={
            "use_docker": False
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )
    
    return critic_user

def get_default_quantifier_user():
    ''' This function returns the default quantifier user'''

    quantifier_user = autogen.UserProxyAgent(
        name="quantifier_user",
        max_consecutive_auto_reply=0,  # terminate without auto-reply
        human_input_mode="NEVER",
        code_execution_config={
            "use_docker": False
        },  # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
    )
    
    return quantifier_user
    

def setup_critic_eval_workflow(agents_dict, env_var_path, group_manager_config=None, restart_generate_config=False):
    ''' This function sets up the evaluation workflow'''
   
    print('Note that the order of agents is important - it should follow')
    
    agents = [agents_dict['critic_user'], agents_dict['critic'], agents_dict['subcritic']]
    
    if group_manager_config is None:
        group_manager_config = {'model_list': ['gpt-4'], 'request_timeout': 120, 'temperature': 0.7, 'cache_seed': 42}
    
    config_list = sf.generate_config_list(env_var_path, restart=restart_generate_config)
    
    config_list = [config for config in config_list if config['model'] in group_manager_config['model_list']]

    groupchat = autogen.GroupChat(
        agents=agents, messages=[], max_round=12, speaker_selection_method="round_robin"
    )
    
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list})

    return manager

def read_without_groundtruth_json(file_name):
    """
    Read the mathproblem logs - bypassing any information about the ground truths.

    Args:
    - file_name (str): The single log file that wants to get evaluated.

    Returns:
    - str: The log file without any information about the ground truth answer of the problem.
    """
    with open(file_name, "r") as f:
        data = json.load(f)

    new_data = {}
    correctness = None
    for key in data.keys():
        if "is_correct" in key or "correct_ans" in key or "check_result" in key:
            
            if 'is_correct' in key:
                correctness = data[key]
        else:
            new_data[key] = data[key]
    output_dictionary = json.dumps(new_data)
    return [output_dictionary, correctness]

def define_task(task_name, task_description, successful_responses, unsuccessful_responses, additional_considerations=None):
    ''' This function defines the task to be evaluated'''
    task = {
        "Task name": task_name, 
        "Task description": task_description
    }
    
    for i, response in enumerate(successful_responses):
        task[f"successful_response_{i}"] = response
    
    for i, response in enumerate(unsuccessful_responses):
        task[f"unsuccessful_response_{i}"] = response
    
    if additional_considerations:
        task["additional_considerations"] = additional_considerations
    
    return task


def ask_critic(task, critic_user, critics, write_file=True):


    task_items = '\n'.join([f'{k}: {v}' for k, v in task.items()])
    request = f"""I need your help to evaluate the task: {task_items} """

    critic_user.initiate_chat(critics, message=request)
    criteria = critic_user.last_message()['content']
    
    if write_file:
        cr_file = open(f"./{task['Task name']}_criteria.json", "w")
        cr_file.write(criteria)
        cr_file.close()
        
    return criteria

def ignore_criteria(criteria_dict, ignore_list):
    ''' This function ignores the criteria'''
    for key in ignore_list:
        criteria_dict.pop(key, None)
    return criteria_dict

def assess_task(response_to_eval, task, criteria_dict, quantifier_user, quantifier, criteria_to_ignore=None, write_file=True):
    
    
    if criteria_to_ignore is not None:
        criteria_dict = ignore_criteria(criteria_dict, criteria_to_ignore)
        
    ''' This function assesses the task'''
    
    request = f"""I need your help to evaluate the task: {'/n'.join([f'{k}: {v}' for k, v in task.items()])} 
    
            \n Evaluation dictionary: {criteria_dict}
            \n
            \n RESPONSE TO EVALUATE: {response_to_eval}"""

    quantifier_user.initiate_chat(quantifier, message=request)
    assessment = quantifier_user.last_message()['content']
    

    if write_file:
        assess_file = open(f"./{task['Task name']}_assessment.json", "w")
        assess_file.write(assessment)
        assess_file.close()

    return assessment


def load_question_dict_format():
    ''' This function loads the question dict format'''
    
    sample_question_dict = {
        1: {
            "Question": "",
            "GT": {"Run Agents": [], "Final Answer": ""},
            "Type": "Direct"
        }
    }
    return sample_question_dict

def gather_agent_response(question_dict, agent_worklow):
    ''' This function gathers the agent response'''

    response_dict = {}
    
    for question_id, question in question_dict.items():


        query = question['Question']
        response_dict[question_id] = {'Question': query, 'Question Type': question['Type'], 
                                      'Correct Approach and Answer': question['GT']}

        start_time = time.time()
        try:
            agent_worklow.run_network(query)
        except Exception as e:
            print(f"Failed to run question: {query}. Got this error {e}")
            continue
        end_time = time.time()
        execution_time = end_time - start_time

        results = {}
        results['Planner Response'] = agent_worklow.planner_response # planner response
        
        
        results['Agents chosen to run by Orchestrator']= agent_worklow.orchestrator_chosen_agents   # orchastrator response
        results['Agent Responses/Messages'] = agent_worklow.agent_responses # individual agent responses
        
        
        results['Final Response Context'] = agent_worklow.presenter_context # final response context
        results['Final Response'] = agent_worklow.presenter_response # final response from presenter
        results['Execution Time'] = execution_time        
        response_dict[question_id]['Results']=results  
        
    
    return response_dict

    
    
def save_output(response_dict, file_name):
    ''' This function saves the output'''
    
    if '.json' not in file_name:
        file_name = file_name + '.json'
        
    with open(file_name, 'w') as f:
        json.dump(response_dict, f)

    
