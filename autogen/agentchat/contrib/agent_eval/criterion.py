from __future__ import annotations

import json
from typing import List, Optional

import pydantic_core
from pydantic import BaseModel
from pydantic.json import pydantic_encoder


class Criterion(BaseModel):
    """
    A class that represents a criterion for agent evaluation.
    """

    name: str
    description: str
    accepted_values: Optional[List[str]] = None
    sub_criteria: Optional[List[Criterion]] = None

    @staticmethod
    def parse_json_str(criteria: str):
        """
        Create a list of Criterion objects from a json string.
        Args:
            criteria (str): Json string that represents the criteria
        returns:
            [Criterion]: A list of Criterion objects that represents the json criteria information.
        """
        def parse_dict(crit: dict):  
            if 'sub_criteria' in crit:  
                crit['sub_criteria'] = [parse_dict(c) for c in crit['sub_criteria']]
            return Criterion(**crit)  
  
        criteria_list = json.loads(criteria)  
        return [parse_dict(crit) for crit in criteria_list] 

    @staticmethod
    def write_json(criteria):
        """
        Create a json string from a list of Criterion objects.
        Args:
            criteria ([Criterion]): A list of Criterion objects.
        Returns:
            str: A json string that represents the list of Criterion objects.
        """
        return json.dumps([crit.dict(exclude_unset=True) for crit in criteria], indent=2, default=str)  
