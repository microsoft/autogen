import re
import copy
from typing import List, Dict

import autogen


def response_preparer(
    inner_messages: List[Dict[str, str]],
    PROMPT: str,
    client: autogen.OpenAIWrapper,
) -> str:

    messages = [
        {
            "role": "user",
            "content": f"""Earlier you were asked the following:

{PROMPT}

Your team then worked diligently to address that request. Here is a transcript of that conversation:""",
        }
    ]

    for message in inner_messages:
        if not message.get("content"):
            continue
        message = copy.deepcopy(message)
        message["role"] = "user"
        messages.append(message)

    # ask for the final answer
    messages.append(
        {
            "role": "user",
            "content": f"""
Read the above conversation and output a FINAL ANSWER to the question. The question is repeated here for convenience:

{PROMPT}

""",
        }
    )

    response = client.create(context=None, messages=messages)
    if "finish_reason='content_filter'" in str(response):
        raise Exception(str(response))
    extracted_response = client.extract_text_or_completion_object(response)[0]

    # No answer
    if "unable to determine" in extracted_response.lower():
        print("\n>>>Making an educated guess.\n")
        messages.append({"role": "assistant", "content": extracted_response})
        messages.append(
            {
                "role": "user",
                "content": """
I understand that a definitive answer could not be determined. Please make a well-informed EDUCATED GUESS based on the conversation.

To output the educated guess, use the following template: EDUCATED GUESS: [YOUR EDUCATED GUESS]
Your EDUCATED GUESS should be a number OR as few words as possible OR a comma separated list of numbers and/or strings. DO NOT OUTPUT 'I don't know', 'Unable to determine', etc.
ADDITIONALLY, your EDUCATED GUESS MUST adhere to any formatting instructions specified in the original question (e.g., alphabetization, sequencing, units, rounding, decimal places, etc.)
If you are asked for a number, express it numerically (i.e., with digits rather than words), don't use commas, and don't include units such as $ or percent signs unless specified otherwise.
If you are asked for a string, don't use articles or abbreviations (e.g. for cities), unless specified otherwise. Don't output any final sentence punctuation such as '.', '!', or '?'.
If you are asked for a comma separated list, apply the above rules depending on whether the elements are numbers or strings.
""".strip(),
            }
        )

        response = client.create(context=None, messages=messages)
        if "finish_reason='content_filter'" in str(response):
            raise Exception(str(response))
        extracted_response = client.extract_text_or_completion_object(response)[0]

        return re.sub(r"EDUCATED GUESS:", "FINAL ANSWER:", extracted_response)
    else:
        return extracted_response
