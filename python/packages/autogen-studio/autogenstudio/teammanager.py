
import time
from .provider import Provider
from .datamodel import TeamConfig, TeamResult


class TeamManager(object):
    def __init__(self) -> None:
        self.provider = Provider()

    async def run(self, task: str, team_config: TeamConfig | dict) -> None:
        start_time = time.time()
        if isinstance(team_config, dict):
            team_config = TeamConfig(**team_config)

        team = self.provider.load_team(team_config)
        result = await team.run(task=task)
        result = TeamResult(task_result=result, usage="",
                            duration=time.time() - start_time)
        return result
