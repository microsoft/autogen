from autogen import oai


class TextAnalyzer():
    """ Analyzes the content of text as instructed in each call. """
    def __init__(self, use_cache):
        self.use_cache = use_cache

        # Prepare the system prompt.
        system_message_text = """You are a helpful assistant specializing in content analysis."""
        system_message = {"role": "system", "content": system_message_text}
        self.base_messages = [system_message]

    def analyze(self, llm_config, text_to_analyze, analysis_instructions):
        # Assembled the messages.
        messages = self.base_messages.copy()
        messages.append({"role": "user", "content": text_to_analyze})
        messages.append({"role": "user", "content": analysis_instructions})

        # Get the response.
        response = oai.ChatCompletion.create(context=None, messages=messages, use_cache=self.use_cache, **llm_config)
        response_text = oai.ChatCompletion.extract_text_or_function_call(response)[0]
        return response_text
