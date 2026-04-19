"""autogen-opa: Open Policy Agent authorization for AutoGen tool calls and agent handoffs."""

from ._exceptions import OPAAuthorizationError, OPAConnectionError
from ._opa_tool import OPAAuthorizedTool, opa_authorize_tools

__all__ = [
    "OPAAuthorizedTool",
    "opa_authorize_tools",
    "OPAAuthorizationError",
    "OPAConnectionError",
]
