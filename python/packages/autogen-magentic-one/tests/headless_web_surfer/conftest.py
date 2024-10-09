skip_openai: bool = False
skip_redis: bool = False
skip_docker: bool = False
reason: str = "requested to skip"
MOCK_OPEN_AI_API_KEY: str = "sk-mockopenaiAPIkeyinexpectedformatfortestingonly"
MOCK_CHAT_COMPLETION_KWARGS: str = """
{
  "api_key": "sk-mockopenaiAPIkeyinexpectedformatfortestingonly",
  "model": "gpt-4o-2024-05-13"
}
"""
