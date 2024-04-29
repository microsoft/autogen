import sys
import time
from typing import Any, Dict

import _paths
import zmq
from autogencap.Config import dealer_url, router_url, xpub_url, xsub_url
from zmq.utils.monitor import recv_monitor_message


def zmq_sub_test():
    context = zmq.Context()
    sub_socket = context.socket(zmq.SUB)
    sub_socket.setsockopt(zmq.LINGER, 0)
    sub_socket.setsockopt(zmq.RCVTIMEO, 10000)
    sub_socket.connect(xpub_url)
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    start_time = time.time()
    while True:
        try:
            msg = sub_socket.recv_string()
            print(f"Received: {msg}")
            start_time = time.time()
        except KeyboardInterrupt:
            print("Interrupted by user. Exiting...")
            break
        except zmq.Again:
            elapsed_time = time.time() - start_time
            if elapsed_time > 60000:  # in seconds
                break
            print(f"No message received in {elapsed_time:.2f} seconds")
    sub_socket.close()


def event_monitor(pub_socket: zmq.Socket) -> None:
    monitor = pub_socket.get_monitor_socket()
    while monitor.poll():
        evt: Dict[str, Any] = {}
        mon_evt = recv_monitor_message(monitor)
        evt.update(mon_evt)
        print(evt)
        if evt["event"] == zmq.EVENT_MONITOR_STOPPED or evt["event"] == zmq.EVENT_HANDSHAKE_SUCCEEDED:
            break
    monitor.close()


def zmq_pub_test():
    context = zmq.Context()
    pub_socket = context.socket(zmq.PUB)
    pub_socket.setsockopt(zmq.XPUB_VERBOSE, 1)
    pub_socket.setsockopt(zmq.LINGER, 0)
    pub_socket.connect(xsub_url)
    event_monitor(pub_socket)
    zmq_req_test(context)
    for i in range(1, 11):
        pub_socket.send_string(str(i))
    pub_socket.close()


def zmq_router_dealer_test():
    context = zmq.Context()
    router_socket = context.socket(zmq.ROUTER)
    router_socket.bind(router_url)
    dealer_socket = context.socket(zmq.DEALER)
    dealer_socket.bind(dealer_url)
    try:
        # Poll sockets for events
        poller: zmq.Poller = zmq.Poller()
        poller.register(router_socket, zmq.POLLIN)
        poller.register(dealer_socket, zmq.POLLIN)

        print("Running...")
        # Receive msgs, forward and process
        start_time = time.time()
        last_time = start_time
        while True:
            events = dict(poller.poll(500))
            since_last_time = time.time() - last_time
            if since_last_time > 60:  # in seconds
                elapsed_time = time.time() - start_time
                print(f"Elapsed time: {elapsed_time:.2f} seconds")
                last_time = time.time()

            if router_socket in events:
                message = router_socket.recv_multipart()
                print("BROKER", f"subscription message: {message[0]}")
                dealer_socket.send_multipart(message)

            if dealer_socket in events:
                message = dealer_socket.recv_multipart()
                print("BROKER", f"publishing message: {message[0]}")
                router_socket.send_multipart(message)

    except Exception as e:
        print("BROKER", f"thread encountered an error: {e}")
    finally:
        print("BROKER", "thread ended")
    return


def zmq_req_test(context: zmq.Context = None):
    if context is None:
        context = zmq.Context()
    req_socket = context.socket(zmq.REQ)
    req_socket.connect(router_url)
    try:
        req_socket.send_string("Request ")
        message = req_socket.recv_string()
        print(f"Received: {message}")
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    finally:
        req_socket.close()


def zmq_rep_test():
    context = zmq.Context()
    rep_socket = context.socket(zmq.REP)
    rep_socket.connect(dealer_url)
    try:
        while True:
            message = rep_socket.recv_string()
            print(f"Received: {message}")
            rep_socket.send_string("Acknowledged: " + message)
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    finally:
        rep_socket.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "pub":
            zmq_pub_test()
        elif sys.argv[1] == "sub":
            zmq_sub_test()
        elif sys.argv[1] == "router":
            zmq_router_dealer_test()
        elif sys.argv[1] == "req":
            zmq_req_test()
        elif sys.argv[1] == "rep":
            zmq_rep_test()
        else:
            print("Invalid argument. Please use 'pub', 'sub' 'router', 'req', 'rep'")
    else:
        print("Please provide an argument. Please use 'pub', 'sub' 'router', 'req', 'rep'")
