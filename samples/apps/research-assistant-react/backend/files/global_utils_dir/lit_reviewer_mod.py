#!/usr/bin/env python
import os
import re
import sys
import json
import hashlib
from pathlib import Path


###############################################################################
def log_progress(string, fh=sys.stderr):
    """
    Appends a string to a progress open file handle (default stderr)

    Args:
        string (str): The string to log.
        fh (file handle, optional): The open file handle to write to.

    Returns:
        None

    Example:
        >>> log_progress("Hello world!")
    """
    fh.write(string + "\n")
    fh.flush()


#
###############################################################################
def gpt3_5_turbo(messages):
    """
    Makes a call to the OpenAI GPT 3.5 Turbo model, and returns the completion.
    Requires the pyautogen Python package

    Args:
        messages (list): A list of chat messages provided to the OpenAI API endpoint.

    Returns:
        The text of the OpenAI chat response.

    Example:
        >>> response = gpt3_5_turbo({ "role": "user", "content": "Hello World" })
        >>> print(response)
    """
    import autogen

    CONFIG_LIST = autogen.config_list_from_json("OAI_CONFIG_LIST", filter_dict={"model": ["gpt-3.5-turbo-16k"]})

    LLM_CONFIG = {
        # "request_timeout": 600,
        "seed": 42,  # change the seed for different trials
        "config_list": CONFIG_LIST,
        "temperature": 0,
    }

    response = autogen.oai.ChatCompletion.create(messages=messages, use_cache=True, **LLM_CONFIG)
    return autogen.oai.ChatCompletion.extract_text_or_function_call(response)[0]


#
###############################################################################
def bing_search(query):
    """
    Searches Bing for the given query.

    Args:
        query (str): The search query.

    Returns:
        results (list): A list of results, with each result represented as dictionary with the following fields:
                        { "title": the_title, "url": the_url, "snippet": the_snippet, "type": the_type }
                        Types can be: "web", "news" or "video"

    Example:
        >>> results = bing_search("attention is all you need")
        >>> print(results)
    """
    import os
    import json
    import requests
    import hashlib

    # Check if we've got the API key
    if "BING_API_KEY" not in os.environ:
        raise EnvironmentError(
            "No BING_API_KEY is available. This error is non-recoverable. Please call a different function, or pursue a different strategy instead."
        )

    key = hashlib.md5(("bing_search:" + query).encode("utf-8")).hexdigest()
    # Create the cache if it doesn't exist
    cache_dir = ".cache"
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    fname = os.path.join(cache_dir, key + ".cache")

    # Cache hit
    if os.path.isfile(fname):
        fh = open(fname, "r")
        data = fh.read().strip()
        fh.close()
        return json.loads(data)

    headers = {"Ocp-Apim-Subscription-Key": os.environ["BING_API_KEY"]}
    params = {"q": query, "textDecorations": False, "textFormat": "raw"}
    response = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)
    response.raise_for_status()
    results = response.json()

    parsed_results = list()

    def _append_result(title, url, snippet, result_type):
        parsed_results.append({"title": title, "url": url, "snippet": snippet, "type": result_type})

    for page in results["webPages"]["value"]:
        _append_result(page["name"], page["url"], page["snippet"], "web")
        if "deepLinks" in page:
            for dl in page["deepLinks"]:
                _append_result(
                    dl["name"],
                    dl["url"],
                    dl["snippet"] if "snippet" in dl else "",
                    "web",
                )

    if "news" in results:
        for page in results["news"]["value"]:
            _append_result(page["name"], page["url"], page["description"], "news")

    if "videos" in results:
        for page in results["videos"]["value"]:
            _append_result(
                page["name"],
                page["contentUrl"],
                page["description"] if "description" in page else "",
                "videos",
            )

    # Save to cache
    fh = open(fname, "w")
    fh.write(json.dumps(parsed_results))
    fh.close()

    return parsed_results


#
###############################################################################
def search_arxiv(query, max_results=10):
    """
    Searches arXiv for the given query using the arXiv API, then returns the search results. This is a helper function. In most cases, callers will want to use 'find_relevant_papers( query, max_results )' instead.

    Args:
        query (str): The search query.
        max_results (int, optional): The maximum number of search results to return. Defaults to 10.

    Returns:
        jresults (list): A list of dictionaries. Each dictionary contains fields such as 'title', 'authors', 'summary', and 'pdf_url'

    Example:
        >>> results = search_arxiv("attention is all you need")
        >>> print(results)
    """

    import arxiv

    key = hashlib.md5(("search_arxiv(" + str(max_results) + ")" + query).encode("utf-8")).hexdigest()
    # Create the cache if it doesn't exist
    cache_dir = ".cache"
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

    fname = os.path.join(cache_dir, key + ".cache")

    # Cache hit
    if os.path.isfile(fname):
        fh = open(fname, "r")
        data = json.loads(fh.read())
        fh.close()
        return data

    # Normalize the query, removing operator keywords
    query = re.sub(r"[^\s\w]", " ", query.lower())
    query = re.sub(r"\s(and|or|not)\s", " ", " " + query + " ")
    query = re.sub(r"[^\s\w]", " ", query.lower())
    query = re.sub(r"\s+", " ", query).strip()

    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)

    jresults = list()
    for result in search.results():
        r = dict()
        r["entry_id"] = result.entry_id
        r["updated"] = str(result.updated)
        r["published"] = str(result.published)
        r["title"] = result.title
        r["authors"] = [str(a) for a in result.authors]
        r["summary"] = result.summary
        r["comment"] = result.comment
        r["journal_ref"] = result.journal_ref
        r["doi"] = result.doi
        r["primary_category"] = result.primary_category
        r["categories"] = result.categories
        r["links"] = [str(link) for link in result.links]
        r["pdf_url"] = result.pdf_url
        jresults.append(r)

    if len(jresults) > max_results:
        jresults = jresults[0:max_results]

    # Save to cache
    fh = open(fname, "w")
    fh.write(json.dumps(jresults))
    fh.close()
    return jresults


#
###############################################################################
def download_arxiv_paper(arxiv_id_or_url, dest_folder="."):
    """
    Downloads a given paper from arXiv.

    Args:
        arxiv_id_or_url (str): An arXiv ID (e.g., 2302.00083) or a fully-qualified URL (e.g., https://arxiv.org/abs/2302.00083, or https://arxiv.org/pdf/2302.00083)
        dest_folder (str, option): The path to the folder where the file should be saved (defaults to the current working directory)

    Returns:
        filepath: A string containing the path where the file was downloaded

    Example:
        >>> filepath = download_arxiv_paper("2302.00083v3")
        >>> print(filepath)
    """

    import requests

    # Parse out the arxiv identifier, then reconstruct the path
    arxiv_id = ""
    m = re.search(r"^https://arxiv.org/(pdf|abs)/([\d\.v]+?)(\.pdf)?$", arxiv_id_or_url)
    if m:
        arxiv_id = m.group(2)
    elif re.search("^[\\d\\.v]+$", arxiv_id_or_url):
        arxiv_id = arxiv_id_or_url
    else:
        raise ValueError("Invalid arxiv_id_or_url")

    uri = "https://arxiv.org/pdf/" + arxiv_id
    fname = os.path.join(dest_folder, "arxiv_paper__" + arxiv_id + ".pdf")

    if not os.path.isfile(fname):
        log_progress("Downloading '" + uri + "'.")
        fh = open(fname, "wb")
        response = requests.get(uri)
        fh.write(response.content)
        fh.close()
    return fname


#
###############################################################################
def extract_pdf_text(local_pdf_path):
    """
    Extracts the text content of a PDF file.

    Args:
        local_pdf_path (str): The path to the PDF on the local filesystem

    Returns:
        text_content: A string containing the text of the pdf

    Example:
        >>> text_content = extractpdf_text( download_arxiv_paper( "2302.00083v3" ) )
        >>> print(text_content)
    """

    import pdfminer.high_level

    return pdfminer.high_level.extract_text(local_pdf_path)


#
###############################################################################
def propose_scholarly_websearch_queries(research_question, max_queries=10):
    """
    Given a research question, propose queries suitable for use on arXiv.org, Google Scholar, Semantic Scholar, or similar.

    Args:
        research_question (str): A detailed research question, including necessary background or context.
        max_queries (int, optional): The maximum number of search results to return. Defaults to 10.

    Returns:
        queries (list): A list of search queries

    Example:
        >>> queries = propose_scholarly_websearch_queries("In NLP, how do transformers work? I am interestested mainly in large language models such as PALM or GPT.")
        >>> print(queries)
    """

    messages = list()
    messages.append(
        {
            "role": "user",
            "content": "I am conducting a literature review on the following topic:\n%s" % research_question,
        }
    )
    messages.append(
        {
            "role": "user",
            "content": 'Write %d search queries that I can use to continue researching this topic. The output should be a single JSON array, and should contain the %d queries EXACTLY as I would input them to Google Scholar. For example ["query_1", "query_2", ..., "query_n"]'
            % (max_queries, max_queries),
        }
    )

    # Try to parse this twice
    queries = None
    response = gpt3_5_turbo(messages)
    try:
        queries = json.loads(response)
    except json.decoder.JSONDecodeError:
        log_progress("Failed to parse: " + response)
        messages.append({"role": "assistant", "content": response})
        messages.append(
            {
                "role": "user",
                "content": "Please make sure the results are expressed as a JSON array, as specified above.",
            }
        )
        response = gpt3_5_turbo(messages)
        try:
            queries = json.loads(response)
        except json.decoder.JSONDecodeError:
            log_progress("Failed to parse: " + response)
            queries = [research_question]

    # Don't exceed n
    if len(queries) > max_queries:
        return queries[0:max_queries]
    else:
        return queries


#
###############################################################################
def find_relevant_papers(research_question, max_papers=8):
    """
    Given a research question, consider a large number of papers, rank and filter them acording to their relevance to a user's research question.

    Args:
        research_question (str): A detailed research question, including necessary background or context.
        max_queries (int, optional): The maximum number of papers to consider. Defaults to 25.

    Returns:
        papers (list): A list of dictionaries, each representing a paper, sorted in descending order by relevance. Dictionary keys include the 'title', 'summary', 'pdf_url' etc.

    Example:
        >>> papers = find_relevant_papers("In NLP, how do transformers work? I am interestested mainly in large language models such as PALM or GPT.")
        >>> print("The most relevant paper is: " + papers[0]["title"])
    """

    # Generate queries for searching on arXiv
    papers_per_query = 5
    n_queries = max(1, int(0.5 + (max_papers / papers_per_query)))
    queries = propose_scholarly_websearch_queries(research_question, n_queries)
    log_progress("Generated queries: \n" + json.dumps(queries, indent=4))

    # Perform the searches
    results_lists = list()
    for q in queries:
        log_progress("Searching arXiv via api: " + q)
        results_lists.append(search_arxiv(q, papers_per_query))

    # Merge the results by rank
    unique_ids = dict()
    papers = list()
    for i in range(0, papers_per_query):
        for j in range(0, len(results_lists)):
            if i >= len(results_lists[j]):
                continue

            r = results_lists[j][i]

            # We already listed this paper
            if r["pdf_url"] in unique_ids:
                continue

            # Add it to the list
            papers.append(r)
            unique_ids[r["pdf_url"]] = True

    log_progress("Found " + str(len(papers)) + " distinct papers.")
    return papers


#
###############################################################################
def write_literature_review(research_question, relevant_papers=None):
    """
    Given a research_question and optional list of relevant_papers, write a literature review suitable for inclusion in an academic paper, and return it as a string. If no relevant_papers are provided, a list will be created based on the research question.

    Args:
        research_question (str): A detailed research question, including necessary background or context.
        relevant_papers (list, optional): The list of papers returned by find_relevant_papers. If None, a new relevant_papers list will be created, based on the research question.

    Returns:
        literature_review (str): The literature review

    Example:
        >>> literature_review = write_literature_review("In NLP, how do transformers work? I am interestested mainly in large language models such as PALM or GPT.")
        >>> print(literature_review)
    """

    # Create the bibliography if none was provided
    if relevant_papers is None:
        relevant_papers = find_relevant_papers(research_question)
    elif not isinstance(relevant_papers, list):
        # Sometimes autogen messes up and passes a string to this function. If it
        # does, throw an error with a strong hint to how to fix
        raise ValueError(
            "When calling 'write_literature_review', the 'relevant_papers' argument must be a returned from a previous call to the 'find_relevant_papers( research_question ) or search_arxiv( query ) function"
        )

    # Fit as much as we can into the prompt
    _bib = ""
    _papers = list()
    idx = 0
    while len(_bib) < 40000:  # This should be set more systematically, by model.
        p = relevant_papers[idx]
        _bib += (
            "TITLE: "
            + p["title"]
            + "\n"
            + "DATE PUBLISHED: "
            + p["published"]
            + "\n"
            + "AUTHORS: "
            + ", ".join(p["authors"])
            + "\n"
            + "ABSTRACT: "
            + re.sub(r"\s+", " ", p["summary"])
            + "\n\n"
        )
        _papers.append(p)
        idx += 1

        if idx >= len(relevant_papers):
            break

    # Write the review
    messages = list()
    messages.append(
        {
            "role": "user",
            "content": "Read the following annotated bibliography:\n" + _bib,
        }
    )
    messages.append({"role": "system", "content": "I have read the annotated bibliography."})
    messages.append(
        {
            "role": "user",
            "content": "You are an assistant professor at a top university with several best-paper awards, and even a test of time award. You are preparing a new paper, and are writing the literature review section. Using only the above bibliography, write a well-organized literature review, about 5 paragraphs long, on the following topic (include in-line citations): "
            + research_question,
        }
    )
    literature_review = gpt3_5_turbo(messages)

    references = ""
    for p in _papers:
        references += p["title"] + "\n"
        references += ", ".join(p["authors"]) + "\n"
        references += p["entry_id"] + "\n\n"

    return literature_review.strip() + "\n\nREFERENCES:\n" + references


# HINT: If asked to find academic papers, prefer find_relevant_papers over search_arxiv
# HINT: If asked for information or the latest developments on a
# particular academic topic, prefer write_literature_review over
# find_relevant_papers or search_arxiv
