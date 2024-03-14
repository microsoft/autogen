from autogencap.ag_adapter.CAP2AG import CAP2AG


class CAPPair:
    def __init__(self, network, first, second):
        self._network = network
        self._first_ag_agent = first
        self._second_ag_agent = second
        self._first_adptr = None
        self._second_adptr = None

    def initiate_chat(self, message: str):
        self._first_adptr = CAP2AG(
            ag_agent=self._first_ag_agent,
            the_other_name=self._second_ag_agent.name,
            init_chat=True,
            self_recursive=True,
        )
        self._second_adptr = CAP2AG(
            ag_agent=self._second_ag_agent,
            the_other_name=self._first_ag_agent.name,
            init_chat=False,
            self_recursive=True,
        )
        self._network.register(self._first_adptr)
        self._network.register(self._second_adptr)
        self._network.connect()

        # Send a message to the user_proxy
        agent_connection = self._network.lookup_actor(self._first_ag_agent.name)
        agent_connection.send_txt_msg(message)

    def running(self):
        return self._first_adptr.run and self._second_adptr.run
