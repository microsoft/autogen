import os
import re
import asyncio
import json
import subprocess
import sys
from typing import Dict, List, Any

from chromadb import PersistentClient


async def generate_issue_tdlr(issue_number: str, tldr: str) -> str:
    "Generate a single sentence TLDR for the issue."
    return f"TLDR (#{issue_number}): " + tldr


def get_mentioned_issues(issue_number: int, issue_content: str) -> List[int]:
    matches = re.findall(r"#(\d+)", issue_content)
    matches = [match for match in matches if int(match) != issue_number]
    return list(map(int, matches))


def get_related_issues(issue_number: int, issue_content: str, gitty_dir: str, n_results: int = 2) -> List[int]:
    client = PersistentClient(path=os.path.join(gitty_dir, "chroma"))
    try:
        collection = client.get_collection("issues")
    except Exception:
        return []
    results = collection.query(
        query_texts=[issue_content],
        n_results=n_results,
    )
    ids = results.get("ids", [[]])[0]

    if str(issue_number) in ids:
        ids.remove(str(issue_number))

    return [int(_id) for _id in ids if _id.isdigit()]

async def get_github_issue_content(owner: str, repo: str, issue_number: int) -> str:
    cmd = ["gh", "issue", "view", str(issue_number), "--repo", f"{owner}/{repo}", "--json", "body,author,comments"]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
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

def fetch_issue_summaries(owner: str, repo: str) -> List[Dict[Any, Any]]:
    cmd = ["gh", "issue", "list", "--repo", f"{owner}/{repo}", "-L", "1000", "--json", "number,title,updatedAt"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error fetching issues:", result.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Error decoding issues JSON:", e)
        return []
