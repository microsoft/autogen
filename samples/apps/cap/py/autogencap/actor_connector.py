# Agent_Sender takes a zmq context, Topic and creates a
# socket that can publish to that topic. It exposes this functionality
# using send_msg method
from abc import ABC, abstractmethod



class IActorSender(ABC):
    @abstractmethod
    def send_txt_msg(self, msg):
        pass

    @abstractmethod
    def send_bin_msg(self, msg_type: str, msg):
        pass

    @abstractmethod
    def send_recv_msg(self, msg_type: str, msg, resp_topic: str):
        pass

    @abstractmethod
    def close(self):
        pass


class IActorConnector(ABC):
    @abstractmethod
    def send_txt_msg(self, msg):
        pass

    def send_bin_msg(self, msg_type: str, msg):
        pass

    def send_proto_msg(self, msg):
        pass

    def send_recv_proto_msg(self, msg, num_attempts=5):
        pass

    def send_recv_msg(self, msg_type: str, msg, num_attempts=5):
        pass

    def close(self):
        pass
