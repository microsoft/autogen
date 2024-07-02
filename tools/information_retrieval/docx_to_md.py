def docx_to_md(local_path):
    """
    Converts a DOCX file to Markdown format.

    Args:
        local_path (str): The local path of the DOCX file.

    Returns:
        str: The converted Markdown content.
    """
    # A simplified version of https://github.com/microsoft/autogen/blob/266cefc1737e0077667bce441c541a90865582b1/autogen/browser_utils/mdconvert.py
    # Will import the MdConverter Class as soon as PR#1929 is merged.
    import mammoth
    import markdownify
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

    with open(local_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html_content = result.value
        result = _convert(html_content)
    return result
