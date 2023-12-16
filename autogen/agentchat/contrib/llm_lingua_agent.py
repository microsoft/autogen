"""
Use LLMLingua with CompressibleAgent

https://github.com/microsoft/LLMLingua

@inproceedings{jiang-etal-2023-llmlingua,
    title = "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models",
    author = "Huiqiang Jiang and Qianhui Wu and Chin-Yew Lin and Yuqing Yang and Lili Qiu",
    booktitle = "Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing",
    month = dec,
    year = "2023",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/2310.05736",
}

@article{jiang-etal-2023-longllmlingua,
    title = "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression",
    author = "Huiqiang Jiang and Qianhui Wu and and Xufang Luo and Dongsheng Li and Chin-Yew Lin and Yuqing Yang and Lili Qiu",
    url = "https://arxiv.org/abs/2310.06839",
    journal = "ArXiv preprint",
    volume = "abs/2310.06839",
    year = "2023",
}
"""

from typing import Any, List, Optional, Union
from llmlingua import PromptCompressor
from .compressible_agent import CompressibleAgent


class LLMLinguaAgent(CompressibleAgent):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        llm_config = self.compress_config.get("llm_config", {})

        # use https://github.com/microsoft/LLMLingua
        self.llm_lingua = PromptCompressor(**llm_config)

    def compressor(self, messages: List[str] | str, tail_messages: List[str] | str, config: Any | None = None) -> str:
        tail_messages = tail_messages if isinstance(tail_messages, list) else [tail_messages]
        question_message = "\n\n".join([(message.get("content", "") or "") for message in tail_messages])

        compressed_message = self.llm_lingua.compress_prompt(
            context=messages,
            instruction=self.system_message,
            question=question_message,
            ratio=0.25,
            rank_method="longllmlingua",
            concate_question=False,
        ).get("compressed_prompt", None)

        return compressed_message
