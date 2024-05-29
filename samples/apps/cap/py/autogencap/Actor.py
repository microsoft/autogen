import threading
import traceback

import zmq

from .Config import xpub_url
from .DebugLog import Debug, Error, Info


class Actor:
    def __init__(self, agent_name: str, description: str, start_thread: bool = True):
        self.actor_name: str = agent_name
        self.agent_description: str = description
        self.run = False
        self._start_event = threading.Event()
        self._start_thread = start_thread

    def on_connect(self, network):
        Debug(self.actor_name, f"is connecting to {network}")
        Debug(self.actor_name, "connected")

    def on_txt_msg(self, msg: str, msg_type: str, receiver: str, sender: str) -> bool:
        Info(self.actor_name, f"InBox: {msg}")
        return True

    def on_bin_msg(self, msg: bytes, msg_type: str, receiver: str, sender: str) -> bool:
        Info(self.actor_name, f"Msg: receiver=[{receiver}], msg_type=[{msg_type}]")
        return True

    def _msg_loop_init(self):
        Debug(self.actor_name, "recv thread started")
        self._socket: zmq.Socket = self._context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.RCVTIMEO, 500)
        self._socket.connect(xpub_url)
        str_topic = f"{self.actor_name}"
        Debug(self.actor_name, f"subscribe to: {str_topic}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{str_topic}")
        self._start_event.set()

    def get_message(self):
        try:
            topic, msg_type, sender_topic, msg = self._socket.recv_multipart()
            topic = topic.decode("utf-8")  # Convert bytes to string
            msg_type = msg_type.decode("utf-8")  # Convert bytes to string
            sender_topic = sender_topic.decode("utf-8")  # Convert bytes to string
        except zmq.Again:
            return None  # No message received, continue to next iteration
        except Exception as e:
            Error(self.actor_name, f"recv thread encountered an error: {e}")
            traceback.print_exc()
            return None
        return topic, msg_type, sender_topic, msg

    def dispatch_message(self, message):
        if message is None:
            return
        topic, msg_type, sender_topic, msg = message
        if msg_type == "text":
            msg = msg.decode("utf-8")  # Convert bytes to string
            if not self.on_txt_msg(msg, msg_type, topic, sender_topic):
                msg = "quit"
            if msg.lower() == "quit":
                self.run = False
        else:
            if not self.on_bin_msg(msg, msg_type, topic, sender_topic):
                self.run = False

    def _msg_loop(self):
        try:
            self._msg_loop_init()
            while self.run:
                message = self.get_message()
                self.dispatch_message(message)
        except Exception as e:
            Debug(self.actor_name, f"recv thread encountered an error: {e}")
            traceback.print_exc()
        finally:
            self.run = False
            # In case there was an exception at startup signal
            # the main thread.
            self._start_event.set()
            Debug(self.actor_name, "recv thread ended")

    def on_start(self, context: zmq.Context):
        self._context = context
        self.run: bool = True
        if self._start_thread:
            self._thread = threading.Thread(target=self._msg_loop)
            self._thread.start()
            self._start_event.wait()
        else:
            self._msg_loop_init()

    def disconnect_network(self, network):
        Debug(self.actor_name, f"is disconnecting from {network}")
        Debug(self.actor_name, "disconnected")
        self.stop()

    def stop(self):
        self.run = False
        if self._start_thread:
            self._thread.join()
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.close()
