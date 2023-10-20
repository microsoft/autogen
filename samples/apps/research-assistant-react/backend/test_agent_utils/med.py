import requests
import json


def find_papers_pmc(query, size=10):
    """
    Find papers in PubMed Central (PMC) using Europe PMC API.

    Args:
        query (str): The search query to use.
        size (int): The number of results to return (default 10).

    Returns:
        None. Prints the title, url, publication date, and abstract of each paper found.
    """
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&resulttype=core&pageSize={size}&format=json"

    response = requests.get(url)
    data = json.loads(response.text)

    papers = data["resultList"]["result"]

    for i, paper in enumerate(papers):
        print(f"{i + 1}. {paper['title']}")
        print(f"URL: https://europepmc.org/article/MED/{paper['id']}")
        # print(f"Authors: {paper['authorString']}")
        print(f"Publication Date: {paper['firstPublicationDate']}")
        abstract = paper.get("abstractText", "No abstract available")
        print(f"Abstract: {abstract}\n")
