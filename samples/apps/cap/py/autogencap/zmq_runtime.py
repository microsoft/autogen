import time
from typing import List

import zmq


from .actor import Actor
from .actor_connector import IActorConnector
from .actor_runtime import IMessageReceiver, IRuntime
from .broker import Broker
from .constants import Termination_Topic
from .debug_log import Debug, Warn
from .proto.CAP_pb2 import ActorInfo, ActorInfoCollection
from .zmq_actor_connector import ZMQActorConnector


class ZMQRuntime(IRuntime):
    def __init__(self, start_broker: bool = True):
        self.local_actors = {}
        self._context: zmq.Context = zmq.Context()
        self._start_broker: bool = start_broker
        self._broker: Broker = None
        self._directory_svc = None
        self._log_name = self.__class__.__name__

    def __str__(self):
        return f" \
{self._log_name}\n \
is_broker: {self._broker is not None}\n \
is_directory_svc: {self._directory_svc is not None}\n \
local_actors: {self.local_actors}\n"

    def _init_runtime(self):
        if self._start_broker and self._broker is None:
            self._broker = Broker(self._context)
            if not self._broker.start():
                self._start_broker = False  # Don't try to start the broker again
                self._broker = None
        if self._directory_svc is None:
            from .zmq_directory_svc import ZMQDirectorySvc

            self._directory_svc = ZMQDirectorySvc(self._context)
            self._directory_svc.start(self)
        time.sleep(0.25)  # Process queued thread events in Broker and Directory

    def register(self, actor: Actor):
        self._init_runtime()
        self._directory_svc.register_actor_by_name(actor.actor_name)
        self.local_actors[actor.actor_name] = actor
        actor.on_start(self)  # Pass self (the runtime) to on_start
        Debug(self._log_name, f"{actor.actor_name} registered in the network.")

    def get_new_msg_receiver(self) -> IMessageReceiver:
        from .zmq_msg_receiver import ZMQMsgReceiver

        return ZMQMsgReceiver(self._context)

    def connect(self):
        self._init_runtime()
        for actor in self.local_actors.values():
            actor.on_connect()

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
            Warn(self._log_name, f"{name}, not found in the network.")
            return None
        Debug(self._log_name, f"[{name}] found in the network.")
        return self.find_by_topic(name)

    def find_termination(self) -> IActorConnector:
        termination_topic: str = Termination_Topic
        return self.find_by_topic(termination_topic)

    def find_by_name_regex(self, name_regex) -> List[ActorInfo]:
        actor_info: ActorInfoCollection = self._directory_svc.lookup_actor_info_by_name(name_regex)
        if actor_info is None:
            Warn(self._log_name, f"{name_regex}, not found in the network.")
            return None
        Debug(self._log_name, f"[{name_regex}] found in the network.")
        actor_list = []
        for actor in actor_info.info_coll:
            actor_list.append(actor)
        return actor_list
