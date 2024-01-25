from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

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
        code_execution_config: Optional[Union[Dict[str, Any], Literal[False]]] = None,
    ):
        self._code_execution_config: Union[Dict[str, Any], Literal[False]] = (
            {} if code_execution_config is None else code_execution_config
        )
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
        return reply if final else next(messages, sender)  # type: ignore[no-any-return, misc]

    @property
    def use_docker(self) -> Union[bool, str, None]:
        """Bool value of whether to use docker to execute the code,
        or str value of the docker image name to use, or None when code execution is disabled.
        """
        return None if self._code_execution_config is False else self._code_execution_config.get("use_docker")

    def _generate_code_execution_reply(
        self, messages: List[Dict[str, Any]], config: Optional[Union[Dict[str, Any], Literal[False]]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Generate a reply using code execution."""

        code_execution_config = config if config is not None else self._code_execution_config
        if code_execution_config is False:
            return False, None
        last_n_messages = code_execution_config.pop("last_n_messages", 1)

        if not (isinstance(last_n_messages, (int, float)) and last_n_messages >= 0) and last_n_messages != "auto":
            raise ValueError("last_n_messages must be either a non-negative integer, or the string 'auto'.")

        messages_to_scan = last_n_messages
        if last_n_messages == "auto":
            # Find when the agent last spoke
            messages_to_scan = 0
            for i in range(len(messages)):
                message = messages[-(i + 1)]
                if "role" not in message:
                    break
                elif message["role"] != "user":
                    break
                else:
                    messages_to_scan += 1

        # iterate through the last n messages in reverse
        # if code blocks are found, execute the code blocks and return the output
        # if no code blocks are found, continue
        for i in range(min(len(messages), messages_to_scan)):
            message = messages[-(i + 1)]
            if "content" not in message:
                continue
            if not message["content"]:
                continue
            code_blocks = extract_code(message["content"])
            if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
                continue

            # found code blocks, execute code and push "last_n_messages" back
            exitcode, logs = self._execute_code_blocks(code_blocks)
            code_execution_config["last_n_messages"] = last_n_messages
            exitcode2str = "execution succeeded" if exitcode == 0 else "execution failed"
            return True, f"exitcode: {exitcode} ({exitcode2str})\nCode output: {logs}"

        # no code blocks are found, push last_n_messages back and return.
        code_execution_config["last_n_messages"] = last_n_messages

        return False, None

    def _execute_code_blocks(self, code_blocks: List[Tuple[str, str]]) -> Tuple[int, str]:
        """Execute the code blocks and return the result."""
        logs_all = ""
        for i, code_block in enumerate(code_blocks):
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
                exitcode, logs, image = self._run_code(code, lang=lang, **self._code_execution_config)  # type: ignore[arg-type]
            elif lang in ["python", "Python"]:
                if code.startswith("# filename: "):
                    filename = code[11 : code.find("\n")].strip()
                else:
                    filename = None
                exitcode, logs, image = self._run_code(  # type: ignore[arg-type]
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
                # raise NotImplementedError
            if image is not None:
                self._code_execution_config["use_docker"] = image  # type: ignore[index]
            logs_all += "\n" + logs
            if exitcode != 0:
                return exitcode, logs_all
        return exitcode, logs_all

    def _run_code(self, code: Optional[str], **kwargs: Any) -> Tuple[int, str, Optional[str]]:
        """Run the code and return the result.

        Override this function to modify the way to run the code.
        Args:
            code (str): the code to be executed.
            **kwargs: other keyword arguments.

        Returns:
            A tuple of (exitcode, logs, image).
            exitcode (int): the exit code of the code execution.
            logs (str): the logs of the code execution.
            image (str or None): the docker image used for the code execution.
        """
        return execute_code(code, **kwargs)
