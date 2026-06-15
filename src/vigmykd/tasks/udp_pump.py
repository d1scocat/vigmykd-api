import asyncio
import logging

from vigmykd.packets.communication import UDPClient


class UDPPumper:
    logger = logging.getLogger("tasks.udp_pump")

    def __init__(
        self,
        udp_client: UDPClient
    ):
        self.udp_client = udp_client

        self._shutdown_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def start(self):
        self._shutdown_event.clear()
        self._task = asyncio.create_task(self._pump_loop())
        self.logger.info("▶️ Started UDP pump loop")

    async def stop(self):
        if self._task and not self._task.done():
            self._shutdown_event.set()
            await self._task
            self.logger.info("🛑 UDP pump loop stopped")

    async def _pump_loop(self):
        while not self._shutdown_event.is_set():
            try:
                self.udp_client.pump()
            except Exception as ex:
                self.logger.warning(f"⚠️ UDP pump loop failed once: {ex}", exc_info=True)

            await asyncio.sleep(1 / 60)
