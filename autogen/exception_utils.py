class AgentNameConflict(Exception):
    def __init__(self, msg="Found multiple agents with the same name.", *args, **kwargs):
        super().__init__(msg, *args, **kwargs)
