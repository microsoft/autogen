import threading
from asyncio import Future
from typing import Any, Callable, List


class CancellationToken:
    """A token used to cancel pending async calls.

    Pass the **same** token instance from the caller through every nested
    execution boundary. Typical boundaries are:

    - :meth:`~autogen_core.AgentRuntime.send_message` (and
      :meth:`~autogen_core.BaseAgent.send_message`)
    - :class:`~autogen_core.MessageContext` ``cancellation_token`` on a message
      handler
    - :meth:`~autogen_core.tools.Workbench.call_tool` /
      :meth:`~autogen_core.tools.StreamWorkbench.call_tool_stream`
    - :meth:`~autogen_core.tools.BaseTool.run_json` and nested tool calls
    - in-flight I/O, via :meth:`link_future`

    If ``cancellation_token`` is omitted, :meth:`~autogen_core.AgentRuntime.send_message`
    and :class:`~autogen_core.tools.StaticWorkbench` construct a **new**
    :class:`CancellationToken`. That new token is a separate cancellation
    boundary: cancelling the caller's token can complete the original
    ``send_message`` await (the runtime links the response future) while a
    nested tool, browser, or network call that never received the caller's
    token continues.

    Cancelling a token that was forwarded and linked raises
    :class:`asyncio.CancelledError` at the await site. That error is a
    :class:`BaseException`, so :meth:`~autogen_core.tools.StaticWorkbench.call_tool`
    does not convert it into a :class:`~autogen_core.tools.ToolResult` error.

    :class:`~autogen_core.tools.FunctionTool` forwards the token into the wrapped
    function when the function declares a ``cancellation_token`` parameter
    (the parameter is omitted from the tool schema). Nested awaits inside that
    function should call :meth:`link_future` on this token, not a new one.

    Example:

        .. code-block:: python

            import asyncio

            from autogen_core import CancellationToken
            from autogen_core.tools import FunctionTool, StaticWorkbench


            async def inner_compute(duration: float, cancellation_token: CancellationToken) -> str:
                sleep = asyncio.ensure_future(asyncio.sleep(duration))
                cancellation_token.link_future(sleep)
                await sleep
                return "completed"


            inner_tool = FunctionTool(inner_compute, description="A nested cancellable operation.")


            async def outer_compute(duration: float, cancellation_token: CancellationToken) -> str:
                # Forward the same token. Do not construct a new CancellationToken here.
                return await inner_tool.run_json({"duration": duration}, cancellation_token)


            outer_tool = FunctionTool(outer_compute, description="Forwards the token to inner_compute.")


            async def main() -> None:
                cancellation_token = CancellationToken()
                async with StaticWorkbench(tools=[outer_tool]) as workbench:
                    call = asyncio.create_task(
                        workbench.call_tool(
                            "outer_compute",
                            {"duration": 10},
                            cancellation_token=cancellation_token,
                        )
                    )
                    await asyncio.sleep(0.1)
                    cancellation_token.cancel()
                    try:
                        await call
                    except asyncio.CancelledError:
                        print("nested operation cancelled")


            asyncio.run(main())
    """

    def __init__(self) -> None:
        self._cancelled: bool = False
        self._lock: threading.Lock = threading.Lock()
        self._callbacks: List[Callable[[], None]] = []

    def cancel(self) -> None:
        """Cancel pending async calls linked to this cancellation token."""
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                for callback in self._callbacks:
                    callback()

    def is_cancelled(self) -> bool:
        """Check if the CancellationToken has been used"""
        with self._lock:
            return self._cancelled

    def add_callback(self, callback: Callable[[], None]) -> None:
        """Attach a callback that will be called when cancel is invoked"""
        with self._lock:
            if self._cancelled:
                callback()
            else:
                self._callbacks.append(callback)

    def link_future(self, future: Future[Any]) -> Future[Any]:
        """Link a pending async call to a token to allow its cancellation"""
        with self._lock:
            if self._cancelled:
                future.cancel()
            else:

                def _cancel() -> None:
                    future.cancel()

                self._callbacks.append(_cancel)
        return future
