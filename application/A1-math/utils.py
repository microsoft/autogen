import datasets
import re
import os
import json

math_type_mapping = {
    "Algebra": "algebra",
    "Counting & Probability": "counting_and_probability",
    "Geometry": "geometry",
    "Intermediate Algebra": "intermediate_algebra",
    "Number Theory": "number_theory",
    "Prealgebra": "prealgebra",
    "Precalculus": "precalculus",
}


def write_json(dict_to_save, file):
    """Write a dictionary to a json file.
    Args:

        dict_to_save (dict): The dictionary to save.
        file (str): The file to save to.
    """
    jstring = json.dumps(dict_to_save, indent=2)
    with open(file, "w") as j:
        j.write(jstring)


class mylogger:
    def __init__(self, file) -> None:
        self.file = file

    def log(self, message, verbose=True):
        """Print the message.
        Args:
            message (str): The message to print.
        """
        with open(self.file, "a") as f:
            f.write(message + "\n")
        if verbose:
            print(message, flush=True)


def load_samples(base_dir, num_samples=10):
    # List of directories to search for .json files
    folders = [
        "algebra",
        "number_theory",
        "counting_and_probability",
        "prealgebra",
        "intermediate_algebra",
        "precalculus",
    ]

    samples = {}

    for folder in folders:
        folder_path = os.path.join(base_dir, folder)

        # Check if directory exists
        if not os.path.isdir(folder_path):
            print(f"Warning: {folder_path} not found!")
            continue

        # Load each .json file up to num_samples
        for i in range(num_samples):
            file_path = os.path.join(folder_path, f"{i}.json")

            # Check if file exists
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found!")
                continue

            with open(file_path, "r") as file:
                data = json.load(file)

            # Append to the dictionary with a folder-wise key
            if folder not in samples:
                samples[folder] = []
            samples[folder].append(data)

    return samples


# def load_fixed(folder, category_to_load=None):
#     category_to_load = [i for i in range(7)] if not category_to_load or "all" in category_to_load else category_to_load
#     category_to_load = [int(x) for x in category_to_load]
#     sep_cat = []

#     for i, category in enumerate(math_type_mapping.keys()):
#         if i not in category_to_load:
#             continue

#         c = math_type_mapping[category]
#         sep_cat.append([])
#         for i in range(20):
#             try:
#                 with open(os.path.join(folder, c, f"{i}.json"), "r") as fp:
#                     problem = json.load(fp)
#             except Exception:
#                 continue
#             del problem["is_valid_reply"]
#             del problem["is_correct"]
#             del problem["correct_ans"]
#             del problem["voted_answer"]
#             del problem["round"]
#             del problem["valid_q_count"]
#             del problem["total_q_count"]
#             del problem["cost"]
#             del problem["messages"]

#             sep_cat[-1].append(problem)
#     return sep_cat


# def load_level5_math_test_each_category(samples_per_category=20, category_to_load=None):
#     """
#     Load level 5 math problems from the testset of competition dataset.
#     Returns:
#         A list of list of problems. Each list of problems is of the same category.
#     """
#     category_to_load = [i for i in range(7)] if not category_to_load or "all" in category_to_load else category_to_load
#     category_to_load = [int(x) for x in category_to_load]
#     data = datasets.load_dataset("competition_math")
#     test_data = data["test"]
#     sep_cate = []
#     for i, category in enumerate(math_type_mapping.keys()):
#         if i not in category_to_load:
#             print(i, category, "(skipped)", flush=True)
#             continue
#         tmp = [
#             test_data[x]
#             for x in range(len(test_data))
#             if test_data[x]["level"] == "Level 5" and test_data[x]["type"] == category
#         ]
#         # if len(tmp) < samples_per_category:
#         #     print(f"Warning: {category} has {len(tmp)} problems.", flush=True)

#         sep_cate.append(tmp[:samples_per_category])
#         print(i, category, f"{len(sep_cate[-1])} problems loaded", flush=True)

#     if len(sep_cate) == 0:
#         raise ValueError("No category is loaded.")
#     return sep_cate


# def load_level5_math_test(num_samples=100):
#     data = datasets.load_dataset("competition_math")
#     test_data = data["test"]
#     level_5 = [test_data[x] for x in range(len(test_data)) if test_data[x]["level"] == "Level 5"]
#     return level_5[:num_samples]


# def random_sample_MATH(num_samples=100):
#     """
#     Load level 5 math problems from the competition dataset.
#     Returns:
#         A list of list of problems. Each list of problems is of the same category.
#     """
#     seed = 41
#     data = datasets.load_dataset("competition_math")
#     test_data = data["test"].shuffle(seed=seed)

#     test_data = [test_data[x] for x in range(min(num_samples, len(test_data)))]

#     sep_cate = []
#     for i, category in enumerate(math_type_mapping.keys()):
#         sep_cate.append([test_data[x] for x in range(len(test_data)) if test_data[x]["type"] == category])
#         print(i, category, f"{len(sep_cate[-1])} problems sampled ", flush=True)

#     if len(sep_cate) == 0:
#         raise ValueError("No category is loaded.")
#     return sep_cate


def remove_asy_sections(input_string):
    """Remove asy sections from the input string.

    Args:
        input_string (str): The input string.
    Returns:
        str: The string without asy sections.
    """
    pattern = r"\[asy\](.*?)\[\\asy\]"
    output_string = re.sub(pattern, "", input_string, flags=re.DOTALL)
    pattern = r"\[asy\](.*?)\[/asy\]"
    output_string = re.sub(pattern, "", output_string, flags=re.DOTALL)
    pattern = r"\[ASY\](.*?)\[\\ASY\]"
    output_string = re.sub(pattern, "", output_string, flags=re.DOTALL)
    pattern = r"\[ASY\](.*?)\[/ASY\]"
    output_string = re.sub(pattern, "", output_string, flags=re.DOTALL)
    return output_string
