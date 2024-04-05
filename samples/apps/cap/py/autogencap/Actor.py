import threading
import time
import traceback

import zmq

from .Config import xpub_url
from .DebugLog import Debug, Error, Info


class Actor:
    def __init__(self, agent_name: str, description: str):
        self.actor_name: str = agent_name
        self.agent_description: str = description
        self.run = False
        self._start_event = threading.Event()

    def connect_network(self, network):
        Debug(self.actor_name, f"is connecting to {network}")
        Debug(self.actor_name, "connected")

    def _process_txt_msg(self, msg: str, msg_type: str, topic: str, sender: str) -> bool:
        Info(self.actor_name, f"InBox: {msg}")
        return True

    def _process_bin_msg(self, msg: bytes, msg_type: str, topic: str, sender: str) -> bool:
        Info(self.actor_name, f"Msg: topic=[{topic}], msg_type=[{msg_type}]")
        return True

    def _recv_thread(self):
        try:
            Debug(self.actor_name, "recv thread started")
            self._socket: zmq.Socket = self._context.socket(zmq.SUB)
            self._socket.setsockopt(zmq.RCVTIMEO, 500)
            self._socket.connect(xpub_url)
            str_topic = f"{self.actor_name}"
            Debug(self.actor_name, f"subscribe to: {str_topic}")
            self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{str_topic}")
            self._start_event.set()
            while self.run:
                try:
                    topic, msg_type, sender_topic, msg = self._socket.recv_multipart()
                    topic = topic.decode("utf-8")  # Convert bytes to string
                    msg_type = msg_type.decode("utf-8")  # Convert bytes to string
                    sender_topic = sender_topic.decode("utf-8")  # Convert bytes to string
                except zmq.Again:
                    continue  # No message received, continue to next iteration
                except Exception as e:
                    Error(self.actor_name, f"recv thread encountered an error: {e}")
                    traceback.print_exc()
                    continue
                if msg_type == "text":
                    msg = msg.decode("utf-8")  # Convert bytes to string
                    if not self._process_txt_msg(msg, msg_type, topic, sender_topic):
                        msg = "quit"
                    if msg.lower() == "quit":
                        break
                else:
                    if not self._process_bin_msg(msg, msg_type, topic, sender_topic):
                        break
        except Exception as e:
            Debug(self.actor_name, f"recv thread encountered an error: {e}")
            traceback.print_exc()
        finally:
            self.run = False
            # In case there was an exception at startup signal
            # the main thread.
            self._start_event.set()
            Debug(self.actor_name, "recv thread ended")

    def start(self, context: zmq.Context):
        self._context = context
        self.run: bool = True
        self._thread = threading.Thread(target=self._recv_thread)
        self._thread.start()
        self._start_event.wait()

    def disconnect_network(self, network):
        Debug(self.actor_name, f"is disconnecting from {network}")
        Debug(self.actor_name, "disconnected")
        self.stop()

    def stop(self):
        self.run = False
        self._thread.join()
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.close()
