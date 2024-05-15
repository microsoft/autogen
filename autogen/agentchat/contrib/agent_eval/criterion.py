from __future__ import annotations

import json
from typing import List

import pydantic_core
from pydantic import BaseModel
from pydantic.json import pydantic_encoder


class Criterion(BaseModel):
    """
    A class that represents a criterion for agent evaluation.
    """

    name: str
    description: str
    accepted_values: List[str]
    sub_criteria: List[Criterion] = list()

    @staticmethod
    def parse_json_str(criteria: str):
        """
        Create a list of Criterion objects from a json string.
        Args:
            criteria (str): Json string that represents the criteria
        returns:
            [Criterion]: A list of Criterion objects that represents the json criteria information.
        """
        return [Criterion(**crit) for crit in json.loads(criteria)]

    @staticmethod
    def write_json(criteria):
        """
        Create a json string from a list of Criterion objects.
        Args:
            criteria ([Criterion]): A list of Criterion objects.
        Returns:
            str: A json string that represents the list of Criterion objects.
        """
        return json.dumps([crit.model_dump() for crit in criteria], indent=2)
