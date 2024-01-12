from autogen import AssistantAgent, UserProxyAgent, ConversableAgent, config_list_from_json
from spider_env import SpiderEnv
from typing import Annotated, Dict
import json

# Load LLM inference endpoints from an env variable or a file
# See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
# and OAI_CONFIG_LIST_sample
config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

def check_termination(msg: Dict):
    if 'tool_responses' not in msg:
        return False
    json_str = msg['tool_responses'][0]['content']
    obj = json.loads(json_str)
    return "error" not in obj or obj["error"] is None and obj["reward"] == 1

sql_writer = ConversableAgent("sql_writer",
                              llm_config={"config_list": config_list},
                              system_message="You are good at writing SQL queries. Always respond with a function call to execute_sql().",
                              is_termination_msg=check_termination)
user_proxy = UserProxyAgent("user_proxy", human_input_mode="NEVER", max_consecutive_auto_reply=5)
spider = SpiderEnv()

@sql_writer.register_for_llm(description="Function for executing SQL query and returning a response")
@user_proxy.register_for_execution()
def execute_sql(reflection: Annotated[str, "Think about what to do"], sql: Annotated[str, "SQL query"]) -> Annotated[Dict[str, str], "Dictionary with keys 'result' and 'error'"]:
    observation, reward, terminated, truncated, info = spider.step(sql)
    error = observation["feedback"]["error"]
    if not error and reward == 0:
        error = "The SQL query returned an incorrect result"
    if error:
        return {
            "error": error,
            "wrong_result": observation["feedback"]["result"],
            "correct_result": info["gold_result"],
        }
    else:
        return {
            "result": observation["feedback"]["result"],
        }

for i in range(100):
    observation, info = spider.reset()
    question = observation["instruction"]
    schema = info["schema"]
    message = f"""Below is the schema for a SQL database:
    {schema}
    Generate a SQL query to answer the following question:
    {question}
    """
    user_proxy.initiate_chat(sql_writer, message=message)
