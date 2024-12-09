from llama_index.core.callbacks import CallbackManager
from langfuse.llama_index import LlamaIndexCallbackHandler
from llama_index.llms.openai_like import OpenAILike

langfuse_callback_handler = LlamaIndexCallbackHandler(
    public_key="pk-lf-05e5e78f-dffc-43ef-93ae-cf3c885d695b",
    secret_key="sk-lf-7838d833-99dc-4eb7-9955-4f8cce5e0db1",
    host="http://127.0.0.1:13001"
)
from llama_index.core import Settings
Settings.callback_manager = CallbackManager([langfuse_callback_handler])

# Define a tool
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."
from llama_index.core.agent.react.step import ReActAgentWorker
from llama_index.core.tools import BaseTool, FunctionTool

tools=[FunctionTool.from_defaults(async_fn=get_weather)]
llm = OpenAILike(model="qwen2.5:14b-instruct-q4_K_M",is_chat_model=True,is_function_calling_model=False,
                 api_base="http://127.0.0.1:11434/v1",api_key="fake",temperature=0.3,max_tokens=200)
agent = ReActAgentWorker.from_tools(tools=tools,llm=llm).as_agent()

rsp = agent.chat("深圳今天的天气怎么样")
print(rsp)
