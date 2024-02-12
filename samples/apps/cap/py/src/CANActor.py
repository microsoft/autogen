from DebugLog import Debug, Info
import zmq
import threading
import traceback
from CANConstants import Termination_Topic, xpub_url

class CANActor():
    def __init__(self, agent_name, description):
        self.agent_name = agent_name
        self.agent_description = description
        self.run = False

    def connect(self, network):
        Debug(self.agent_name, f"is connecting to {network}")
        Debug(self.agent_name, "connected")

    def process_txt_msg(self, msg:str, msg_type:str, topic:str, sender:str) -> bool:
        Info(self.agent_name, f"Msg: {msg}")
        return True

    def process_bin_msg(self, msg:bytes, msg_type:str, topic:str, sender:str) -> bool:
        Info(self.agent_name, f"Msg: topic=[{topic}], msg_type=[{msg_type}]")
        return True

    def recv_thread(self):
        Debug(self.agent_name, "recv thread started")
        try:
            while self.run:
                try:
                    topic, msg_type, sender_topic, msg = self._socket.recv_multipart()
                    topic = topic.decode("utf-8")  # Convert bytes to string
                    msg_type = msg_type.decode("utf-8")  # Convert bytes to string
                    sender_topic = sender_topic.decode("utf-8")  # Convert bytes to string
                except zmq.Again:
                    continue  # No message received, continue to next iteration
                except Exception as e:
                    continue
                if msg_type == "text":
                    msg = msg.decode("utf-8")  # Convert bytes to string
                    if not self.process_txt_msg(msg, msg_type, topic, sender_topic):
                        msg = 'quit'
                    if msg.lower() == 'quit':
                        break
                else:
                    if not self.process_bin_msg(msg, msg_type, topic, sender_topic):
                        break
        except Exception as e:
            Debug(self.agent_name, f"recv thread encountered an error: {e}")
            traceback.print_exc()
        finally:
            self.run = False
            Debug(self.agent_name, "recv thread ended")

    def start_recv_thread(self, context):
        self.run = True
        self._socket = context.socket(zmq.SUB)
        self._socket.setsockopt(zmq.LINGER, 0 )
        self._socket.setsockopt(zmq.RCVTIMEO, 500)
        self._socket.connect(xpub_url)
        str_topic = f"{self.agent_name}"
        Debug(self.agent_name, f"subscribe to: {str_topic}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{str_topic}")
        str_topic = Termination_Topic
        Debug(self.agent_name, f"subscribe to: {str_topic}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{str_topic}")
        self.thread = threading.Thread(target=self.recv_thread)
        self.thread.start()

    def disconnect(self, network):
        Debug(self.agent_name, f"is disconnecting from {network}")
        Debug(self.agent_name, "disconnected")
        self.stop_recv_thread()

    def stop_recv_thread(self):
        self.run = False
        self.thread.join()
        self._socket.close()