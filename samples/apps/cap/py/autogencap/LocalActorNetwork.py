import zmq
from .DebugLog import Debug, Warn
from .ActorConnector import ActorConnector
from .Broker import Broker
from .DirectorySvc import DirectorySvc
from .Constants import Termination_Topic
from .Actor import Actor
from .proto.CAP_pb2 import ActorInfo, ActorInfoCollection
from typing import List
import time

# TODO: remove time import


class LocalActorNetwork:
    def __init__(self, name: str = "Local Actor Network", start_broker: bool = True):
        self.local_actors = {}
        self.name: str = name
        self._context: zmq.Context = zmq.Context()
        self._start_broker: bool = start_broker
        self._broker: Broker = None
        self._directory_svc: DirectorySvc = None

    def __str__(self):
        return f"{self.name}"

    def _init_runtime(self):
        if self._start_broker and self._broker is None:
            self._broker = Broker(self._context)
            if not self._broker.start():
                self._start_broker = False  # Don't try to start the broker again
                self._broker = None
        if self._directory_svc is None:
            self._directory_svc = DirectorySvc(self._context)
            self._directory_svc.start()

    def register(self, actor: Actor):
        self._init_runtime()
        # Get actor's name and description and add to a dictionary so
        # that we can look up the actor by name
        self._directory_svc.register_actor_by_name(actor.actor_name)
        self.local_actors[actor.actor_name] = actor
        actor.start(self._context)
        Debug("Local_Actor_Network", f"{actor.actor_name} registered in the network.")

    def connect(self):
        self._init_runtime()
        for actor in self.local_actors.values():
            actor.connect_network(self)

    def disconnect(self):
        for actor in self.local_actors.values():
            actor.disconnect_network(self)
        if self._directory_svc:
            self._directory_svc.stop()
        if self._broker:
            self._broker.stop()

    def actor_connector_by_topic(self, topic: str) -> ActorConnector:
        return ActorConnector(self._context, topic)

    def lookup_actor(self, name: str) -> ActorConnector:
        actor_info: ActorInfo = self._directory_svc.lookup_actor_by_name(name)
        if actor_info is None:
            Warn("Local_Actor_Network", f"{name}, not found in the network.")
            return None
        Debug("Local_Actor_Network", f"[{name}] found in the network.")
        return self.actor_connector_by_topic(name)

    def lookup_termination(self) -> ActorConnector:
        termination_topic: str = Termination_Topic
        return self.actor_connector_by_topic(termination_topic)

    def lookup_actor_info(self, name_regex) -> List[ActorInfo]:
        actor_info: ActorInfoCollection = self._directory_svc.lookup_actor_info_by_name(name_regex)
        if actor_info is None:
            Warn("Local_Actor_Network", f"{name_regex}, not found in the network.")
            return None
        Debug("Local_Actor_Network", f"[{name_regex}] found in the network.")
        actor_list = []
        for actor in actor_info.info_coll:
            actor_list.append(actor)
        return actor_list
