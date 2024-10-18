"""From WebArena with minor modifications. Implements helper functions to assist evaluation cases where other evaluators are not suitable."""

import json
from typing import Any
from urllib.parse import urlparse

import requests
from playwright.async_api import Page

from .env_config import (
    ACCOUNTS,
    GITLAB,
    MAP,
    REDDIT,
    SHOPPING,
    SHOPPING_ADMIN,
    WIKIPEDIA,
)

from .openai_utils import (
    generate_from_openai_chat_completion,
)

import autogen


def shopping_get_auth_token() -> str:
    response = requests.post(
        url=f"{SHOPPING}/rest/default/V1/integration/admin/token",
        headers={"content-type": "application/json"},
        data=json.dumps(
            {
                "username": ACCOUNTS["shopping_site_admin"]["username"],
                "password": ACCOUNTS["shopping_site_admin"]["password"],
            }
        ),
    )
    token: str = response.json()
    return token


def shopping_get_latest_order_url() -> str:
    """Get the latest order url from the shopping website."""

    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }

    params = {
        "searchCriteria[sortOrders][0][field]": "created_at",
        "searchCriteria[sortOrders][0][direction]": "DESC",
        "searchCriteria[pageSize]": "1",
    }

    response = requests.get(f"{SHOPPING}/rest/V1/orders", params=params, headers=header)
    assert response.status_code == 200
    response_obj = response.json()["items"][0]
    order_id = int(response_obj["increment_id"])
    order_url = f"{SHOPPING}/sales/order/view/order_id/{order_id}/"
    return order_url


def shopping_get_sku_latest_review_author(sku: str) -> str:
    """Get the latest review for shopping admin."""
    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }
    response = requests.get(f"{SHOPPING}/rest/V1/products/{sku}/reviews", headers=header)
    assert response.status_code == 200
    response_obj = response.json()
    if len(response_obj) == 0:
        return ""
    author: str = response_obj[-1]["nickname"]
    return author


def shopping_get_sku_latest_review_rating(sku: str) -> str:
    """Get the latest review for shopping admin."""
    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }
    response = requests.get(f"{SHOPPING}/rest/V1/products/{sku}/reviews", headers=header)
    assert response.status_code == 200
    response_obj = response.json()
    if len(response_obj) == 0:
        return ""
    assert response_obj[0]["ratings"][0]["rating_name"] == "Rating"
    rating: str = str(response_obj[-1]["ratings"][0]["percent"])
    return rating


def reddit_get_post_url(url: str) -> str:
    """Get the post url"""
    # Url is http://domain/f/subreddit/post_id/...
    # get domain, subreddit, post_id
    domain = urlparse(url).netloc
    tok_url = urlparse(url).path.split("/")
    # not a valid post/comment url, return the url as is
    if len(tok_url) < 4:
        return url
    if tok_url[1] != "f":
        return url
    subreddit = urlparse(url).path.split("/")[2]
    post_id = urlparse(url).path.split("/")[3]
    scheme = urlparse(url).scheme
    post_url = f"{scheme}://{domain}/f/{subreddit}/{post_id}/"
    return post_url


async def gitlab_get_project_memeber_role(page: Page, account_name: str) -> str:
    # get the account index
    try:
        account_idx = await page.evaluate(
            f"""(() => {{
                const elements = document.querySelectorAll("td[data-label='Account'] span.gl-avatar-labeled-sublabel");
                let index = -1;  // Default value if not found

                for(let i = 0; i < elements.length; i++) {{
                    if(elements[i].outerText === '@{account_name}') {{
                        index = i;
                        break;
                    }}
                }}

                return index;
            }})()"""
        )

        # get the role
        role: str = await page.evaluate(
            f"""(() => {{
                return document.querySelectorAll("td.col-max-role span")[{account_idx}].outerText;
            }})()"""
        )
    except Exception:
        role = ""

    return role


def llm_fuzzy_match(pred: str, reference: str, question: str, azure_config: dict[str, Any] | None) -> float:
    """Check whether the prediction matches the reference with GPT4-turbo"""
    messages: list[dict[str, Any]] = []
    # construct the question to ask
    message = "Help a teacher to grade the answer of a student given a question. Keep in mind that the student may use different phrasing or wording to answer the question. The goal is to evaluate whether the answer is semantically equivalent to the reference answer.\n"
    message += f"question: {question}\n"
    message += f"reference answer: {reference}\n"
    message += "all the string 'N/A' that you see is a special sequence that means 'not achievable'\n"
    message += f"student answer: {pred}\n"
    message += "Conclude the judgement by correct/incorrect/partially correct."
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": message},
    ]

    response = None
    if azure_config is None:
        response = generate_from_openai_chat_completion(
            model="gpt-4-1106-preview",
            messages=messages,
            temperature=0,
            max_tokens=768,
            top_p=1.0,
            context_length=0,
        ).lower()
    else:
        client = autogen.OpenAIWrapper(**azure_config)
        raw_response = client.create(context=None, messages=messages)
        response = client.extract_text_or_completion_object(raw_response)[0].lower()

    if "partially correct" in response or "incorrect" in response:
        return 0.0
    else:
        assert "correct" in response
        return 1.0


def llm_ua_match(pred: str, reference: str, question: str, azure_config: dict[str, Any] | None) -> float:
    """Check whether the prediction matches the reference with GPT-turbo"""
    messages: list[dict[str, Any]] = []
    # construct the question to ask
    message = ""
    message += f"task: {question}\n"
    message += f"actual unachievable reason: {reference}\n"
    message += f"reported unachievable reason: {pred}\n"
    message += (
        "The task described above is inherently unachievable due to the reason specified under 'actual unachievable reason'. "
        "An individual previously attempted this task and was unable to complete it. They provided a reason for their failure, "
        "which is listed under 'reported unachievable reason'. Your role is to review both the actual and reported reasons. "
        "Determine if the reported reason aligns with the actual reason, even if implicitly. "
        "If the stated reason is in line with the actual reason, respond with 'same'. Otherwise, respond with 'different'."
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": message},
    ]

    response = None
    if azure_config is None:
        response = generate_from_openai_chat_completion(
            model="gpt-4-1106-preview",
            messages=messages,
            temperature=0,
            max_tokens=768,
            top_p=1.0,
            context_length=0,
        ).lower()
    else:
        client = autogen.OpenAIWrapper(**azure_config)
        raw_response = client.create(context=None, messages=messages)
        response = client.extract_text_or_completion_object(raw_response)[0].lower()

    if "different" in response:
        return 0.0
    else:
        assert "same" in response
        return 1.0


class PseudoPage:
    def __init__(self, original_page: Page, url: str):
        self.url = url
        self.original_page = original_page

    def __getattr__(self, attr: str) -> Any:
        # Delegate attribute access to the original page object
        if attr not in ["url"]:
            return getattr(self.original_page, attr)
        else:
            return getattr(self, attr)
