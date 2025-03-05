import argparse
import asyncio
import logging
import subprocess
import sys
import json
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"  # disable parallelism to avoid warning
import re
import sqlite3  # new import for database operations
from typing import List, Optional
from tqdm import tqdm  # new import for progress bar

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import TextMessage, ToolCallSummaryMessage, ToolCallRequestEvent, ToolCallExecutionEvent
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.theme import Theme
from chromadb import PersistentClient
from chromadb.utils import embedding_functions  # new import for sentence transformer

custom_theme = Theme({
    "header": "bold",
    "thinking": "italic yellow",
    "acting": "italic red",
    "prompt": "italic",
    "observe": "italic",
    "success": "bold green",
})
console = Console(theme=custom_theme)

logger = logging.getLogger("gitty")
logger.addHandler(logging.StreamHandler())

async def generate_issue_tdlr(issue_number: str, tldr: str) -> str:
    "Generate a single sentence TLDR for the issue."
    return f"TLDR (#{issue_number}): " + tldr

async def get_github_issue_content(owner: str, repo: str, issue_number: int) -> str:
    cmd = [
        "gh", "issue", "view", str(issue_number),
        "--repo", f"{owner}/{repo}",
        "--json", "body,author,comments"
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_detail = stderr.decode().strip()
        print(f"Error fetching issue: {error_detail}")
        sys.exit(1)
    try:
        issue_data = json.loads(stdout)
    except json.JSONDecodeError as e:
        print("Error decoding gh cli output:", e)
        sys.exit(1)

    issue_body = issue_data.get("body", "No content")
    issue_author = issue_data.get("author", {}).get("login", "Unknown user")
    comments = issue_data.get("comments", [])
    comments_content = "\n\n".join(
        f"{comment.get('author', {}).get('login', 'Unknown user')}: {comment.get('body', 'No content')}"
        for comment in comments
    )
    return f"Content (#{issue_number})\n\nauthor: {issue_author}:\n{issue_body}\n\nComments:\n{comments_content}"

# New helper function to extract mentioned issues using regex.
def get_mentioned_issues(issue_number: int, issue_content: str) -> List[int]:
    # Finds issue numbers mentioned as "#123"
    matches = re.findall(r'#(\d+)', issue_content)
    # remove the current issue number from the list
    matches = [match for match in matches if int(match) != issue_number]
    return list(map(int, matches))

# Updated helper function to extract related issues using a RAG approach via Chroma DB.
def get_related_issues(issue_number: int, issue_content: str, n_results: int = 2) -> List[int]:
    gitty_dir = get_gitty_dir()
    client = PersistentClient(path=os.path.join(gitty_dir, "chroma"))
    try:
        collection = client.get_collection("issues")
    except Exception:
        console.print("[error]Error: Chroma DB not found. Please run 'gitty fetch' to update the database.[/error]")
        return []
    results = collection.query(
        query_texts=[issue_content],  # Chroma will embed the text for you
        n_results=n_results
    )
    ids = results.get("ids", [[]])[0]

    if str(issue_number) in ids:
        ids.remove(str(issue_number))

    return [int(_id) for _id in ids if _id.isdigit()]

async def run(agent: AssistantAgent, task: str, log: bool=False) -> str:
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
                formatted_text = result.content[:200].replace('\n', r'\n')
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

async def get_user_confirmation(prompt: str) -> bool:
    user_input = await get_user_input(f"{prompt} (y to confirm, or provide feedback)")
    user_input = user_input.lower().strip()
    return user_input == "y"

async def get_user_input(prompt: str) -> str:
    user_input = Prompt.ask(f"\n? {prompt} (or type 'exit')")
    if user_input.lower().strip() == "exit":
        console.print("[prompt]Exiting...[/prompt]")
        sys.exit(0)
    return user_input

async def gitty(owner: str, repo: str, command: str, number: int):
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
        base_system_message += "\n\nAdditional Instructions from global config:\n" + global_instructions
    if local_instructions:
        base_system_message += "\n\nAdditional Instructions from local config:\n" + local_instructions

    agent = AssistantAgent(
        name="GittyAgent",
        system_message=base_system_message,
        model_client=OpenAIChatCompletionClient(model="gpt-4o"),
        tools=[get_github_issue_content, generate_issue_tdlr],
    )

    console.print("\n[thinking]- Fetching issue content...[/thinking]")
    task = f"Fetch comments for the {command} #{number} for the {owner}/{repo} repository"
    text = await run(agent, task)

    console.print("\n[thinking]- Checking for mentioned issues...[/thinking]")
    mentioned_issues = get_mentioned_issues(number, text)
    if len(mentioned_issues) > 0:
        console.print(f"  [observe]> Found mentioned issues: {mentioned_issues}[/observe]")
        task = f"Fetch mentioned issues and generate tldrs for each of them: {mentioned_issues}"
        text = await run(agent, task)
    else:
        console.print("  [observe]> No mentioned issues found.[/observe]")

    related_issues = get_related_issues(number, text)
    console.print("\n[thinking]- Checking for other related issues...[/thinking]")

    if len(related_issues) > 0:
        console.print(f"  [observe]> Found related issues: {related_issues}.[/observe]")
        task = f"Fetch related issues and generate tldrs for each of them: {related_issues}"
        text = await run(agent, task)
    else:
        console.print("  [observe]> No related issues found.[/observe]")

    updated_prompt = (
        f"Considering the additional context:\n"
        "You are workin on issue #{number} for the {owner}/{repo} repository. "
        "The issue content is:\n"
        f"{text}\n\n"
        "You also previously fetched related issues that may or may not be relevant"
        "Answer the following questions:"
        f"- What facts are known based on the issue thread # {number}? "
        f"- What is the main issue or problem in #{number}?"
        f"- Which other issues are truly relevant to #{number}?"
        "- What type of a new response from the maintainers would help make progress on this issue? Be concise."
    )

    await run(agent, updated_prompt, log=False)

    summary_text = await run(agent, "Summarize what is the status of this issue. Be concise.")
    console.print("\n[success]> The Summary of the Issue:[/success]")
    console.print("  " + summary_text)

    # console.print("[thinking]! Thinking...[/thinking]")

    suggested_response = await run(
        agent,
        "On behalf of the maintainers, generate a response to the issue/pr that is technical and helpful to make progress. Be concise. Use as few sentences as possible. 1-2 sentence preferred. Do not engage in open ended dialog. If not response is necessary to make progress, say 'No response needed'.",
    )

    console.print("\n[success]> The Suggested Response:[/success]")
    console.print("  " + suggested_response)

    while True:
        user_feedback = await get_user_input("Provide feedback")
        if user_feedback.lower().strip() == "exit":
            console.print("[prompt]Exiting...[/prompt]")
            break
        if user_feedback.lower().strip() == "y":
            console.print("[success]The Suggested Response:[/success]")
            console.print(Panel(suggested_response, title="Suggested Response"))
            break
        else:
            console.print("\n[thinking]Thinking...[/thinking]")
            suggested_response = await run(
                agent,
                f"Accommodate the following feedback: {user_feedback}. Then generate a response to the issue/pr that is technical and helpful to make progress. Be concise.",
            )
            console.print("[success]The Suggested Response:[/success]")
            console.print(suggested_response)

def get_repo_root() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: not a git repository.")
        sys.exit(1)

def get_gitty_dir() -> str:
    """Get the .gitty directory in the repository root. Create it if it doesn't exist."""
    repo_root = get_repo_root()
    gitty_dir = os.path.join(repo_root, ".gitty")
    if not os.path.exists(gitty_dir):
        os.makedirs(gitty_dir)
    return gitty_dir

def edit_config_file(file_path: str):
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            f.write("# Instructions for gitty agents\n")
            f.write("# Add your configuration below\n")
    editor = os.getenv("EDITOR", "vi")
    subprocess.run([editor, file_path])

# Updated function to fetch all issues and update the database.
def fetch_and_update_issues(owner: str, repo: str, db_path: Optional[str] = None):
    """
    Fetch all GitHub issues for the repo and update the local database.
    Only updates issues that have a more recent updatedAt timestamp.
    The database stores full issue content as produced by get_github_issue_content.
    If db_path is not provided, it is set to "<repo_root>/.gitty.db".
    """
    if db_path is None:
        gitty_dir = get_gitty_dir()
        db_path = os.path.join(gitty_dir, "issues.db")
    print(f"Using database at: {db_path}")

    # Fetch issues using gh CLI (fetch summary without content)
    cmd = [
        "gh", "issue", "list",
        "--repo", f"{owner}/{repo}",
        "-L", "1000",
        "--json", "number,title,updatedAt"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error fetching issues:", result.stderr)
        return
    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Error decoding issues JSON:", e)
        return

    print(f"Fetched {len(issues)} issues. Beginning update...")

    # Connect to or create the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            number INTEGER PRIMARY KEY,
            title TEXT,
            updatedAt TEXT,
            content TEXT
        )
    """)

    for issue in tqdm(issues, desc="Fetching issues"):
        number = issue.get("number")
        title = issue.get("title")
        updatedAt = issue.get("updatedAt")
        # Retrieve full issue content using the async method

        cursor.execute("SELECT updatedAt FROM issues WHERE number = ?", (number,))
        row = cursor.fetchone()
        if row:
            existing_updatedAt = row[0]
            if updatedAt > existing_updatedAt:
                content = asyncio.run(get_github_issue_content(owner, repo, number))
                cursor.execute("""
                    UPDATE issues
                    SET title = ?, updatedAt = ?, content = ?
                    WHERE number = ?
                """, (title, updatedAt, content, number))
        else:
            content = asyncio.run(get_github_issue_content(owner, repo, number))
            cursor.execute("""
                INSERT INTO issues (number, title, updatedAt, content)
                VALUES (?, ?, ?, ?)
            """, (number, title, updatedAt, content))
    conn.commit()
    conn.close()
    print("Issue database update complete.")

    # Update Chroma DB with latest issues
    gitty_dir = get_gitty_dir()
    persist_directory = os.path.join(gitty_dir, "chroma")
    # Updated Chroma client construction (removed deprecated Settings usage)
    chroma_client = PersistentClient(path=persist_directory)
    try:
        collection = chroma_client.get_collection("issues")
    except Exception:
        collection = chroma_client.create_collection("issues")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT number, title, content FROM issues")
    rows = cursor.fetchall()
    conn.close()

    # New embedding function using sentence_transformers
    sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()

    if sentence_transformer_ef is None:
        print("Error: Default embedding function is not available.")
        exit(1)

    for issue_number, title, content in rows:
        meta = {"title": title}  # metadata for each issue
        embedding = sentence_transformer_ef([content])[0]
        collection.upsert(
            documents=[content],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[str(issue_number)],
        )
    print("Chroma DB update complete.")

def check_gh_cli():
    """Check if GitHub CLI is installed and accessible."""
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[error]Error: GitHub CLI (gh) is not installed or not found in PATH.[/error]")
        console.print("Please install it from: https://cli.github.com")
        sys.exit(1)

def check_openai_key():
    """Check if OpenAI API key is set in environment variables."""
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[error]Error: OPENAI_API_KEY environment variable is not set.[/error]")
        console.print("Please set your OpenAI API key using:")
        console.print("  export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Gitty: A GitHub Issue/PR Assistant.\n\n"
                    "This tool fetches GitHub issues or pull requests and uses an AI assistant to generate concise,\n"
                    "technical responses to help make progress on your project. You can specify a repository using --repo\n"
                    "or let the tool auto-detect the repository based on the current directory.",
        epilog="Subcommands:\n  issue - Process and respond to GitHub issues\n  pr    - Process and respond to GitHub pull requests\n  local - Edit repo-specific gitty config\n  global- Edit global gitty config\n\n"
               "Usage examples:\n  gitty issue 123\n  gitty pr 456\n  gitty local\n  gitty global",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("command", choices=["issue", "pr", "fetch", "local", "global"], nargs="?", help="Command to execute")
    parser.add_argument("number", type=int, nargs="?", help="Issue or PR number (if applicable)")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    command = args.command

    # Check for gh CLI installation before processing commands that need it
    if command in ["issue", "pr", "fetch"]:
        check_gh_cli()
    
    # Check for OpenAI API key before processing commands that need it
    if command in ["issue", "pr"]:
        check_openai_key()

    if command in ["issue", "pr"]:
        # Always auto-detect repository
        pipe = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json", "owner,name",
                "-q", '.owner.login + "/" + .name',
            ],
            check=True,
            capture_output=True,
        )
        owner, repo = pipe.stdout.decode().strip().split("/")
        number = args.number
        if command == "issue":
            asyncio.run(gitty(owner, repo, command, number))
        else:
            console.print(f"Command '{command}' is not implemented.")
            sys.exit(1)
    elif command == "fetch":
        # New command for updating the database
        pipe = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json", "owner,name",
                "-q", '.owner.login + "/" + .name',
            ],
            check=True,
            capture_output=True,
        )
        owner, repo = pipe.stdout.decode().strip().split("/")
        gitty_dir = get_gitty_dir()
        db_path = os.path.join(gitty_dir, "issues.db")
        fetch_and_update_issues(owner, repo, db_path)
    elif command == "local":
        gitty_dir = get_gitty_dir()
        local_config_path = os.path.join(gitty_dir, "config")
        edit_config_file(local_config_path)
    elif command == "global":
        global_config_dir = os.path.expanduser("~/.gitty")
        os.makedirs(global_config_dir, exist_ok=True)
        global_config_path = os.path.join(global_config_dir, "config")
        edit_config_file(global_config_path)

if __name__ == "__main__":
    main()
