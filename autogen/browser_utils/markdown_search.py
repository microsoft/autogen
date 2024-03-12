# ruff: noqa: E722
import json
import re
import requests
import logging
import os

from bs4 import BeautifulSoup
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse, quote, quote_plus, unquote, urlunparse, parse_qs
from abc import ABC, abstractmethod
from typing import Optional, Union, Dict

from .mdconvert import MarkdownConverter

logger = logging.getLogger(__name__)

class AbstractMarkdownSearch(ABC):
    """
    An abstract class for providing search capabilities to a Markdown browser.
    """

    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def search(self, query) -> str:
        pass


class BingMarkdownSearch(AbstractMarkdownSearch):

    def __init__(self, bing_api_key: str = None):
        super().__init__()

        self._mdconvert = MarkdownConverter()

        if not None or bing_api_key.strip() == "":
            self._bing_api_key = os.environ.get("BING_API_KEY")
        else:
            self._bing_api_key = bing_api_key

        if self._bing_api_key is None:
            logger.warning("Warning: No Bing API key provided. BingMarkdownSearch will submit an HTTP request to the Bing landing page, but results may be missing or low quality. To resolve this warning provide a Bing API key by setting the BING_API_KEY environment variable, or using the 'bing_api_key' parameter in by BingMarkdownSearch's constructor. Bing API keys can be obtained via https://www.microsoft.com/en-us/bing/apis/bing-web-search-api\n")


    def search(self, query: str):
        if self._bing_api_key is None:
            return self._fallback_search(query)
        else:
            return self._api_search(query)

    def _api_search(self, query: str):
        results = self._bing_api_call(query)

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
                snippet = f"__POS__. {self._markdown_link(page['name'], page['url'])}\n{page['snippet']}"
            
                if "richFacts" in page:
                    snippet += "\n" + _processFacts(page["richFacts"])

                if "mentions" in page:
                    snippet += "\n" + _processMentions(page["mentions"])

                if page["id"] not in snippets:
                    snippets[page["id"]] = list()
                snippets[page["id"]].append(snippet)

                if "deepLinks" in page:
                    for dl in page["deepLinks"]:
                        snippets[page["id"]].append(f"__POS__. {self._markdown_link(dl['name'], dl['url'])}\n{dl['snippet'] if 'snippet' in dl else ''}")

        # News results
        if "news" in results:
            news_snippets = list()
            for page in results["news"]["value"]:
                snippet = f"__POS__. {self._markdown_link(page['name'], page['url'])}\n{page['description']}"

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

                snippet = f"__POS__. {self._markdown_link(page['name'], page['contentUrl'])}\n{page['description']}"

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


    def _bing_api_call(self, query: str):
        # Make sure the key was set
        if not self._bing_api_key:
            raise ValueError("Missing Bing API key.")

        # Prepare the request parameters
        request_kwargs = {}
        request_kwargs["headers"] = {}
        request_kwargs["headers"]["Ocp-Apim-Subscription-Key"] = self._bing_api_key

        request_kwargs["params"] = {}
        request_kwargs["params"]["q"] = query
        request_kwargs["params"]["textDecorations"] = False
        request_kwargs["params"]["textFormat"] = "raw"

        request_kwargs["stream"] = False

        # Make the reques
        response = requests.get("https://api.bing.microsoft.com/v7.0/search", **request_kwargs)
        response.raise_for_status()
        results = response.json()

        return results  


    def _fallback_search(self, query: str):
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        headers = {"User-Agent": user_agent}

        url = f"https://www.bing.com/search?q={quote_plus(query)}&FORM=QBLH"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return self._mdconvert.convert_response(response).text_content


    def _markdown_link(self, anchor, href):
        """ Create a Markdown hyperlink, escaping the URLs as appropriate."""
        try:
            parsed_url = urlparse(href)
            href = urlunparse(parsed_url._replace(path=quote(unquote(parsed_url.path))))
            anchor = re.sub(r"[\[\]]", " ", anchor)
            return f"[{anchor}]({href})"
        except ValueError: # It's not clear if this ever gets thrown
            return f"[{anchor}]({href})"
