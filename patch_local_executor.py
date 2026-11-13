with open("python/packages/autogen-ext/src/autogen_ext/code_executors/local/__init__.py", "r") as f:
    content = f.read()

old_doc = """    Command line code is sanitized using regular expression match against a list of dangerous commands in order to prevent self-destructive
    commands from being executed which may potentially affect the users environment.
    Currently the only supported languages is Python and shell scripts."""

new_doc = """    The executor performs no content filtering and containment must come from the execution environment.
    Currently the only supported languages is Python and shell scripts."""

content = content.replace(old_doc, new_doc)

with open("python/packages/autogen-ext/src/autogen_ext/code_executors/local/__init__.py", "w") as f:
    f.write(content)
