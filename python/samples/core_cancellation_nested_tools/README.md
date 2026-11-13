# CancellationToken through nested agents

This sample shows how to forward `CancellationToken` from a parent
`RoutedAgent` to a nested `send_message` call so cancellation stops work in
both layers.

## Run

From the `python/` directory (with `autogen-core` installed):

```bash
python -m samples.core_cancellation_nested_tools.main
```

Expected output:

```
Top-level request cancelled (expected).
Coordinator cancelled: True
Worker started: True, cancelled: True
```

## Key pattern

```python
response = self.send_message(
    message,
    nested_agent_id,
    cancellation_token=ctx.cancellation_token,  # forward the token
)
await response
```

If you omit `cancellation_token`, cancelling the outer request may return
`CancelledError` to the caller while the nested agent continues running.

See also the unit tests in
`packages/autogen-core/tests/test_cancellation.py`.
