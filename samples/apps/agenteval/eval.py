""" This python file provides tool to to evaluate the performance of the agents."""

import autogen
import json

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
        They should be dinstinguishable, quantifieable and related to the overall theme of the critics provided criteria.
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
        with the assessed performance based on accepted values for each subcriteria. Make sure to return a valid json and not a python dictionary and do not
        return anything other then the assessment - no additional text"""

additional_considerations_message_base = "\n You must take into account these considerations provided by the user: "


class EvalWorkflow:
    def __init__(
        self,
        task,
        critic_llm_config,
        subcritic_llm_config,
        quantifier_llm_config,
        critic_manager_llm_config=None,
    ):
        self.task = task
        self.critic = Critic(critic_llm_config).agent
        self.subcritic = SubCritic(subcritic_llm_config).agent
        self.critic_user = get_default_critic_user()
        self.quantifier = Quantifier(quantifier_llm_config).agent
        self.quantifier_user = get_default_quantifier_user()
        self.criteria = None
        self.file_name = None

        agents = [self.critic_user, self.critic, self.subcritic]

        groupchat = autogen.GroupChat(agents=agents, messages=[], max_round=12, speaker_selection_method="round_robin")

        self.critic_manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=critic_manager_llm_config)

    def run_critic_workflow(self, write_file=False):
        """This function runs the generates the criteria for the task"""
        task_items = "\n".join([f"{k}: {v}" for k, v in self.task.items()])
        request = f"""I need your help to evaluate the task: {task_items} """

        self.critic_user.initiate_chat(self.critic_manager, message=request)
        self.criteria = self.critic_user.last_message()["content"]

        if write_file:
            self.file_name = f"./{self.task['Task name']}_criteria.json"
            cr_file = open(self.file_name, "w")
            cr_file.write(self.criteria)
            cr_file.close()

        return self.criteria

    def run_quantifier_workflow(self, response_to_eval, criteria, criteria_to_ignore=None, write_file=False):
        """This function assesses the task"""
        if criteria_to_ignore is not None:
            criteria = ignore_criteria(criteria, criteria_to_ignore)

        id_ = list(response_to_eval.keys())[0]
        response = response_to_eval[id_]

        request = f"""I need your help to evaluate the task: {'/n'.join([f'{k}: {v}' for k, v in self.task.items()])}

                    \n Evaluation dictionary: {criteria}
                    \n
                    \n RESPONSE TO EVALUATE: question_id={id_} with response={response}"""

        self.quantifier_user.initiate_chat(self.quantifier, message=request)
        assessment = self.quantifier_user.last_message()["content"]

        if write_file:
            assess_file = open(f"./{self.task['Task name']}_assessment.json", "a")
            assess_file.write(assessment)
            assess_file.write("\n\n")
            assess_file.close()

        return assessment

    def run_workflow(self, response_to_eval, write_file=False):
        """This function runs the entire workflow for the given task. It generates the criteria and then assesses the task based on the criteria."""
        if self.criteria is None:
            self.criteria = self.run_critic_workflow(write_file)

        assessment_dict = self.run_quantifier_workflow(response_to_eval, self.criteria, write_file=write_file)

        return assessment_dict


class Critic:
    """This class is used to create a critic agent"""

    def __init__(self, critic_llm_config, critic_with_sub=True, additional_considerations=None):
        critic_message = worfklow_critic_message_base if critic_with_sub else original_critic_message_base

        if additional_considerations:
            critic_message += additional_considerations_message_base + additional_considerations

        self.agent = autogen.AssistantAgent(name="critic", system_message=critic_message, llm_config=critic_llm_config)


class SubCritic:
    """This class is used to create a subcritic agent"""

    def __init__(self, subcritic_llm_config, additional_considerations=None):
        subcritic_message = sub_critic_message_base

        if additional_considerations:
            subcritic_message += additional_considerations_message_base + additional_considerations
        self.agent = autogen.AssistantAgent(
            name="sub_critic", system_message=subcritic_message, llm_config=subcritic_llm_config
        )


class Quantifier:
    """This class is used to create a quantifier agent"""

    def __init__(self, quantifier_llm_config, critic_with_sub=True, additional_considerations=None):
        quantifier_message = workflow_quantifier_message_base if critic_with_sub else original_quantifier_message_base

        if additional_considerations:
            quantifier_message += additional_considerations_message_base + additional_considerations

        self.agent = autogen.AssistantAgent(
            name="quantifier",
            llm_config=quantifier_llm_config,
            system_message=quantifier_message,
        )


def get_default_critic_user():
    """This function returns the default critic user"""

    critic_user = autogen.UserProxyAgent(
        name="critic_user",
        max_consecutive_auto_reply=0,
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )

    return critic_user


def get_default_quantifier_user():
    """This function returns the default quantifier user"""

    quantifier_user = autogen.UserProxyAgent(
        name="quantifier_user",
        max_consecutive_auto_reply=0,
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False},
    )
    return quantifier_user


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
            if "is_correct" in key:
                correctness = data[key]
        else:
            new_data[key] = data[key]
    output_dictionary = json.dumps(new_data)
    return [output_dictionary, correctness]


def define_task(
    task_name, task_description, successful_responses, unsuccessful_responses, additional_considerations=None
):
    """This function defines the task to be evaluated"""
    task = {"Task name": task_name, "Task description": task_description}

    for i, response in enumerate(successful_responses):
        task[f"successful_response_{i}"] = response

    for i, response in enumerate(unsuccessful_responses):
        task[f"unsuccessful_response_{i}"] = response

    if additional_considerations:
        task["additional_considerations"] = additional_considerations

    return task


def ignore_criteria(criteria_dict, ignore_list):
    """This function ignores the criteria"""
    for key in ignore_list:
        criteria_dict.pop(key, None)
    return criteria_dict
