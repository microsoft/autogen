import json


class Task:
    """
    Class representing a task for agent completion, includes example agent execution for criteria generation.
    """

    def __init__(self, name: str, description: str, successful_response: str, failed_response: str):
        """
        args:
        - name (str): The name of the task.
        - description (str): The description of the task.
        - successful_response (str): An example of a successful response execution.
        - failed_response (str): An example of a failed response execution.
        """
        self.name = name
        self.description = description
        self.successful_response = successful_response
        self.failed_response = failed_response
        self.sys_msg = f"""Task: {self.name}.
    Task description: {self.description}
    Task successful example: {self.successful_response}
    Task failed example: {self.failed_response}
    """

    @staticmethod
    def parse_json_str(task: str):
        """
        Create a Task object from a json object.
        args:
        - json_data (dict): A dictionary that represents the task.
        returns:
        - Task: A Task object that represents the json task information.
        """
        json_data = json.loads(task)
        name = json_data.get("name")
        description = json_data.get("description")
        successful_response = json_data.get("successful_response")
        failed_response = json_data.get("failed_response")
        return Task(name, description, successful_response, failed_response)
