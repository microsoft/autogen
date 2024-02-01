import sys
from autogen.oai.openai_utils import filter_config
from autogenbench.run_cmd import run_scenarios
from autogen import config_list_from_json

if __name__ == "__main__":

    config_list = config_list_from_json(env_or_file='OAI_CONFIG_LIST')

    # Add the model name to the tags to simplify filtering
    for entry in config_list:
        if "tags" not in entry:
            entry["tags"] = list()
        if entry["model"] not in entry["tags"]:
            entry["tags"].append(entry["model"])

    # Filter if requested
    filter_dict = {"tags": ['gpt-4-1106-preview']}
    config_list = filter_config(config_list, filter_dict)
    if len(config_list) == 0:
        sys.exit(
            f"The model configuration list is empty. This may be because the model filter 'gpt-4-1106-preview' returned 0 results."
        )

    run_scenarios(
        scenario="math/MATH/Tasks/math_autobuild.jsonl",
        n_repeats=1,
        is_native=True,
        config_list=config_list,
        requirements=None,
        docker_image=None,
        subsample=1,
    )