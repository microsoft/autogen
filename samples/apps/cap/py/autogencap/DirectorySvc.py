from autogencap.Constants import Directory_Svc_Topic
from autogencap.Config import xpub_url, xsub_url
from autogencap.DebugLog import Debug, Info, Error
from autogencap.ActorConnector import ActorConnector
from autogencap.Actor import Actor
from autogencap.proto.CAP_pb2 import ActorRegistration, ActorInfo, ActorLookup, ActorLookupResponse
import zmq
import threading
import time

#TODO (Future DirectorySv PR) use actor description, network_id, other properties to make directory
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
        else:
            Error("DirectorySvc", f"Unknown message type: {msg_type}")
        return True

    def _actor_registration_msg_handler(self, topic: str, msg_type: str, msg: bytes):
        actor_reg = ActorRegistration()
        actor_reg.ParseFromString(msg)
        Info("DirectorySvc", f"Actor registration: {actor_reg.actor_info.name}")
        name = actor_reg.actor_info.name
        #TODO (Future DirectorySv PR) network_id should be namespace prefixed to support multiple networks
        network_id = actor_reg.actor_info.name + self._network_prefix
        if name in self._registered_actors:
            Error("DirectorySvc", f"Actor already registered: {name}")
            return
        self._registered_actors[name] = actor_reg.actor_info
        
    def _actor_lookup_msg_handler(self, topic: str, msg_type: str, msg: bytes, sender_topic: str):
        actor_lookup = ActorLookup()
        actor_lookup.ParseFromString(msg)
        Debug("DirectorySvc", f"Actor lookup: {actor_lookup.actor_info.name}")
        actor:ActorInfo = None
        if actor_lookup.actor_info.name in self._registered_actors:
            Info("DirectorySvc", f"Actor found: {actor_lookup.actor_info.name}")
            actor = self._registered_actors[actor_lookup.actor_info.name]
        else:
            Error("DirectorySvc", f"Actor not found: {actor_lookup.actor_info.name}")
        actor_lookup_resp = ActorLookupResponse()
        actor_lookup_resp.actor.info_coll.extend([actor])
        sender_connection = ActorConnector(self._context, sender_topic)
        serialized_msg = actor_lookup_resp.SerializeToString()
        sender_connection.send_bin_msg(ActorLookupResponse.__name__, serialized_msg)
        
class DirectorySvc:
    def __init__(self, context: zmq.Context = zmq.Context()):
        self._context: zmq.Context = context
        self._directory_connector: ActorConnector = None
        self._directory_actor: DirectoryActor = None

    def start(self):
        self._directory_actor = DirectoryActor(Directory_Svc_Topic, "Directory Service")
        self._directory_actor.start(self._context)
        self._directory_connector = ActorConnector(self._context, Directory_Svc_Topic)
        
    def stop(self):
        self._directory_actor.run = False
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

    def lookup_actor_by_name(self, actor_name: str) -> ActorInfo:
        actor_info = ActorInfo(name=actor_name)
        actor_lookup = ActorLookup(actor_info=actor_info)
        serialized_msg = actor_lookup.SerializeToString()
        resp_topic, resp_msg_type, resp_sender_topic, resp = self._directory_connector.binary_request(ActorLookup.__name__, serialized_msg)
        actor_lookup_resp = ActorLookupResponse()
        actor_lookup_resp.ParseFromString(resp)
        if (actor_lookup_resp.found):
            if len(actor_lookup_resp.actor_info_coll) > 0:
                return actor_lookup_resp.actor_info_coll[0]
        return None

class MinProxy:
    def __init__(self, context: zmq.Context):
        self._context: zmq.Context = context
        self._xpub: zmq.Socket = None
        self._xsub: zmq.Socket = None
        
    def start(self):
        # Start the proxy thread
        proxy_thread = threading.Thread(target=self.proxy_thread_fn)
        proxy_thread.start()

    def stop(self):
        self._xsub.setsockopt(zmq.LINGER, 0)
        self._xpub.setsockopt(zmq.LINGER, 0)
        self._xpub.close()
        self._xsub.close()

    def proxy_thread_fn(self):
        self._xpub: zmq.Socket = self._context.socket(zmq.XPUB)
        self._xsub: zmq.Socket = self._context.socket(zmq.XSUB)
        try:
            self._xpub.bind(xpub_url)
            self._xsub.bind(xsub_url)
            zmq.proxy(self._xpub, self._xsub)
        except zmq.ContextTerminated as e:
            self._xpub.close()
            self._xsub.close()
        except Exception as e:
            Error(f"proxy_thread_fn", f"proxy_thread_fn encountered an error: {e}")
            self._xpub.setsockopt(zmq.LINGER, 0)
            self._xsub.setsockopt(zmq.LINGER, 0)
            self._xpub.close()
            self._xsub.close()
        finally:
            Info(f"proxy_thread_fn", f"proxy_thread_fn terminated.")

def main():
    # Standalone min repro sanity check for DirectorySvc
    
    context: zmq.Context = zmq.Context()
    # Start simple broker (will exit if real broker is running)
    proxy: MinProxy = MinProxy(context)
    proxy.start()
    time.sleep(0.05) # wait for proxy sockets to bind
    # Start the directory service
    directory_svc = DirectorySvc(context)
    directory_svc.start()
    time.sleep(0.05) # wait for directory sockets to connect
    # register an actor
    directory_svc.register_actor_by_name("my_actor")
    # look up an actor
    actor:ActorInfo = directory_svc.lookup_actor_by_name("my_actor")
    if(actor is not None):
        Info("main", f"Found actor: {actor.name}")
    
    directory_svc.stop()
    proxy.stop()
    time.sleep(0.05) # wait for directory and proxy sockets to close
    context.term()
    Info("main", "Done.")
    
if __name__ == "__main__":
    main()