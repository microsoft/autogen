
import time
from .provider import Provider
from .datamodel import TeamConfig


class WorkflowManager(object):
    def __init__(self, team_config: TeamConfig | dict) -> None:
        self.provider = Provider()
        if isinstance(team_config, dict):
            team_config = TeamConfig(**team_config)
        self.team = self.provider.load_team(team_config)

    async def run(self, task: str) -> None:
        start_time = time.time()
        result = await self.team.run(task=task)
        response = {
            "messages": result.messages,
            "usage": "",
            "duration": time.time() - start_time,
        }
        return response
