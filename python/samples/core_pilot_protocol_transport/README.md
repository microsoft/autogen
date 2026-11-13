# Pilot Protocol transport for distributed AutoGen agents

This sample shows how to use [Pilot Protocol](https://pilotprotocol.network/docs) as the transport between two AutoGen Core agents running as separate processes, instead of the built-in gRPC worker runtime.

Pilot Protocol gives each process a permanent virtual address and an encrypted, NAT-traversing tunnel to its peer, with an explicit mutual-trust handshake before any messages flow. That's useful when your agents live on different hosts or clouds and you don't want to stand up your own gRPC host/relay.

This is not a replacement for `GrpcWorkerAgentRuntime` in general — it's an option when your distributed agents need to reach each other across networks you don't control (behind NAT, on different clouds) without deploying a shared server.

## What this demonstrates

Two independent Python processes, each running a single AutoGen `SingleThreadedAgentRuntime`:

- `run_responder.py` starts an agent that listens for a `Greeting` message and replies.
- `run_requester.py` starts an agent that sends a `Greeting` to the responder and prints the reply.

Instead of both connecting to a shared gRPC host, they exchange the message bytes over a Pilot Protocol connection between their two daemon-backed virtual addresses.

## Setup

### 1. Install Pilot Protocol and AutoGen

```bash
curl -fsSL https://pilotprotocol.network/install.sh | sh
pip install pilotprotocol "autogen-core"
```

### 2. Start a daemon on each machine (or two terminals on one machine for testing)

```bash
# machine / terminal A
pilotctl daemon start --hostname autogen-responder

# machine / terminal B
pilotctl daemon start --hostname autogen-requester
```

### 3. Establish trust between the two agents

Messaging is dropped silently until both sides have mutual trust (see [Trust & Handshakes](https://pilotprotocol.network/docs/trust)):

```bash
# on the requester machine
pilotctl handshake autogen-responder "autogen sample"

# on the responder machine
pilotctl pending
pilotctl approve <requester_node_id>
```

## Running the example

Terminal A (responder):

```bash
python run_responder.py
```

Terminal B (requester):

```bash
python run_requester.py
```

The requester's runtime publishes a `Greeting`, the responder's runtime receives it via `dial`/`listen` over Pilot Protocol, and its reply comes back over the same connection.

## How the transport works

Each script wraps AutoGen's runtime with a small transport class (`pilot_transport.py`) using the [Python SDK's](https://pilotprotocol.network/docs/python-sdk) `Driver`:

```python
from pilotprotocol import Driver

with Driver() as d:
    with d.listen(5000) as listener:
        conn = listener.accept()
        payload = conn.read(65536)
        # hand payload to the AutoGen runtime as an incoming message
```

and on the sending side:

```python
with Driver() as d:
    with d.dial("autogen-responder:5000") as conn:
        conn.write(serialized_message)
        reply = conn.read(65536)
```

Message payloads are the same serialized AutoGen message types you'd send over gRPC — Pilot Protocol only carries the bytes between the two virtual addresses.

## Notes

- This sample uses Pilot Protocol's stream connections (`dial`/`listen`), not the async data-exchange or pub/sub services — see [Messaging](https://pilotprotocol.network/docs/messaging) for the other delivery models if you need fire-and-forget or persistent inbox delivery instead.
- Trust is per-peer and separate from network membership; if you're coordinating more than two agents, look at [Networks](https://pilotprotocol.network/docs/networks) for group-level connectivity instead of pairwise handshakes.
