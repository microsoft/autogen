# metrics - agent_frequency, execution_count, tool_count,

from .datamodel import Message


class Profiler:
    """
    Profiler class to profile agent task runs and compute metrics
    for performance evaluation.
    """

    def __init__(self):
        self.metrics = []

    def profile(self, agent_message: Message):
        """
        Profile the agent task run and compute metrics.

        :param agent: The agent instance that ran the task.
        :param task: The task instance that was run.
        """
        pass
