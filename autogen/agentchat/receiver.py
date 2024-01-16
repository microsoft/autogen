import functools

import threading
import time
from typing import Dict

from .agent import Agent
from .remote_agent import RemoteAgent


import http.server
import json


class Handler(http.server.BaseHTTPRequestHandler):
    def __init__(self, receiver, *args, **kwargs):
        self._receiver = receiver
        super().__init__(*args, **kwargs)

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        post_obj = json.loads(post_data)

        recipient = post_obj["recipient"]
        if recipient not in self._receiver._agents:
            print("Received message for unknown agent: ", recipient)
            self.send_response(401)
            return

        recipient_agent = self._receiver._agents[recipient]
        # Ignore this for now and hardcode to True below
        # This is usually configured by the initiate conversation code, but this
        # isn't available here.
        # request_reply = post_obj["request_reply"]
        request_reply = True
        sender = post_obj["sender"]
        sender_agent = self._receiver._agents[sender]
        message = post_obj["message"]

        sender_remote_agent = RemoteAgent(sender, host=sender_agent.host, port=sender_agent.port)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.flush()

        def handle():
            time.sleep(1)
            # Request reply is hardcoded to True for now
            # Causes issues with termination
            recipient_agent.receive(message, sender_remote_agent, request_reply)

        # Fire off the task on another thread to not block the server
        thread = threading.Thread(target=handle)
        thread.start()


class Receiver:
    def __init__(self, port):
        self.port = port
        self._agents: Dict[str, Agent] = {}

    def register_agent(self, agent: Agent):
        self._agents[agent.name] = agent

    def start(self):
        self._run = True
        handler = functools.partial(Handler, self)
        self.server = http.server.HTTPServer(("", self.port), handler)
        self.server.timeout = 1000

        # Spawn a thread to run the server
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

    def stop(self):
        self.server.shutdown()
        self.server_thread.join()
