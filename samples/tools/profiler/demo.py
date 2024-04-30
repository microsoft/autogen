from profiler.profiler import Profiler
from profiler.message import Message
from profiler.llm import OpenAIJSONService


chat_history = [
    Message(
        source="user",
        role="user",
        content="Plot a chart of NVIDIA stock prices; Also here are results from prev execution",
    ),
    Message(source="orchestrator", role="assistant", content="assistant please write code to solve the task"),
    Message(
        source="assistant",
        role="assistant",
        content="""Sure, I can help with that.

    Please run the following script in your terminal to plot the chart:

    ```python
    import pandas as pd
    import yfinance as yf
    import matplotlib.pyplot as plt

    # Download NVIDIA stock data
    nvda = yf.Ticker("NVDA")
    nvda_data = nvda.history(period="1y")

    ```

""",
    ),
    Message(
        source="user", role="user", content="""I'm getting an error when I run the script. Can you help me debug it?"""
    ),
]


profiler = Profiler(llm_service=OpenAIJSONService())

for idx, message in enumerate(chat_history):
    profile = profiler.profile_message(chat_history, idx)
    print(profile)
