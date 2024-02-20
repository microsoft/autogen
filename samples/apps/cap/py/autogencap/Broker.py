from .DebugLog import Debug
import zmq
import threading
from .Constants import xsub_url, xpub_url


class Broker:
    def __init__(self, context:zmq.Context=zmq.Context()):
        self._context:zmq.Context = context
        self._xpub:zmq.Socket = self._context.socket(zmq.XPUB)
        self._xpub.setsockopt(zmq.LINGER, 0)
        self._xpub.bind(xpub_url)
        self._xsub:zmq.Socket = self._context.socket(zmq.XSUB)
        self._xsub.setsockopt(zmq.LINGER, 0)
        self._xsub.bind(xsub_url)
        self._run:bool = False

    def start(self):
        self._run = True
        self._broker_thread:threading.Thread = threading.Thread(target=self.thread_fn)
        self._broker_thread.start()

    def stop(self):
        # Error("BROKER_ERR", "fix cleanup self._context.term()")
        Debug("BROKER", "stopped")
        self._run = False
        self._broker_thread.join()
        self._xpub.close()
        self._xsub.close()
        # self._context.term()

    def thread_fn(self):
        try:
            self._poller:zmq.Poller = zmq.Poller()
            self._poller.register(self._xpub, zmq.POLLIN)
            self._poller.register(self._xsub, zmq.POLLIN)
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
