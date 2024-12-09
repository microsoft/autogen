from autogen_core.components import FunctionCall

from llama_index.core.tools import BaseTool, FunctionTool as LlamaIndexFunctionTool,ToolOutput


def ag_function_call_convert(llama_tool_output:ToolOutput)-> list[FunctionCall]:
    return [FunctionCall(id=llama_tool_output.tool_name,
                         name=llama_tool_output.tool_name,
                         arguments=str(llama_tool_output.raw_input['args']))]