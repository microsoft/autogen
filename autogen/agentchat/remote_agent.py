from collections import defaultdict
from typing import Dict, List, Optional, Union

import requests
from .agent import Agent

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


class RemoteAgent(Agent):
    def __init__(
        self,
        name: str,
        host: str,
        port: int,
    ):
        super().__init__(name)
        self.host = host
        self.port = port
        self.reply_at_receive = defaultdict(bool)

    def send(self, message: Union[Dict, str], recipient: "Agent", request_reply: Optional[bool] = None):
        raise NotImplementedError()

    async def a_send(self, message: Union[Dict, str], recipient: "Agent", request_reply: Optional[bool] = None):
        raise NotImplementedError()

    def receive(
        self,
        message: Union[Dict, str],
        sender: "Agent",
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        print(colored(sender.name, "yellow"), "(to", f"{self.name}):\n", flush=True)
        print(message)
        print("\n", "-" * 80, flush=True, sep="")
        requests.post(
            f"http://{self.host}:{self.port}",
            json={
                "sender": sender.name,
                "recipient": self.name,
                "message": message,
                "request_reply": request_reply,
            },
        )

    async def a_receive(self, message: Union[Dict, str], sender: "Agent", request_reply: Optional[bool] = None):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional["Agent"] = None,
        **kwargs,
    ) -> Union[str, Dict, None]:
        raise NotImplementedError()

    async def a_generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional["Agent"] = None,
        **kwargs,
    ) -> Union[str, Dict, None]:
        raise NotImplementedError()

    def reset_consecutive_auto_reply_counter(self, sender: Optional[Agent] = None):
        raise NotImplementedError()
