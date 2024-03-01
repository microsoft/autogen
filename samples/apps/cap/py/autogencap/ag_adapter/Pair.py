from autogencap.ag_adapter.CAP2AG import CAP2AG
import time


class Pair:
    def __init__(self, network, first, second):
        self._network = network
        self._first = first
        self._second = second
        self._user_proxy_adptr = None
        self._assistant_adptr = None

    def initiate_chat(self, message: str):
        self._user_proxy_adptr = CAP2AG(
            ag_agent=self._first, the_other_name="assistant", init_chat=True, self_recursive=True
        )

        self._assistant_adptr = CAP2AG(
            ag_agent=self._second, the_other_name="user_proxy", init_chat=False, self_recursive=True
        )
        self._network.register(self._user_proxy_adptr)
        self._network.register(self._assistant_adptr)
        self._network.connect()

        # Send a message to the user_proxy
        user_proxy_connection = self._network.lookup_actor("user_proxy")
        user_proxy_connection.send_txt_msg("Plot a chart of MSFT daily closing prices for last 1 Month.")

    def running(self):
        return self._user_proxy_adptr.run and self._assistant_adptr.run
