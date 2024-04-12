import threading
import time

import zmq

from autogencap.Config import router_url, xpub_url, xsub_url
from autogencap.DebugLog import Debug, Info, Warn


class Broker:
    def __init__(self, context: zmq.Context = zmq.Context()):
        self._context: zmq.Context = context
        self._run: bool = False
        self._xpub: zmq.Socket = None
        self._xsub: zmq.Socket = None
        self._router: zmq.Socket = None
        self._start_event = threading.Event()

    def _init_sockets(self):
        try:
            # XPUB setup
            self._xpub = self._context.socket(zmq.XPUB)
            self._xpub.setsockopt(zmq.LINGER, 0)
            self._xpub.bind(xpub_url)
            # XSUB setup
            self._xsub = self._context.socket(zmq.XSUB)
            self._xsub.setsockopt(zmq.LINGER, 0)
            self._xsub.bind(xsub_url)
            # ROUTER setup
            self._router = self._context.socket(zmq.ROUTER)
            self._router.setsockopt(zmq.LINGER, 0)
            self._router.bind(router_url)
            return True
        except zmq.ZMQError as e:
            Debug("BROKER", f"Unable to start.  Check details: {e}")
            # If binding fails, close the sockets and return False
            if self._xpub:
                self._xpub.close()
            if self._xsub:
                self._xsub.close()
            if self._router:
                self._router.close()
            return False

    def start(self) -> bool:
        Debug("BROKER", "Trying to start broker.")
        self._run = True
        self._broker_thread: threading.Thread = threading.Thread(target=self.thread_fn)
        self._broker_thread.start()
        self._start_event.wait()
        # this will be false if the thread is not running
        return self._run

    def stop(self):
        if not self._run:
            return
        # Error("BROKER_ERR", "fix cleanup self._context.term()")
        Debug("BROKER", "stopped")
        self._run = False
        self._broker_thread.join()
        if self._xpub:
            self._xpub.close()
        if self._xsub:
            self._xsub.close()
        if self._router:
            self._router.close()
        # self._context.term()

    def thread_fn(self):
        try:
            if not self._init_sockets():
                Debug("BROKER", "Receive thread not started since sockets were not initialized")
                self._run = False
                self._start_event.set()
                return

            # Poll sockets for events
            self._poller: zmq.Poller = zmq.Poller()
            self._poller.register(self._xpub, zmq.POLLIN)
            self._poller.register(self._xsub, zmq.POLLIN)
            self._poller.register(self._router, zmq.POLLIN)

            Info("BROKER", "Started.  Waiting for events")
            # signal to the main thread that Broker has started
            self._start_event.set()
            # Receive msgs, forward and process
            while self._run:
                events = dict(self._poller.poll(500))
                if self._xpub in events:
                    message = self._xpub.recv_multipart()
                    Debug("BROKER", f"subscription message: {message[0]}")
                    self._xsub.send_multipart(message)

                if self._xsub in events:
                    message = self._xsub.recv_multipart()
                    Debug("BROKER", f"publishing message: {message}")
                    self._xpub.send_multipart(message)

                if self._router in events:
                    message = self._router.recv_multipart()
                    Debug("BROKER", f"router message: {message}")
                    # Mirror it back for now to confirm connectivity
                    # More interesting reserved point to point
                    # routing coming in the the future
                    self._router.send_multipart(message)

        except Exception as e:
            Debug("BROKER", f"thread encountered an error: {e}")
        finally:
            self._run = False
            Debug("BROKER", "thread ended")
        return


# Run a standalone broker that all other Actors can connect to.
# This can also run inproc with the other actors.
def main():
    broker = Broker()
    Info("BROKER", "Starting.")
    if broker.start():
        Info("BROKER", "Running.")
    else:
        Warn("BROKER", "Failed to start.")
        return

    status_interval = 300  # seconds
    last_time = time.time()

    # Broker is running in a separate thread. Here we are watching the
    # broker's status and printing status every few seconds.  This is
    # a good place to print other statistics captured as the broker runs.
    # -- Exits when the user presses Ctrl+C --
    while broker._run:
        # print a message every n seconds
        current_time = time.time()
        elapsed_time = current_time - last_time
        if elapsed_time > status_interval:
            Info("BROKER", "Running.")
            last_time = current_time
        try:
            # Hang out for a while and print out
            # status every now and then
            time.sleep(0.5)
        except KeyboardInterrupt:
            Info("BROKER", "KeyboardInterrupt.  Stopping the broker.")
            broker.stop()


if __name__ == "__main__":
    main()
