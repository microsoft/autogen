from typing import Awaitable, Callable

from ..core._agent import Agent
from ..core._agent_id import AgentId
from ..core._agent_type import AgentType


async def get_impl(
    *,
    id_or_type: AgentId | AgentType | str,
    key: str,
    lazy: bool,
    instance_getter: Callable[[AgentId], Awaitable[Agent]],
) -> AgentId:
    if isinstance(id_or_type, AgentId):
        if not lazy:
            await instance_getter(id_or_type)

        return id_or_type

    type_str = id_or_type if isinstance(id_or_type, str) else id_or_type.type
    id = AgentId(type_str, key)
    if not lazy:
        await instance_getter(id)

    return id
