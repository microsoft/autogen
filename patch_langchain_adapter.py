with open("python/packages/autogen-ext/src/autogen_ext/tools/langchain/_langchain_adapter.py", "r") as f:
    content = f.read()

import re

# Add ConfigDict import if not present
if "from pydantic import ConfigDict" not in content:
    content = content.replace("from pydantic import BaseModel, Field, create_model", "from pydantic import BaseModel, ConfigDict, Field, create_model")

# Add __config__ to create_model
content = re.sub(
    r'args_type = create_model\(f"\{name\}Args", \*\*fields\)',
    'args_type = create_model(f"{name}Args", __config__=ConfigDict(arbitrary_types_allowed=True), **fields)',
    content
)

with open("python/packages/autogen-ext/src/autogen_ext/tools/langchain/_langchain_adapter.py", "w") as f:
    f.write(content)
