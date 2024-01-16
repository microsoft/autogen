import asyncio
import sys


async def a_input(prompt: str) -> str:
    """
    Async alternative to input()
    Args:
        prompt (str): Prompt for user input.

    Returns: The stdin str.

    """
    sys.stdout.write(prompt)
    user_input: str = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
    return user_input.strip()
