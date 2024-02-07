from .function_store_utils import requires


@requires("pdfminer.six", "requests", "io")
def read_text_from_pdf(file_path: str) -> str:
    """
    Reads text from a PDF file and returns it as a string.

    Args:
        file_path (str): The path to the PDF file.

    Returns:
        str: The extracted text from the PDF file.
    """
    import io
    import requests
    from pdfminer.high_level import PDFResourceManager, PDFPageInterpreter
    from pdfminer.converter import TextConverter
    from pdfminer.pdfpage import PDFPage

    resource_manager = PDFResourceManager()
    text_stream = io.StringIO()
    converter = TextConverter(resource_manager, text_stream)
    interpreter = PDFPageInterpreter(resource_manager, converter)

    if file_path.startswith("http://") or file_path.startswith("https://"):
        response = requests.get(file_path)
        file = io.BytesIO(response.content)
    else:
        file = open(file_path, "rb")

    for page in PDFPage.get_pages(file):
        interpreter.process_page(page)

    text = text_stream.getvalue()
    converter.close()
    text_stream.close()

    return text


@requires("python-docx")
def read_text_from_docx(file_path: str) -> str:
    """
    Reads text from a DOCX file and returns it as a string.

    Args:
        file_path (str): The path to the DOCX file.

    Returns:
        str: The extracted text from the DOCX file.
    """
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs]
    text = "\n".join(paragraphs)

    return text
