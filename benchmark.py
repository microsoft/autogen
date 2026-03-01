import anthropic
import os
import glob as glob_module
import subprocess

client = anthropic.Anthropic()

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

TOOLS = [
    {
        "name": "read_file",
        "description": "Read the content of a file",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to file"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "glob_files",
        "description": "Find files matching a pattern",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "base_dir": {"type": "string"}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "grep_content",
        "description": "Search for text in files",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"}
            },
            "required": ["pattern", "path"]
        }
    }
]

def execute_tool(tool_name, tool_input):
    if tool_name == "read_file":
        path = tool_input["path"]
        if not os.path.realpath(path).startswith(os.path.realpath(REPO_ROOT)):
            return "Error: access denied — path is outside the repository"
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if len(content) > 8000:
                content = content[:8000] + "\n...[truncated]"
            return content
        except Exception as e:
            return f"Error: {e}"
    elif tool_name == "glob_files":
        pattern = tool_input["pattern"]
        base = tool_input.get("base_dir", REPO_ROOT)
        if not pattern.startswith("/"):
            pattern = os.path.join(base, pattern)
        matches = glob_module.glob(pattern, recursive=True)
        return "\n".join(matches[:20]) if matches else "No files found"
    elif tool_name == "grep_content":
        pattern = tool_input["pattern"]
        path = tool_input["path"]
        if not os.path.realpath(path).startswith(os.path.realpath(REPO_ROOT)):
            return "Error: access denied — path is outside the repository"
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", "-m", "5", pattern, path],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout[:2000] if result.stdout else "No matches"
        except Exception as e:
            return f"Error: {e}"
    return "Unknown tool"

def run_agent(system_prompt, query, max_turns=20):
    messages = [{"role": "user", "content": query}]
    tool_count = 0
    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system_prompt,
            tools=TOOLS,
            messages=messages
        )
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        tool_count += len(tool_uses)
        if response.stop_reason == "end_turn" or not tool_uses:
            return "", tool_count
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result
            })
        messages.append({"role": "user", "content": tool_results})
    return "", tool_count

BASELINE_PROMPT = f"""You are a helpful assistant answering questions about the AutoGen framework.
The repository is at {REPO_ROOT}.
Use the available tools to read files and find the answer.
Start by exploring the repository structure to understand where to find information."""

KCP_PROMPT = f"""You are a helpful assistant answering questions about the AutoGen framework.
The repository is at {REPO_ROOT}.
IMPORTANT: First read {REPO_ROOT}/knowledge.yaml to understand the repository structure.
Match the question to the triggers in knowledge.yaml and read only the files pointed to by matching units.
If a unit has summary_available: true, read the summary_unit file first (it's much smaller)."""

QUERIES = [
    "What is the difference between AutoGen Core and AgentChat?",
    "How do I build my first multi-agent chat with AutoGen?",
    "How do I add tools to an agent in AutoGen?",
    "What design patterns does AutoGen support for multi-agent orchestration?",
    "How do I implement group chat with multiple agents?",
    "How do I add memory to an agent?",
    "What LLM providers and model clients does AutoGen support?",
    "How do I handle human-in-the-loop approval in AutoGen?",
]

if __name__ == "__main__":
    print("AutoGen KCP Benchmark")
    print("=" * 60)
    results = []
    for i, query in enumerate(QUERIES):
        print(f"\nQuery {i+1}: {query[:60]}...")
        _, baseline = run_agent(BASELINE_PROMPT, query)
        print(f"  Baseline: {baseline} tool calls")
        _, kcp = run_agent(KCP_PROMPT, query)
        print(f"  KCP: {kcp} tool calls")
        results.append((query, baseline, kcp))

    print("\n" + "=" * 60)
    total_baseline = sum(r[1] for r in results)
    total_kcp = sum(r[2] for r in results)
    print(f"\n{'Query':<55} {'Base':>5} {'KCP':>5} {'Saved':>6}")
    print("-" * 75)
    for query, b, k in results:
        print(f"{query[:55]:<55} {b:>5} {k:>5} {b-k:>6}")
    print("-" * 75)
    print(f"{'TOTAL':<55} {total_baseline:>5} {total_kcp:>5} {total_baseline-total_kcp:>6}")
    pct = round((1 - total_kcp/total_baseline) * 100) if total_baseline > 0 else 0
    print(f"\nReduction: {pct}% fewer tool calls with KCP")
