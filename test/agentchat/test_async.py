import pytest
import asyncio
import autogen
from conftest import skip_openai
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai


def get_market_news(ind, ind_upper):
    data = {
        "feed": [
            {
                "title": "Palantir CEO Says Our Generation's Atomic Bomb Could Be AI Weapon - And Arrive Sooner Than You Think - Palantir Technologies  ( NYSE:PLTR ) ",
                "summary": "Christopher Nolan's blockbuster movie \"Oppenheimer\" has reignited the public discourse surrounding the United States' use of an atomic bomb on Japan at the end of World War II.",
                "overall_sentiment_score": 0.009687,
            },
            {
                "title": '3 "Hedge Fund Hotels" Pulling into Support',
                "summary": "Institutional quality stocks have several benefits including high-liquidity, low beta, and a long runway. Strategist Andrew Rocco breaks down what investors should look for and pitches 3 ideas.",
                "banner_image": "https://staticx-tuner.zacks.com/images/articles/main/92/87.jpg",
                "overall_sentiment_score": 0.219747,
            },
            {
                "title": "PDFgear, Bringing a Completely-Free PDF Text Editing Feature",
                "summary": "LOS ANGELES, July 26, 2023 /PRNewswire/ -- PDFgear, a leading provider of PDF solutions, announced a piece of exciting news for everyone who works extensively with PDF documents.",
                "overall_sentiment_score": 0.360071,
            },
            {
                "title": "Researchers Pitch 'Immunizing' Images Against Deepfake Manipulation",
                "summary": "A team at MIT says injecting tiny disruptive bits of code can cause distorted deepfake images.",
                "overall_sentiment_score": -0.026894,
            },
            {
                "title": "Nvidia wins again - plus two more takeaways from this week's mega-cap earnings",
                "summary": "We made some key conclusions combing through quarterly results for Microsoft and Alphabet and listening to their conference calls with investors.",
                "overall_sentiment_score": 0.235177,
            },
        ]
    }
    feeds = data["feed"][ind:ind_upper]
    feeds_summary = "\n".join(
        [
            f"News summary: {f['title']}. {f['summary']} overall_sentiment_score: {f['overall_sentiment_score']}"
            for f in feeds
        ]
    )
    return feeds_summary


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
@pytest.mark.asyncio
async def test_async_groupchat():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)

    llm_config = {
        "timeout": 600,
        "cache_seed": 41,
        "config_list": config_list,
        "temperature": 0,
    }

    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 41,
            "config_list": config_list,
            "temperature": 0,
        },
        system_message="You are a helpful assistant.  Reply 'TERMINATE' to end the conversation.",
    )
    # create a UserProxyAgent instance named "user"
    user_proxy = autogen.UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        code_execution_config=False,
        default_auto_reply=None,
    )

    groupchat = autogen.GroupChat(agents=[user_proxy, assistant], messages=[], max_round=12)
    manager = autogen.GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    )
    await user_proxy.a_initiate_chat(manager, message="""Have a short conversation with the assistant.""")
    assert len(user_proxy.chat_messages) > 0


@pytest.mark.skipif(skip, reason="openai not installed OR requested to skip")
@pytest.mark.asyncio
async def test_stream():
    config_list = autogen.config_list_from_json(OAI_CONFIG_LIST, KEY_LOC)
    data = asyncio.Future()

    async def add_stock_price_data():
        # simulating the data stream
        for i in range(0, 2, 1):
            latest_news = get_market_news(i, i + 1)
            if data.done():
                data.result().append(latest_news)
            else:
                data.set_result([latest_news])
            # print(data.result())
            await asyncio.sleep(5)

    data_task = asyncio.create_task(add_stock_price_data())
    # create an AssistantAgent instance named "assistant"
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config={
            "timeout": 600,
            "cache_seed": 41,
            "config_list": config_list,
            "temperature": 0,
        },
        system_message="You are a financial expert.",
    )
    # create a UserProxyAgent instance named "user"
    user_proxy = autogen.UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        code_execution_config=False,
        default_auto_reply=None,
    )

    async def add_data_reply(recipient, messages, sender, config):
        await asyncio.sleep(0.1)
        data = config["news_stream"]
        if data.done():
            result = data.result()
            if result:
                news_str = "\n".join(result)
                result.clear()
                return (
                    True,
                    f"Just got some latest market news. Merge your new suggestion with previous ones.\n{news_str}",
                )
            return False, None

    user_proxy.register_reply(autogen.AssistantAgent, add_data_reply, position=2, config={"news_stream": data})

    await user_proxy.a_initiate_chat(
        assistant,
        message="""Give me investment suggestion in 3 bullet points.""",
    )
    while not data_task.done() and not data_task.cancelled():
        reply = await user_proxy.a_generate_reply(sender=assistant)
        if reply is not None:
            await user_proxy.a_send(reply, assistant)


if __name__ == "__main__":
    asyncio.run(test_stream())
