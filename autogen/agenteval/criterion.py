import json


class Criterion:
    """
    A class that represents a criterion for agent evaluation.
    """

    def __init__(self, name: str, description: str, accepted_values: [str]):
        """
        args:
        - name (str): The name of the criterion.
        - description (str): The description of the criterion.
        - accepted_values ([str]): The list of accepted values for the criterion.
        """
        self.name = name
        self.description = description
        self.accepted_values = accepted_values

    def to_json(self):
        """
        Create a json object from the criterion.
        """
        return {self.name: {"description": self.description, "accepted_values": self.accepted_values}}

    @staticmethod
    def parse_json_str(criteria: str):
        """
        Create a list of Criterion objects from a json string.
        args:
        - criteria (str): Json string that represents the criteria
        returns:
        - [Criterion]: A list of Criterion objects that represents the json criteria information.
        """
        criteria_list = []
        parsed_json = json.loads(criteria)
        for criterion_name, criterion_data in parsed_json.items():
            criterion = Criterion(criterion_name, criterion_data["description"], criterion_data["accepted_values"])
            criteria_list.append(criterion)
        return criteria_list

    @staticmethod
    def write_json(criteria):
        """
        Create a json string from a list of Criterion objects.
        args:
        - criteria ([Criterion]): A list of Criterion objects.
        returns:
        - str: A json string that represents the list of Criterion objects.
        """
        criteria_json = {}
        for criterion in criteria:
            criteria_json.update(criterion.to_json())
        return json.dumps(criteria_json)
