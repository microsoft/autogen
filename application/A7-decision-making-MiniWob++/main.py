import os
os.environ["OPENAI_API_KEY"] = ""
from autogen.agentchat.assistant_agent import AssistantAgent
from miniwob_agent import MiniWobUserProxyAgent
from autogen import oai
import argparse

parser = argparse.ArgumentParser(description="input task")
parser.add_argument(
    "--problem", type=str, default="click-button-sequence", help="task"
)
args = parser.parse_args()
problem = args.problem
Configlist=[{"model":"gpt-3.5-turbo-16k", "api_key":""}]


for _ in range(10):
    
    assistant = AssistantAgent(
        name="miniwob_assistant", 
        llm_config={
            "request_timeout": 600,
            "seed": 42,
            "config_list": Configlist,
        },
        is_termination_msg = lambda x: "terminate" in x.get("content").lower(),
        system_message="You are an autoregressive language model that completes user's sentences."
    )

    MiniWob = MiniWobUserProxyAgent(
        name="MiniWobUserProxyAgent", 
        human_input_mode="NEVER",
        problem = args.problem,
        headless=False,
        env_name= args.problem,
        rci_plan_loop=0,
        rci_limit=1,
        llm="chatgpt",
        state_grounding=False,
    )

    assistant.reset()

    MiniWob.initiate_chat(assistant)
