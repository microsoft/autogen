import zmq
from .DebugLog import Debug, Warn
from .ActorConnector import ActorConnector
from .Broker import Broker
from .Constants import Termination_Topic
from .Actor import Actor

class LocalActorNetwork:
    def __init__(self, name:str ="Local Actor Network", start_broker:bool = True):
        self.actors = {}
        self.name: str = name
        self._context: zmq.Context = zmq.Context()
        self._start_broker: bool = start_broker
        self._broker: Broker = None

    def __str__(self):
        return f"{self.name}"

    def __init_broker(self):
        if self._start_broker and self._broker is None:
            self._broker = Broker(self._context)
            if not self._broker.start():
                self._start_broker = False  # Don't try to start the broker again
                self._broker = None

    def register(self, actor: Actor):
        self.__init_broker()
        # Get actor's name and description and add to a dictionary so
        # that we can look up the actor by name
        self.actors[actor.actor_name] = actor
        actor.start_recv_thread(self._context)
        Debug("Local_Actor_Network", f"{actor.actor_name} registered in the network.")

    def connect(self):
        self.__init_broker()
        for actor in self.actors.values():
            actor.connect(self)

    def disconnect(self):
        for actor in self.actors.values():
            actor.disconnect(self)
        if self._broker: 
            self._broker.stop()

    def actor_connector_by_topic(self, topic: str) -> ActorConnector:
        return ActorConnector(self._context, topic)

    def lookup_actor(self, name: str) -> ActorConnector:
        actor = self.actors.get(name, None)
        if actor is None:
            Warn("Local_Actor_Network", f"{name}, not found in the network.")
            return None
        Debug("Local_Actor_Network", f"[{name}] found in the network.")
        return self.actor_connector_by_topic(name)

    def lookup_termination(self) -> ActorConnector:
        termination_topic: str = Termination_Topic
        return self.actor_connector_by_topic(termination_topic)
