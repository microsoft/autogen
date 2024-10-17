import warnings

from ...tools import LangChainToolAdapter

warnings.warn("LangChainToolAdapter moved to autogen_ext.tools.LangChainToolAdapter", DeprecationWarning, stacklevel=2)

__all__ = ["LangChainToolAdapter"]
