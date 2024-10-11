import json

from pydantic import BaseModel


class Task(BaseModel):
    """
    Class representing a task for agent completion, includes example agent execution for criteria generation.
    """

    name: str
    description: str
    successful_response: str
    failed_response: str

    def get_sys_message(self):
        return f"""Task: {self.name}.
        Task description: {self.description}
        Task successful example: {self.successful_response}
        Task failed example: {self.failed_response}
        """

    @staticmethod
    def parse_json_str(task: str):
        """
        Create a Task object from a json object.
        Args:
            json_data (dict): A dictionary that represents the task.
        Returns:
            Task: A Task object that represents the json task information.
        """
        json_data = json.loads(task)
        name = json_data.get("name")
        description = json_data.get("description")
        successful_response = json_data.get("successful_response")
        failed_response = json_data.get("failed_response")
        return Task(name, description, successful_response, failed_response)
