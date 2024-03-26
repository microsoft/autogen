# Agent_Sender takes a zmq context, Topic and creates a
# socket that can publish to that topic. It exposes this functionality
# using send_msg method
import zmq
from zmq.utils.monitor import recv_monitor_message
import time
import uuid
from .DebugLog import Debug, Error
from .Config import xsub_url, xpub_url, router_url
from typing import Any, Dict

class ActorConnector:
    def __init__(self, context, topic):
        self._context = context

        self._resp_socket = self._context.socket(zmq.SUB)
        self._resp_socket.setsockopt(zmq.LINGER, 0)
        self._resp_socket.setsockopt(zmq.RCVTIMEO, 250)
        self._resp_socket.connect(xpub_url)
        self._resp_topic = str(uuid.uuid4())
        Debug("AgentConnector", f"subscribe to: {self._resp_topic}")
        self._resp_socket.setsockopt_string(zmq.SUBSCRIBE, f"{self._resp_topic}")
        self._topic = topic

        self._pub_socket = self._context.socket(zmq.PUB)
        self._pub_socket.setsockopt(zmq.LINGER, 0)
        self._pub_socket.connect(xsub_url)
        self._handshake()

    def _send_recv_router_msg(self):
        # Send a request to the router and wait for a response
        req_socket = self._context.socket(zmq.REQ)
        req_socket.connect(router_url)
        try:
            req_socket.send_string("Request")
            _ = req_socket.recv_string()
        finally:
            req_socket.close()

    def _handshake(self):
        # Monitor handshake on the pub socket
        monitor = self._pub_socket.get_monitor_socket()
        while monitor.poll():
            evt: Dict[str, Any] = {}
            mon_evt = recv_monitor_message(monitor)
            evt.update(mon_evt)
            print(evt)
            if evt['event'] == zmq.EVENT_MONITOR_STOPPED or evt['event'] == zmq.EVENT_HANDSHAKE_SUCCEEDED:
                break
        monitor.close()
        self._send_recv_router_msg()

    def send_txt_msg(self, msg):
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), "text".encode("utf8"), self._resp_topic.encode("utf8"), msg.encode("utf8")]
        )

    def send_bin_msg(self, msg_type: str, msg):
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), self._resp_topic.encode("utf8"), msg]
        )

    def binary_request(self, msg_type: str, msg, retry=5):
        time.sleep(0.5)  # Let the network do things.
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), self._resp_topic.encode("utf8"), msg]
        )
        time.sleep(0.5)  # Let the network do things.
        for i in range(retry + 1):
            try:
                self._resp_socket.setsockopt(zmq.RCVTIMEO, 10000)
                resp_topic, resp_msg_type, resp_sender_topic, resp = self._resp_socket.recv_multipart()
                return resp_topic, resp_msg_type, resp_sender_topic, resp
            except zmq.Again:
                Debug("ActorConnector", f"binary_request: No response received. retry_count={i}, max_retry={retry}")
                time.sleep(0.01)  # Wait a bit before retrying
                continue
        Error("ActorConnector", "binary_request: No response received. Giving up.")
        return None, None, None, None

    def close(self):
        self._pub_socket.close()
        self._resp_socket.close()
