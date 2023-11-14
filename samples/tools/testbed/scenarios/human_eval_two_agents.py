import os
import json
import base64
import testbed_utils
import autogen

# NOTE:
# This scenario runs Human Eval in a slightly unconventional way:
# The agents have access to the unit tests, and can keep trying
# until they pass.

testbed_utils.init()
##############################

work_dir = "coding"

# These come formatted as Base64 to avoid conflicting with the triple-quotes
TESTS = base64.b64decode("__TEST_BASE64__").decode("utf-8")
PROMPT = base64.b64decode("__PROMPT_BASE64__").decode("utf-8")

# Write the tests to a file so that the agents can access them
if not os.path.isdir(work_dir):
    os.mkdir(work_dir)
with open(os.path.join(work_dir, "my_tests.py"), "wt") as fh:
    fh.write(
        TESTS
        + """


def run_tests(candidate):
   check(candidate)
   # We can search for this string in the output
   print("ALL TESTS PASSED !#!#\\nTERMINATE")
"""
    )


# Ok, now get autogen to solve it.
config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["__MODEL__"]},
)

assistant = autogen.AssistantAgent(
    "assistant",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config=testbed_utils.default_llm_config(config_list, timeout=180),
)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": work_dir,
        "use_docker": False,
    },
    max_consecutive_auto_reply=10,
    default_auto_reply="TERMINATE",
)
user_proxy.initiate_chat(
    assistant,
    message="""
The following python code imports the `run_tests(candidate)` function from my_tests.py, and runs
it on the function `__ENTRY_POINT__`. This will run a set of automated unit tests to verify the
correct implementation of `__ENTRY_POINT__`. However, `__ENTRY_POINT__` is only partially
implemented in the code below. Complete the implementation of `__ENTRY_POINT__` and output
a new stand-alone code block that contains everything needed run the tests, including: importing
`my_tests`, calling `run_tests(__ENTRY_POINT__)`, as well as __ENTRY_POINT__'s comepelte definition,
such that this code block can be run direcly in Python.

```python
from my_tests import run_tests


"""
    + PROMPT
    + """


# Run the unit tests
run_tests(__ENTRY_POINT__)
```
""",
)


##############################
testbed_utils.finalize(agents=[assistant, user_proxy])
