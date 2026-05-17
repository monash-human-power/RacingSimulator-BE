"""bluetooth/manager.py"""

import asyncio
import logging
from typing import Optional, Callable

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .kickr import (
    CharacteristicUUID, is_kickr,
    parse_indoor_bike_data, parse_ftms_control_response,
    cmd_request_control, cmd_start_resume,
    cmd_set_target_power, cmd_set_target_resistance, cmd_set_simulation,
)
from .models import TrainerState, FTMSControlResponse, FTMSStatusCode, IndoorBikeData

logger = logging.getLogger(__name__)

_INDICATION_TIMEOUT_S = 5.0
_SCAN_TIMEOUT_S = 10.0
_RECONNECT_DELAY_S = 3.0
_MAX_RECONNECT_TRIES = 5


class BLEManager:
    def __init__(self) -> None:
        self._client: Optional[BleakClient] = None
        self._device: Optional[BLEDevice] = None
        self._state = TrainerState()
        self._running = False
        self._connect_lock = asyncio.Lock()
        self._control_lock = asyncio.Lock()
        self._pending_indication: Optional[asyncio.Future[FTMSControlResponse]] = None
        self._on_bike_data_callback: Optional[callable[[TrainerState], None]] = None

    # -- Lifecycle --

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._state.connected = False

    # -- Connection --

    async def connect(self, address: Optional[str] = None) -> bool:
        async with self._connect_lock:
            if address:
                self._device = await BleakScanner.find_device_by_address(
                    address, timeout=_SCAN_TIMEOUT_S
                )
            else:
                devices = await BleakScanner.discover(timeout=_SCAN_TIMEOUT_S)
                self._device = next((d for d in devices if is_kickr(d.name)), None)

            if not self._device:
                logger.warning("No device found")
                return False

            return await self._connect(self._device)

    async def _connect(self, device: BLEDevice) -> bool:
        try:
            self._client = BleakClient(device, disconnected_callback=self._on_disconnected)
            await self._client.connect()

            await self._client.start_notify(CharacteristicUUID.INDOOR_BIKE_DATA, self._on_bike_data)
            await self._client.start_notify(CharacteristicUUID.FTMS_CONTROL_POINT, self._on_control_indication)
            await self._client.write_gatt_char(CharacteristicUUID.FTMS_CONTROL_POINT, cmd_request_control(), response=True)
            await self._client.write_gatt_char(CharacteristicUUID.FTMS_CONTROL_POINT, cmd_start_resume(), response=True)

            self._state.connected = True
            self._state.device_address = device.address
            self._state.device_name = device.name
            asyncio.create_task(self._watchdog(), name="ble-watchdog")
            logger.info("Connected to %s", device.name)
            return True

        except BleakError as exc:
            logger.error("Connection failed: %s", exc)
            self._client = None
            return False

    def _on_disconnected(self, _: BleakClient) -> None:
        self._state.connected = False
        logger.warning("Disconnected")

    # -- Commands --

    async def set_target_power(self, watts: int) -> FTMSControlResponse:
        resp = await self._write_control_point(cmd_set_target_power(watts))
        if resp.ok:
            self._state.target_power_w = watts
        return resp

    async def set_target_resistance(self, level: int) -> FTMSControlResponse:
        resp = await self._write_control_point(cmd_set_target_resistance(level))
        if resp.ok:
            self._state.target_resistance_level = level
        return resp

    async def set_simulation(self, grade_pct: float, wind_speed_ms: float = 0.0, crr: float = 0.004, cda: float = 0.51) -> FTMSControlResponse:
        resp = await self._write_control_point(cmd_set_simulation(wind_speed_ms, grade_pct, crr, cda))
        if resp.ok:
            self._state.simulation_grade_pct = grade_pct
        return resp

    # -- State --

    @property
    def is_connected(self) -> bool:
        return bool(self._client and self._client.is_connected)

    @property
    def state(self) -> TrainerState:
        return self._state

    def bike_data_as_dict(self) -> dict:
        from dataclasses import asdict
        return {k: v for k, v in asdict(self._state.bike).items() if v is not None}

    # -- Notification handlers --

    def _on_bike_data(self, _: object, data: bytearray) -> None:
        bike = parse_indoor_bike_data(bytes(data))
        self._state.bike = bike

        if self._on_bike_data_callback:
            self._on_bike_data_callback(bike)

    def set_bike_data_callback(self, callback: Callable[[IndoorBikeData], None]) -> None:
        self._on_bike_data_callback = callback
    
    def _on_control_indication(self, _: object, data: bytearray) -> None:
        resp = parse_ftms_control_response(bytes(data))
        if self._pending_indication and not self._pending_indication.done():
            self._pending_indication.set_result(resp)

    # -- Control point --

    async def _write_control_point(self, payload: bytes) -> FTMSControlResponse:
        if not self.is_connected:
            return FTMSControlResponse(status=FTMSStatusCode.OPERATION_FAILED)

        async with self._control_lock:
            self._pending_indication = asyncio.get_running_loop().create_future()
            try:
                await self._client.write_gatt_char(CharacteristicUUID.FTMS_CONTROL_POINT, payload, response=True)
                return await asyncio.wait_for(self._pending_indication, timeout=_INDICATION_TIMEOUT_S)
            except (asyncio.TimeoutError, BleakError) as exc:
                logger.error("Control point error: %s", exc)
                return FTMSControlResponse(status=FTMSStatusCode.OPERATION_FAILED)
            finally:
                self._pending_indication = None

    # -- Watchdog --

    async def _watchdog(self) -> None:
        tries = 0
        while self._running:
            await asyncio.sleep(_RECONNECT_DELAY_S)
            if self.is_connected:
                tries = 0
            elif tries < _MAX_RECONNECT_TRIES and self._device:
                tries += 1
                logger.info("Reconnect attempt %d/%d", tries, _MAX_RECONNECT_TRIES)
                async with self._connect_lock:
                    await self._connect(self._device)
            else:
                logger.error("Giving up after %d attempts", tries)
                break