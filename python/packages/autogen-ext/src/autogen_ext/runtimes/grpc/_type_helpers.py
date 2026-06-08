from typing import Any, Sequence, Tuple

# Had to redefine this from grpc.aio._typing as using that one was causing mypy errors
ChannelArgumentType = Sequence[Tuple[str, Any]]
