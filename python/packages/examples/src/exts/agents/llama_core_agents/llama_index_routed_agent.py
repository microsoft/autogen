from collections import deque
import asyncio,json,logging,uuid
from typing import AsyncGenerator, Coroutine, List, Optional, Sequence, Union
from pydantic import Field
from typing_extensions import Self
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_core.base import CancellationToken
from autogen_agentchat.base import TaskResult, TerminationCondition
from autogen_core.base import CancellationToken

from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Sequence

from autogen_core.base import CancellationToken
from autogen_core.components import FunctionCall
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,

)
from autogen_agentchat.messages import (
    AgentMessage,
    ChatMessage,
    TextMessage,
    HandoffMessage,
    MultiModalMessage,
    TextMessage,
    ToolCallMessage,
    ToolCallResultMessage,
    StopMessage
)
from autogen_agentchat.agents import Handoff
from autogen_core.components.tools import FunctionTool, Tool

from autogen_core.components import FunctionCall, RoutedAgent, TypeSubscription, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    FunctionExecutionResult,
    FunctionExecutionResultMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from .llama_index_core_type import(
    AgentResponse
)
from autogen_core.base import MessageContext, TopicId

##### llamaIndex import ##################

from llama_index.core.agent.react.step import ReActAgentWorker
from llama_index.core.agent import ReActAgent,AgentRunner
from llama_index.core.agent.types import (
    BaseAgentWorker,
    Task,
    TaskStep,
    TaskStepOutput,
)
from llama_index.agent.openai import OpenAIAgentWorker, OpenAIAgent
from llama_index.core.llms.llm import LLM
from llama_index.core.tools import BaseTool, FunctionTool as LlamaIndexFunctionTool,ToolOutput
from llama_index.core.callbacks import (
    CallbackManager
)
from llama_index.core.callbacks.base import EventContext
from llama_index.core.agent.runner.base import TaskState
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.llms.openai import OpenAI

from llama_index.core.base.llms.types import MessageRole
from llama_index.core.base.llms.types import  ChatResponse as LlamaIndexChatResponse,ChatMessage as LlmaIndexCahtMessage
from llama_index.core.memory import BaseMemory, ChatMemoryBuffer
import llama_index.core.instrumentation as instrument


############### llama index end #############################################
AsyncCallable = Callable[..., Awaitable[Any]]
from ..llamaIndex_autogen_utils import ag_function_call_convert

dispatcher = instrument.get_dispatcher(__name__)

event_logger = logging.getLogger('LLAMA_INDEX_AGENT')
class LlamaIndexRoutedAgent(RoutedAgent):
    def __init__(
        self,
        name: str,
        factory: Callable[[list[BaseTool]], AgentRunner],
        next_agent_name:str,
        *,
        tools: List[BaseTool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        
        handoffs: List[Handoff | str] | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: str
        | None = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        callbackManager:CallbackManager=None,

    ):
        super().__init__(description=description)
        self.name=name
        self.next_agent_name=next_agent_name
        self._callbakcManager = callbackManager
        self._task_state=None
        
        # Handoff tools.
        self._handoff_tools: List[BaseTool] = []
        self._handoffs: Dict[str, Handoff] = {}
        self._tools: list[BaseTool] = []
        self.agent_runner = factory(self._build_tools(tools,handoffs))
        self.memory = self.agent_runner.memory
        if tools:
            tool_names = [tool.metadata.name for tool in self._tools]

            if len(tool_names) != len(set(tool_names)):
                raise ValueError(f"Tool names must be unique: {tool_names}")
        if system_message is None:
            self._system_messages = []
        else:
            self._system_messages = [SystemMessage(content=system_message)]
        # Check if handoff tool names are unique.
        handoff_tool_names = [tool.metadata.name for tool in self._handoff_tools]
        if len(handoff_tool_names) != len(set(handoff_tool_names)):
            raise ValueError(f"Handoff names must be unique: {handoff_tool_names}")
        # Check if handoff tool names not in tool names.
        if tools and  any(name in tool_names for name in handoff_tool_names):
            raise ValueError(
                f"Handoff names must be unique from tool names. Handoff names: {handoff_tool_names}; tool names: {tool_names}"
            )
        self._model_context: List[LLMMessage] = []

    @message_handler
    async def on_messages(self, messages: ChatMessage, ctx: MessageContext) ->  None:
        # Add messages to the model context.
        for msg in messages:
            if isinstance(msg, MultiModalMessage):
                raise ValueError("The model does not support vision.")
            self._model_context.append(UserMessage(content=msg.content, source=msg.source))
        user_input = messages[-1].content if len(messages)>0 else None
        
        result_output= None

        # Inner messages.
        inner_messages: List[AgentMessage] = []

        cur_step_output=None
        # Generate an inference result based on the current model context.
        task = self.get_or_create_task(user_input)
        while True:
            # pass step queue in as argument, assume step executor is stateless
            # ensure tool_choice does not cause endless loops
            tool_choice = "auto"
            cur_step_output = await self.agent_runner.arun_step(
                task.task_id
            )
            result_output = cur_step_output.output.response

             # Add the response to the model context.
            self._model_context.append(AssistantMessage(content=result_output, source=self.name))
            # 将最后的结果添加到memory模块中
            if cur_step_output.is_last:
                break
            else:
                # 临时的方案： 如果is_last为False，它必定是工具调用。通过
                tool_output:ToolOutput = cur_step_output.output.sources[-1]
                tool_call_msg = ToolCallMessage(content=ag_function_call_convert(tool_output), source=self.name)
                inner_messages.append(tool_call_msg)
                tool_call_result_msg = ToolCallResultMessage(content=[FunctionExecutionResult(tool_output.raw_output,"")], source=self.name)
                inner_messages.append(tool_call_result_msg)
                tool_output.tool_name
                # Detect handoff requests.
                if tool_output.tool_name in self._handoffs:
                    # Return the output messages to signal the handoff.
                    target_name=self._handoffs[tool_output.tool_name].target
                    await self.publish_message(message=Response(
                        chat_message=HandoffMessage(
                            content=tool_output.content, target=target_name, source=self.name
                        ),
                        inner_messages=inner_messages,
                    ),topic_id=TopicId(target_name, source=self.id.key))
                    return

        assert isinstance(result_output, str)
        result = self.agent_runner.finalize_response(
            task.task_id,
            cur_step_output,
        )
        if result.response:

            await self.publish_message(message=Response(
                        chat_message=TextMessage(content=result.response, source=self.name)),topic_id=TopicId(self.next_agent_name, source=self.id.key))
            return 
        else: 
            await self.publish_message(Response(
                chat_message=StopMessage(source=self.name,content="看起来你没有其他需要帮忙的了，那么我结束对话吧")),topic_id=TopicId(self.next_agent_name, source=self.id.key))
            return
    

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the assistant agent to its initialization state."""
        self._model_context.clear()
        self._task_state=None
        self.memory.reset()


    def _build_tools(self,tools: List[BaseTool | Callable[..., Any]] | None = None,
                            handoffs: List[Handoff | str] | None = None)->list[BaseTool]:
        llama_tools = []
        if tools:
            for tool in tools:
                if isinstance(tool,BaseTool):
                    llama_tools.append(tool)
                    self._tools.append(tool)
                elif asyncio.iscoroutinefunction(tool):
                    lm_tool = LlamaIndexFunctionTool.from_defaults(async_fn=tool)
                    llama_tools.append(lm_tool)
                    self._tools.append(lm_tool)
                elif isinstance(tool,Callable):
                    lm_tool = LlamaIndexFunctionTool.from_defaults(fn=tool)
                    llama_tools.append(lm_tool)
                    self._tools.append(lm_tool)
                
        if handoffs:
            for handoff in handoffs:
                if isinstance(handoff, str):
                    handoff = Handoff(target=handoff)
                if isinstance(handoff, Handoff) :
                    ho_tool=handoff_tool(handoff)
                    self._handoff_tools.append(ho_tool)
                    self._handoffs[handoff.name] = handoff
                    llama_tools.append(ho_tool)
                else:
                    raise ValueError(f"Unsupported handoff type: {type(handoff)}")
        
        return llama_tools
    

    def get_or_create_task(self, input: str, **kwargs: Any) -> Task:
        """
        创建一个task和step_queue。 
        task记录任务的全局上下文信息，step_queue存储着需要执行任务队列。
        
        task.extra_state["new_memory"],用于保存agent_worker与llm之间的历史数据。
        """
        if self._task_state is None:
            task:Task = self.agent_runner.create_task(input)
            self._task_state = self.agent_runner.state.task_dict[task.task_id]
        
        else:
            step_queue = self.agent_runner.state.get_step_queue(self._task_state.task.task_id)
            
            # 如果没有任务，要补充一个任务进去，以便继续执行
            if len(step_queue)==0:
                last_step = TaskStep(
                    task_id=self._task_state.task.task_id,
                    step_id=str(uuid.uuid4()),
                    input=input,
                )
            else:
                last_step = step_queue.popleft()
                # 更新任务输入内容
                last_step.input = input
            # 放入队列中
            step_queue.append(last_step)
        return self._task_state.task

    

def handoff_tool(handoff:Handoff) -> BaseTool:
    """Create a handoff tool from this handoff configuration."""

    def _handoff_tool( thought: str = Field(
        description="你想要他完成的事情"
    )) -> str:
        return thought

    return LlamaIndexFunctionTool.from_defaults(fn=_handoff_tool, name=handoff.name, description=handoff.description)


