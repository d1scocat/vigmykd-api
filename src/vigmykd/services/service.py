from abc import ABC, abstractmethod


class Service(ABC):
    @abstractmethod
    async def init(self):
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        pass
