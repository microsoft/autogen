import time
import zmq
import threading
from autogencap.DebugLog import Debug, Info, Warn
from autogencap.Config import xsub_url, xpub_url


class Broker:
    def __init__(self, context: zmq.Context = zmq.Context()):
        self._context: zmq.Context = context
        self._run: bool = False
        self._xpub: zmq.Socket = None
        self._xsub: zmq.Socket = None

    def start(self) -> bool:
        try:
            # XPUB setup
            self._xpub = self._context.socket(zmq.XPUB)
            self._xpub.setsockopt(zmq.LINGER, 0)
            self._xpub.bind(xpub_url)

            # XSUB setup
            self._xsub = self._context.socket(zmq.XSUB)
            self._xsub.setsockopt(zmq.LINGER, 0)
            self._xsub.bind(xsub_url)

        except zmq.ZMQError as e:
            Debug("BROKER", f"Unable to start.  Check details: {e}")
            # If binding fails, close the sockets and return False
            if self._xpub:
                self._xpub.close()
            if self._xsub:
                self._xsub.close()
            return False

        self._run = True
        self._broker_thread: threading.Thread = threading.Thread(target=self.thread_fn)
        self._broker_thread.start()
        time.sleep(0.01)
        return True

    def stop(self):
        # Error("BROKER_ERR", "fix cleanup self._context.term()")
        Debug("BROKER", "stopped")
        self._run = False
        self._broker_thread.join()
        if self._xpub:
            self._xpub.close()
        if self._xsub:
            self._xsub.close()
        # self._context.term()

    def thread_fn(self):
        try:
            # Poll sockets for events
            self._poller: zmq.Poller = zmq.Poller()
            self._poller.register(self._xpub, zmq.POLLIN)
            self._poller.register(self._xsub, zmq.POLLIN)

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
            time.sleep(0.5)
        except KeyboardInterrupt:
            Info("BROKER", "KeyboardInterrupt.  Stopping the broker.")
            broker.stop()


if __name__ == "__main__":
    main()
