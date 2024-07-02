import os

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["easyocr"], ["os"])
def optical_character_recognition(image):
    """
    Perform optical character recognition (OCR) on the given image.

    Args:
        image (Union[str, Image.Image]): The image to perform OCR on. It can be either a file path or an Image object.

    Returns:
        str: The extracted text from the image.

    Raises:
        FileNotFoundError: If the image file path does not exist.
    """
    import io

    import easyocr
    from PIL import Image

    def image_processing(img):
        if isinstance(img, Image.Image):
            return img.convert("RGB")
        elif isinstance(img, str):
            if os.path.exists(img):
                return Image.open(img).convert("RGB")
            else:
                full_path = img
                if os.path.exists(full_path):
                    return Image.open(full_path).convert("RGB")
                else:
                    raise FileNotFoundError

    reader = easyocr.Reader(["en"])  # Load the OCR model into memory

    if isinstance(image, str):
        # If image is a path, use it directly
        if not os.path.exists(image):
            raise FileNotFoundError
        image_path_or_bytes = image
    else:
        # If image is an Image object, convert it to a bytes stream
        buffer = io.BytesIO()
        image = image_processing(image)  # Process the image if needed
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        image_path_or_bytes = buffer

    # Read text from the image or image path
    result = reader.readtext(image_path_or_bytes)

    # Extract only the text from the result
    result_text = [text for _, text, _ in result]

    return ", ".join(result_text)
