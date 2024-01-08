from sample_service import assistant, user_proxy

user_proxy.initiate_chat(
    assistant,
    message="What is the change YTD of the S&P 500?",
)
