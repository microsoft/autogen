import openai
import tiktoken

class ChatCompletionProxy():
    @classmethod
    def _prompt_tokens(cls, messages):
        # Get the encoding for OpenAI's "cl100k_base" model
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # Calculate the total number of tokens in the prompt
        # by iterating over each message in the 'messages' list,
        # encoding its content, and summing up the token counts.
        return sum([len(encoding.encode(msg['content'])) for msg in messages])

    @classmethod
    def create(cls, *args, **kwargs):
        # Check if streaming is enabled in the function arguments
        if kwargs.get("stream", False):
            response_content = ""
            completion_tokens = 0
            
            # Set the terminal text color to green for better visibility
            print("\033[32m", end='')
            
            # Send the chat completion request to OpenAI's API and process the response in chunks
            for chunk in openai.ChatCompletion.create(*args, **kwargs):
                if chunk["choices"]:
                    content = chunk["choices"][0].get("delta", {}).get("content")
                    # If content is present, print it to the terminal and update response variables
                    if content is not None:
                        print(content, end='', flush=True)
                        response_content += content
                        completion_tokens += 1
            
            # Reset the terminal text color
            print("\033[0m\n")
            
            # Prepare the final response object based on the accumulated data
            response = chunk
            response["choices"][0]["message"] = {
                'role': 'assistant',
                'content': response_content
            }
            
            prompt_tokens = cls._prompt_tokens(kwargs["messages"])
            # Add usage information to the response
            response["usage"] = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        else:
            # If streaming is not enabled, send a regular chat completion request
            response = openai.ChatCompletion.create(*args, **kwargs)
        
        # Return the final response object
        return response
