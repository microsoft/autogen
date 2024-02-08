from .functions_utils import requires


@requires("pdfminer.six", "requests")
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


@requires("pillow", "requests", "easyocr")
def read_text_from_image(file_path: str) -> str:
    """
    Reads text from an image file or URL and returns it as a string.

    Args:
        file_path (str): The path to the image file or URL.

    Returns:
        str: The extracted text from the image file or URL.
    """
    import io
    import requests
    import easyocr
    from PIL import Image

    reader = easyocr.Reader(["en"])  # specify the language(s)

    if file_path.startswith("http://") or file_path.startswith("https://"):
        response = requests.get(file_path)
        image = Image.open(io.BytesIO(response.content))
    else:
        image = Image.open(file_path)

    output = reader.readtext(image)

    # The output is a list of tuples, each containing the coordinates of the text and the text itself.
    # We join all the text pieces together to get the final text.
    text = " ".join([item[1] for item in output])

    return text
