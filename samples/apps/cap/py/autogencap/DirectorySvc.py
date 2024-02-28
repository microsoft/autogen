from autogencap.Constants import Directory_Svc_Topic
from autogencap.Config import xpub_url, xsub_url
from autogencap.DebugLog import Debug, Info, Error
from autogencap.ActorConnector import ActorConnector
from autogencap.proto.CAP_pb2 import ActorRegistration, ActorInfo, ActorLookup
import zmq
import threading
import time

#TODO (Deferred DirectorySv PR) use actor description, network_id, other properties to make directory
# service more generic and powerful

class DirectorySvc:
    # TODO: clean termination
    def __init__(self, context: zmq.Context = zmq.Context()):
        self._context: zmq.Context = context
        self._run: bool = False
        self._directory_pub: zmq.Socket = None
        self._directory_sub: zmq.Socket = None
        self._registered_actors = {}
        self._network_prefix = ""
        self._directory_connector: ActorConnector = None

    def actor_registration_msgproc(self, topic: str, msg_type: str, msg: bytes):
        actor_reg = ActorRegistration()
        actor_reg.ParseFromString(msg)
        Info("DirectorySvc", f"Actor registration: {actor_reg.actor_info.name}")
        name = actor_reg.actor_info.name
        #TODO (Deferred DirectorySv PR) network_id should be namespace prefixed to support multiple networks
        #TODO (Deferred DirectorySv PR) Should network id be passed in during DirectorySvc construction?
        network_id = actor_reg.actor_info.name + self._network_prefix
        if name in self._registered_actors:
            Error("DirectorySvc", f"Actor already registered: {name}")
            return
        self._registered_actors[name] = network_id
        
    def actor_lookup_msgproc(self, topic: str, msg_type: str, msg: bytes):
        actor_lookup = ActorLookup()
        actor_lookup.ParseFromString(msg)
        Debug("DirectorySvc", f"Actor lookup: {actor_lookup.actor_info.name}")
        if actor_lookup.actor_info.name in self._registered_actors:
            Info("DirectorySvc", f"Actor found: {actor_lookup.actor_info.name}")
        else:
            Error("DirectorySvc", f"Actor not found: {actor_lookup.actor_info.name}")

    def recv_thread(self):
        Debug("DirectorySvc", "recv thread started")
        try:
            while self._run:
                try:
                    topic, msg_type, msg = self._directory_sub.recv_multipart()
                    topic = topic.decode("utf-8")  # Convert bytes to string
                    msg_type = msg_type.decode("utf-8")  # Convert bytes to string
                except zmq.Again:
                    continue  # No message received, continue to next iteration
                if msg_type == ActorRegistration.__name__:
                    self.actor_registration_msgproc(topic, msg_type, msg)
                elif msg_type == ActorLookup.__name__:
                    self.actor_lookup_msgproc(topic, msg_type, msg)
                else:
                    Error("DirectorySvc", f"Unhandled message type: topic=[{topic}], msg_type=[{msg_type}]")

        except Exception as e:
            Debug("DirectorySvc", f"recv thread encountered an error: {e}")
        finally:
            self.run = False
            Debug("DirectorySvc", "recv thread ended")
    
    def start(self):
        
        # Directory service subscription socket
        self._directory_sub = self._context.socket(zmq.SUB)
        self._directory_sub.setsockopt(zmq.RCVTIMEO, 500)
        self._directory_sub.connect(xpub_url)
        Debug("DirectorySvc", f"subscribe to: {Directory_Svc_Topic}")
        self._directory_sub.setsockopt_string(zmq.SUBSCRIBE, f"{Directory_Svc_Topic}")

        # Directory service registration socket
        self._directory_pub = self._context.socket(zmq.PUB)
        self._directory_pub.connect(xsub_url)
        Debug("DirectorySvc", f"subscribe to: {Directory_Svc_Topic}")

        self._run = True
        self._broker_thread: threading.Thread = threading.Thread(target=self.recv_thread)
        self._broker_thread.start()

    def register_actor(self, actor_info: ActorInfo):
        # Send a message to the directory service
        # to register the actor        
        actor_reg = ActorRegistration()
        actor_reg.actor_info.CopyFrom(actor_info)
        serialized_msg = actor_reg.SerializeToString()
        self._directory_pub.send_multipart(
            [Directory_Svc_Topic.encode("utf8"), type(actor_reg).__name__.encode("utf8"), serialized_msg]
        )

    def register_actor_by_name(self, actor_name: str):
        actor_info = ActorInfo(name=actor_name)
        self.register_actor(actor_info)

    def lookup_actor_by_name(self, actor_name: str) -> ActorInfo:
        actor_info = ActorInfo(name=actor_name)
        actor_lookup = ActorLookup(actor_info=actor_info)
        serialized_msg = actor_lookup.SerializeToString()
        self._directory_pub.send_multipart(
            [Directory_Svc_Topic.encode("utf8"), type(actor_lookup).__name__.encode("utf8"), serialized_msg]
        )

def proxy_thread_fn(context: zmq.Context):
    xpub: zmq.Socket = context.socket(zmq.XPUB)
    xsub: zmq.Socket = context.socket(zmq.XSUB)
    try:
        xpub.bind(xpub_url)
        xsub.bind(xsub_url)
        zmq.proxy(xpub, xsub)
    except zmq.ContextTerminated as e:
        Info(f"proxy_thread_fn", f"proxy_thread_fn terminated.")
    except Exception as e:
        Error(f"proxy_thread_fn", f"proxy_thread_fn encountered an error: {e}")
    finally:
        xpub.setsockopt(zmq.LINGER, 0)
        xpub.close()
        xsub.setsockopt(zmq.LINGER, 0)
        xsub.close()

def main():
    # Start simple broker (will exit if real broker is running)
    context: zmq.Context = zmq.Context()
    # Start the proxy thread
    proxy_thread = threading.Thread(target=proxy_thread_fn, args=(context,))
    proxy_thread.start()
    time.sleep(0.01)
    # Start the directory service
    directory_svc = DirectorySvc(context)
    directory_svc.start()
    # register an actor
    directory_svc.register_actor_by_name("my_actor")
    # look up an actor
    actor:ActorInfo = directory_svc.lookup_actor_by_name("my_actor")
    time.sleep(10)
    context.term()
    
if __name__ == "__main__":
    main()