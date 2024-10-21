from autogencap.actor import Actor
from autogencap.constants import Termination_Topic
from autogencap.debug_log import Debug

class AGActor(Actor):
    def on_start(self, runtime):
        super().on_start(runtime)
        str_topic = Termination_Topic
        self._msg_receiver.add_listener(str_topic)
        Debug(self.actor_name, f"subscribe to: {str_topic}")