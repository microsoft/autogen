import os
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent, ToolCallRequestEvent, ToolCallSummaryMessage
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ._github import get_github_issue_content, get_mentioned_issues, get_related_issues, generate_issue_tdlr
from ._config import custom_theme, get_gitty_dir


console = Console(theme=custom_theme)

async def _run(agent: AssistantAgent, task: str, log: bool = False) -> str:
    output_stream = agent.on_messages_stream(
        [TextMessage(content=task, source="user")],
        cancellation_token=CancellationToken(),
    )
    last_txt_message = ""
    async for message in output_stream:
        if isinstance(message, ToolCallRequestEvent):
            for tool_call in message.content:
                console.print(f"  [acting]! Calling {tool_call.name}... [/acting]")

        if isinstance(message, ToolCallExecutionEvent):
            for result in message.content:
                # Compute formatted text separately to avoid backslashes in the f-string expression.
                formatted_text = result.content[:200].replace("\n", r"\n")
                console.print(f"  [observe]> {formatted_text} [/observe]")

        if isinstance(message, Response):
            if isinstance(message.chat_message, TextMessage):
                last_txt_message += message.chat_message.content
            elif isinstance(message.chat_message, ToolCallSummaryMessage):
                content = message.chat_message.content
                # only print the first 100 characters
                # console.print(Panel(content[:100] + "...", title="Tool(s) Result (showing only 100 chars)"))
                last_txt_message += content
            else:
                raise ValueError(f"Unexpected message type: {message.chat_message}")
            if log:
                print(last_txt_message)
    return last_txt_message


async def _get_user_input(prompt: str) -> str:
    user_input = Prompt.ask(f"\n? {prompt} (or type 'exit')")
    if user_input.lower().strip() == "exit":
        console.print("[prompt]Exiting...[/prompt]")
        sys.exit(0)
    return user_input


async def run_gitty(owner: str, repo: str, command: str, number: int) -> None:
    console.print("[header]Gitty - GitHub Issue/PR Assistant[/header]")
    console.print(f"[thinking]Assessing issue #{number} for repository {owner}/{repo}...[/thinking]")
    console.print(f"https://github.com/{owner}/{repo}/issues/{number}")

    global_instructions = ""
    try:
        global_config_path = os.path.expanduser("~/.gitty/config")
        if os.path.exists(global_config_path):
            with open(global_config_path, "r") as f:
                global_instructions = f.read().strip()
    except Exception as e:
        print("Warning: Could not load global config:", e)

    local_instructions = ""
    try:
        gitty_dir = get_gitty_dir()
        local_config_path = os.path.join(gitty_dir, "config")
        print(f"Local config path: {local_config_path}")
        if os.path.exists(local_config_path):
            with open(local_config_path, "r") as f:
                local_instructions = f.read().strip()
    except Exception as e:
        print("Warning: Could not load local config:", e)

    base_system_message = (
        "You are a helpful AI assistant whose purpose is to reply to GitHub issues and pull requests. "
        "Use the content in the thread to generate an auto reply that is technical and helpful to make progress on the issue/pr. "
        "Your response must be very concise and focus on precision. Just be direct and to the point."
    )
    if global_instructions:
        base_system_message += "\n\nAdditional Instructions from global config. These instructions should take priority over previous instructions. \n" + global_instructions
    if local_instructions:
        base_system_message += "\n\nAdditional Instructions from local config. These instructions should take priority over previous instructions. \n" + local_instructions

    print(base_system_message)

    agent = AssistantAgent(
        name="GittyAgent",
        system_message=base_system_message,
        model_client=OpenAIChatCompletionClient(model="gpt-4o"),
        tools=[get_github_issue_content, generate_issue_tdlr],
    )

    console.print("\n[thinking]- Fetching issue content...[/thinking]")
    task = f"Fetch comments for the {command} #{number} for the {owner}/{repo} repository"
    text = await _run(agent, task)

    console.print("\n[thinking]- Checking for mentioned issues...[/thinking]")
    mentioned_issues = get_mentioned_issues(number, text)
    if len(mentioned_issues) > 0:
        console.print(f"  [observe]> Found mentioned issues: {mentioned_issues}[/observe]")
        task = f"Fetch mentioned issues and generate tldrs for each of them: {mentioned_issues}"
        text = await _run(agent, task)
    else:
        console.print("  [observe]> No mentioned issues found.[/observe]")

    related_issues = get_related_issues(number, text, get_gitty_dir())
    console.print("\n[thinking]- Checking for other related issues...[/thinking]")

    if len(related_issues) > 0:
        console.print(f"  [observe]> Found related issues: {related_issues}.[/observe]")
        task = f"Fetch related issues and generate tldrs for each of them: {related_issues}"
        text = await _run(agent, task)
    else:
        console.print("  [observe]> No related issues found.[/observe]")

    updated_prompt = (
        "Considering the additional context:\n"
        f"You are working on issue #{number} for the {owner}/{repo} repository. "
        "The issue content is:\n"
        f"{text}\n\n"
        "You also previously fetched related issues that may or may not be relevant"
        "Answer the following questions:"
        f"- What facts are known based on the issue thread # {number}? "
        f"- What is the main issue or problem in #{number}?"
        f"- Which other issues are truly relevant to #{number}?"
        "- What type of a new response from the maintainers would help make progress on this issue? Be concise."
    )

    await _run(agent, updated_prompt, log=False)

    summary_text = await _run(agent, "Summarize what is the status of this issue. Be concise.")
    console.print("\n[success]> The Summary of the Issue:[/success]")
    console.print("  " + summary_text)

    suggested_response = await _run(
        agent,
        "On behalf of the maintainers, generate a response to the issue/pr that is technical and helpful to make progress. Be concise. Use as few sentences as possible. 1-2 sentence preferred. Do not engage in open ended dialog. If not response is necessary to make progress, say 'No response needed'. Make sure you follow the instructions in the system message, especially the local and global instructions.",
    )

    console.print("\n[success]> The Suggested Response:[/success]")
    console.print("  " + suggested_response)

    while True:
        user_feedback = await _get_user_input("Provide feedback")
        if user_feedback.lower().strip() == "exit":
            console.print("[prompt]Exiting...[/prompt]")
            break
        if user_feedback.lower().strip() == "y":
            console.print("[success]The Suggested Response:[/success]")
            console.print(Panel(suggested_response, title="Suggested Response"))
            break
        else:
            console.print("\n[thinking]Thinking...[/thinking]")
            suggested_response = await _run(
                agent,
                f"Accommodate the following feedback: {user_feedback}. Then generate a response to the issue/pr that is technical and helpful to make progress. Be concise.",
            )
            console.print("[success]The Suggested Response:[/success]")
            console.print(suggested_response)
