with open("python/packages/autogen-ext/src/autogen_ext/models/cache/_chat_completion_cache.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "self._check_cache(" in line and "messages, tools, json_output, extra_create_args" in lines[i+1]:
        lines[i+1] = lines[i+1].replace("messages, tools, json_output, extra_create_args", "messages, tools, tool_choice, json_output, extra_create_args")

with open("python/packages/autogen-ext/src/autogen_ext/models/cache/_chat_completion_cache.py", "w") as f:
    f.writelines(lines)
