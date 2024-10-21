# ZMQ implementation of the message receiver
from autogencap.DebugLog import Debug, Error
from autogencap.actor_runtime import IMessageReceiver
from autogencap.config import xpub_url
import zmq
import threading

class ZMQMsgReceiver(IMessageReceiver):
    def __init__(self, context: zmq.Context):
        self._socket = None
        self._context = context
        self._start_event = threading.Event()
        self.run = False

    def init(self, actor_name: str):
        """Initialize the ZMQ message receiver."""
        self.actor_name = actor_name
        self._socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.RCVTIMEO, 500)
        self._socket.connect(xpub_url)
        str_topic = f"{self.actor_name}"
        self.add_listener(str_topic)
        self._start_event.set()

    def add_listener(self, topic: str):
        """Add a topic to the message receiver."""
        Debug(self.actor_name, f"subscribe to: {topic}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{topic}")

    def get_message(self):
        """Retrieve a message from the ZMQ socket."""
        try:
            topic, msg_type, sender_topic, msg = self._socket.recv_multipart()
            topic = topic.decode("utf-8")  # Convert bytes to string
            msg_type = msg_type.decode("utf-8")  # Convert bytes to string
            sender_topic = sender_topic.decode("utf-8")  # Convert bytes to string
        except zmq.Again:
            return None  # No message received, continue to next iteration
        except Exception as e:
            Error(self.actor_name, f"recv thread encountered an error: {e}")
            return None
        return topic, msg_type, sender_topic, msg

    def stop(self):
        """Stop the ZMQ message receiver."""
        self.run = False
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.close()