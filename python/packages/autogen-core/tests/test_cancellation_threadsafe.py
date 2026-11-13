import asyncio

import pytest
from autogen_core import CancellationToken


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_before_link", [False, True])
async def test_worker_cancellation_notifies_future_callbacks(cancel_before_link: bool) -> None:
    loop = asyncio.get_running_loop()
    debug = loop.get_debug()
    loop.set_debug(True)
    try:
        token = CancellationToken()
        future = loop.create_future()
        notified = loop.create_future()
        future.add_done_callback(lambda _: notified.set_result(None))

        if cancel_before_link:
            token.cancel()
            assert await asyncio.to_thread(token.link_future, future) is future
        else:
            assert token.link_future(future) is future
            await asyncio.to_thread(token.cancel)

        await asyncio.wait_for(notified, timeout=1)
        assert future.cancelled()
        assert token.is_cancelled()
    finally:
        loop.set_debug(debug)


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel_before_link", [False, True])
async def test_owning_loop_cancellation_remains_immediate(cancel_before_link: bool) -> None:
    token = CancellationToken()
    future = asyncio.get_running_loop().create_future()

    if cancel_before_link:
        token.cancel()
        token.link_future(future)
    else:
        token.link_future(future)
        token.cancel()

    assert future.cancelled()


@pytest.mark.asyncio
async def test_worker_cancellation_preserves_completed_result() -> None:
    token = CancellationToken()
    future = asyncio.get_running_loop().create_future()
    future.set_result("completed")
    token.link_future(future)

    await asyncio.to_thread(token.cancel)

    assert future.result() == "completed"


def test_cancellation_before_loop_starts_remains_immediate() -> None:
    loop = asyncio.new_event_loop()
    try:
        token = CancellationToken()
        future = loop.create_future()
        token.link_future(future)
        token.cancel()
        assert future.cancelled()
    finally:
        loop.close()
