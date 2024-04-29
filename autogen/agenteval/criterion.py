import json
from typing import List


class Criterion:
    """
    A class that represents a criterion for agent evaluation.
    """

    def __init__(self, name: str, description: str, accepted_values: List[str], sub_criteria=[]):
        """
        Args:
            name (str): The name of the criterion.
            description (str): The description of the criterion.
            accepted_values ([str]): The list of accepted values for the criterion.
            sub_criteria ([Criterion]): The list of sub-criteria for the criterion.
        """
        self.name = name
        self.description = description
        self.accepted_values = accepted_values
        self.sub_criteria = sub_criteria

    def to_json(self):
        """
        Create a json object from the criterion.
        """
        return {
            self.name: {
                "description": self.description,
                "accepted_values": self.accepted_values,
                "sub_criteria": [x.to_json() for x in self.sub_criteria],
            }
        }

    @staticmethod
    def parse_json_str(criteria: str):
        """
        Create a list of Criterion objects from a json string.
        Args:
            criteria (str): Json string that represents the criteria
        returns:
            [Criterion]: A list of Criterion objects that represents the json criteria information.
        """
        criteria_list = []
        parsed_json = json.loads(criteria)
        for criterion_name, criterion_data in parsed_json.items():
            sub_criteria = []
            accepted_values = ""
            if criterion_data.get("sub_criteria") is not None and len(criterion_data.get("sub_criteria")) > 0:
                sub_criteria = Criterion.parse_json_str(json.dumps(criterion_data.get("sub_criteria")))
            else:
                accepted_values = criterion_data.get("accepted_values")
            criterion = Criterion(criterion_name, criterion_data["description"], accepted_values, sub_criteria)
            criteria_list.append(criterion)
        return criteria_list

    @staticmethod
    def write_json(criteria):
        """
        Create a json string from a list of Criterion objects.
        Args:
            criteria ([Criterion]): A list of Criterion objects.
        Returns:
            str: A json string that represents the list of Criterion objects.
        """
        criteria_json = {}
        for criterion in criteria:
            criteria_json.update(criterion.to_json())
        return json.dumps(criteria_json, indent=2)
