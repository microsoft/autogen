from autogencap.Constants import Directory_Svc_Topic
from autogencap.Config import xpub_url, xsub_url, router_url
from autogencap.DebugLog import Debug, Info, Error
from autogencap.ActorConnector import ActorConnector
from autogencap.Actor import Actor
from autogencap.Broker import Broker
from autogencap.proto.CAP_pb2 import (
    ActorRegistration,
    ActorInfo,
    ActorLookup,
    ActorLookupResponse,
    Ping,
    Pong,
    ActorInfoCollection,
)
import zmq
import threading
import time
import re

# TODO (Future DirectorySv PR) use actor description, network_id, other properties to make directory
# service more generic and powerful


class DirectoryActor(Actor):
    def __init__(self, topic: str, name: str):
        super().__init__(topic, name)
        self._registered_actors = {}
        self._network_prefix = ""

    def _process_bin_msg(self, msg: bytes, msg_type: str, topic: str, sender: str) -> bool:
        if msg_type == ActorRegistration.__name__:
            self._actor_registration_msg_handler(topic, msg_type, msg)
        elif msg_type == ActorLookup.__name__:
            self._actor_lookup_msg_handler(topic, msg_type, msg, sender)
        elif msg_type == Ping.__name__:
            self._ping_msg_handler(topic, msg_type, msg, sender)
        else:
            Error("DirectorySvc", f"Unknown message type: {msg_type}")
        return True

    def _ping_msg_handler(self, topic: str, msg_type: str, msg: bytes, sender_topic: str):
        Info("DirectorySvc", f"Ping received: {sender_topic}")
        pong = Pong()
        serialized_msg = pong.SerializeToString()
        sender_connection = ActorConnector(self._context, sender_topic)
        sender_connection.send_bin_msg(Pong.__name__, serialized_msg)

    def _actor_registration_msg_handler(self, topic: str, msg_type: str, msg: bytes):
        actor_reg = ActorRegistration()
        actor_reg.ParseFromString(msg)
        Info("DirectorySvc", f"Actor registration: {actor_reg.actor_info.name}")
        name = actor_reg.actor_info.name
        # TODO (Future DirectorySv PR) network_id should be namespace prefixed to support multiple networks
        actor_reg.actor_info.name + self._network_prefix
        if name in self._registered_actors:
            Error("DirectorySvc", f"Actor already registered: {name}")
            return
        self._registered_actors[name] = actor_reg.actor_info

    def _actor_lookup_msg_handler(self, topic: str, msg_type: str, msg: bytes, sender_topic: str):
        actor_lookup = ActorLookup()
        actor_lookup.ParseFromString(msg)
        Debug("DirectorySvc", f"Actor lookup: {actor_lookup.actor_info.name}")
        actor_lookup_resp = ActorLookupResponse()
        actor_lookup_resp.found = False
        try:
            pattern = re.compile(actor_lookup.actor_info.name)
        except re.error:
            Error("DirectorySvc", f"Invalid regex pattern: {actor_lookup.actor_info.name}")
        else:
            found_actor_list = [
                self._registered_actors[registered_actor]
                for registered_actor in self._registered_actors
                if pattern.match(registered_actor)
            ]

        if found_actor_list:
            for actor in found_actor_list:
                Info("DirectorySvc", f"Actor found: {actor.name}")
            actor_lookup_resp.found = True
            actor_lookup_resp.actor.info_coll.extend(found_actor_list)
        else:
            Error("DirectorySvc", f"Actor not found: {actor_lookup.actor_info.name}")

        sender_connection = ActorConnector(self._context, sender_topic)
        serialized_msg = actor_lookup_resp.SerializeToString()
        sender_connection.send_bin_msg(ActorLookupResponse.__name__, serialized_msg)


class DirectorySvc:
    def __init__(self, context: zmq.Context = zmq.Context()):
        self._context: zmq.Context = context
        self._directory_connector: ActorConnector = None
        self._directory_actor: DirectoryActor = None

    def _no_other_directory(self) -> bool:
        Debug("DirectorySvc", "Pinging existing DirectorySvc")
        ping = Ping()
        serialized_msg = ping.SerializeToString()
        _, _, _, resp = self._directory_connector.binary_request(Ping.__name__, serialized_msg, retry=0)
        if resp is None:
            return True
        return False

    def start(self):
        self._directory_connector = ActorConnector(self._context, Directory_Svc_Topic)
        if self._no_other_directory():
            self._directory_actor = DirectoryActor(Directory_Svc_Topic, "Directory Service")
            self._directory_actor.start(self._context)
            Info("DirectorySvc", "Directory service started.")
        else:
            Info("DirectorySvc", "Another directory service is running. This instance will not start.")

    def stop(self):
        if self._directory_actor:
            self._directory_actor.stop()
        if self._directory_connector:
            self._directory_connector.close()

    def register_actor(self, actor_info: ActorInfo):
        # Send a message to the directory service
        # to register the actor
        actor_reg = ActorRegistration()
        actor_reg.actor_info.CopyFrom(actor_info)
        serialized_msg = actor_reg.SerializeToString()
        self._directory_connector.send_bin_msg(ActorRegistration.__name__, serialized_msg)

    def register_actor_by_name(self, actor_name: str):
        actor_info = ActorInfo(name=actor_name)
        self.register_actor(actor_info)

    def _lookup_actors_by_name(self, name_regex: str):
        actor_info = ActorInfo(name=name_regex)
        actor_lookup = ActorLookup(actor_info=actor_info)
        serialized_msg = actor_lookup.SerializeToString()
        _, _, _, resp = self._directory_connector.binary_request(ActorLookup.__name__, serialized_msg)
        actor_lookup_resp = ActorLookupResponse()
        actor_lookup_resp.ParseFromString(resp)
        return actor_lookup_resp

    def lookup_actor_by_name(self, actor_name: str) -> ActorInfo:
        actor_lookup_resp = self._lookup_actors_by_name(actor_name)
        if actor_lookup_resp.found:
            if len(actor_lookup_resp.actor.info_coll) > 0:
                return actor_lookup_resp.actor.info_coll[0]
        return None

    def lookup_actor_info_by_name(self, actor_name: str) -> ActorInfoCollection:
        actor_lookup_resp = self._lookup_actors_by_name(actor_name)
        if actor_lookup_resp.found:
            if len(actor_lookup_resp.actor.info_coll) > 0:
                return actor_lookup_resp.actor
        return None


# Run a standalone directory service
def main():
    context: zmq.Context = zmq.Context()
    # Start simple broker (will exit if real broker is running)
    proxy: Broker = Broker(context)
    proxy.start()
    # Start the directory service
    directory_svc = DirectorySvc(context)
    directory_svc.start()
    # # How do you register an actor?
    # directory_svc.register_actor_by_name("my_actor")
    #
    # # How do you look up an actor?
    # actor: ActorInfo = directory_svc.lookup_actor_by_name("my_actor")
    # if actor is not None:
    #     Info("main", f"Found actor: {actor.name}")

    # DirectorySvc is running in a separate thread. Here we are watching the
    # status and printing status every few seconds.  This is
    # a good place to print other statistics captured as the broker runs.
    # -- Exits when the user presses Ctrl+C --
    status_interval = 300  # seconds
    last_time = time.time()
    while True:
        # print a message every n seconds
        current_time = time.time()
        elapsed_time = current_time - last_time
        if elapsed_time > status_interval:
            Info("DirectorySvc", "Running.")
            last_time = current_time
        try:
            time.sleep(0.5)
        except KeyboardInterrupt:
            Info("DirectorySvc", "KeyboardInterrupt.  Stopping the DirectorySvc.")
            break

    directory_svc.stop()
    proxy.stop()
    context.term()
    Info("main", "Done.")


if __name__ == "__main__":
    main()
