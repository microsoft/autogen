try:
    from ._torchagentic_planner import TorchAgenticPlannerAgent
except ImportError as e:
    raise ImportError(
        "Dependencies for TorchAgenticPlannerAgent not found. "
        'Please install autogen-ext with the "torchagentic" extra: '
        "pip install autogen-ext[torchagentic]"
    ) from e

__all__ = ["TorchAgenticPlannerAgent"]
