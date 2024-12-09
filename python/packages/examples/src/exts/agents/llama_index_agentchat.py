from collections import deque
import asyncio,json,logging,uuid
from typing import AsyncGenerator, Coroutine, List, Optional, Sequence, Union
from pydantic import Field
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
)
from autogen_agentchat.agents import Handoff
from autogen_core.components.tools import FunctionTool, Tool


##### llamaIndex import ##################

from llama_index.core.agent.react.step import ReActAgentWorker
from llama_index.core.agent import ReActAgent
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
from llama_index.core.agent.runner.base import TaskState
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.llms.openai import OpenAI
from llama_index.core.chat_engine.types import (
    AGENT_CHAT_RESPONSE_TYPE,
    AgentChatResponse,
    ChatResponseMode,
    StreamingAgentChatResponse,
)
from llama_index.core.base.llms.types import MessageRole
from llama_index.core.base.llms.types import  ChatResponse as LlamaIndexChatResponse,ChatMessage as LlmaIndexCahtMessage
from llama_index.core.memory import BaseMemory, ChatMemoryBuffer
from llama_index.core.callbacks import (
    trace_method,
)
import llama_index.core.instrumentation as instrument
from llama_index.core.callbacks.schema import (
    BASE_TRACE_EVENT,
    LEAF_EVENTS,
    CBEventType,
    EventPayload,
)
############### llama index end #############################################
AsyncCallable = Callable[..., Awaitable[Any]]
from .llamaIndex_autogen_utils import ag_function_call_convert

dispatcher = instrument.get_dispatcher(__name__)

event_logger = logging.getLogger('LLAMA_INDEX_AGENT')
class LlamaIndexAssistantAgent(BaseChatAgent):
    def __init__(
        self,
        name: str,
        llm: LLM,
        max_func_calls: int,
        *,
        tools: List[BaseTool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        handoffs: List[Handoff | str] | None = None,
        description: str = "An agent that provides assistance with ability to use tools.",
        system_message: str
        | None = "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
        callbackManager:CallbackManager=None
    ):
        super().__init__(name=name, description=description)
        self._callbakcManager = callbackManager
        self._task_state=None
        
        # Handoff tools.
        self._handoff_tools: List[Tool] = []
        self.memory = ChatMemoryBuffer.from_defaults(llm=llm)
        self._handoffs: Dict[str, Handoff] = {}
        self._tools = []
        self.agent_worker = self.create_agent_worker(llm,tools,handoffs,system_message,callbackManager,max_func_calls)
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

    @property
    def produced_message_types(self) -> List[type[ChatMessage]]:
        """The types of messages that the assistant agent produces."""
        if self._handoffs:
            return [TextMessage, HandoffMessage]
        return [TextMessage]

    async def on_messages(self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken) -> Response:
        async for message in self.on_messages_stream(messages, cancellation_token):
            if isinstance(message, Response):
                return message
        raise AssertionError("The stream should have returned the final result.")

    @dispatcher.span
    @trace_method("chat")
    async def on_messages_stream(
        self, messages: Sequence[ChatMessage], cancellation_token: CancellationToken
    ) -> AsyncGenerator[AgentMessage | Response, None]:
        # Add messages to the model context.
        for msg in messages:
            if isinstance(msg, MultiModalMessage):
                raise ValueError("The model does not support vision.")
            self._model_context.append(UserMessage(content=msg.content, source=msg.source))
        user_input = messages[-1].content if len(messages)>0 else None
        

        result_output= None

        # Inner messages.
        inner_messages: List[AgentMessage] = []

        
        # Generate an inference result based on the current model context.
        task,task_step = self.get_or_create_task(user_input)
        while True:
            # pass step queue in as argument, assume step executor is stateless
            cur_step_output = await self.agent_worker.arun_step(
                task_step,task
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
                    yield Response(
                        chat_message=HandoffMessage(
                            content=tool_output.content, target=self._handoffs[tool_output.tool_name].target, source=self.name
                        ),
                        inner_messages=inner_messages,
                    )
                    return
                # 如果不需要handoff，继续下一个step的执行
                task_step = cur_step_output.task_step
            # ensure tool_choice does not cause endless loops
            tool_choice = "auto"

        assert isinstance(result_output, str)
        yield Response(
            chat_message=TextMessage(content=result_output, source=self.name),
            inner_messages=inner_messages,
        )
    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        """Reset the assistant agent to its initialization state."""
        self._model_context.clear()
        self._task_state=None
        self.memory.reset()


    def create_agent_worker(self,llm:LLM,tools: List[BaseTool | Callable[..., Any]] | None = None,
                            handoffs: List[Handoff | str] | None = None,system_message:str=None,
                            callbackManager:CallbackManager=None,max_func_calls:int=10)->BaseAgentWorker:
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
        
        if llm.metadata.is_function_calling_model and isinstance(llm,OpenAI):
            return OpenAIAgentWorker.from_tools(tools=llama_tools,
                                        llm=llm,callback_manager=callbackManager,max_function_calls=max_func_calls,
                                        system_prompt=system_message)
        else:
            return ReActAgentWorker.from_tools(tools=llama_tools,
                                        llm=llm,callback_manager=callbackManager,max_iterations=max_func_calls,
                                        react_chat_formatter=ReActChatFormatter.from_defaults(context=system_message if system_message else ""))
    

    def get_or_create_task(self, input: str, **kwargs: Any) -> tuple[Task,TaskStep]:
        """
        创建一个task和step_queue。 
        task记录任务的全局上下文信息，step_queue存储着需要执行任务队列。
        
        task.extra_state["new_memory"],用于保存agent_worker与llm之间的历史数据。
        """
        if self._task_state is None:
            sources: List[ToolOutput] = []
            # temporary memory for new messages
            new_memory = self.memory
            # initialize task state
            task_state = {
                "sources": sources,
                "n_function_calls": 0,
                "current_reasoning" : [],
                "new_memory": new_memory,
            }
            # task.extra_state["new_memory"],用于保存整个task的上下文。
            task = Task(
                input=input,
                memory=ChatMemoryBuffer.from_defaults(),
                extra_state=task_state,
                callback_manager=self._callbakcManager,
                **kwargs
            )
            step = TaskStep(
                task_id=task.task_id,
                step_id=str(uuid.uuid4()),
                input=task.input,
                step_state={"is_first": True},
            )
            self._task_state = TaskState(
                task=task,
                step_queue=deque([step])
            )
                
        if len(self._task_state.step_queue)==0:
            step = TaskStep(
                task_id=self._task_state.task.task_id,
                step_id=str(uuid.uuid4()),
                input=input,
            )
        else :
            step = self._task_state.step_queue.popleft()
        return self._task_state.task,step

    

def handoff_tool(handoff:Handoff) -> BaseTool:
    """Create a handoff tool from this handoff configuration."""

    def _handoff_tool( thought: str = Field(
        description="你想要他完成的事情"
    )) -> str:
        return thought

    return LlamaIndexFunctionTool.from_defaults(fn=_handoff_tool, name=handoff.name, description=handoff.description)


