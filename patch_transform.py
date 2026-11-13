with open("python/packages/autogen-ext/src/autogen_ext/models/openai/_message_transform.py", "r") as f:
    content = f.read()

old_content = """__unknown_models = list(
    set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models) - set(__llama_models)
)
__mistral_models = [model for model in total_models if ModelFamily.is_mistral(model)]

__unknown_models = list(
    set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models) - set(__mistral_models)
)"""

new_content = """__mistral_models = [model for model in total_models if ModelFamily.is_mistral(model)]

__unknown_models = list(
    set(total_models) - set(__openai_models) - set(__claude_models) - set(__gemini_models) - set(__llama_models) - set(__mistral_models)
)"""

content = content.replace(old_content, new_content)

# Update docstrings as well
# Docstring 1 in _message_transform.py
doc_old = """    transformer = get_transformer("openai", "gpt-4", type(llm_message))
    sdk_message = transformer(llm_message, context={})"""
doc_new = """    transformer = get_transformer("openai", "gpt-4", type(llm_message))
    sdk_message = transformer.get()(llm_message, context={})"""
content = content.replace(doc_old, doc_new)

with open("python/packages/autogen-ext/src/autogen_ext/models/openai/_message_transform.py", "w") as f:
    f.write(content)
