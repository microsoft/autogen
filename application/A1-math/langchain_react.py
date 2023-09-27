from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.tools.python.tool import PythonREPLTool
from langchain.agents.agent_toolkits import create_python_agent
from flaml.autogen.math_utils import eval_math_responses, get_answer
from utils import remove_asy_sections
from langchain.callbacks import FileCallbackHandler
from langchain.callbacks import get_openai_callback
# https://python.langchain.com/docs/modules/model_io/models/llms/token_usage_tracking
from loguru import logger
import time
logfile = "langchain.log"

logger.add(logfile, colorize=True, enqueue=True)
handler = FileCallbackHandler(logfile)
import signal

def timeout_handler(signum, frame):
    raise Exception("LangChain Timeout")

class ReAct:
    def __init__(self, config_list, use_azure) -> None:
        config_list = config_list[0]
        if not use_azure:
            self.llm = ChatOpenAI(model_name=config_list['model'], openai_api_key=config_list['api_key'])
        else:
            self.llm = AzureChatOpenAI(
                deployment_name=config_list['model'],
                openai_api_base=config_list['api_base'],
                openai_api_version=config_list['api_version'],
                openai_api_key=config_list['api_key'],
            )

        # https://python.langchain.com/docs/integrations/toolkits/python
        self.agent = create_python_agent(
            llm=self.llm,
            tool=PythonREPLTool(),
            verbose=True,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
            agent_executor_kwargs={
                "handle_parsing_errors": True, 
                "callbacks" : [handler], 
                "return_intermediate_steps": True,
                "max_execution_time" : 600},
        )

    def solve_one_problem(self, problem):
        result, cb = self._solve(problem)

        tmp = {
            "response_with_ans": result['output'],
            "correct_ans": get_answer(problem["solution"]),
            "intermediate_steps": [act[0].log + f"\n{act[1]}" for act in result['intermediate_steps']],
            "time": result['time'],
        }
        if cb is not None:
            tmp.update({
                "total_token": cb.total_tokens,
                "prompt_token": cb.prompt_tokens,
                "completion_token": cb.completion_tokens,
                "total_cost": cb.total_cost,
            })
        
        return tmp

    def _solve(self, problem):
        signal.signal(signal.SIGALRM, timeout_handler)
        start = time.time()
        try:
            signal.alarm(600)
            with get_openai_callback() as cb:
                result = self.agent({'input': problem["problem"]})
            signal.alarm(0)
        except Exception as e:
            print(e)
            result = {
                "output" : "No reply from the model.",
                "intermediate_steps": [],
            }
            cb = None
        result['time'] = time.time() - start
        return result, cb
