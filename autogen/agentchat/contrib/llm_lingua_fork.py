"""
LLM Lingua dependencies complain about forking after being instantiated. So pre-fork LLM Lingua to isolate it from autogen forking

lingua_compressor forks, memoizes, and then utilizes llmlingua.prompt_compressor
lingua_shotdown signals the forked process to shutdown
"""

import multiprocessing
from typing import Dict, List
from llmlingua.prompt_compressor import PromptCompressor


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


def process_wrapper(task_queue, result_queue):
    while True:
        task = task_queue.get()
        if task is None:  # Termination signal
            break
        args, kwargs = task
        print("calling forked_lingua_compressor from subprocess")
        result = forked_lingua_compressor(*args, **kwargs)
        result_queue.put(result)


def start_process():
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    process = multiprocessing.Process(target=process_wrapper, args=(task_queue, result_queue))
    process.start()
    return task_queue, result_queue, process


task_queue, result_queue, process = None, None, None


def lingua_compressor(*args, **kwargs):
    global task_queue, result_queue, process
    if process is None:
        task_queue, result_queue, process = start_process()
    task_queue.put((args, kwargs))
    result = result_queue.get()
    return result


def lingua_shutdown():
    global task_queue, process
    if process is not None:
        task_queue.put(None)
        process.join()
