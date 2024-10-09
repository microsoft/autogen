# metrics - agent_frequency, execution_count, tool_count,

from typing import Dict, List, Optional

from .datamodel import Message, MessageMeta


class Profiler:
    """
    Profiler class to profile agent task runs and compute metrics
    for performance evaluation.
    """

    def __init__(self):
        self.metrics: List[Dict] = []

    def _is_code(self, message: Message) -> bool:
        """
        Check if the message contains code.

        :param message: The message instance to check.
        :return: True if the message contains code, False otherwise.
        """
        content = message.get("message").get("content").lower()
        return "```" in content

    def _is_tool(self, message: Message) -> bool:
        """
        Check if the message uses a tool.

        :param message: The message instance to check.
        :return: True if the message uses a tool, False otherwise.
        """
        content = message.get("message").get("content").lower()
        return "from skills import" in content

    def _is_code_execution(self, message: Message) -> bool:
        """
        Check if the message indicates code execution.

        :param message: The message instance to check.
        :return: dict with is_code and status keys.
        """
        content = message.get("message").get("content").lower()
        if "exitcode:" in content:
            status = "exitcode: 0" in content
            return {"is_code": True, "status": status}
        else:
            return {"is_code": False, "status": False}

    def _is_terminate(self, message: Message) -> bool:
        """
        Check if the message indicates termination.

        :param message: The message instance to check.
        :return: True if the message indicates termination, False otherwise.
        """
        content = message.get("message").get("content").lower()
        return "terminate" in content

    def profile(self, agent_message: Message):
        """
        Profile the agent task run and compute metrics.

        :param agent: The agent instance that ran the task.
        :param task: The task instance that was run.
        """
        meta = MessageMeta(**agent_message.meta)
        print(meta.log)
        usage = meta.usage
        messages = meta.messages
        profile = []
        bar = []
        stats = {}
        total_code_executed = 0
        success_code_executed = 0
        agents = []
        for message in messages:
            agent = message.get("sender")
            is_code = self._is_code(message)
            is_tool = self._is_tool(message)
            is_code_execution = self._is_code_execution(message)
            total_code_executed += is_code_execution["is_code"]
            success_code_executed += 1 if is_code_execution["status"] else 0

            row = {
                "agent": agent,
                "tool_call": is_code,
                "code_execution": is_code_execution,
                "terminate": self._is_terminate(message),
            }
            bar_row = {
                "agent": agent,
                "tool_call": "tool call" if is_tool else "no tool call",
                "code_execution": (
                    "success"
                    if is_code_execution["status"]
                    else "failure" if is_code_execution["is_code"] else "no code"
                ),
                "message": 1,
            }
            profile.append(row)
            bar.append(bar_row)
            agents.append(agent)
        code_success_rate = (success_code_executed / total_code_executed if total_code_executed > 0 else 0) * 100
        stats["code_success_rate"] = code_success_rate
        stats["total_code_executed"] = total_code_executed
        return {"profile": profile, "bar": bar, "stats": stats, "agents": set(agents), "usage": usage}
