# Agent_Sender takes a zmq context, Topic and creates a
# socket that can publish to that topic. It exposes this functionality
# using send_msg method
import time
import uuid
from typing import Any, Dict

import zmq
from zmq.utils.monitor import recv_monitor_message

from .Config import router_url, xpub_url, xsub_url
from .DebugLog import Debug, Error, Info


class ActorSender:
    def __init__(self, context, topic):
        self._context = context
        self._topic = topic
        self._connect_pub_socket()

    def _connect_pub_socket(self):
        Debug("ActorSender", f"Connecting pub socket {self._topic}")
        self._pub_socket = self._context.socket(zmq.PUB)
        monitor = self._pub_socket.get_monitor_socket()
        self._pub_socket.setsockopt(zmq.LINGER, 0)
        self._pub_socket.connect(xsub_url)
        # Monitor handshake on the pub socket
        while monitor.poll():
            evt: Dict[str, Any] = {}
            mon_evt = recv_monitor_message(monitor)
            evt.update(mon_evt)
            if evt["event"] == zmq.EVENT_HANDSHAKE_SUCCEEDED:
                Debug("ActorSender", "Handshake received")
                break
            elif evt["event"] == zmq.EVENT_MONITOR_STOPPED:
                Debug("ActorSender", "Monitor stopped")
                break
        self._pub_socket.disable_monitor()
        monitor.close()
        self._send_recv_router_msg()

    def _send_recv_router_msg(self):
        # Send a request to the router and wait for a response
        req_socket = self._context.socket(zmq.REQ)
        req_socket.connect(router_url)
        try:
            Debug("ActorSender", "Broker Check Request Sent")
            req_socket.send_string("Request")
            _ = req_socket.recv_string()
            Debug("ActorSender", "Broker Check Response Received")
        finally:
            req_socket.close()

    def send_txt_msg(self, msg):
        Debug("ActorSender", f"[{self._topic}] send_txt_msg: {msg}")
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), "text".encode("utf8"), "no_resp".encode("utf8"), msg.encode("utf8")]
        )

    def send_bin_msg(self, msg_type: str, msg):
        Debug("ActorSender", f"[{self._topic}] send_bin_msg: {msg_type}")
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), "no_resp".encode("utf8"), msg]
        )

    def send_bin_request_msg(self, msg_type: str, msg, resp_topic: str):
        Debug("ActorSender", f"[{self._topic}] send_bin_request_msg: {msg_type}")
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), resp_topic.encode("utf8"), msg]
        )

    def close(self):
        self._pub_socket.close()


class ActorConnector:
    def __init__(self, context, topic):
        self._context = context
        self._topic = topic
        self._connect_sub_socket()
        self._sender = ActorSender(context, topic)
        time.sleep(0.1)  # Wait for the socket to connect

    def _connect_sub_socket(self):
        self._resp_socket = self._context.socket(zmq.SUB)
        monitor = self._resp_socket.get_monitor_socket()
        self._resp_socket.setsockopt(zmq.LINGER, 0)
        self._resp_socket.setsockopt(zmq.RCVTIMEO, 250)
        self._resp_socket.connect(xpub_url)
        self._resp_topic = str(uuid.uuid4())
        Debug("ActorConnector", f"subscribe to: {self._resp_topic}")
        self._resp_socket.setsockopt_string(zmq.SUBSCRIBE, f"{self._resp_topic}")
        while monitor.poll():
            evt: Dict[str, Any] = {}
            mon_evt = recv_monitor_message(monitor)
            evt.update(mon_evt)
            Debug("ActorConnector", evt)
            if evt["event"] == zmq.EVENT_MONITOR_STOPPED or evt["event"] == zmq.EVENT_HANDSHAKE_SUCCEEDED:
                Debug("ActorConnector", "Handshake received (Or Monitor stopped)")
                break
        self._resp_socket.disable_monitor()
        monitor.close()
        self._send_recv_router_msg()

    def _send_recv_router_msg(self):
        # Send a request to the router and wait for a response
        req_socket = self._context.socket(zmq.REQ)
        req_socket.connect(router_url)
        try:
            Debug("ActorConnector", "Broker Check Request Sent")
            req_socket.send_string("Request")
            _ = req_socket.recv_string()
            Debug("ActorConnector", "Broker Check Response Received")
        finally:
            req_socket.close()

    def send_txt_msg(self, msg):
        self._sender.send_txt_msg(msg)

    def send_bin_msg(self, msg_type: str, msg):
        self._sender.send_bin_msg(msg_type, msg)

    def send_proto_msg(self, msg):
        bin_msg = msg.SerializeToString()
        class_type = type(msg)
        self._sender.send_bin_msg(class_type.__name__, bin_msg)

    def send_recv_proto_msg(self, msg, num_attempts=5):
        bin_msg = msg.SerializeToString()
        class_type = type(msg)
        return self.send_recv_msg(class_type.__name, bin_msg, num_attempts)

    def send_recv_msg(self, msg_type: str, msg, num_attempts=5):
        original_timeout: int = 0
        if num_attempts == -1:
            original_timeout = self._resp_socket.getsockopt(zmq.RCVTIMEO)
            self._resp_socket.setsockopt(zmq.RCVTIMEO, 1000)

        try:
            self._sender.send_bin_request_msg(msg_type, msg, self._resp_topic)
            while num_attempts == -1 or num_attempts > 0:
                try:
                    topic, resp_msg_type, _, resp = self._resp_socket.recv_multipart()
                    return topic, resp_msg_type, resp
                except zmq.Again:
                    Debug(
                        "ActorConnector",
                        f"{self._topic}: No response received. retry_count={num_attempts}, max_retry={num_attempts}",
                    )
                    time.sleep(0.01)
                    if num_attempts != -1:
                        num_attempts -= 1
        finally:
            if num_attempts == -1:
                self._resp_socket.setsockopt(zmq.RCVTIMEO, original_timeout)

        Error("ActorConnector", f"{self._topic}: No response received. Giving up.")
        return None, None, None

    def close(self):
        self._sender.close()
        self._resp_socket.close()
