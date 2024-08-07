import zmq

from autogencap.actor import Actor
from autogencap.constants import Termination_Topic
from autogencap.debug_log import Debug


class AGActor(Actor):
    def on_start(self, context: zmq.Context):
        super().on_start(context)
        str_topic = Termination_Topic
        Debug(self.actor_name, f"subscribe to: {str_topic}")
        self._socket.setsockopt_string(zmq.SUBSCRIBE, f"{str_topic}")
