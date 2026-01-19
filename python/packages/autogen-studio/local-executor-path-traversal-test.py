import asyncio
import json
import httpx
import websockets

# Configuration
BASE_URL = "http://127.0.0.1:8081/api"
WS_URL = "ws://127.0.0.1:8081/api/ws"
USER_ID = "guestuser@gmail.com"
PROXY_BASE_URL = "https://example.com/v1"
PROXY_API_KEY = "sk-123"

async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Fetch Team ID (Required for Session)
        teams = (await client.get(f"/teams/?user_id={USER_ID}")).json()['data']
        if not teams: return print("No teams found.")
        
        # 2. Create Session & Run
        session = (await client.post("/sessions/", json={"user_id": USER_ID, "team_id": teams[0]['id']})).json()['data']
        run = (await client.post("/runs/", json={"session_id": session['id'], "user_id": USER_ID})).json()['data']
        run_id = run.get('id') or run.get('run_id')
        if not run_id:
            print(f"Error: Could not find run ID in response: {run}")
            return
        print(f"Run ID: {run_id}")

        # 3. Construct Minimal Team Config (Single Agent with Code Execution)
        team_config = {
            "provider": "autogen_agentchat.teams.RoundRobinGroupChat",
            "component_type": "team",
            "config": {
                "termination_condition": {
                    "provider": "autogen_agentchat.conditions.MaxMessageTermination",
                    "component_type": "termination",
                    "config": {"max_messages": 5}
                },
                "participants": [{
                    "provider": "autogen_agentchat.agents.AssistantAgent",
                    "component_type": "agent",
                    "config": {
                        "name": "hacker_agent",
                        "description": "An AI assistant with code execution",
                        "reflect_on_tool_use": False,
                        "tool_call_summary_format": "{result}",
                        "model_client": {
                            "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
                            "component_type": "model",
                            "config": {
                                "model": "gpt-4o-mini-2024-07-18",
                                "base_url": PROXY_BASE_URL,
                                "api_key": PROXY_API_KEY
                            }
                        },
                        "model_client_stream": True,
                        "system_message": "You are a helpful AI assistant with python code execution capabilities.",
                        "tools": [{
                            "provider": "autogen_ext.tools.code_execution.PythonCodeExecutionTool",
                            "component_type": "tool",
                            "config": {"executor": {
                                "provider": "autogen_ext.code_executors.local.LocalCommandLineCodeExecutor",
                                "component_type": "code_executor",
                                "config": {"work_dir": "work_dir"}
                            }}
                        }]
                    }
                }]
            }
        }

        # 4. WebSocket Interaction
        async with websockets.connect(f"{WS_URL}/runs/{run_id}") as ws:
            await ws.recv() # Wait for connection
            
            # Send Task
            await ws.send(json.dumps({
                "type": "start",
                "task": "Please create a file named ../../pwned using python code.",
                "team_config": team_config
            }))
            
            # Process Messages
            while True:
                msg = json.loads(await ws.recv())
                mtype = msg.get('type')
                
                if mtype == 'text':
                    print(f"[Agent]: {msg['data']['content']}")
                elif mtype == 'tool_output':
                    print(f"[Tool]: {msg['data']['content'].strip()}")
                elif mtype in ['completion', 'result', 'error']:
                    print(f"[Finished]: {mtype}")
                    break

if __name__ == "__main__":
    asyncio.run(main())