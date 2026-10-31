"""Exceptions for autogen OPA authorization."""


class OPAAuthorizationError(PermissionError):
    """Raised when OPA denies a tool call.

    Attributes:
        tool_name: The name of the tool that was denied.
        policy_reason: Optional human-readable reason returned by the OPA policy.
    """

    def __init__(
        self,
        tool_name: str,
        reason: str = "OPA policy denied the request",
        policy_reason: str | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.policy_reason = policy_reason
        message = f"Tool '{tool_name}' denied by OPA policy: {reason}"
        if policy_reason:
            message += f" (policy reason: {policy_reason})"
        super().__init__(message)


class OPAConnectionError(RuntimeError):
    """Raised when the OPA server cannot be reached and fail_open=False.

    Attributes:
        opa_url: The OPA server URL that could not be reached.
        cause: The underlying exception, if any.
    """

    def __init__(self, opa_url: str, cause: Exception | None = None) -> None:
        self.opa_url = opa_url
        self.cause = cause
        message = f"Cannot connect to OPA server at {opa_url}"
        if cause:
            message += f": {cause}"
        super().__init__(message)
