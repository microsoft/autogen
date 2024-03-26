class Task:
    def __init__(self, name, description, successful_response, failed_response):
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
    def from_json(json_data):
        name = json_data.get("name")
        description = json_data.get("description")
        successful_response = json_data.get("successful_response")
        failed_response = json_data.get("failed_response")
        return Task(name, description, successful_response, failed_response)
