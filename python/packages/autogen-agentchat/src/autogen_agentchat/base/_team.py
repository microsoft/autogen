from typing import Protocol

from ._task import TaskRunner


class Team(TaskRunner, Protocol):
    pass
