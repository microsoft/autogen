import os

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["PyMuPDF"], ["os"])
def extract_pdf_image(pdf_path: str, output_dir: str, page_number=None):
    """
    Extracts images from a PDF file and saves them to the specified output directory.

    Args:
        pdf_path (str): The path to the PDF file.
        output_dir (str): The directory to save the extracted images.
        page_number (int, optional): The page number to extract images from. If not provided, extract images from all pages.
    """
    import fitz  # PyMuPDF library

    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Extract images from the PDF file
    images = []
    if page_number is not None:
        page = doc[page_number - 1]  # Adjust page number to 0-based index
        for img in page.get_images():
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            images.append(image_bytes)
    else:
        for page in doc:
            for img in page.get_images():
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                images.append(image_bytes)

    # Save the extracted images
    for i, image_bytes in enumerate(images):
        image_path = os.path.join(output_dir, f"image_{i}.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)

    # Print the total number of images saved
    print(f"Saved a total of {len(images)} images")

    # Close the PDF file
    doc.close()
