import openai
import tiktoken

from openai.openai_object import OpenAIObject


class ChatCompletionProxy:
    @classmethod
    def _prompt_tokens(cls, messages):
        # Get the encoding for OpenAI's "cl100k_base" model
        encoding = tiktoken.get_encoding("cl100k_base")

        # Calculate the total number of tokens in the prompt
        # by iterating over each message in the 'messages' list,
        # encoding its content, and summing up the token counts.
        return sum([len(encoding.encode(msg["content"])) for msg in messages])

    @classmethod
    def create(cls, *args, **kwargs):
        # Check if streaming is enabled in the function arguments
        if kwargs.get("stream", False) and "functions" not in kwargs:
            # Prepare response array based on parameter 'n'
            response_contents = [""] * kwargs.get("n", 1)
            finish_reasons = [""] * kwargs.get("n", 1)
            completion_tokens = 0

            # Set the terminal text color to green for better visibility
            print("\033[32m", end="")

            # Send the chat completion request to OpenAI's API and process the response in chunks
            for chunk in openai.ChatCompletion.create(*args, **kwargs):
                if chunk["choices"]:
                    for choice in chunk["choices"]:
                        content = choice.get("delta", {}).get("content")
                        # If content is present, print it to the terminal and update response variables
                        if content is not None:
                            print(content, end="", flush=True)
                            response_contents[choice.index] += content
                            finish_reasons[choice.index] = choice.get("finish_reasons", None)
                            completion_tokens += 1
                        else:
                            print()

            # Reset the terminal text color
            print("\033[0m\n")

            # Prepare the final response object based on the accumulated data
            prompt_tokens = cls._prompt_tokens(kwargs["messages"])
            response = OpenAIObject()
            response.id = chunk["id"]
            response.object = "chat.completion"
            response.created = chunk["created"]
            response.model = chunk["model"]
            response.choices = []
            response.usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }
            for i in range(len(response_contents)):
                response["choices"].append(
                    {
                        "index": i,
                        "finish_reason": finish_reasons[i],
                        "message": {"role": "assistant", "content": response_contents[i]},
                    }
                )
        else:
            # If streaming is not enabled, send a regular chat completion request
            # Ensure streaming is disabled
            kwargs["stream"] = False
            response = openai.ChatCompletion.create(*args, **kwargs)

        # Return the final response object
        return response
