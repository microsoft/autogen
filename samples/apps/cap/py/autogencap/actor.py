import threading
import traceback
from .actor_runtime import IMsgActor, IRuntime, IMessageReceiver
from .debug_log import Debug, Info


class Actor(IMsgActor):
    def __init__(self, agent_name: str, description: str, start_thread: bool = True):
        """Initialize the Actor with a name, description, and threading option."""
        self.actor_name: str = agent_name
        self.agent_description: str = description
        self.run = False
        self._start_event = threading.Event()
        self._start_thread = start_thread
        self._msg_receiver: IMessageReceiver = None
        self._runtime: IRuntime = None

    def on_connect(self):
        """Connect the actor to the runtime."""
        Debug(self.actor_name, f"is connecting to {self._runtime}")
        Debug(self.actor_name, "connected")

    def on_txt_msg(self, msg: str, msg_type: str, receiver: str, sender: str) -> bool:
        """Handle incoming text messages."""
        Info(self.actor_name, f"InBox: {msg}")
        return True

    def on_bin_msg(self, msg: bytes, msg_type: str, receiver: str, sender: str) -> bool:
        """Handle incoming binary messages."""
        Info(self.actor_name, f"Msg: receiver=[{receiver}], msg_type=[{msg_type}]")
        return True

    def dispatch_message(self, message):
        """Dispatch the received message based on its type."""
        if message is None:
            return
        topic, msg_type, sender_topic, msg = message
        if msg_type == "text":
            msg = msg.decode("utf-8")  # Convert bytes to string
            if not self.on_txt_msg(msg, msg_type, topic, sender_topic):
                msg = "quit"
            if msg.lower() == "quit":
                self.run = False
        else:
            if not self.on_bin_msg(msg, msg_type, topic, sender_topic):
                self.run = False

    def get_message(self):
        """Retrieve a message from the runtime implementation."""
        return self._msg_receiver.get_message()

    def _msg_loop(self):
        """Main message loop for receiving and dispatching messages."""
        try:
            self._msg_receiver = self._runtime.get_new_msg_receiver()
            self._msg_receiver.init(self.actor_name)
            self._start_event.set()
            while self.run:
                message = self._msg_receiver.get_message()
                self.dispatch_message(message)
        except Exception as e:
            Debug(self.actor_name, f"recv thread encountered an error: {e}")
            traceback.print_exc()
        finally:
            # In case there was an exception at startup signal
            # the main thread.
            self._start_event.set()
            self.run = False
            Debug(self.actor_name, "recv thread ended")

    def on_start(self, runtime: IRuntime):
        """Start the actor and its message receiving thread if applicable."""
        self._runtime = runtime  # Save the runtime
        self.run = True
        if self._start_thread:
            self._thread = threading.Thread(target=self._msg_loop)
            self._thread.start()
            self._start_event.wait()
        else:
            self._msg_receiver = self._runtime.get_new_msg_receiver()
            self._msg_receiver.init(self.actor_name)

    def disconnect_network(self, network):
        """Disconnect the actor from the network."""
        Debug(self.actor_name, f"is disconnecting from {network}")
        Debug(self.actor_name, "disconnected")
        self.stop()

    def stop(self):
        """Stop the actor and its message receiver."""
        self.run = False
        if self._start_thread:
            self._thread.join()
        self._msg_receiver.stop()
