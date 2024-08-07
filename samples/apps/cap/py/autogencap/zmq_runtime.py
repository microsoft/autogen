import time
import uuid
from typing import Any, Dict, List

import zmq
from zmq.utils.monitor import recv_monitor_message

from autogencap.actor_connector import IActorSender
from autogencap.config import router_url, xpub_url, xsub_url
from autogencap.debug_log import Debug, Error, Warn

from .actor import Actor
from .actor_connector import IActorConnector
from .actor_runtime import IRuntime
from .broker import Broker
from .constants import Termination_Topic
from .proto.CAP_pb2 import ActorInfo, ActorInfoCollection
from .zmq_directory_svc import ZMQDirectorySvc


class ZMQActorSender(IActorSender):
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

    def send_recv_msg(self, msg_type: str, msg, resp_topic: str):
        Debug("ActorSender", f"[{self._topic}] send_bin_request_msg: {msg_type}")
        self._pub_socket.send_multipart(
            [self._topic.encode("utf8"), msg_type.encode("utf8"), resp_topic.encode("utf8"), msg]
        )

    def close(self):
        self._pub_socket.close()


class ZMQActorConnector(IActorConnector):
    def __init__(self, context, topic):
        self._context = context
        self._topic = topic
        self._connect_sub_socket()
        self._sender = ZMQActorSender(context, topic)
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
            self._sender.send_recv_msg(msg_type, msg, self._resp_topic)
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


class ZMQRuntime(IRuntime):
    def __init__(self, name: str = "Local Actor Network", start_broker: bool = True):
        self.local_actors = {}
        self.name: str = name
        self._context: zmq.Context = zmq.Context()
        self._start_broker: bool = start_broker
        self._broker: Broker = None
        self._directory_svc: ZMQDirectorySvc = None

    def __str__(self):
        return f"{self.name}"

    def _init_runtime(self):
        if self._start_broker and self._broker is None:
            self._broker = Broker(self._context)
            if not self._broker.start():
                self._start_broker = False  # Don't try to start the broker again
                self._broker = None
        if self._directory_svc is None:
            self._directory_svc = ZMQDirectorySvc(self._context)
            self._directory_svc.start()
        time.sleep(0.25)  # Process queued thread events in Broker and Directory

    def register(self, actor: Actor):
        self._init_runtime()
        # Get actor's name and description and add to a dictionary so
        # that we can look up the actor by name
        self._directory_svc.register_actor_by_name(actor.actor_name)
        self.local_actors[actor.actor_name] = actor
        actor.on_start(self._context)
        Debug("Local_Actor_Network", f"{actor.actor_name} registered in the network.")

    def connect(self):
        self._init_runtime()
        for actor in self.local_actors.values():
            actor.on_connect(self)

    def disconnect(self):
        for actor in self.local_actors.values():
            actor.disconnect_network(self)
        if self._directory_svc:
            self._directory_svc.stop()
        if self._broker:
            self._broker.stop()

    def find_by_topic(self, topic: str) -> IActorConnector:
        return ZMQActorConnector(self._context, topic)

    def find_by_name(self, name: str) -> IActorConnector:
        actor_info: ActorInfo = self._directory_svc.lookup_actor_by_name(name)
        if actor_info is None:
            Warn("Local_Actor_Network", f"{name}, not found in the network.")
            return None
        Debug("Local_Actor_Network", f"[{name}] found in the network.")
        return self.find_by_topic(name)

    def find_termination(self) -> IActorConnector:
        termination_topic: str = Termination_Topic
        return self.find_by_topic(termination_topic)

    def find_by_name_regex(self, name_regex) -> List[ActorInfo]:
        actor_info: ActorInfoCollection = self._directory_svc.lookup_actor_info_by_name(name_regex)
        if actor_info is None:
            Warn("Local_Actor_Network", f"{name_regex}, not found in the network.")
            return None
        Debug("Local_Actor_Network", f"[{name_regex}] found in the network.")
        actor_list = []
        for actor in actor_info.info_coll:
            actor_list.append(actor)
        return actor_list
