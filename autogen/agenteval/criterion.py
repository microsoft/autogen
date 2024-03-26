import json


class Criterion:
    def __init__(self, name, description, accepted_values):
        self.name = name
        self.description = description
        self.accepted_values = accepted_values

    def to_json(self):
        return {self.name: {"description": self.description, "accepted_values": self.accepted_values}}

    @staticmethod
    def parse_json_str(criteria: str):
        criteria_list = []
        parsed_json = json.loads(criteria)
        for criterion_name, criterion_data in parsed_json.items():
            criterion = Criterion(criterion_name, criterion_data["description"], criterion_data["accepted_values"])
            criteria_list.append(criterion)
        return criteria_list

    @staticmethod
    def write_json(criteria):
        criteria_json = {}
        for criterion in criteria:
            criteria_json.update(criterion.to_json())
        return json.dumps(criteria_json)
