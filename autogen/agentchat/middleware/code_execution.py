import logging
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from ...asyncio_utils import sync_to_async

from ...code_utils import (
    UNKNOWN,
    check_can_use_docker_or_throw,
    decide_use_docker,
    execute_code,
    extract_code,
    infer_lang,
)
from ...tty_utils import colored
from ..agent import Agent

__all__ = ["CodeConfig", "CodeExecutionMiddleware"]

CodeConfig = Union[Dict[str, Any], Literal[False]]

logger = logging.getLogger(__name__)


class CodeExecutionMiddleware:
    """A middleware that executes code blocks in the messages.

    This middleware handles messages with OpenAI-compatible schema.

    Args:
        code_execution_config (dict or False): config for the code execution.
            To disable code execution, set to False. Otherwise, set to a dictionary with the following keys:
            - work_dir (Optional, str): The working directory for the code execution.
                If None, a default working directory will be used.
                The default working directory is the "extensions" directory under
                "path_to_autogen".
            - use_docker (Optional, list, str or bool): The docker image to use for code execution.
                Default is True, which means the code will be executed in a docker container. A default list of images will be used.
                If a list or a str of image name(s) is provided, the code will be executed in a docker container
                with the first image successfully pulled.
                If False, the code will be executed in the current environment.
                We strongly recommend using docker for code execution.
            - timeout (Optional, int): The maximum execution time in seconds.
            - last_n_messages (Experimental, Optional, int or str): The number of messages to look back for code execution. Default to 1. If set to 'auto', it will scan backwards through all messages arriving since the agent last spoke (typically this is the last time execution was attempted).
    """

    def __init__(
        self,
        code_execution_config: Optional[CodeConfig] = None,
    ):
        self._code_execution_config: CodeConfig = {} if code_execution_config is None else code_execution_config
        if isinstance(self._code_execution_config, dict):
            use_docker = self._code_execution_config.get("use_docker", None)
            use_docker = decide_use_docker(use_docker)
            check_can_use_docker_or_throw(use_docker)
            self._code_execution_config["use_docker"] = use_docker

    def call(
        self,
        messages: List[Dict[str, Any]],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
        config: Optional[CodeConfig] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Call the middleware.

        Args:
            messages (List[Dict]): the messages to be processed.
            sender (Optional[Agent]): the sender of the messages.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        final, reply = self._generate_code_execution_reply(messages)
        if final:
            return reply
        else:
            return next(messages, sender)  # type: ignore[no-any-return, misc]

    async def a_call(
        self,
        messages: List[Dict[str, Any]],
        sender: Optional[Agent] = None,
        next: Optional[Callable[..., Any]] = None,
        config: Optional[CodeConfig] = None,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Call the middleware.

        Args:
            messages (List[Dict]): the messages to be processed.
            sender (Optional[Agent]): the sender of the messages.
            next (Optional[Callable[..., Any]]): the next middleware to be called.

        Returns:
            Union[str, Dict, None]: the reply message.
        """
        final, reply = await self._a_generate_code_execution_reply(messages)
        if final:
            return reply
        else:
            return await next(messages, sender)  # type: ignore[no-any-return, misc]

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled.
        """
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    @staticmethod
    def _get_last_n_messages(code_execution_config: Optional[CodeConfig]) -> Union[int, Literal["auto"]]:
        last_n_messages = code_execution_config.pop("last_n_messages", 1)  # type: ignore[union-attr]

        if not (isinstance(last_n_messages, (int, float)) and last_n_messages >= 0) and last_n_messages != "auto":
            raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

        return last_n_messages  # type: ignore[no-any-return]

    @staticmethod
    def _get_messages_to_scan(messages: List[Dict[str, Any]], last_n_messages: Union[int, Literal["auto"]]) -> int:
        messages_to_scan = last_n_messages
        if last_n_messages == "auto":
            # Find when the agent last spoke
            messages_to_scan = 0
            for i in range(len(messages)):  # pragma: no cover
                message = messages[-(i + 1)]
                if "role" not in message:
                    break
                elif message["role"] != "user":
                    break
                else:
                    messages_to_scan += 1

        return messages_to_scan  # type: ignore[return-value]

    @staticmethod
    def _get_code_blocks_from_message(message: Dict[str, Any]) -> Optional[List[Tuple[str, str]]]:
        if "content" not in message:
            return None
        if not message["content"]:
            return None  # pragma: no cover
        code_blocks = extract_code(message["content"])
        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            return None

        return code_blocks

    @staticmethod
    def _get_code_blocks(messages: List[Dict[str, Any]]) -> Optional[List[Tuple[str, str]]]:
        for message in messages:
            code_blocks = CodeExecutionMiddleware._get_code_blocks_from_message(message)
            if code_blocks is not None:
                return code_blocks
        return None

    def _execute_code_block(self, code_block: Tuple[Optional[str], str], i: int, logs_all: str) -> Tuple[int, str]:
        """Execute the code blocks and return the result."""
        lang, code = code_block
        if not lang:
            lang = infer_lang(code)
        print(
            colored(
                f"\n>>>>>>>> EXECUTING CODE BLOCK {i} (inferred language is {lang})...",
                "red",
            ),
            flush=True,
        )
        if lang in ["bash", "shell", "sh"]:
            exitcode, logs, image = execute_code(code, lang=lang, **self._code_execution_config)  # type: ignore[arg-type]
        elif lang in ["python", "Python"]:
            if code.startswith("# filename: "):
                filename = code[11 : code.find("\n")].strip()
            else:
                filename = None
            exitcode, logs, image = execute_code(  # type: ignore[arg-type]
                code,
                lang="python",
                filename=filename,
                **self._code_execution_config,
            )
        else:
            # In case the language is not supported, we return an error message.
            exitcode, logs, image = (
                1,
                f"unknown language {lang}",
                None,
            )
        if image is not None:
            self._code_execution_config["use_docker"] = image  # type: ignore[index]  # pragma: no cover
        logs_all += "\n" + logs

        return exitcode, logs_all

    def _execute_code_blocks(self, code_blocks: List[Tuple[str, str]]) -> Tuple[int, str]:
        """Execute the code blocks and return the result."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
            exitcode, logs_all = self._execute_code_block(code_block, i, logs_all)
            if exitcode != 0:
                break  # pragma: no cover

        return exitcode, logs_all

    def _generate_code_execution_reply(
        self, messages: List[Dict[str, Any]], config: Optional[CodeConfig] = None
    ) -> Tuple[bool, Optional[str]]:
        code_execution_config = self._code_execution_config if config is None else config

        if code_execution_config is not False:
            last_n_messages = self._get_last_n_messages(code_execution_config)

            no_messages_to_scan = self._get_messages_to_scan(messages, last_n_messages)

            messages_to_scan = messages[-no_messages_to_scan:][::-1]
            code_blocks = self._get_code_blocks(messages_to_scan)
            if code_blocks is not None:
                # found code blocks, execute code and push "last_n_messages" back
                exitcode, logs = self._execute_code_blocks(code_blocks)

                code_execution_config["last_n_messages"] = last_n_messages
                exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
                return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

            # no code blocks are found, push last_n_messages back and return.
            code_execution_config["last_n_messages"] = last_n_messages

        return False, None

    async def _a_generate_code_execution_reply(
        self, messages: List[Dict[str, Any]], config: Optional[CodeConfig] = None
    ) -> Tuple[bool, Optional[str]]:
        code_execution_config = self._code_execution_config if config is None else config

        if code_execution_config is not False:
            last_n_messages = self._get_last_n_messages(code_execution_config)

            no_messages_to_scan = self._get_messages_to_scan(messages, last_n_messages)

            messages_to_scan = messages[-no_messages_to_scan:][::-1]
            code_blocks = self._get_code_blocks(messages_to_scan)
            if code_blocks is not None:
                # found code blocks, execute code and push "last_n_messages" back
                exitcode, logs = await sync_to_async()(self._execute_code_blocks)(code_blocks)  # type: ignore[misc]
                code_execution_config["last_n_messages"] = last_n_messages
                exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
                return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

            # no code blocks are found, push last_n_messages back and return.
            code_execution_config["last_n_messages"] = last_n_messages

        return False, None
