"""
bluetooth/models.py

BLE data structures for the FTMS Indoor Bike Data characteristic (0x2AD2).
All values use SI units unless noted.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
import time


# ---------------------------------------------------------------------------
# FTMS Indoor Bike Data flags  (0x2AD2, first two bytes)
# Bluetooth FTMS spec §4.9.1 Table 4.25
# ---------------------------------------------------------------------------

class IndoorBikeDataFlags(IntEnum):
    MORE_DATA                        = 0x0001  # if set, instantaneous speed is NOT present
    AVERAGE_SPEED_PRESENT            = 0x0002
    INSTANTANEOUS_CADENCE_PRESENT    = 0x0004
    AVERAGE_CADENCE_PRESENT          = 0x0008
    TOTAL_DISTANCE_PRESENT           = 0x0010
    RESISTANCE_LEVEL_PRESENT         = 0x0020
    INSTANTANEOUS_POWER_PRESENT      = 0x0040
    AVERAGE_POWER_PRESENT            = 0x0080
    EXPENDED_ENERGY_PRESENT          = 0x0100
    HEART_RATE_PRESENT               = 0x0200
    METABOLIC_EQUIVALENT_PRESENT     = 0x0400
    ELAPSED_TIME_PRESENT             = 0x0800
    REMAINING_TIME_PRESENT           = 0x1000


# ---------------------------------------------------------------------------
# FTMS status / control response codes
# ---------------------------------------------------------------------------

class FTMSStatusCode(IntEnum):
    """Fitness Machine Control Point result codes (FTMS spec §4.16.2)."""
    SUCCESS                 = 0x01
    OP_CODE_NOT_SUPPORTED   = 0x02
    INVALID_PARAMETER       = 0x03
    OPERATION_FAILED        = 0x04
    CONTROL_NOT_PERMITTED   = 0x05


# ---------------------------------------------------------------------------
# Parsed data dataclasses
# ---------------------------------------------------------------------------

@dataclass
class IndoorBikeData:
    """
    Parsed from FTMS Indoor Bike Data characteristic (0x2AD2).
    The KICKR emits this notification every ~250 ms while in use.

    All optional fields are None when the corresponding flag bit is not set.
    """
    timestamp: float = field(default_factory=time.monotonic)

    # Speed — present when MORE_DATA flag is NOT set (i.e. the common case)
    # Raw unit from spec is km/h with 0.01 resolution; stored here in m/s.
    instantaneous_speed_ms: Optional[float] = None
    average_speed_ms: Optional[float] = None

    # Cadence — resolution 0.5 rpm, stored as float rpm
    instantaneous_cadence_rpm: Optional[float] = None
    average_cadence_rpm: Optional[float] = None

    # Distance — unit: metres (uint24)
    total_distance_m: Optional[int] = None

    # Resistance / power
    resistance_level: Optional[int] = None           # unitless, signed 16-bit
    instantaneous_power_w: Optional[int] = None      # watts, signed 16-bit
    average_power_w: Optional[int] = None

    # Energy
    total_energy_kj: Optional[int] = None
    energy_per_hour_kj: Optional[int] = None
    energy_per_minute_kj: Optional[int] = None

    # Physiological
    heart_rate_bpm: Optional[int] = None             # uint8
    metabolic_equivalent: Optional[float] = None     # MET × 0.1

    # Session time
    elapsed_time_s: Optional[int] = None
    remaining_time_s: Optional[int] = None


@dataclass
class TrainerState:
    """
    Composite snapshot handed to the physics engine each tick.
    """
    timestamp: float = field(default_factory=time.monotonic)
    bike: IndoorBikeData = field(default_factory=IndoorBikeData)

    # Last control-point target sent to the trainer
    target_power_w: Optional[int] = None
    target_resistance_level: Optional[int] = None
    simulation_grade_pct: Optional[float] = None

    # Connection health
    connected: bool = False
    device_address: Optional[str] = None
    device_name: Optional[str] = None


@dataclass
class FTMSControlResponse:
    """Response received via Control Point indication after a write."""
    request_op_code: int = 0x00
    status: FTMSStatusCode = FTMSStatusCode.SUCCESS
    raw: bytes = field(default_factory=bytes)

    @property
    def ok(self) -> bool:
        return self.status == FTMSStatusCode.SUCCESS
