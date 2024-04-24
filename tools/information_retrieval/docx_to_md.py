def docx_to_md(local_path):
    """
    Converts a DOCX file to Markdown format.

    Args:
        local_path (str): The local path of the DOCX file.

    Returns:
        str: The converted Markdown content.
    """
    # Code adapted from https://github.com/microsoft/autogen/blob/gaia_multiagent_v01_march_1st/autogen/mdconvert.py
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
