import asyncio
import logging
import time
from typing import Optional

from bluetooth import IndoorBikeData, TrainerState
from engine.models import EngineOutput
from websocket import ConnectionManager

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self) -> None:
        self._state: Optional[TrainerState] = None
        self.websocket_manager: Optional[ConnectionManager] = None
        self._last_broadcast = 0.0
        self._min_broadcast_interval = 0.2  # ~5 Hz cap

    def on_bike_data(self, bike: IndoorBikeData) -> None:
        if self._state is None:
            self._state = TrainerState(bike=bike)
        else:
            self._state.bike = bike
        self._tick()

    def _tick(self) -> None:
        if not self._state:
            return

        now = time.monotonic()
        if now - self._last_broadcast < self._min_broadcast_interval:
            return
        self._last_broadcast = now

        bike = self._state.bike
        output = EngineOutput(
            speed_ms=bike.instantaneous_speed_ms or 0.0,
            power_w=bike.instantaneous_power_w or 0,
            cadence_rpm=bike.instantaneous_cadence_rpm,
            heart_rate_bpm=bike.heart_rate_bpm,
            resistance_level=bike.resistance_level,
            average_power_w=bike.average_power_w,
            total_distance_m=bike.total_distance_m,
            connected=self._state.connected,
            device_name=self._state.device_name,
        )

        if self.websocket_manager:
            asyncio.create_task(self.websocket_manager.broadcast(output.to_message()))

    @property
    def state(self) -> Optional[TrainerState]:
        return self._state
