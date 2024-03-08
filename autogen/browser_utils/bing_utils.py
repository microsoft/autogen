# ruff: noqa: E722
import json
import time
import requests
import re
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse, quote, unquote, urlunparse

def bing_api_call(query: str, bing_api_key: str) -> Dict[str, Dict[str, List[Dict[str, Union[str, Dict[str, str]]]]]]:
    # Make sure the key was set
    if not bing_api_key:
        raise ValueError("Missing Bing API key.")

    # Prepare the request parameters
    request_kwargs = {}
    request_kwargs["headers"] = {}
    request_kwargs["headers"]["Ocp-Apim-Subscription-Key"] = bing_api_key

    request_kwargs["params"] = {}
    request_kwargs["params"]["q"] = query
    request_kwargs["params"]["textDecorations"] = False
    request_kwargs["params"]["textFormat"] = "raw"

    request_kwargs["stream"] = False

    # Make the reques
    response = requests.get("https://api.bing.microsoft.com/v7.0/search", **request_kwargs)
    response.raise_for_status()
    results = response.json()

    return results  # type: ignore[no-any-return]


def bing_search_markdown(query: str, bing_api_key: str) -> str:
    results = bing_api_call(query, bing_api_key)

    snippets = dict()

    def _processFacts(elm):
        facts = list()
        for e in elm:
            k = e["label"]["text"]
            v = " ".join(item["text"] for item in e["items"])
            facts.append(f"{k}: {v}")
        return "\n".join(facts)

    # Web pages
    # __POS__ is a placeholder for the final ranking positon, added at the end
    if "webPages" in results:
        for page in results["webPages"]["value"]:
            snippet = f"__POS__. {_markdown_link(page['name'], page['url'])}\n{page['snippet']}"
            
            if "richFacts" in page:
                snippet += "\n" + _processFacts(page["richFacts"])

            if "mentions" in page:
                snippet += "\n" + _processMentions(page["mentions"])

            if page["id"] not in snippets:
                snippets[page["id"]] = list()
            snippets[page["id"]].append(snippet)

            if "deepLinks" in page:
                for dl in page["deepLinks"]:
                    snippets[page["id"]].append(f"__POS__. {_markdown_link(dl['name'], dl['url'])}\n{dl['snippet'] if 'snippet' in dl else ''}")

    # News results
    if "news" in results:
        news_snippets = list()
        for page in results["news"]["value"]:
            snippet = f"__POS__. {_markdown_link(page['name'], page['url'])}\n{page['description']}"

            if "datePublished" in page:
                snippet += "\nDate published: " + page["datePublished"].split("T")[0]

            if "richFacts" in page:
                snippet += "\n" + _processFacts(page["richFacts"])

            if "mentions" in page:
                snippet += "\nMentions: " + ", ".join(e["name"] for e in page["mentions"]) 

            news_snippets.append(snippet)

        if len(news_snippets) > 0:
            snippets[results["news"]["id"]] = news_snippets

    # Videos
    if "videos" in results:
        video_snippets = list()
        for page in results["videos"]["value"]:
            if not page["contentUrl"].startswith("https://www.youtube.com/watch?v="):
                continue

            snippet = f"__POS__. {_markdown_link(page['name'], page['contentUrl'])}\n{page['description']}"

            if "datePublished" in page:
                snippet += "\nDate published: " + page["datePublished"].split("T")[0]

            if "richFacts" in page:
                snippet += "\n" + _processFacts(page["richFacts"])

            if "mentions" in page:
                snippet += "\nMentions: " + ", ".join(e["name"] for e in page["mentions"]) 

            video_snippets.append(snippet)

        if len(video_snippets) > 0:
            snippets[results["videos"]["id"]] = video_snippets

    # Related searches
    if "relatedSearches" in results:
        related_searches = "## Related Searches:\n"
        for s in results["relatedSearches"]["value"]:
            related_searches += "- " + s["text"] + "\n"
        snippets[results["relatedSearches"]["id"]] = [ related_searches.strip() ]

    idx = 0
    content = ""
    for item in results["rankingResponse"]["mainline"]["items"]:
        _id = item["value"]["id"]
        if _id in snippets:
            for s in snippets[_id]:
                if "__POS__" in s:
                    idx += 1
                    content += s.replace("__POS__", str(idx)) + "\n\n"
                else:
                    content += s + "\n\n"

    return f"## A Bing search for '{query}' found {idx} results:\n\n" + content.strip()


def _markdown_link(anchor, href):
    """ Create a Markdown hyperlink, escaping the URLs as appropriate."""
    try:
        parsed_url = urlparse(href)
        href = urlunparse(parsed_url._replace(path=quote(unquote(parsed_url.path))))
        anchor = re.sub(r"[\[\]]", " ", anchor)
        return f"[{anchor}]({href})"
    except ValueError: # It's not clear if this ever gets thrown
        return f"[{anchor}]({href})"


###############################################################################
if __name__ == "__main__":
    import os
    import sys
    print(bing_search_markdown(" ".join(sys.argv[1:]), os.environ["BING_API_KEY"]))
