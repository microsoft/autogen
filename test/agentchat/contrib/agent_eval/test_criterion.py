#!/usr/bin/env python3 -m pytest

from autogen.agentchat.contrib.agent_eval.criterion import Criterion


def test_parse_json_str():
    criteria_file = "test/test_files/agenteval-in-out/samples/sample_math_criteria.json"
    criteria = open(criteria_file, "r").read()
    criteria = Criterion.parse_json_str(criteria)
    assert criteria
    assert len(criteria) == 6
    assert criteria[0].name == "Problem Interpretation"
    assert criteria[0].description == "Ability to correctly interpret the problem."
    assert len(criteria[0].accepted_values) == 5


def test_write_json():
    criteria1 = Criterion(name="test1", description="test1 description", accepted_values=["test1", "test2"])
    criteria2 = Criterion(name="test2", description="test2 description", accepted_values=["test1", "test2"])
    output = Criterion.write_json([criteria1, criteria2])
    assert (
        output
        == """[
  {
    "name": "test1",
    "description": "test1 description",
    "accepted_values": [
      "test1",
      "test2"
    ],
    "sub_criteria": []
  },
  {
    "name": "test2",
    "description": "test2 description",
    "accepted_values": [
      "test1",
      "test2"
    ],
    "sub_criteria": []
  }
]"""
    )


def test_write_parse_compatibility():
    criterion1 = Criterion(name="test1", description="test1 description", accepted_values=["test1", "test2"])
    criterion2 = Criterion(name="test2", description="test2 description", accepted_values=["test1", "test2"])

    output = Criterion.write_json([criterion1, criterion2])
    criteria = Criterion.parse_json_str(output)
    assert criteria
    assert len(criteria) == 2
    assert criteria[0].name == "test1"
    assert criteria[0].description == "test1 description"
    assert len(criteria[0].accepted_values) == 2
    assert criteria[1].name == "test2"
    assert criteria[1].description == "test2 description"
    assert len(criteria[1].accepted_values) == 2
