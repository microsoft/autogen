with open("python/packages/autogen-ext/src/autogen_ext/models/openai/_transformation/registry.py", "r") as f:
    content = f.read()

old_code = """            register_transformer(
                "gpt-4o",
                {
                    UserMessage: user_message_to_oai,
                    SystemMessage: system_message_to_oai,
                },
            )"""

new_code = """            register_transformer(
                "openai",
                "gpt-4o",
                {
                    UserMessage: user_message_to_oai,
                    SystemMessage: system_message_to_oai,
                },
            )"""

content = content.replace(old_code, new_code)
with open("python/packages/autogen-ext/src/autogen_ext/models/openai/_transformation/registry.py", "w") as f:
    f.write(content)
