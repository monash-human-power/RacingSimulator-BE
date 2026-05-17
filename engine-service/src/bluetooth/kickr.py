"""
bluetooth/kickr.py

FTMS Indoor Bike Service — GATT UUIDs, characteristic parsers,
and Control Point command builders.

Only the Fitness Machine Service (0x1826) is used. No CPS (0x1818)
or Wahoo proprietary characteristics.

References:
  - FTMS spec v1.0: https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/
  - BT Assigned Numbers: https://www.bluetooth.com/specifications/assigned-numbers/
"""

import struct
from typing import Optional

from .models import (
    IndoorBikeData,
    IndoorBikeDataFlags,
    FTMSControlResponse,
    FTMSStatusCode,
)


# ---------------------------------------------------------------------------
# GATT UUIDs — FTMS only
# ---------------------------------------------------------------------------

class ServiceUUID:
    FITNESS_MACHINE = "00001826-0000-1000-8000-00805f9b34fb"


class CharacteristicUUID:
    FTMS_FEATURE       = "00002acc-0000-1000-8000-00805f9b34fb"  # read
    INDOOR_BIKE_DATA   = "00002ad2-0000-1000-8000-00805f9b34fb"  # notify
    FTMS_STATUS        = "00002ada-0000-1000-8000-00805f9b34fb"  # notify
    FTMS_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"  # write + indicate


# ---------------------------------------------------------------------------
# FTMS Control Point op-codes  (FTMS spec §4.16.1)
# ---------------------------------------------------------------------------

class FTMSOpCode:
    REQUEST_CONTROL          = 0x00
    RESET                    = 0x01
    SET_TARGET_RESISTANCE    = 0x04  # level mode
    SET_TARGET_POWER         = 0x05  # ERG mode
    START_RESUME             = 0x07
    STOP_PAUSE               = 0x08
    SET_INDOOR_BIKE_SIMULATION = 0x11  # grade / wind / Crr / CdA
    RESPONSE_CODE            = 0x80


# ---------------------------------------------------------------------------
# Device name prefixes used for BLE scan filtering
# ---------------------------------------------------------------------------

KICKR_NAME_PREFIXES = ("KICKR", "Wahoo", "WAHOO")


# ---------------------------------------------------------------------------
# Indoor Bike Data parser  (0x2AD2)
# ---------------------------------------------------------------------------

def parse_indoor_bike_data(data: bytes) -> IndoorBikeData:
    """
    Parse FTMS Indoor Bike Data notification (characteristic 0x2AD2).

    Byte layout (FTMS spec §4.9, Table 4.25):
      [0-1]  uint16  flags
      [2-3]  uint16  instantaneous speed  (km/h, res 0.01) — if MORE_DATA clear
      [...]  optional fields in flag order

    All speeds converted to m/s on the way out.
    All cadences are stored as float RPM (raw unit is 0.5 rpm).
    """
    if len(data) < 2:
        return IndoorBikeData()

    flags = struct.unpack_from("<H", data, 0)[0]
    result = IndoorBikeData()
    offset = 2

    # Instantaneous speed (km/h × 0.01) — present when MORE_DATA is NOT set
    if not (flags & IndoorBikeDataFlags.MORE_DATA):
        if offset + 2 <= len(data):
            raw = struct.unpack_from("<H", data, offset)[0]
            result.instantaneous_speed_ms = (raw * 0.01) / 3.6
            offset += 2

    if flags & IndoorBikeDataFlags.AVERAGE_SPEED_PRESENT:
        if offset + 2 <= len(data):
            raw = struct.unpack_from("<H", data, offset)[0]
            result.average_speed_ms = (raw * 0.01) / 3.6
            offset += 2

    if flags & IndoorBikeDataFlags.INSTANTANEOUS_CADENCE_PRESENT:
        if offset + 2 <= len(data):
            raw = struct.unpack_from("<H", data, offset)[0]
            result.instantaneous_cadence_rpm = raw * 0.5
            offset += 2

    if flags & IndoorBikeDataFlags.AVERAGE_CADENCE_PRESENT:
        if offset + 2 <= len(data):
            raw = struct.unpack_from("<H", data, offset)[0]
            result.average_cadence_rpm = raw * 0.5
            offset += 2

    if flags & IndoorBikeDataFlags.TOTAL_DISTANCE_PRESENT:
        if offset + 3 <= len(data):
            # uint24 little-endian
            b0, b1, b2 = data[offset], data[offset + 1], data[offset + 2]
            result.total_distance_m = b0 | (b1 << 8) | (b2 << 16)
            offset += 3

    if flags & IndoorBikeDataFlags.RESISTANCE_LEVEL_PRESENT:
        if offset + 2 <= len(data):
            result.resistance_level = struct.unpack_from("<h", data, offset)[0]
            offset += 2

    if flags & IndoorBikeDataFlags.INSTANTANEOUS_POWER_PRESENT:
        if offset + 2 <= len(data):
            result.instantaneous_power_w = struct.unpack_from("<h", data, offset)[0]
            offset += 2

    if flags & IndoorBikeDataFlags.AVERAGE_POWER_PRESENT:
        if offset + 2 <= len(data):
            result.average_power_w = struct.unpack_from("<h", data, offset)[0]
            offset += 2

    if flags & IndoorBikeDataFlags.EXPENDED_ENERGY_PRESENT:
        # total (uint16) + per-hour (uint16) + per-minute (uint8)
        if offset + 5 <= len(data):
            result.total_energy_kj      = struct.unpack_from("<H", data, offset)[0]
            result.energy_per_hour_kj   = struct.unpack_from("<H", data, offset + 2)[0]
            result.energy_per_minute_kj = data[offset + 4]
            offset += 5

    if flags & IndoorBikeDataFlags.HEART_RATE_PRESENT:
        if offset + 1 <= len(data):
            result.heart_rate_bpm = data[offset]
            offset += 1

    if flags & IndoorBikeDataFlags.METABOLIC_EQUIVALENT_PRESENT:
        if offset + 1 <= len(data):
            result.metabolic_equivalent = data[offset] * 0.1
            offset += 1

    if flags & IndoorBikeDataFlags.ELAPSED_TIME_PRESENT:
        if offset + 2 <= len(data):
            result.elapsed_time_s = struct.unpack_from("<H", data, offset)[0]
            offset += 2

    if flags & IndoorBikeDataFlags.REMAINING_TIME_PRESENT:
        if offset + 2 <= len(data):
            result.remaining_time_s = struct.unpack_from("<H", data, offset)[0]
            offset += 2

    return result


# ---------------------------------------------------------------------------
# FTMS Control Point response parser
# ---------------------------------------------------------------------------

def parse_ftms_control_response(data: bytes) -> FTMSControlResponse:
    """
    Parse a Control Point indication (response from trainer).

    Layout:
      [0]  0x80  response op-code
      [1]  uint8 request op-code echoed back
      [2]  uint8 result code
    """
    if len(data) < 3 or data[0] != FTMSOpCode.RESPONSE_CODE:
        return FTMSControlResponse(raw=bytes(data))

    try:
        status = FTMSStatusCode(data[2])
    except ValueError:
        status = FTMSStatusCode.OPERATION_FAILED

    return FTMSControlResponse(
        request_op_code=data[1],
        status=status,
        raw=bytes(data),
    )


# ---------------------------------------------------------------------------
# Control Point command builders
# ---------------------------------------------------------------------------

def cmd_request_control() -> bytes:
    """Must be sent before any other control command."""
    return bytes([FTMSOpCode.REQUEST_CONTROL])


def cmd_reset() -> bytes:
    return bytes([FTMSOpCode.RESET])


def cmd_start_resume() -> bytes:
    return bytes([FTMSOpCode.START_RESUME])


def cmd_stop() -> bytes:
    return bytes([FTMSOpCode.STOP_PAUSE, 0x01])


def cmd_set_target_power(watts: int) -> bytes:
    """
    ERG mode: hold a fixed power output.
    Clamped to [0, 4000] W. Resolution: 1 W (signed int16).
    """
    watts = max(0, min(4000, int(watts)))
    return struct.pack("<Bh", FTMSOpCode.SET_TARGET_POWER, watts)


def cmd_set_target_resistance(level: int) -> bytes:
    """
    Level / resistance mode.
    level: unitless signed int16; valid range depends on trainer capability.
    """
    level = int(level)
    return struct.pack("<Bh", FTMSOpCode.SET_TARGET_RESISTANCE, level)


def cmd_set_simulation(
    wind_speed_ms: float = 0.0,
    grade_pct: float = 0.0,
    crr: float = 0.004,
    cda: float = 0.51,
) -> bytes:
    """
    Simulation mode: send road conditions so the trainer adjusts resistance.

    wind_speed_ms : headwind (+) / tailwind (-), m/s, resolution 0.001 m/s  → int16
    grade_pct     : road gradient %, resolution 0.01 %                       → int16
    crr           : rolling resistance coefficient, resolution 0.0001        → uint8
    cda           : drag area m², resolution 0.01 m²                        → uint8
    """
    wind_raw  = int(wind_speed_ms * 1000)
    grade_raw = int(grade_pct * 100)
    crr_raw   = max(0, min(255, int(crr * 10000)))
    cda_raw   = max(0, min(255, int(cda * 100)))

    return struct.pack(
        "<BhhBB",
        FTMSOpCode.SET_INDOOR_BIKE_SIMULATION,
        wind_raw,
        grade_raw,
        crr_raw,
        cda_raw,
    )


# ---------------------------------------------------------------------------
# Scan helper
# ---------------------------------------------------------------------------

def is_kickr(device_name: Optional[str]) -> bool:
    """True if the advertised device name matches a known KICKR prefix."""
    if not device_name:
        return False
    return any(device_name.startswith(p) for p in KICKR_NAME_PREFIXES)
