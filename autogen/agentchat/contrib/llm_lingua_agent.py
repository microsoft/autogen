"""
Use LLMLingua with CompressibleAgent

https://github.com/microsoft/LLMLingua

```shell
pip install pyautogen[llmlingua]
```

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

from ast import Dict
import atexit
import functools
import multiprocessing
from typing import Any, List, Optional, Union
from llmlingua import PromptCompressor
from .compressible_agent import CompressibleAgent
from .llm_lingua_fork import lingua_compressor, lingua_shutdown


class LLMLinguaAgent(CompressibleAgent):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        atexit.register(self.close)

        # use https://github.com/microsoft/LLMLingua
        self.llm_lingua = None

    def compressor(self, messages: List[Dict], tail_messages: List[Dict] = [], config: Dict = None) -> str:
        return lingua_compressor(
            messages,
            tail_messages,
            dict(
                {"system_message": self.system_message},
                **(self.compress_config.get("llm_config", {})),
                **(config or {}),
            ),
        )

    def close(self):
        lingua_shutdown()

    def __del__(self):
        self.close()  # Ensure cleanup when object is destroyed
