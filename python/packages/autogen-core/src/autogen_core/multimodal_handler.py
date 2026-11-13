"""
AutoGen Multimodal Image Handling Module

This module provides multimodal message support for AutoGen agents,
enabling image analysis with multilingual clinical queries.

Author: Dr. Rajan Prasad Tripathi | AUT AI Innovation Lab
Reference: https://github.com/microsoft/autogen/issues/4708
"""

import base64
import os
from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any
from pathlib import Path
import mimetypes


@dataclass
class Image:
    """
    Represents an image for multimodal messages.

    Supports:
    - File path loading
    - Base64 encoding
    - URL references
    - Language metadata for medical imaging
    """

    data: Optional[str] = None  # Base64-encoded image data
    url: Optional[str] = None   # Image URL
    path: Optional[str] = None  # Local file path
    mime_type: str = "image/png"
    language: str = "en"  # For medical imaging context
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: str, language: str = "en") -> "Image":
        """Load image from file path."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image file not found: {path}")

        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        mime_type, _ = mimetypes.guess_type(path)
        if mime_type is None:
            mime_type = "image/png"

        return cls(
            data=data,
            path=path,
            mime_type=mime_type,
            language=language
        )

    @classmethod
    def from_url(cls, url: str, language: str = "en") -> "Image":
        """Create image reference from URL."""
        return cls(url=url, language=language)

    @classmethod
    def from_base64(cls, data: str, mime_type: str = "image/png", language: str = "en") -> "Image":
        """Create image from base64 data."""
        return cls(data=data, mime_type=mime_type, language=language)

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API format."""
        if self.url:
            return {
                "type": "image_url",
                "image_url": {"url": self.url}
            }
        else:
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{self.mime_type};base64,{self.data}"
                }
            }


@dataclass
class MultiModalMessage:
    """
    A multimodal message containing text and optional images.

    This class enables AutoGen agents to handle:
    - Text-only queries (multilingual)
    - Image-only inputs
    - Mixed text + image content

    Example:
        >>> message = MultiModalMessage(
        ...     content="What abnormalities do you see in this X-ray?",
        ...     images=[Image.from_file("chest_xray.png")],
        ...     language="en"
        ... )
    """

    content: str
    images: List[Image] = field(default_factory=list)
    language: str = "en"
    role: str = "user"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_openai_messages(self) -> List[Dict[str, Any]]:
        """Convert to OpenAI API message format."""
        content_parts = [{"type": "text", "text": self.content}]

        for image in self.images:
            content_parts.append(image.to_openai_format())

        return [{
            "role": self.role,
            "content": content_parts
        }]

    def add_image(self, image: Image) -> "MultiModalMessage":
        """Add an image to the message."""
        self.images.append(image)
        return self

    def detect_language(self) -> str:
        """Auto-detect language from content script."""
        if any('\u4e00' <= c <= '\u9fff' for c in self.content):
            return "zh"
        elif any('\u0600' <= c <= '\u06ff' for c in self.content):
            return "ar"
        elif any('\u0400' <= c <= '\u04ff' for c in self.content):
            return "uz"
        return "en"


# Medical imaging specific extensions
class MedicalImage(Image):
    """
    Medical image with clinical metadata.

    Supports:
    - DICOM metadata extraction
    - Modality classification (X-ray, CT, MRI, Pathology)
    - Anatomical region tagging
    """

    VALID_MODALITIES = ["xray", "ct", "mri", "ultrasound", "pathology", "dermatology"]

    def __init__(
        self,
        data: Optional[str] = None,
        url: Optional[str] = None,
        path: Optional[str] = None,
        mime_type: str = "image/png",
        language: str = "en",
        modality: Optional[str] = None,
        anatomical_region: Optional[str] = None,
        patient_id: Optional[str] = None,  # Should be anonymized
        study_date: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            data=data,
            url=url,
            path=path,
            mime_type=mime_type,
            language=language,
            metadata=kwargs
        )
        self.modality = modality
        self.anatomical_region = anatomical_region
        self.patient_id = patient_id
        self.study_date = study_date

    @classmethod
    def from_dicom(cls, path: str, language: str = "en") -> "MedicalImage":
        """
        Load medical image from DICOM file.

        Note: Requires pydicom for full DICOM support.
        This is a simplified version for demonstration.
        """
        # In production, extract DICOM metadata here
        image = cls.from_file(path, language)
        image.modality = "unknown"  # Would extract from DICOM

        return image

    def to_clinical_context(self) -> str:
        """Generate clinical context string for the image."""
        parts = []

        if self.modality:
            parts.append(f"Modality: {self.modality}")
        if self.anatomical_region:
            parts.append(f"Region: {self.anatomical_region}")
        if self.study_date:
            parts.append(f"Date: {self.study_date}")

        return " | ".join(parts) if parts else "Medical image"


class MultimodalMessageHandler:
    """
    Handler for processing multimodal messages in AutoGen.

    This class provides:
    - Message validation
    - Image preprocessing
    - Language detection and routing
    - Medical imaging specific handling
    """

    def __init__(
        self,
        max_image_size_mb: float = 10.0,
        supported_formats: List[str] = None,
        enable_medical_mode: bool = False
    ):
        self.max_image_size_mb = max_image_size_mb
        self.supported_formats = supported_formats or ["png", "jpg", "jpeg", "gif", "webp", "dicom"]
        self.enable_medical_mode = enable_medical_mode

    def validate_message(self, message: MultiModalMessage) -> bool:
        """Validate a multimodal message."""
        # Check content exists
        if not message.content and not message.images:
            raise ValueError("Message must have content or images")

        # Validate images
        for image in message.images:
            self._validate_image(image)

        return True

    def _validate_image(self, image: Image) -> bool:
        """Validate an image."""
        # Check size if we have data
        if image.data:
            size_bytes = len(base64.b64decode(image.data))
            size_mb = size_bytes / (1024 * 1024)

            if size_mb > self.max_image_size_mb:
                raise ValueError(f"Image size {size_mb:.2f}MB exceeds limit {self.max_image_size_mb}MB")

        # Check format if we have a path
        if image.path:
            ext = os.path.splitext(image.path)[1].lower().lstrip(".")
            if ext not in self.supported_formats and ext != "dcm":
                raise ValueError(f"Unsupported image format: {ext}")

        return True

    def preprocess_for_model(
        self,
        message: MultiModalMessage,
        target_model: str = "gpt-4o"
    ) -> Dict[str, Any]:
        """
        Preprocess multimodal message for specific model.

        Args:
            message: The multimodal message
            target_model: Target model identifier

        Returns:
            Preprocessed message dict ready for API call
        """
        self.validate_message(message)

        # Detect language if not specified
        if message.language == "en" and message.content:
            message.language = message.detect_language()

        # Build message for model
        result = {
            "messages": message.to_openai_messages(),
            "language": message.language,
            "image_count": len(message.images)
        }

        # Add medical context if applicable
        if self.enable_medical_mode:
            medical_contexts = []
            for image in message.images:
                if isinstance(image, MedicalImage):
                    medical_contexts.append(image.to_clinical_context())

            if medical_contexts:
                result["medical_context"] = " | ".join(medical_contexts)

        return result


# Example usage with AutoGen
async def handle_multimodal_query(
    image_path: str,
    query: str,
    language: str = "en",
    modality: str = None
) -> Dict[str, Any]:
    """
    Handle a multimodal query with AutoGen agents.

    Example:
        >>> result = await handle_multimodal_query(
        ...     image_path="chest_xray.png",
        ...     query="What abnormalities do you see?",
        ...     language="en",
        ...     modality="xray"
        ... )
    """
    # Create medical image if modality specified
    if modality:
        image = MedicalImage.from_file(image_path, language=language)
        image.modality = modality
    else:
        image = Image.from_file(image_path, language=language)

    # Create multimodal message
    message = MultiModalMessage(
        content=query,
        images=[image],
        language=language
    )

    # Process with handler
    handler = MultimodalMessageHandler(enable_medical_mode=True)
    processed = handler.preprocess_for_model(message)

    # In production, this would call AutoGen agents:
    # from autogen_agentchat.agents import AssistantAgent
    # from autogen_ext.models.openai import OpenAIChatCompletionClient
    #
    # model_client = OpenAIChatCompletionClient(model="gpt-4o")
    # agent = AssistantAgent(
    #     "medical_imaging_agent",
    #     model_client=model_client,
    #     system_message="You are a medical imaging specialist..."
    # )
    # result = await agent.run(processed["messages"])

    return processed


# Multilingual medical terminology for prompts
MEDICAL_PROMPTS = {
    "en": {
        "analyze": "Analyze this medical image and describe any abnormalities.",
        "disclaimer": "This is for clinical decision support only, not a definitive diagnosis."
    },
    "zh": {
        "analyze": "分析这张医学图像并描述任何异常。",
        "disclaimer": "这仅供临床决策支持参考，不是确诊结果。"
    },
    "ar": {
        "analyze": "حلل هذه الصورة الطبية وصف أي abnormalities.",
        "disclaimer": "هذا لدعم القرارات السريرية فقط، وليس تشخيصًا نهائيًا."
    },
    "uz": {
        "analyze": "Bu tibbiy tasvirni tahlil qiling va har qanday anomaliyalarni tasvirlang.",
        "disclaimer": "Bu faqat klinik qarorlarni qo'llab-quvvatlash uchun, aniq tashhis emas."
    }
}


def get_localized_prompt(language: str = "en", prompt_type: str = "analyze") -> str:
    """Get a localized prompt for medical imaging analysis."""
    return MEDICAL_PROMPTS.get(language, MEDICAL_PROMPTS["en"]).get(prompt_type, "")


# Main execution example
if __name__ == "__main__":
    import asyncio

    async def main():
        # Example: Create a multimodal message for chest X-ray analysis
        image = MedicalImage.from_file("chest_xray.png", language="en")
        image.modality = "xray"
        image.anatomical_region = "chest"

        message = MultiModalMessage(
            content="What abnormalities do you see in this chest X-ray?",
            images=[image],
            language="en"
        )

        handler = MultimodalMessageHandler(enable_medical_mode=True)
        processed = handler.preprocess_for_model(message)

        print(f"Language: {processed['language']}")
        print(f"Image count: {processed['image_count']}")
        print(f"Medical context: {processed.get('medical_context', 'N/A')}")

    asyncio.run(main())
