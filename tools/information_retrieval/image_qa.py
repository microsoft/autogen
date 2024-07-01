import os

import textract
from PIL import Image

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["textract", "transformers", "torch"], ["textract", "transformers", "torch", "PIL", "os"])
def image_qa(image, question, ckpt="Salesforce/blip-vqa-base"):
    """
    Perform question answering on an image using a pre-trained VQA model.

    Args:
        image (Union[str, Image.Image]): The image to perform question answering on. It can be either file path to the image or a PIL Image object.
        question: The question to ask about the image.

    Returns:
        dict: The generated answer text.
    """
    import torch
    from transformers import BlipForQuestionAnswering, BlipProcessor

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

    def text_processing(file_path):
        # Check the file extension
        if file_path.endswith(".txt"):
            with open(file_path, "r") as file:
                content = file.read()
        elif file_path.endswith(".doc") or file_path.endswith(".docx"):
            # Use textract to extract text from doc and docx files
            content = textract.process(file_path).decode("utf-8")
        else:
            # if the file is not .txt .doc .docx, then it is a string, directly return the string
            return file_path
        return content

    image = image_processing(image)
    question = text_processing(question)

    processor = BlipProcessor.from_pretrained(ckpt)
    model = BlipForQuestionAnswering.from_pretrained(ckpt, torch_dtype=torch.float16).to("cuda")

    raw_image = image

    inputs = processor(raw_image, question, return_tensors="pt").to("cuda", torch.float16)
    out = model.generate(**inputs)
    result_formatted = processor.decode(out[0], skip_special_tokens=True)

    return result_formatted
