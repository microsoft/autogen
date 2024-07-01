def perform_web_search(query, count=10, offset=0):
    """
    Perform a web search using Bing API.

    Args:
        query (str): The search query.
        count (int, optional): Number of search results to retrieve. Defaults to 10.
        offset (int, optional): Offset of the first search result. Defaults to 0.

    Returns:
        The name, URL and snippet of each search result.
    """
    import os

    import requests

    # Get the Bing API key from the environment variable
    bing_api_key = os.getenv("BING_API_KEY")

    # Check if the API key is available
    if not bing_api_key:
        raise ValueError("Bing API key not found in environment variable")

    # Set up the API request
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {
        "Ocp-Apim-Subscription-Key": bing_api_key,
    }
    params = {
        "q": query,
        "count": count,  # Number of search results to retrieve
        "offset": offset,  # Offset of the first search result
    }

    # Send the API request
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    # Process the search results
    search_results = response.json()
    for index, result in enumerate(search_results["webPages"]["value"]):
        print(f"Search Result {index+1}:")
        print(result["name"])
        print(result["url"])
        print(result["snippet"])
