import asyncio
import logging
import time

from typing import Dict, List, Tuple, Union

from vigmykd.settings import config

from vigmykd.services import Service


class ServiceHandler:
    logger = logging.getLogger("services.service_handler")

    services: List[Service]
    statuses: Dict[Service, Tuple[float, bool]]

    def __init__(
        self,
        frequency: Union[int, float],
        services: List[Service] | None = None,
    ):
        self.services = services if services else []
        self.statuses = {}
        self.healthcheck_period = frequency

        self._lock = asyncio.Lock()

        self._check_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()
        self._pause_event = asyncio.Event()

        self._pause_event.set()

    async def init_services(self):
        if not self.services:
            return

        results = await asyncio.gather(
            *[service.init() for service in self.services],
            return_exceptions=True
        )

        for service, result in zip(self.services, results):
            if isinstance(result, Exception):
                self.logger.error(f"❌ Could not initialize service {service}: {result}")
                raise result

    async def register_service(self, service: Service):
        async with self._lock:
            if service in self.services:
                self.logger.warning(f"⚠️ Cannot re-register a service {service}")
                return
            self.services.append(service)
            self.logger.info(f"▶️ Registered service {service}")

    async def unregister_service(self, service: Service) -> bool:
        async with self._lock:
            if service not in self.services:
                return False

            self.services.remove(service)
            self.statuses.pop(service, None)
            self.logger.info(f"♻️ Unregistered service {service}")
            return True

    async def force_recheck(self):
        current = time.time()
        # cannot modify dict amidst iteration
        new_statuses: Dict[Service, Tuple[float, bool]] = {}

        # run all healthchecks first
        async with self._lock:
            services_snapshot = list(self.services)

        tasks = [
            # technically all implementations already have their own timeouts
            # but just in case, i have another failsafe
            asyncio.wait_for(service.is_healthy(), timeout=config.GLOBAL_HEALTHCHECK_TIMEOUT)
            for service in services_snapshot
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for service, result in zip(services_snapshot, results):
            if isinstance(result, Exception):
                self.logger.error(f"❌ Exception caught in healthcheck for {service=}: "
                                  f"{result} | {result.__class__.__name__}")
                new_statuses[service] = (current, False)
            elif isinstance(result, bool):  # aka "else" but for typecheckers
                new_statuses[service] = (current, result)
            else:
                self.logger.warning(f"⚠️ Unexpected healthcheck result for {service=}: "
                                    f"{result} ({type(result)=})")
                new_statuses[service] = (current, False)

        async with self._lock:
            self.statuses = new_statuses

    async def is_healthy(self, service: Service, max_age: float = 120) -> bool:
        async with self._lock:
            last_check, healthy = self.statuses.get(service, (0, False))
            if time.time() - last_check > max_age:
                self.logger.warning(f"⚠️ Stale health data for {service}")
                return False
            return healthy

    async def start(self):
        if self._check_task and not self._check_task.done():
            self.logger.warning("⚠️ Healthcheck task already running")
            return

        self._shutdown_event.clear()
        self._pause_event.set()  # unpause

        self._check_task = asyncio.create_task(self._checker(), name="healthcheck-loop")

        self.logger.info("▶️ Started healthcheck task")

    async def stop(self):
        if not self._check_task or self._check_task.done():
            self.logger.warning("⚠️ Cannot stop a task that is not running (healthcheck task)")
            return

        self.logger.info("🛑 Stopping healthcheck task...")
        self._shutdown_event.set()

        try:
            await self._check_task
        except asyncio.CancelledError:
            pass
        finally:
            self._check_task = None
            self.logger.info("🛑 Stopped healthcheck task")

    async def pause(self):
        self._pause_event.clear()
        self.logger.info("⏸️ Healthcheck task paused")

    async def resume(self):
        self._pause_event.set()
        self.logger.info("⏯️ Healthcheck task resumed")

    async def _checker(self):
        try:
            while not self._shutdown_event.is_set():
                await asyncio.wait(
                    [
                        asyncio.create_task(self._pause_event.wait()),
                        asyncio.create_task(self._shutdown_event.wait())
                    ],
                    return_when=asyncio.FIRST_COMPLETED
                )

                if self._shutdown_event.is_set():
                    break

                await self.force_recheck()

                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.healthcheck_period
                    )
                    break
                except asyncio.TimeoutError:  # weird ass flow lmao i hate pythno
                    pass
        except asyncio.CancelledError:
            self.logger.info("🛑 Healthcheck task cancelled")
            raise
        except Exception as ex:
            self.logger.error(f"❌ UNHANDLED EXCEPTION (healthcheck task): {ex}", exc_info=True)
