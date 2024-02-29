import re
from typing import Callable, Dict, List, Literal, Optional, Tuple, Union

from autogen.agentchat import AssistantAgent

from .prompts import PROMPTS_GENERATOR, PROMPTS_RAG
from .utils import logger, timer


def contains_only_one_sentence(text: str) -> bool:
    # Count the number of periods (.), question marks (?), and exclamation marks (!)
    punctuation_count = text.count(".") + text.count("?") + text.count("!")
    return punctuation_count == 1


def extract_refined_questions(input_text: str) -> List[str]:
    """
    Extract refined questions from the input text.

    Args:
        input_text: str | The input text.

    Returns:
        List[str] | The list of refined questions.
    """
    # If the input text contains only one sentence, return the input text
    if contains_only_one_sentence(input_text):
        return [input_text.strip()]
    # Define a regular expression pattern to match sentences starting with a number
    pattern = r"\d+\.\s(.*?)(?:\?|\.\.\.)"
    matches = re.findall(pattern, input_text)
    return [match.strip() for match in matches]


def verify_prompt(prompt: str, contains: List[str]) -> None:
    """
    Verify the prompt.

    Args:
        prompt: str | The prompt.
        contains: List[str] | The list of strings that the prompt must contain.

    Returns:
        None
    """
    if not prompt:
        raise ValueError("Prompt cannot be empty.")
    for c in contains:
        if c not in prompt:
            raise ValueError(f"Prompt must contain {contains}, but it does not contain '{c}'.")


class PromptGenerator:
    """
    Select the best prompt for the given task and refine questions using a language model.
    """

    def __init__(
        self,
        llm_config: Union[Dict, Literal[False]] = False,
        prompt_rag: str = None,
        prompt_refine: str = None,
        prompt_select: str = None,
        post_process_func: Optional[Callable] = None,
    ) -> None:
        """
        Initialize the prompt generator.

        Args:
            llm_config: Union[Dict, Literal[False]] | The configuration for the language model. Default is False.
            prompt_rag: str | The prompt for RAG. Default is None.
            prompt_refine: str | The prompt for refining questions. Default is None.
            prompt_select: str | The prompt for selecting the task. Default is None.
            post_process_func: Optional[Callable] | The post process function. Default is None.

        Returns:
            None
        """
        self.assistant = AssistantAgent(
            name="prompt_generator",
            system_message="You are a helpful AI assistant.",
            llm_config=llm_config,
            max_consecutive_auto_reply=1,
            human_input_mode="NEVER",
        )
        self.llm_config = llm_config
        self.prompt_rag = prompt_rag
        self.prompt_refine = prompt_refine if prompt_refine else PROMPTS_GENERATOR["refine"]
        verify_prompt(prompt_refine, ["{input_question}", "{n}", "{chat_history}"]) if prompt_refine else None
        self.prompt_select = prompt_select if prompt_select else PROMPTS_GENERATOR["select"]
        verify_prompt(prompt_select, ["{input_question}"]) if prompt_select else None
        if isinstance(post_process_func, Callable):
            self.post_process_func = post_process_func
        elif post_process_func is not None:
            raise ValueError("post_process_func must be a Callable.")
        else:
            self.post_process_func = self._post_process
        self.cost = []
        self._print_no_llm_warning = True

    def _call_llm(self, message: str, silent: bool = True) -> str:
        """
        Call the language model.

        Args:
            message: str | The message.
            silent: bool | Whether to suppress the output. Default is True.

        Returns:
            str | The last message.
        """
        self.assistant.reset()
        chat = self.assistant.initiate_chat(self.assistant, message=message, silent=silent)
        self.last_message = self.assistant.last_message().get("content", "")
        self.cost.append(chat.cost)
        return self.last_message

    @timer
    def __call__(self, input_question: str, n: int = 3, chat_history: List[str] = None, silent=True) -> Tuple[str, str]:
        """
        Refine the input question and select the best prompt for the given task.

        Args:
            input_question: str | The input question.
            n: int | The number of refined questions. Default is 3.
            chat_history: List[str] | The chat history. Default is None.
            silent: bool | Whether to suppress the output. Default is True.

        Returns:
            Tuple[str, str] | The refined message and the prompt for the given task.
        """
        self.input_question = input_question
        if self.llm_config is False:
            logger.warning(
                f"LLM config is not set. Will not refine the input question and use the {'given' if self.prompt_rag else 'default'} prompt.",
                color="yellow",
            ) if self._print_no_llm_warning else None
            self._print_no_llm_warning = False
            return [input_question], self.prompt_rag if self.prompt_rag else PROMPTS_RAG["unknown"]
        message = self.prompt_refine.format(input_question=input_question, n=n, chat_history=chat_history or [])
        self.refined_message = self.post_process_func(self._call_llm(message, silent))
        if self.prompt_rag:
            return self.refined_message, self.prompt_rag
        else:
            message = self.prompt_select.format(input_question=input_question)
            self.task = self._ensure_task(self._call_llm(message, silent))
            return self.refined_message, PROMPTS_RAG[self.task]

    def _post_process(self, last_message: str) -> str:
        """
        Post process the last message.

        Args:
            last_message: str | The last message.

        Returns:
            str | The post processed message.
        """
        questions = extract_refined_questions(last_message)
        if not questions:
            logger.warning(
                f"Error in prompt_refine LLM call, get: {last_message}. Using default input.", color="yellow"
            )
            # self.error_message = last_message
            return [self.input_question]
        return questions

    def _ensure_task(self, task: str) -> str:
        """
        Ensure the predicted task is a valid value.

        Args:
            task: str | The predicted task.

        Returns:
            str | The valid task.
        """
        logger.debug(f"Task predicted: {task}", color="green")
        self.error_message = None
        if len(task) > 12 or "TERMINATE" in task.upper():
            self.error_message = task
        for key in PROMPTS_RAG.keys():
            if key in task:
                return key
        logger.warning(
            f"Error in prompt_selelct LLM call, get: {task}. Using default prompt for unknown tasks.", color="yellow"
        )
        return "unknown"

    def get_cost(self) -> Dict[str, float]:
        """
        Get the total cost of the llm calls for refining questions and selecting the task.
        The cost will be {"nominal": total_cost_nominal, "actual": total_cost_actual}.

        Returns:
            Dict[str, float] | The total cost.
        """
        total_cost_nominal = 0
        total_cost_actual = 0
        for cost in self.cost:
            total_cost_nominal += cost[0].get("total_cost", 0)
            total_cost_actual += cost[1].get("total_cost", 0)
        return {"nominal": total_cost_nominal, "actual": total_cost_actual}
