import markdownify

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["markdownify"], ["markdownify"])
def spreadsheet_to_md(path):
    """
    Convert an Excel spreadsheet file to Markdown format.

    Args:
        path (str): The path to the Excel file.

    Returns:
        str: The Markdown content generated from the Excel file.
    """
    # A simplified version of https://github.com/microsoft/autogen/blob/266cefc1737e0077667bce441c541a90865582b1/autogen/browser_utils/mdconvert.py
    # Will change the code into importing the MdConverter Class as soon as PR#1929 is merged.
    import pandas as pd
    from bs4 import BeautifulSoup

    def _convert(html_content):
        """Helper function that converts and HTML string."""

        # Parse the string
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove javascript and style blocks
        for script in soup(["script", "style"]):
            script.extract()

        # Print only the main content
        body_elm = soup.find("body")
        webpage_text = ""
        if body_elm:
            webpage_text = markdownify.MarkdownConverter().convert_soup(body_elm)
        else:
            webpage_text = markdownify.MarkdownConverter().convert_soup(soup)
        return webpage_text

    sheets = pd.read_excel(path, sheet_name=None)
    md_content = ""
    for s in sheets:
        md_content += f"## {s}\n"
        html_content = sheets[s].to_html(index=False)
        md_content += _convert(html_content).strip() + "\n\n"
    return md_content
