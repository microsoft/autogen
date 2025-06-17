from __future__ import annotations

import importlib
from typing import Any, Callable, Dict, Iterable, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    try:
        import dspy
    except ImportError:
        dspy = None

from autogen_agentchat.optimize._backend import BaseBackend
from ._utils import AutoGenLM, DSPyAgentWrapper


def _check_dspy_available() -> None:
    """Check if DSPy is available and raise helpful error if not."""
    try:
        import dspy  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "DSPy is required for optimization but not installed. "
            "Please install it with: pip install dspy"
        ) from e


class DSPyBackend(BaseBackend):
    """Optimise AutoGen agents with any DSPy optimiser."""
    
    name = "dspy"

    def compile(
        self,
        agent: Any,
        trainset: Iterable[Any],
        metric: Callable[[Any, Any], float | bool],
        *,
        lm_client: Any | None = None,
        optimizer_name: str = "SIMBA",
        optimizer_kwargs: Dict[str, Any] | None = None,
        **extra: Any,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Compile/optimize an AutoGen agent using DSPy.

        Parameters
        ----------
        agent
            AutoGen agent to optimize
        trainset
            Training examples for optimization
        metric
            Evaluation metric function
        lm_client
            Language model client (if None, uses agent.model_client)
        optimizer_name
            Name of DSPy optimizer to use
        optimizer_kwargs
            Additional arguments for the optimizer
        extra
            Additional keyword arguments (ignored)

        Returns
        -------
        Tuple of (optimized_agent, report)
        """
        _check_dspy_available()
        import dspy

        if not optimizer_kwargs:
            optimizer_kwargs = {}

        # 1. Configure DSPy with the supplied AutoGen LM (or grab from agent)
        lm_client = lm_client or getattr(agent, "model_client", None) or getattr(agent, "_model_client", None)
        if lm_client is None:
            raise ValueError("Could not find model_client in agent and none provided")
            
        dspy_lm = AutoGenLM(lm_client)
        dspy.configure(lm=dspy_lm)

        # 2. Wrap agent
        wrapper = DSPyAgentWrapper(agent)

        # 3. Create optimiser instance
        try:
            opt_mod = importlib.import_module("dspy.optimizers")
            OptimCls = getattr(opt_mod, optimizer_name)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not find optimizer '{optimizer_name}' in dspy.optimizers") from e
            
        optimiser = OptimCls(metric=metric, **optimizer_kwargs)

        # 4. Compile
        compiled = optimiser.compile(wrapper, trainset=trainset)

        # 5. Write back tuned texts into the *original* live agent
        if hasattr(agent, "system_message"):
            agent.system_message = compiled.learnable_system_prompt.value
        elif hasattr(agent, "_system_messages") and agent._system_messages:
            from autogen_core.models import SystemMessage
            agent._system_messages[0] = SystemMessage(content=compiled.learnable_system_prompt.value)
        
        # Update tool descriptions
        tools = getattr(agent, "_tools", []) or getattr(agent, "tools", [])
        for new_desc, tool in zip(compiled.learnable_tool_prompts, tools):
            if hasattr(tool, "description"):
                tool.description = new_desc.value

        # Prepare report
        best_metric = getattr(optimiser, "best_metric", None)
        
        # Get current system message for report
        current_system_message = None
        if hasattr(agent, "system_message"):
            current_system_message = agent.system_message
        elif hasattr(agent, "_system_messages") and agent._system_messages:
            current_system_message = agent._system_messages[0].content

        report = {
            "optimizer": optimizer_name,
            "best_metric": best_metric,
            "tuned_system_prompt": current_system_message,
            "tuned_tool_descriptions": [
                getattr(t, "description", "") for t in tools
            ],
        }
        
        return agent, report