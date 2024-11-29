from autogen_core.components.models import UserMessage
from exts.models.litellm.litellm_providers import MistralAiCompletionClient,OllamaChatCompletionClient

import litellm,os
from autogen_core.components.tools import FunctionTool
from autogen_core.components.tools import Tool, ToolSchema,ParametersSchema
from exts.tools.custom_tools_impl import JsonSchemaTool
# 设置可观察性
litellm.success_callback = ["langfuse"]
os.environ['LANGFUSE_SECRET_KEY']="sk-lf-b7935a49-5e9e-4ef7-ba5c-343f1d77456c"
os.environ['LANGFUSE_PUBLIC_KEY']="pk-lf-26e16ca6-57a6-40d8-9d91-930d5b19de48" 
os.environ['LANGFUSE_HOST']="http://127.0.0.1:13001"

def get_ollama_client() -> OllamaChatCompletionClient:
    return OllamaChatCompletionClient(
        model="qwen2.5:14b-instruct-q4_K_M",
         temperature=0.3,max_tokens=100
    )


def get_mistral_client() -> MistralAiCompletionClient:
    return MistralAiCompletionClient(
        model="mistral-large-latest",
        api_key="mqsnQ0WeuaGCbUmrvN3bcBHgkfKCClx7",
         temperature=0.3,max_tokens=10
    )


#model = get_mistral_client()
model = get_ollama_client()
messages = [
    UserMessage(content="计算十乘以16等于多少",source=None),
]

tool_schema=ToolSchema()
tool_schema['name']="cal"
tool_schema['description']="用于数学计算的工具"
ps = ParametersSchema()
tool_schema['parameters']=ps
ps['type']= "object"

ps['properties']={
                    "a": {
                        "type": "string",
                        "description": "第一操作数"
                    },
                    "opt": {
                        "type": "string",
                        "description": "运算符"
                    },
                    "b": {
                        "type": "string",
                        "description": "第二操作数"
                    },
                }



import asyncio
response =  asyncio.run(model.create(messages=messages,tools=[JsonSchemaTool(tool_schema,'cal',"用于数学计算的工具")]))
print(response)