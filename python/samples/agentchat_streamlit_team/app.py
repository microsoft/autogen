# Copyright (c) Microsoft. All rights reserved.
# Streamlit example: Team with AssistantAgent using stop-and-resume pattern.

import asyncio
import yaml
import streamlit as st

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.models import ChatCompletionClient


def init_session():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "model_client" not in st.session_state:
        with open("model_config.yaml", "r") as f:
            config = yaml.safe_load(f)
        st.session_state["model_client"] = ChatCompletionClient.load_component(config)
    if "team" not in st.session_state:
        assistant = AssistantAgent(
            name="assistant",
            model_client=st.session_state["model_client"],
            system_message="You are a helpful AI assistant. Keep responses concise.",
        )
        termination = MaxMessageTermination(max_messages=1)
        st.session_state["team"] = RoundRobinGroupChat(
            [assistant],
            termination_condition=termination,
        )


async def run_team(task: str):
    """Run the team for one turn and return the result."""
    result = await st.session_state["team"].run(task=task)
    return result


def main():
    st.set_page_config(page_title="Team Chat (Stop-and-Resume)", page_icon="🤖")
    st.title("Team Chat: Stop-and-Resume Pattern 🤖")

    init_session()

    # Display chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Type a message...")
    if prompt:
        # Show user message
        st.session_state["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Run team for one turn using a new event loop
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(run_team(prompt))
        finally:
            loop.close()

        # Display assistant response
        for msg in result.messages:
            if hasattr(msg, "content") and msg.source == "assistant":
                content = msg.content
                if content and content != prompt:
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": content}
                    )
                    with st.chat_message("assistant"):
                        st.markdown(content)
                    break  # Only show the first assistant response


if __name__ == "__main__":
    main()
