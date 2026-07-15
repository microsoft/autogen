# External Governance Checkpoint

This sample shows one way to wrap an AutoGen tool call with an external governance checkpoint before the tool performs a high-risk action.

The agent proposes an export of customer records. The tool wrapper builds a deterministic action envelope, hashes it, asks a governance checkpoint for a verdict, and only executes when the verdict and local approval policy allow it.

By default, the sample uses a local mock checkpoint and does not require an API key or a live model. Set `EXTERNAL_GOVERNANCE_URL` to call a real checkpoint service that accepts the action envelope as JSON and returns a verdict.

## Install

From this repository, install the Python workspace as described in `python/README.md`:

```bash
cd python
uv sync --all-extras
source .venv/bin/activate
```

For a standalone environment, install the packages used by this sample:

```bash
pip install -U autogen-agentchat autogen-core autogen-ext
```

## Run

```bash
python samples/agentchat_external_governance/main.py
```

To simulate an already-approved high-risk action:

```bash
AUTO_APPROVE_EXTERNAL_GOVERNANCE=1 python samples/agentchat_external_governance/main.py
```

To call an external governance endpoint:

```bash
EXTERNAL_GOVERNANCE_URL=https://example.com/review python samples/agentchat_external_governance/main.py
```

The endpoint should return JSON like:

```json
{
  "verdict": "require_approval",
  "reason": "Customer data export requires review.",
  "decision_id": "dec_123",
  "action_hash": "..."
}
```

