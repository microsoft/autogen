package autogen.tools

import future.keywords.if
import future.keywords.in

# ---------------------------------------------------------------------------
# Default: deny everything unless explicitly allowed.
# ---------------------------------------------------------------------------
default allow := false
default reason := "no matching allow rule"

# ---------------------------------------------------------------------------
# Read-only tools — allowed for any authenticated user
# ---------------------------------------------------------------------------
read_only_tools := {
    "web_search",
    "read_file",
    "list_directory",
    "get_weather",
    "fetch_url",
    "calculator",
}

allow if {
    input.tool in read_only_tools
    input.context.user != ""
}

reason := "read-only tool allowed for authenticated user" if {
    input.tool in read_only_tools
    input.context.user != ""
}

# ---------------------------------------------------------------------------
# Destructive / privileged tools — admin role only
# ---------------------------------------------------------------------------
destructive_tools := {
    "delete_file",
    "execute_code",
    "write_file",
    "run_shell",
}

allow if {
    input.tool in destructive_tools
    input.context.role == "admin"
}

reason := "destructive tool allowed for admin" if {
    input.tool in destructive_tools
    input.context.role == "admin"
}

# ---------------------------------------------------------------------------
# Argument-level constraint: delete_file restricted to /tmp/
# ---------------------------------------------------------------------------
allow if {
    input.tool == "delete_file"
    input.context.role == "admin"
    startswith(input.args.path, "/tmp/")
}

# ---------------------------------------------------------------------------
# Agent handoff tools — whitelist of permitted target agents
# ---------------------------------------------------------------------------
allowed_handoff_targets := {
    "CoderAgent",
    "ReviewerAgent",
    "PlannerAgent",
    "SummaryAgent",
}

allow if {
    startswith(input.tool, "transfer_to_")
    target := substring(input.tool, count("transfer_to_"), -1)
    target in allowed_handoff_targets
}

reason := "handoff allowed to whitelisted agent" if {
    startswith(input.tool, "transfer_to_")
    target := substring(input.tool, count("transfer_to_"), -1)
    target in allowed_handoff_targets
}
