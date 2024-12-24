from dataclasses import dataclass


@dataclass
class JupyterConnectionInfo:
    """TODO"""

    host: str
    """`str` - Host of the Jupyter gateway server"""
    use_https: bool
    """`bool` - Whether to use HTTPS"""
    port: int | None = None
    """`Optional[int]` - Port of the Jupyter gateway server. If None, the default port is used"""
    token: str | None = None
    """`Optional[str]` - Token for authentication. If None, no token is used"""
