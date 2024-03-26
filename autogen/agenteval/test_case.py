class TestCase:
    def __init__(self, output_dictionary, correctness):
        self.output_dictionary = output_dictionary
        self.correctness = correctness

    def __str__(self):
        return str([self.output_dictionary, self.correctness])

    def create_from_file(file_name):
        """
        Read the mathproblem logs - bypassing any information about the ground truths.

        Args:
        - file_name (str): The single log file that wants to get evaluated.

        Returns:
        - str: The log file without any information about the ground truth answer of the problem.
        """
        f = open(file_name, "r").readlines()
        output_dictionary = ""
        for line in f:
            if "is_correct" not in line and "correct_ans" not in line and "check_result" not in line:
                output_dictionary += line
            elif "is_correct" in line:
                correctness = line.replace(",", "").split(":")[-1].rstrip().strip()
        return TestCase(output_dictionary, correctness)
