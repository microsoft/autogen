import os
import json
import subprocess
import asyncio
from typing import Optional
from tqdm import tqdm
import sqlite3

from chromadb import PersistentClient
from chromadb.utils import embedding_functions

from ._config import get_gitty_dir
from ._github import get_github_issue_content

def init_db(db_path: str) -> None:
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
    conn.close()


def update_issue(db_path: str, number: int, title: str, updatedAt: str, content: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO issues (number, title, updatedAt, content)
        VALUES (?, ?, ?, ?)
        """,
        (number, title, updatedAt, content),
    )
    conn.commit()
    conn.close()


def update_chroma(gitty_dir: str, db_path: str) -> None:
    persist_directory = os.path.join(gitty_dir, "chroma")
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

    sentence_transformer_ef = embedding_functions.DefaultEmbeddingFunction()
    if sentence_transformer_ef is None:
        raise RuntimeError("Default embedding function is not available.")

    for issue_number, title, content in rows:
        meta = {"title": title}
        embedding = sentence_transformer_ef([content])[0]
        collection.upsert(
            documents=[content],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[str(issue_number)],
        )


# Updated function to fetch all issues and update the database.
def fetch_and_update_issues(owner: str, repo: str, db_path: Optional[str] = None) -> None:
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
    cmd = ["gh", "issue", "list", "--repo", f"{owner}/{repo}", "-L", "1000", "--json", "number,title,updatedAt"]
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
                cursor.execute(
                    """
                    UPDATE issues
                    SET title = ?, updatedAt = ?, content = ?
                    WHERE number = ?
                """,
                    (title, updatedAt, content, number),
                )
        else:
            content = asyncio.run(get_github_issue_content(owner, repo, number))
            cursor.execute(
                """
                INSERT INTO issues (number, title, updatedAt, content)
                VALUES (?, ?, ?, ?)
            """,
                (number, title, updatedAt, content),
            )
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