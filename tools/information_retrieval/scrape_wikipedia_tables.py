def scrape_wikipedia_tables(url: str, header_keyword: str):
    """
    Scrapes Wikipedia tables based on a given URL and header keyword.

    Args:
        url: The URL of the Wikipedia page to scrape.
        header_keyword: The keyword to search for in the headers of the page.

    Returns:
        list: A list of lists representing the scraped table data. Each inner list represents a row in the table,
              with each element representing a cell value.
    """
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    headers = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    data = []
    for header in headers:
        if header_keyword.lower() in header.text.lower():
            table = header.find_next_sibling("table", class_="wikitable")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all(["th", "td"])
                    cols = [ele.text.strip() for ele in cols]
                    data.append([ele for ele in cols if ele])
                break
    return data
