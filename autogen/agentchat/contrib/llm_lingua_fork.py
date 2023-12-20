"""
LLM Lingua dependencies complain about forking after being instantiated. So pre-fork LLM Lingua to isolate it from autogen forking

lingua_compressor forks, memoizes, and then utilizes llmlingua.prompt_compressor
lingua_shotdown signals the forked process to shutdown
"""

import logging
import multiprocessing
from typing import Dict, List
from llmlingua.prompt_compressor import PromptCompressor


logger = logging.getLogger(__name__)


llm_lingua = None


def forked_lingua_compressor(messages: List[Dict], tail_messages: List[Dict] = [], config: Dict = {}) -> str:
    global llm_lingua
    if llm_lingua is None:
        llm_lingua = PromptCompressor(
            **{
                key: config[key]
                for key in ["model_name", "model_config", "device_map", "open_api_config"]
                if key in config
            }
        )

    messages = [message.get("content", "") or "" for message in messages]
    question_message = "\n\n".join([(message.get("content", "") or "") for message in tail_messages])

    compressed_message = llm_lingua.compress_prompt(
        context=messages,
        instruction=config.get("system_message"),
        question=question_message,
        ratio=0.25,
        rank_method="longllmlingua",
        concate_question=False,
    ).get("compressed_prompt", None)

    return compressed_message


def process_wrapper(
    pipe,
):
    while True:
        try:
            task = pipe.recv()
            if task is None:  # Termination signal
                break
            args, kwargs = task
            logger.info("calling forked_lingua_compressor from subprocess")
            result = forked_lingua_compressor(*args, **kwargs)
        except Exception as e:
            pipe.send((False, e))
            continue

        pipe.send((True, result))


def start_process():
    parent_pipe, child_pipe = multiprocessing.Pipe()
    process = multiprocessing.Process(target=process_wrapper, args=(child_pipe,))
    process.start()
    return parent_pipe, process


parent_pipe, process = None, None


def lingua_compressor(*args, **kwargs):
    global parent_pipe, process
    if process is None:
        parent_pipe, process = start_process()
    parent_pipe.send((args, kwargs))
    result = parent_pipe.recv()
    if not result[0]:
        raise result[1]
    return result[1]


def lingua_shutdown():
    global parent_pipe, process
    if process is not None:
        parent_pipe.send(None)
        process.join()
