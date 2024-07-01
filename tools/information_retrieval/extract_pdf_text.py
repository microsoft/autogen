from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["PyMuPDF"])
def extract_pdf_text(pdf_path, page_number=None):
    """
    Extracts text from a specified page or the entire PDF file.

    Args:
        pdf_path (str): The path to the PDF file.
        page_number (int, optional): The page number to extract (starting from 0). If not provided,
            the function will extract text from the entire PDF file.

    Returns:
        str: The extracted text.
    """
    import fitz

    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Extract text from the entire PDF file or a specific page
    text = ""
    if page_number is None:
        # Extract content from the entire PDF file
        for page in doc:
            text += page.get_text()
    else:
        # Extract content from a specific page
        page = doc[page_number]
        text = page.get_text()

    # Close the PDF file
    doc.close()

    return text
