# Agent_Sender takes a zmq context, Topic and creates a
# socket that can publish to that topic. It exposes this functionality
# using send_msg method
import zmq
import time
import uuid
from .DebugLog import Debug, Error
from .Config import xsub_url, xpub_url

class ActorConnector:
    def __init__(self, context, topic):
        self._pub_socket = context.socket(zmq.PUB)
        self._pub_socket.setsockopt(zmq.LINGER, 0)
        self._pub_socket.connect(xsub_url)

        self._resp_socket = context.socket(zmq.SUB)
        self._resp_socket.setsockopt(zmq.LINGER, 0)
        self._resp_socket.setsockopt(zmq.RCVTIMEO, 100)
        self._resp_socket.connect(xpub_url)
        self._resp_topic = str(uuid.uuid4())
        Debug("AgentConnector", f"subscribe to: {self._resp_topic}")
        self._resp_socket.setsockopt_string(zmq.SUBSCRIBE, f"{self._resp_topic}")
        self._topic = topic
        time.sleep(0.05)  # Let the network do things.

    def send_txt_msg(self, msg):
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), "text".encode("utf8"), self._resp_topic.encode("utf8"), msg.encode("utf8")]
        )

    def send_bin_msg(self, msg_type: str, msg):
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), self._resp_topic.encode("utf8"), msg]
        )

    def binary_request(self, msg_type: str, msg, retry=5):
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), self._resp_topic.encode("utf8"), msg]
        )
        for i in range(retry+1):
            try:
                resp_topic, resp_msg_type, resp_sender_topic, resp = self._resp_socket.recv_multipart()
                return resp_topic, resp_msg_type, resp_sender_topic, resp
            except zmq.Again:
                Debug("AgentConnector", f"binary_request: No response received. retry_count={i}, max_retry={retry}")
                time.sleep(0.05) # Don't go crazy
                continue
        Error("AgentConnector", "binary_request: No response received. Giving up.")
        return None, None, None, None

    def close(self):
        self._pub_socket.close()
        self._resp_socket.close()
