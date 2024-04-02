import json


class TestCase:
    """
    A class that represents a test case for agent evaluation.
    """

    def __init__(self, test_details: dict, correctness: str):
        """
        args:
        - test_details (dict): The details of the test case (minus the ground truth).
        - correctness (str): The correctness of the agent's output.
        """
        self.test_details = test_details
        self.correctness = correctness

    def __str__(self):
        return str([self.test_details, self.correctness])

    @staticmethod
    def parse_json_str(test_case: str):
        """
        Create a TestCase object from a json string.
        args:
        - test_case (str): Json string that represents the test case

        returns:
        - TestCase: A TestCase object that represents the json test case information.
        """
        test_details = json.loads(test_case)
        # need to remove the ground truth from the test details
        correctness = test_details.pop("is_correct", None)
        test_details.pop("correct_ans", None)
        test_details.pop("check_result", None)
        return TestCase(test_details, correctness)
