# Streamlit Team Chat Example (Stop-and-Resume Pattern)

A Streamlit app demonstrating the **stop-and-resume** pattern for interactive multi-agent teams.

Unlike the [chainlit example](../agentchat_chainlit/) which uses `UserProxyAgent` with a blocking input function, this example uses `MaxMessageTermination(max_messages=1)` to run the assistant for exactly one turn, then returns control to the Streamlit UI. This avoids the async blocking issue that Streamlit has with `UserProxyAgent.input_func`.

## When to Use This Pattern

- Web UIs built with Streamlit, Gradio, or similar frameworks
- Any scenario where you can't block the main thread waiting for user input
- When you need to save/resume team state across page reruns

## Setup

```bash
pip install -r requirements.txt
```

Set your API key:
```bash
export OPENAI_API_KEY=sk-...
```

## Run

```bash
streamlit run app.py
```

## How It Works

1. User sends a message via `st.chat_input`
2. The team runs for **one turn** (`max_messages=1`) and stops
3. The assistant's response is displayed
4. The team state is preserved in `st.session_state` so the conversation continues
5. When the user sends another message, the team resumes from where it left off

## Alternative: UserProxyAgent with ChainLit

If you need real-time human-in-the-loop interaction (where the agent asks questions mid-conversation), see the [ChainLit example](../agentchat_chainlit/) which supports `UserProxyAgent` natively.

## Related

- [Human-in-the-loop tutorial](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html)
- [Termination conditions](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/termination.html)
