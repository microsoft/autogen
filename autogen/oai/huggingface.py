import os
import random
import time
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

from huggingface_hub import ImageToTextOutput, InferenceClient
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from PIL.Image import Image

from autogen.agentchat.contrib import img_utils


class HuggingFaceClient:
    VALID_INFERENCE_MODES = ["auto", "local", "remote"]
    VALID_TASKS = ["text-to-image", "image-to-text", "image-to-image", "visual-question-answering"]

    def __init__(
        self,
        api_key: Optional[Union[str, bool, None]] = None,
        model: Optional[Union[str, None]] = None,
        inference_mode: Optional[Literal["auto", "local", "remote"]] = "auto",
        **kwargs,
    ):
        self._api_key = api_key
        if not self._api_key:
            self._api_key = os.getenv("HF_TOKEN")

        self._default_model = model
        self._default_inference_mode = inference_mode
        if self._default_inference_mode not in self.VALID_INFERENCE_MODES:
            raise ValueError(
                f"Invalid inference mode: {self._default_inference_mode}. Choose from: {self.VALID_INFERENCE_MODES}"
            )

        self._inference_client = InferenceClient(model=self._default_model, token=self._api_key)

    def create(self, params: Dict[str, Any]) -> ChatCompletion:
        task = params.pop("task", "").lower()
        if task not in self.VALID_TASKS:
            raise ValueError(f"Invalid task: {task}. Choose from: {self.VALID_TASKS}")

        model = params.get("model", None)
        if model is None:
            params["model"] = (
                self._default_model if self._default_model is not None else self._get_recommended_model(task)
            )

        if task == "text-to-image":
            img_res = self.text_to_image(**params)
            res = img_utils.pil_to_data_uri(img_res)

        if task == "image-to-text":
            res = self.image_to_text(**params)

        if task == "image-to-image":
            img_res = self.image_to_image(**params)
            res = img_utils.pil_to_data_uri(img_res)

        if task == "visual-question-answering":
            res = self.visual_question_answering(**params)

        # Create ChatCompletion
        message = ChatCompletionMessage(role="assistant", content=res)
        choices = [Choice(finish_reason="stop", index=0, message=message)]

        response_oai = ChatCompletion(
            id=str(random.randint(0, 1000)),
            choices=choices,
            created=int(time.time() * 1000),
            model=model,
            object="chat.completion",
        )

        return response_oai

    def message_retrieval(self, response) -> List:
        return [choice.message.content for choice in response.choices]

    def cost(self, response) -> float:
        return 0.0

    @staticmethod
    def get_usage(response) -> Dict:
        return {
            "model": response.model,
        }

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
        import torch

        return torch.cuda.is_available()

    def _pre_check(
        self,
        task: str,
        model: Optional[str] = None,
        inference_mode: Optional[Union[Literal["auto", "local", "remote"], None]] = None,
    ):
        if model is None:
            model = self._default_model if self._default_model is not None else self._get_recommended_model(task)

        if inference_mode is None:
            inference_mode = self._default_inference_mode

        if inference_mode.lower() not in self.VALID_INFERENCE_MODES:
            raise ValueError(f"Invalid inference mode: {inference_mode}. Choose from: {self.VALID_INFERENCE_MODES}")

        if inference_mode.lower() == "auto":
            inference_mode = self._infer_inference_mode(model)

        return model, inference_mode

    def text_to_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        inference_mode: Optional[Union[Literal["auto", "local", "remote"], None]] = None,
        **kwargs,
    ) -> Image:
        model, inference_mode = self._pre_check("text-to-image", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image = self._inference_client.text_to_image(prompt, model=model, **kwargs)

        elif inference_mode.lower() == "local":
            from diffusers import AutoPipelineForText2Image

            pipeline = AutoPipelineForText2Image.from_pretrained(model, token=self._api_key)
            if self._is_cuda_available():
                pipeline = pipeline.to("cuda")

            image = pipeline(prompt, **kwargs).images[0]

        return image

    def image_to_text(
        self,
        image_file: Union[str, Image],
        prompt: Optional[str] = None,  # Not used
        model: Optional[str] = None,
        inference_mode: Optional[Union[Literal["auto", "local", "remote"], None]] = None,
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
            pipeline = TransformersPipeline("image-to-text", model=model, token=self._api_key, device=device)

            image_data = img_utils.get_pil_image(image_file)
            generated_text = pipeline(image_data, **kwargs)[0]["generated_text"]

        return generated_text

    def image_to_image(
        self,
        image_file: Union[str, Image],
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        inference_mode: Optional[Union[Literal["auto", "local", "remote"], None]] = None,
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

            pipeline = AutoPipelineForImage2Image.from_pretrained(model, token=self._api_key)
            if self._is_cuda_available():
                pipeline = pipeline.to("cuda")

            image_data = img_utils.get_pil_image(image_file)
            tgt_image = pipeline(prompt=prompt, image=image_data, **kwargs).images[0]

        return tgt_image

    def visual_question_answering(
        self,
        image_file: Union[str, Image],
        prompt: str,
        model: Optional[str] = None,
        inference_mode: Optional[Union[Literal["auto", "local", "remote"], None]] = None,
        **kwargs,
    ) -> str:
        model, inference_mode = self._pre_check("visual-question-answering", model, inference_mode)
        kwargs = filter_kwargs(kwargs)

        # Run inference
        if inference_mode.lower() == "remote":
            image_data = img_utils.get_image_data(image_file, use_b64=False)
            answer = self._inference_client.visual_question_answering(image_data, prompt, model=model, **kwargs)[
                0
            ].answer

        elif inference_mode.lower() == "local":
            from transformers import pipeline as TransformersPipeline

            device = "cuda" if self._is_cuda_available() else "cpu"
            pipeline = TransformersPipeline(
                "visual-question-answering", model=model, token=self._api_key, device=device
            )

            image_data = img_utils.get_pil_image(image_file)
            answer = pipeline(image_data, prompt, **kwargs)[0]["answer"]

        return answer


# Helper Function
def filter_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in kwargs.items() if v is not None}
