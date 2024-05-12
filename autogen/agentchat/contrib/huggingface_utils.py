import os
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union

import torch
from huggingface_hub import ImageToTextOutput, InferenceClient
from PIL.Image import Image

from autogen.agentchat.contrib import img_utils


class HuggingFaceClient:
    VALID_INFERENCE_MODES = ["auto", "local", "remote"]

    def __init__(
        self,
        hf_api_key: Optional[Union[str, bool, None]] = None,
    ):
        self._hf_api_key = hf_api_key
        self._inference_client = InferenceClient(token=hf_api_key)

    def _get_recommended_model(self, task: str):
        return self._inference_client.get_recommended_model(task)

    def _get_model_status(self, model: str):
        return self._inference_client.get_model_status(model)

    def _infer_inference_mode(self, model: str):
        # If model is a URL, return remote
        if model.startswith("http://") or model.startswith("https://"):
            return "remote"

        # If model is a local path, return local
        if os.path.exists(model):
            return "local"

        # Otherwise model is a hf model id
        # Return remote if model is loadable for inference API
        model_status = self._get_model_status(model)
        return "remote" if model_status.state == "Loadable" else "local"

    def _is_cuda_available(self):
        return torch.cuda.is_available()

    def _pre_check(
        self,
        task: str,
        model: Optional[str] = None,
        inference_mode: Literal["auto", "local", "remote"] = "auto",
    ):
        if inference_mode.lower() not in self.VALID_INFERENCE_MODES:
            raise ValueError(f"Invalid inference mode: {inference_mode}. Choose from: {self.VALID_INFERENCE_MODES}")

        if model is None:
            model = self._get_recommended_model(task)

        if inference_mode.lower() == "auto":
            inference_mode = self._infer_inference_mode(model)

        return model, inference_mode

    def text_to_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        inference_mode: Literal["auto", "local", "remote"] = "auto",
        **kwargs,
    ) -> Image:
        model, inference_mode = self._pre_check("text-to-image", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image = self._inference_client.text_to_image(prompt, model=model, **kwargs)

        elif inference_mode.lower() == "local":
            from diffusers import AutoPipelineForText2Image

            pipeline = AutoPipelineForText2Image.from_pretrained(model, token=self._hf_api_key)
            if self._is_cuda_available():
                pipeline = pipeline.to("cuda")

            image = pipeline(prompt, **kwargs).images[0]

        return image

    def image_to_text(
        self,
        image_file: Union[str, Image],
        model: Optional[str] = None,
        inference_mode: Literal["auto", "local", "remote"] = "auto",
        **kwargs,
    ) -> str:
        model, inference_mode = self._pre_check("image-to-text", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image_data = img_utils.get_image_data(image_file, use_b64=False)
            raw_response = self._inference_client.post(data=image_data, model=model, task="image-to-text", **kwargs)
            generated_text = ImageToTextOutput.parse_obj_as_list(raw_response)[0].generated_text

        elif inference_mode.lower() == "local":
            from transformers import pipeline as TransformersPipeline

            device = "cuda" if self._is_cuda_available() else "cpu"
            pipeline = TransformersPipeline("image-to-text", model=model, token=self._hf_api_key, device=device)

            image_data = img_utils.get_pil_image(image_file)
            generated_text = pipeline(image_data, **kwargs)[0]["generated_text"]

        return generated_text

    def image_to_image(
        self,
        image_file: Union[str, Image],
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        inference_mode: Literal["auto", "local", "remote"] = "auto",
        **kwargs,
    ) -> Image:
        model, inference_mode = self._pre_check("image-to-image", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image_data = img_utils.get_image_data(image_file, use_b64=False)
            tgt_image = self._inference_client.image_to_image(image_data, prompt=prompt, model=model, **kwargs)

        elif inference_mode.lower() == "local":
            from diffusers import AutoPipelineForImage2Image

            pipeline = AutoPipelineForImage2Image.from_pretrained(model, token=self._hf_api_key)
            if self._is_cuda_available():
                pipeline = pipeline.to("cuda")

            image_data = img_utils.get_pil_image(image_file)
            tgt_image = pipeline(prompt=prompt, image=image_data, **kwargs).images[0]

        return tgt_image

    def visual_question_answering(
        self,
        image_file: Union[str, Image],
        question: str,
        model: Optional[str] = None,
        inference_mode: Literal["auto", "local", "remote"] = "auto",
        **kwargs,
    ) -> str:
        model, inference_mode = self._pre_check("visual-question-answering", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image_data = img_utils.get_image_data(image_file, use_b64=False)
            answer = self._inference_client.visual_question_answering(image_data, question, model=model, **kwargs)[
                0
            ].answer

        elif inference_mode.lower() == "local":
            from transformers import pipeline as TransformersPipeline

            device = "cuda" if self._is_cuda_available() else "cpu"
            pipeline = TransformersPipeline(
                "visual-question-answering", model=model, token=self._hf_api_key, device=device
            )

            image_data = img_utils.get_pil_image(image_file)
            answer = pipeline(image_data, question, **kwargs)[0]["answer"]

        return answer


# Helper Function
def filter_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
