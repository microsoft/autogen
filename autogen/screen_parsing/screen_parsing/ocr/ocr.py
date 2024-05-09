import easyocr
import io
import logging
import numpy as np

from PIL import Image

logger = logging.getLogger(__name__)


class OCRParsingError(Exception):
    pass


class OCR:
    def __init__(self, min_confidence: float = 0.25):
        self.min_confidence = min_confidence

    def get_ocr_text(self, image_content: bytes) -> str:
        try:
            image_stream = io.BytesIO(image_content)
            image = Image.open(image_stream)

            # Remove transparency
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")

            reader = easyocr.Reader(["en"])
            output = reader.readtext(np.array(image))

            # The output is a list of tuples, each containing the coordinates of the text and the text itself.
            # We join all the text pieces together to get the final text.
            ocr_text = " "
            for item in output:
                if item[2] >= self.min_confidence:
                    ocr_text += item[1] + " "
            ocr_text = ocr_text.strip()

            if len(ocr_text) > 0:
                return "Text detected by OCR:\n" + ocr_text
            return None

        except Exception as e:
            logger.error(f"OCR failed to detect from image: {e}")

            raise OCRParsingError("Error occurred during OCR parsing") from e
