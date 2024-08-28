# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
from abc import ABC, abstractmethod
from typing import List

from .Actor import Actor
from .ActorConnector import ActorConnector
from .proto.CAP_pb2 import ActorInfo


class IRuntime(ABC):
    @abstractmethod
    def register(self, actor: Actor):
        pass

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def find_by_topic(self, topic: str) -> ActorConnector:
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> ActorConnector:
        pass

    @abstractmethod
    def find_termination(self) -> ActorConnector:
        pass

    @abstractmethod
    def find_by_name_regex(self, name_regex) -> List[ActorInfo]:
        pass
