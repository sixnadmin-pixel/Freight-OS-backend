from typing import Protocol
from modules.liners.liner_types import LinerNew


class ILinersModule(Protocol):
    async def add_liner(self, payload: LinerNew) -> dict: ...
    async def read_all_liners(self) -> list[dict]: ...
