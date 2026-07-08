"""Minimal helper wrapping the Pilot Protocol Python SDK for this sample.

Not a general-purpose AutoGen runtime transport -- just enough plumbing to
move serialized message bytes between two Pilot Protocol virtual addresses
for the responder/requester scripts in this sample.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from pilotprotocol import Driver

PORT = 5000


@dataclass
class Greeting:
    sender: str
    text: str

    def encode(self) -> bytes:
        return json.dumps(asdict(self)).encode("utf-8")

    @staticmethod
    def decode(payload: bytes) -> "Greeting":
        data = json.loads(payload.decode("utf-8"))
        return Greeting(**data)


def serve_once(port: int = PORT):
    """Block until one Greeting arrives. Returns (greeting, conn) -- the
    caller is responsible for writing a reply on conn and then closing it."""
    with Driver() as d:
        with d.listen(port) as listener:
            conn = listener.accept()
            try:
                payload = conn.read(65536)
                return Greeting.decode(payload), conn
            except Exception:
                conn.close()
                raise


def send_and_wait(peer_hostname: str, greeting: Greeting, port: int = PORT) -> Greeting:
    with Driver() as d:
        with d.dial(f"{peer_hostname}:{port}") as conn:
            conn.write(greeting.encode())
            reply = conn.read(65536)
            return Greeting.decode(reply)
